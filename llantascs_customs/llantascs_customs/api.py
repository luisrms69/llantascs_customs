import frappe
import json
from frappe.utils import now
from frappe.utils import flt, getdate

# Variables globales llantas Customs
estados_comisiones = ["Sin Enviar", "Enviado", "Pagada"]
# fix: esto no puede quedar asi, me esta ocasionando muchos problemas, necesito estandarizar
# fix: corregido el 2 de marzo 2025, se puede elimianr
# cogs_accounts = ['501-005-001 - COSTO DE VENTA LLANTAS   - LLCS', '501-005-002 - COSTO DE VENTA RINES  - LLCS', '501-005-003 - OTROS COSTO DE VENTA  - LLCS']


def get_cogs_account():
    cogs_accounts = frappe.db.get_list(
        "Account", filters={"account_type": "Cost of Goods Sold"}, pluck="name"
    )

    return cogs_accounts


def get_sales_invoices_id(sucursal, fecha_inicial, fecha_final):
    sales_invoice_list = frappe.db.get_list(
        "Sales Invoice",
        filters={
            "status": "paid",
            "custom_status_comisiones": estados_comisiones[0],
            "posting_date": ["between", [fecha_inicial, fecha_final]],
            "cost_center": sucursal,
        },
        pluck="name",
    )

    return sales_invoice_list


def is_delivered(sales_invoice):
    #  frappe.msgprint("entra a is delivered")
    #  frappe.msgprint(str(sales_invoice))
    if sales_invoice.update_stock == 0:
        for partida in sales_invoice.items:
            if partida.item_group == "Servicios":
                return 1
            if (partida.delivered_qty + partida.delivered_by_supplier) < partida.qty:
                return 0

    return 1


def get_costo_ventas_si(sales_invoice: str) -> float:
    """
    Costo de ventas para Sales Invoice sumando componentes, para cubrir MIXTOS:
      - Servicios         → 0 (no aplica)
      - Dropshipping      → PO Item.base_rate * delivered_by_supplier (por renglón DS)
      - Delivery Notes    → DN Item.base_net_rate * qty (por renglón con DN)
      - Update Stock=1    → SUM(stock_value_difference) del voucher (si existen SLE)
      - Vía Purchase Order→ PO Item.base_rate * qty (solo si no hubo DN/DS/SLE para esos renglones)
    Sin fallbacks a 0: cuando no aplica, aporta 0; si aplica y no hay datos, el componente no suma.
    """
    si = frappe.get_doc("Sales Invoice", sales_invoice)

    # 1) Base: si todos los renglones son servicios, el costo es 0 (no aplica inventario)
    if _is_service_only(si.name):
        return 0.0

    total = 0.0

    # 2) Dropshipping (por renglón con delivered_by_supplier > 0)
    total += _cost_from_po_for_dropship(si.name)

    # 3) Delivery Notes (por renglón con DN)
    total += _cost_from_dn_items(si.name)

    # 4) Update Stock = 1 (SLE del voucher) — SOLO si existen SLE para este voucher
    sle = _sle_total_for_si(si.name)
    if sle is not None:  # no usamos "or 0": si no hay SLE, no suma
        total += abs(flt(sle))

    # 5) Vía Purchase Order (renglones sin DN ni DS ni SLE): PO Item.base_rate * qty
    total += _cost_from_po_items(si.name)

    # 6) Fallback ÚTIMO: GL Entry (contable) SOLO si hasta aquí no hubo costo
    if not total:
        total += _cost_from_gl_entries(si.name)

    return flt(total)


def _is_service_only(si_name: str) -> bool:
    rows = frappe.db.sql("""
        SELECT i.is_stock_item
        FROM `tabSales Invoice Item` sii
        JOIN `tabItem` i ON i.name = sii.item_code
        WHERE sii.parent = %s
    """, (si_name,), as_dict=True)
    if not rows:
        # sin renglones: tratamos como no inventario
        return True
    return all(not (r.get("is_stock_item") or 0) for r in rows)


def _cost_from_po_for_dropship(si_name: str) -> float:
    """
    Costo para renglones dropshipping:
    - Detecta DS por el flag delivered_by_supplier en el Sales Order Item (so_detail).
    - Usa tarifa del Purchase Order Item (base_rate) localizado por (sales_order, item_code).
    - Multiplica por la qty facturada del renglón.
    - Excluye renglones que ya tienen Delivery Note (para no duplicar).
    """
    # Tomamos datos del renglón de la SI que nos permiten navegar a SO Item y PO Item
    rows = frappe.db.sql(
        """
        SELECT
            sii.item_code,
            sii.qty,
            sii.sales_order,
            sii.so_detail,
            IFNULL(sii.delivery_note, '') AS dn
        FROM `tabSales Invoice Item` AS sii
        WHERE sii.parent = %s
          AND IFNULL(sii.so_detail, '') != ''
        """,
        (si_name,),
        as_dict=True,
    )
    if not rows:
        return 0.0

    total = 0.0
    for r in rows:
        # Si ya tiene DN, ese renglón se costea por DN y no por DS
        if r.dn:
            continue

        # delivered_by_supplier vive en el Sales Order Item (no en SI Item)
        dbs = frappe.db.get_value("Sales Order Item", r.so_detail, "delivered_by_supplier")
        if not dbs:
            continue  # no es dropship

        # Tomamos la tarifa del PO Item asociado al mismo Sales Order e item_code
        po_rate_rec = frappe.db.sql(
            """
            SELECT base_rate
            FROM `tabPurchase Order Item`
            WHERE sales_order = %s
              AND item_code   = %s
            ORDER BY modified DESC
            LIMIT 1
            """,
            (r.sales_order, r.item_code),
            as_dict=True,
        )
        if po_rate_rec:
            total += flt(po_rate_rec[0].base_rate) * flt(r.qty)

    return total


def _cost_from_dn_items(si_name: str) -> float:
    """
    Costo por renglones con Delivery Note:
    suma DN Item.base_net_rate * qty por cada (delivery_note, item_code) vinculado.
    Si algún renglón no encuentra su DN item, ese renglón no suma.
    """
    rows = frappe.db.sql("""
        SELECT delivery_note, item_code, qty
        FROM `tabSales Invoice Item`
        WHERE parent=%s AND IFNULL(delivery_note,'')!=''
    """, (si_name,), as_dict=True)
    if not rows:
        return 0.0

    total = 0.0
    for r in rows:
        cost_row = frappe.db.sql("""
            SELECT (base_net_rate * %s) AS cost
            FROM `tabDelivery Note Item`
            WHERE parent=%s AND item_code=%s
            ORDER BY idx
            LIMIT 1
        """, (flt(r.qty), r.delivery_note, r.item_code), as_dict=True)
        if cost_row and cost_row[0].get("cost") is not None:
            total += flt(cost_row[0].cost)
    return total


def _sle_total_for_si(si_name: str):
    """
    Devuelve la suma de SLE (stock_value_difference) para el voucher SI si existen filas.
    Si no existen SLE, retorna None (no "0 inventado").
    """
    row = frappe.db.sql("""
        SELECT SUM(stock_value_difference) AS total_cost
        FROM `tabStock Ledger Entry`
        WHERE voucher_type='Sales Invoice' AND voucher_no=%s
    """, (si_name,), as_dict=True)
    # row siempre viene, pero SUM puede ser None si no hay filas; lo respetamos
    return row[0].total_cost if row else None


def _cost_from_po_items(si_name: str) -> float:
    """
    Costo por renglones ligados a Purchase Order (sin DN y sin dropship):
    - Usa tarifa del Purchase Order Item (base_rate) por (sales_order, item_code).
    - Se aplica solo a renglones sin DN y que no sean DS.
    """
    rows = frappe.db.sql(
        """
        SELECT
            sii.item_code,
            sii.qty,
            sii.sales_order,
            sii.so_detail,
            IFNULL(sii.delivery_note, '') AS dn
        FROM `tabSales Invoice Item` AS sii
        WHERE sii.parent = %s
        """,
        (si_name,),
        as_dict=True,
    )
    if not rows:
        return 0.0

    total = 0.0
    for r in rows:
        # Si ya se costea por DN, no entra aquí
        if r.dn:
            continue

        # Si es dropship (flag en SO Item), tampoco entra aquí (ya lo cubre _cost_from_po_for_dropship)
        if r.so_detail:
            dbs = frappe.db.get_value("Sales Order Item", r.so_detail, "delivered_by_supplier")
            if dbs:
                continue

        # Necesitamos tener Sales Order para poder ubicar el PO Item
        if not r.sales_order:
            continue

        po_rate_rec = frappe.db.sql(
            """
            SELECT base_rate
            FROM `tabPurchase Order Item`
            WHERE sales_order = %s
              AND item_code   = %s
            ORDER BY modified DESC
            LIMIT 1
            """,
            (r.sales_order, r.item_code),
            as_dict=True,
        )
        if po_rate_rec:
            total += flt(po_rate_rec[0].base_rate) * flt(r.qty)

    return total


def _cost_from_gl_entries(si_name: str) -> float:
    """
    Fallback contable: suma el impacto en COGS desde GL Entry
    para este Sales Invoice.
    - Usa cuentas con account_type = 'Cost of Goods Sold'
    - Suma (debit - credit) y devuelve valor absoluto
    """
    cogs_accounts = get_cogs_account()  # ya existe en tu archivo
    if not cogs_accounts:
        return 0.0

    row = frappe.db.sql("""
        SELECT SUM(debit - credit) AS cogs
        FROM `tabGL Entry`
        WHERE voucher_type = 'Sales Invoice'
          AND voucher_no   = %s
          AND account      IN %(accs)s
    """, (si_name, {"accs": tuple(cogs_accounts)}), as_dict=True)

    return abs(flt(row[0].cogs)) if row and row[0].cogs is not None else 0.0


def get_costo_ventas_dn(sales_invoice_id: str) -> float:
    # 1) Trae solo las Delivery Notes reales: enviadas y completadas
    dn_names = frappe.get_all(
        "Delivery Note",
        filters={"docstatus": 1, "status": "Completed"},
        pluck="name",
        ignore_permissions=True,
    )

    if not dn_names:
        return 0.0

    # 2) Trae los ítems enlazados a la Sales Invoice y a esas DN
    items = frappe.get_all(
        "Delivery Note Item",
        filters={
            "against_sales_invoice": sales_invoice_id,
            "parent": ["in", dn_names],
        },
        fields=["qty", "grant_commission", "incoming_rate"],
        ignore_permissions=True,
    )

    # 3) Calcula COGS (manejando None con flt)
    cogs = 0.0
    for it in items:
        cogs += (
            flt(it.get("qty"))
            * flt(it.get("grant_commission"))
            * flt(it.get("incoming_rate"))
        )

    return cogs


# def get_costo_ventas_dn(sales_invoice_id):
#     # GL entries for Delivery Note cases

#     cogs = 0
#     dn_items_list = frappe.db.get_list(
#             "Delivery Note Item",
#             filters={'against_sales_invoice' : sales_invoice_id},
#             pluck = 'name',
#             ignore_permissions= True
#         )

#     for dn_item in dn_items_list:
#         variables = frappe.db.get_value('Delivery Note Item', dn_item,['qty','grant_commission','incoming_rate'])

#         cogs += variables[0]*variables[1]*variables[2]

#     return cogs


def actualizar_status_sales_invoice(invoice_id, status):
    frappe.db.set_value(
        "Sales Invoice",
        invoice_id,
        "custom_status_comisiones",
        estados_comisiones[status],
    )


def actualizar_orden_pago_sales_invoice(invoice_id, orden_de_pago):
    frappe.db.set_value(
        "Sales Invoice", invoice_id, "custom_orden_de_pago_comision", orden_de_pago
    )


@frappe.whitelist()
def actualizar_status_orden_pago(orden_pago_id, status):
    status_number = int(status)
    orden_pago = frappe.get_doc("Orden de Pago Comisiones", orden_pago_id)
    orden_pago.db_set(
        {
            "confirmacion_de_pago": estados_comisiones[status_number],
            "fecha_confirmacion_pago": str(now()),
        }
    )
    for invoice in orden_pago.comisiones_incluidas:
        actualizar_status_sales_invoice(invoice.sales_invoice_id, status_number)
        actualizar_orden_pago_sales_invoice(invoice.sales_invoice_id, orden_pago_id)

    return estados_comisiones[2]


@frappe.whitelist()
def get_all_cost_centers():
    """Devuelve todos los Cost Centers activos y no grupo."""
    return frappe.get_all(
        "Cost Center",
        filters={"is_group": 0, "disabled": 0},
        pluck="name"
    )


@frappe.whitelist()
def get_commission_rate():
    commission_rate = frappe.db.get_single_value(
        "Comisiones Settings", "porcentaje_sobre_utilidad"
    )

    return commission_rate


@frappe.whitelist()
def get_sales_invoices(sucursal, fecha_inicial, fecha_final):
    """
    FUENTE ÚNICA DE FILTROS para poblar comisiones desde el servidor.

    Reglas:
      - status = "Paid"
      - posting_date BETWEEN [fecha_inicial, fecha_final]
      - cost_center IN sucursal (acepta list o str)
      - Entregada (para ítems stock). Si la factura es solo de servicios (no-stock), no exige entrega.
      - (Opcional) custom_status_comisiones = "Sin Enviar" si el campo existe.

    Devuelve la lista de Sales Invoice (dicts) ya consistente para que
    tu función de poblado consuma sin recalcular filtros en el cliente.
    """
    import json as _json

    # Normalizar sucursal a lista (acepta list o JSON str)
    if isinstance(sucursal, str):
        try:
            sucursal = _json.loads(sucursal or "[]")
        except Exception:
            sucursal = [sucursal] if sucursal else []
    sucursal = [cc for cc in (sucursal or []) if cc]

    if not fecha_inicial or not fecha_final:
        frappe.throw("Faltan filtros obligatorios: fecha inicial y fecha final.")
    if not sucursal:
        frappe.throw("Faltan filtros obligatorios: seleccionar al menos una sucursal (Cost Center).")

    # Filtros canónicos (no se replican en JS)
    filters = {
        "status": "Paid",
        "posting_date": ["between", [fecha_inicial, fecha_final]],
        "cost_center": ["in", sucursal],
    }
    # Solo si existe el campo custom_status_comisiones
    if frappe.get_meta("Sales Invoice").get_field("custom_status_comisiones"):
        filters["custom_status_comisiones"] = "Sin Enviar"

    # Consulta base (orden determinístico)
    sinv = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=[
            "name", "posting_date", "customer", "cost_center",
            "net_total", "base_net_total", "update_stock"
        ],
        order_by="posting_date asc, name asc",
        limit=2000
    )

    if not sinv:
        return []

    # Determinar si la SI está "entregada" cuando hay ítems stock
    # Regla: si TODOS los ítems son servicio (no stock)-> no exige entrega
    #        si hay algún ítem stock -> exigir entregada
    def _is_service_only(si_name: str) -> bool:
        """
        True si TODOS los items de la SI son no-stock (servicios).
        Optimización: una sola consulta SQL con JOIN a Item.
        """
        items = frappe.db.sql("""
            SELECT i.is_stock_item
            FROM `tabSales Invoice Item` sii
            JOIN `tabItem` i ON i.name = sii.item_code
            WHERE sii.parent = %s
        """, (si_name,), as_dict=True)

        # Sin items: trátalo como servicio (no bloquea)
        if not items:
            return True

        # Si existe al menos un item de inventario, NO es sólo servicio
        return all(not (row.get("is_stock_item") or 0) for row in items)

    def _delivered(si_name: str) -> bool:
        """
        Consideramos 'entregada' si:
          - La factura hizo update_stock (ya descargó inventario), o
          - Tiene Delivery Notes vinculados con qty entregada > 0
        """
        upd = frappe.db.get_value("Sales Invoice", si_name, "update_stock")
        if upd:
            return True

        # ¿Tiene al menos un Delivery Note vinculado?
        has_dn = frappe.db.sql("""
            SELECT 1
            FROM `tabSales Invoice Item`
            WHERE parent = %s AND IFNULL(delivery_note, '') != ''
            LIMIT 1
        """, (si_name,))
        return bool(has_dn)

    # Post-filtrado por entrega según tipo de items
    out = []
    for si in sinv:
        if _is_service_only(si["name"]):
            out.append(si)  # servicios: no exige entrega
        else:
            if _delivered(si["name"]):
                out.append(si)
            # si no está entregada y tiene stock -> se excluye

    return out


def _build_blacklist_with_dates():
    """Lee Comisiones Settings y construye un dict {customer: [(start,end), ...]}."""
    out = {}
    settings = frappe.get_single("Comisiones Settings")
    for row in (getattr(settings, "clientes_sin_comision", None) or []):
        cust = (row.customer or "").strip()
        if not cust:
            continue
        start = getdate(row.start_date) if row.start_date else None
        end   = getdate(row.end_date)   if row.end_date   else None
        out.setdefault(cust, []).append((start, end))
    return out


def _is_blacklisted(customer: str, posting_date, bl_map: dict) -> bool:
    """True si el cliente está en la lista y la fecha cae dentro de alguna vigencia.
       Rango abierto permitido: start only (desde start en adelante), end only (hasta end inclusive)."""
    if not customer or customer not in bl_map:
        return False
    pd = getdate(posting_date)
    for (start, end) in bl_map[customer]:
        if start and end:
            if start <= pd <= end:
                return True
        elif start and not end:
            if pd >= start:
                return True
        elif end and not start:
            if pd <= end:
                return True
        else:
            # sin fechas => siempre bloqueado
            return True
    return False


@frappe.whitelist()
def get_commission_rows(sucursal, fecha_inicial, fecha_final, docname=None, rates_by_cc=None):
    invoices = get_sales_invoices(sucursal, fecha_inicial, fecha_final)
    if not invoices:
        return {"rows": [], "total": 0, "count": 0}

    blacklist = _build_blacklist_with_dates()

    # default global (fallback cuando no hay tasa por sucursal)
    settings = frappe.get_single("Comisiones Settings")
    default_rate = flt(getattr(settings, "porcentaje_sobre_utilidad"))
    negative_policy = (getattr(settings, "negative_commission_policy", "Contabilizar como cero") or "Contabilizar como cero").strip()

    # normalizar rates_by_cc si llega como JSON
    if isinstance(rates_by_cc, str):
        try:
            rates_by_cc = json.loads(rates_by_cc or "{}")
        except Exception:
            rates_by_cc = {}

    # 1) si me mandan rates_by_cc (del doc en memoria), usarlo SIEMPRE
    if rates_by_cc:
        def _rate_for(cc):
            val = rates_by_cc.get(cc)
            return flt(val) if val is not None else default_rate

    # 2) si no, intentar leer tasas desde el documento guardado (docname)
    else:
        rates_doc = {}
        if docname:
            try:
                doc = frappe.get_doc("Orden de Pago Comisiones", docname)
                for r in (doc.comisiones_por_sucursal or []):
                    if r.cost_center:
                        rates_doc[r.cost_center] = (flt(r.porcentaje_comision)
                                                    if r.porcentaje_comision is not None else None)
            except Exception:
                # doc aún no existe (new-...): seguimos sin romper
                pass

        # completar con settings específicas
        specific = {}
        for row in (getattr(settings, "tasas_por_sucursal", None) or []):
            cc = (row.cost_center or "").strip()
            if cc:
                specific[cc] = (flt(row.porcentaje_comision)
                                if row.porcentaje_comision is not None else None)
        def _rate_for(cc):
            val = rates_doc.get(cc) if rates_doc else None
            if val is None:
                val = specific.get(cc)
            return (val if val is not None else default_rate)

    # ===== resto de lógica actual (SIN tocar) =====
    rows, total_sum = [], 0
    subtotal_negativas = 0.0   # NUEVO: informativo, suma de comisiones negativas brutas
    
    def _apply_policy(val: float) -> float:
        nonlocal subtotal_negativas
        # Registrar negativos brutos para el subtotal informativo
        if val < 0:
            subtotal_negativas += val
        # Aplicar política
        if negative_policy == "Contabilizar como cero":
            return max(val, 0.0)
        # Reduce del pago (default)
        return val
    for si in invoices:
        # Excluir si el cliente está en blacklist vigente
        customer = si.get("customer")
        if _is_blacklisted(customer, si.get("posting_date"), blacklist):
            continue

        si_doc = frappe.get_doc("Sales Invoice", si["name"])

        ingreso = si.get("base_net_total")
        if ingreso is None:
            ingreso = si.get("net_total")
        if ingreso is None:
            frappe.throw(f"Ingreso no disponible en Sales Invoice {si.get('name')} (base_net_total / net_total).")
        ingreso = flt(ingreso)

        cogs = flt(get_costo_ventas_si(si["name"]))
        utilidad = ingreso - cogs

        cc = si.get("cost_center")
        rate_cc = _rate_for(cc)

        if not si_doc.sales_team:
            bruto = utilidad * (rate_cc / 100.0)
            total_comision = _apply_policy(bruto)
            rows.append({
                "sales_invoice_id": si["name"],
                "posting_date": si["posting_date"],
                "cost_center": cc,
                "persona_de_ventas": "",
                "porcentaje_comision": 0.0,
                "ingreso": ingreso,
                "costo_de_ventas": cogs,
                "utilidad_transaccion": utilidad,
                "total_comision": total_comision,
                "folio_fiscal": getattr(si_doc, "custom_folio_fiscal", "") or ""
            })
            total_sum += total_comision
            continue

        for sp in si_doc.sales_team:
            alloc = flt(sp.allocated_percentage or 0)
            person_utilidad = utilidad * (alloc / 100.0) if alloc else utilidad
            bruto = person_utilidad * (rate_cc / 100.0)
            total_comision = _apply_policy(bruto)
            rows.append({
                "sales_invoice_id": si["name"],
                "posting_date": si["posting_date"],
                "cost_center": cc,
                "persona_de_ventas": sp.sales_person,
                "porcentaje_comision": alloc,
                "ingreso": ingreso,
                "costo_de_ventas": cogs,
                "utilidad_transaccion": person_utilidad,
                "total_comision": total_comision,
                "folio_fiscal": getattr(si_doc, "custom_folio_fiscal", "") or ""
            })
            total_sum += total_comision

    # Normalizar sucursal a lista de CC
    if isinstance(sucursal, str):
        try:
            import json
            suc_list = json.loads(sucursal or "[]")
        except Exception:
            suc_list = [sucursal] if sucursal else []
    else:
        suc_list = sucursal or []
    suc_list = [cc for cc in suc_list if cc]

    return {"rows": rows, "total": total_sum, "count": len(rows), "subtotal_negativas": subtotal_negativas}


@frappe.whitelist()
def sync_rates_from_settings(cost_centers):
    if isinstance(cost_centers, str):
        cost_centers = json.loads(cost_centers or "[]")
    cost_centers = [cc for cc in (cost_centers or []) if cc]

    settings = frappe.get_single("Comisiones Settings")
    default_rate = flt(getattr(settings, "porcentaje_sobre_utilidad"))

    # tasas específicas por CC (si una fila no tiene tasa, cae al default)
    specific = {}
    for row in (getattr(settings, "tasas_por_sucursal", None) or []):
        cc = (row.cost_center or "").strip()
        if cc:
            specific[cc] = flt(row.porcentaje_comision) if row.porcentaje_comision is not None else default_rate

    rows = [{"cost_center": cc, "porcentaje_comision": specific.get(cc, default_rate)}
            for cc in cost_centers]

    return {"rows": rows, "applied": len(rows), "default_rate": default_rate}


@frappe.whitelist()
def get_costo_ventas_sales_invoice(sales_invoice_id):

    cogs = 0
    cogs += get_costo_ventas_si(sales_invoice_id)
    cogs += get_costo_ventas_dn(sales_invoice_id)

    return cogs
