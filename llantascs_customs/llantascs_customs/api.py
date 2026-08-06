import frappe
import json
from frappe.utils import now
from frappe.utils import flt, getdate

# Los helpers fiscales de facturacion_mexico son OPCIONALES: si la app (o sus módulos) no están
# instalados, el reporte de comisiones sigue funcionando con la evidencia disponible en ERPNext.
# Nunca debe fallar por ImportError. Los fallbacks devuelven "sin evidencia fiscal".
try:
    from facturacion_mexico.facturacion_fiscal.utils import (
        credit_note_lines_use_discount_account,
        get_cuenta_descuentos,
        get_invoice_uuid,
    )
except Exception:  # noqa: BLE001 — app fiscal ausente/rota → degradar sin romper el cálculo

    def get_invoice_uuid(sales_invoice_name):
        return None

    def get_cuenta_descuentos(company):
        return None

    def credit_note_lines_use_discount_account(sales_invoice, cuenta_descuentos):
        return False


# Variables globales llantas Customs
estados_comisiones = ["Sin Enviar", "Enviado", "Pagada"]

# --- Notas de crédito: marcador fiscal persistente (motivo 01 vs 03) ---
# Fuente de verdad: Factura Fiscal Mexico.fm_tipo_nota_credito, derivado y persistido por
# facturacion_mexico al ejecutar "Aplicar como Descuento / Bonificación" (-> TipoRelacion 01)
# o "Revertir a Devolucion" (-> TipoRelacion 03). Se lee el valor ALMACENADO; no se infiere el
# motivo por cuenta contable, SLE, update_stock, item_code, descripcion ni movimiento de almacen.
# El vinculo es: Sales Invoice.fm_factura_fiscal_mx -> Factura Fiscal Mexico.fm_tipo_nota_credito.
NOTA_CREDITO_DESCUENTO = (
    "Descuento / Bonificación"  # motivo 01 (bonificacion/descuento)
)
NOTA_CREDITO_DEVOLUCION = (
    "Devolución de mercancía"  # motivo 03 (devolucion de mercancia)
)
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
    rows = frappe.db.sql(
        """
        SELECT i.is_stock_item
        FROM `tabSales Invoice Item` sii
        JOIN `tabItem` i ON i.name = sii.item_code
        WHERE sii.parent = %s
    """,
        (si_name,),
        as_dict=True,
    )
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
        dbs = frappe.db.get_value(
            "Sales Order Item", r.so_detail, "delivered_by_supplier"
        )
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
    Busca DN vinculados por dos rutas:
    1. SI Item.delivery_note (link directo)
    2. DN Item.against_sales_invoice (link inverso)
    Deduplica por DN y suma COGS desde GL Entries de todos los DN únicos.
    """
    dn_set = set()

    # Ruta 1: DN vinculados directamente en SI Item
    rows_direct = frappe.db.sql(
        """
        SELECT DISTINCT delivery_note
        FROM `tabSales Invoice Item`
        WHERE parent=%s AND IFNULL(delivery_note,'')!=''
    """,
        (si_name,),
        as_dict=True,
    )

    for r in rows_direct:
        if r.delivery_note:
            dn_set.add(r.delivery_note)

    # Ruta 2: DN vinculados por against_sales_invoice
    rows_inverse = frappe.db.sql(
        """
        SELECT DISTINCT parent as delivery_note
        FROM `tabDelivery Note Item`
        WHERE against_sales_invoice = %s
    """,
        (si_name,),
        as_dict=True,
    )

    for r in rows_inverse:
        if r.delivery_note:
            dn_set.add(r.delivery_note)

    if not dn_set:
        return 0.0

    # Obtener cuentas COGS
    cogs_accounts = get_cogs_account()
    if not cogs_accounts:
        return 0.0

    # Sumar COGS de GL Entries de todos los DN únicos
    total = 0.0
    for dn_name in dn_set:
        dn_cogs = frappe.db.sql(
            """
            SELECT SUM(debit) AS cogs
            FROM `tabGL Entry`
            WHERE voucher_type = 'Delivery Note'
              AND voucher_no = %s
              AND account IN %s
              AND is_cancelled = 0
        """,
            (dn_name, tuple(cogs_accounts)),
            as_dict=True,
        )

        if dn_cogs and dn_cogs[0].cogs is not None:
            total += flt(dn_cogs[0].cogs)

    return total


def _sle_total_for_si(si_name: str):
    """
    Devuelve la suma de SLE (stock_value_difference) para el voucher SI si existen filas.
    Si no existen SLE, retorna None (no "0 inventado").
    """
    row = frappe.db.sql(
        """
        SELECT SUM(stock_value_difference) AS total_cost
        FROM `tabStock Ledger Entry`
        WHERE voucher_type='Sales Invoice' AND voucher_no=%s
    """,
        (si_name,),
        as_dict=True,
    )
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
            dbs = frappe.db.get_value(
                "Sales Order Item", r.so_detail, "delivered_by_supplier"
            )
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

    row = frappe.db.sql(
        """
        SELECT SUM(debit - credit) AS cogs
        FROM `tabGL Entry`
        WHERE voucher_type = 'Sales Invoice'
          AND voucher_no   = %s
          AND account      IN %s
    """,
        (si_name, tuple(cogs_accounts)),
        as_dict=True,
    )

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
        "Cost Center", filters={"is_group": 0, "disabled": 0}, pluck="name"
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
        frappe.throw(
            "Faltan filtros obligatorios: seleccionar al menos una sucursal (Cost Center)."
        )

    # Criterio funcional (reemplaza el filtro por status == "Paid").
    # El status "Paid" excluía facturas liquidadas con nota de crédito, porque ERPNext las marca
    # "Credit Note Issued" cuando existe una nota (is_return=1) ligada por return_against, aun con
    # outstanding_amount = 0. La factura ORIGINAL liquidada se define funcionalmente como:
    #   docstatus = 1  ·  is_return = 0  ·  outstanding_amount = 0 (con tolerancia de precisión).
    prec = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2
    tol = (
        1.0 / (10**prec) / 2.0
    )  # media unidad monetaria: outstanding "== 0" respetando precisión
    filters = {
        "docstatus": 1,
        "is_return": 0,
        "outstanding_amount": ["<=", tol],
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
            "name",
            "posting_date",
            "customer",
            "cost_center",
            "net_total",
            "base_net_total",
            "outstanding_amount",
            "update_stock",
        ],
        order_by="posting_date asc, name asc",
        limit=2000,
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
        items = frappe.db.sql(
            """
            SELECT i.is_stock_item
            FROM `tabSales Invoice Item` sii
            JOIN `tabItem` i ON i.name = sii.item_code
            WHERE sii.parent = %s
        """,
            (si_name,),
            as_dict=True,
        )

        # Sin items: trátalo como servicio (no bloquea)
        if not items:
            return True

        # Si existe al menos un item de inventario, NO es sólo servicio
        return all(not (row.get("is_stock_item") or 0) for row in items)

    def _delivered(si_name: str) -> bool:
        """
        Consideramos 'entregada' si:
          - La factura hizo update_stock (ya descargó inventario), o
          - TODOS los items de stock tienen entrega completa:
            (delivered_qty + delivered_by_supplier) >= qty
        """
        si = frappe.get_doc("Sales Invoice", si_name)

        # Si update_stock=1, ya descargó inventario automáticamente
        if si.update_stock:
            return True

        # Validar entrega completa para items de stock
        for item in si.items:
            # Verificar si es item de stock (usar cached para performance)
            item_doc = frappe.get_cached_doc("Item", item.item_code)
            if not item_doc.is_stock_item:
                continue  # Servicios no requieren entrega

            # Validar entrega completa
            total_delivered = flt(item.delivered_qty) + flt(item.delivered_by_supplier)
            if total_delivered < item.qty:
                return False  # Entrega incompleta

        return True  # Todos los items de stock están completamente entregados

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
    for row in getattr(settings, "clientes_sin_comision", None) or []:
        cust = (row.customer or "").strip()
        if not cust:
            continue
        start = getdate(row.start_date) if row.start_date else None
        end = getdate(row.end_date) if row.end_date else None
        out.setdefault(cust, []).append((start, end))
    return out


def _is_blacklisted(customer: str, posting_date, bl_map: dict) -> bool:
    """True si el cliente está en la lista y la fecha cae dentro de alguna vigencia.
    Rango abierto permitido: start only (desde start en adelante), end only (hasta end inclusive)."""
    if not customer or customer not in bl_map:
        return False
    pd = getdate(posting_date)
    for start, end in bl_map[customer]:
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


def _ffm_tipo_map(ffm_names):
    """Devuelve {ffm_name: fm_tipo_nota_credito} desde Factura Fiscal Mexico.

    Seam aislado de acceso a la app fiscal: los tests de integración lo sustituyen cuando
    facturacion_mexico no está instalado, manteniendo real todo el resto del cálculo.
    """
    tipo_by_ffm = {}
    if ffm_names:
        for f in frappe.get_all(
            "Factura Fiscal Mexico",
            filters={"name": ["in", ffm_names]},
            fields=["name", "fm_tipo_nota_credito"],
        ):
            tipo_by_ffm[f.name] = (f.fm_tipo_nota_credito or "").strip()
    return tipo_by_ffm


def _dn_cogs_gl(dn_name):
    """COGS (magnitud >=0) de una Delivery Note desde GL Entry (cuentas Cost of Goods Sold).

    Para una DN de retorno el asiento COGS es un crédito (debit-credit < 0); se devuelve el valor
    absoluto = costo que regresa a inventario.
    """
    cogs_accounts = get_cogs_account()
    if not cogs_accounts:
        return 0.0
    row = frappe.db.sql(
        """
        SELECT SUM(debit - credit) AS cogs
        FROM `tabGL Entry`
        WHERE voucher_type = 'Delivery Note'
          AND voucher_no   = %s
          AND account      IN %s
          AND is_cancelled = 0
        """,
        (dn_name, tuple(cogs_accounts)),
        as_dict=True,
    )
    return abs(flt(row[0].cogs)) if row and row[0].cogs is not None else 0.0


def _cogs_revertido_return_dn(invoice_name, exclude_dn):
    """COGS revertido por Delivery Notes de retorno del inventario de la factura original.

    Cubre el caso donde la mercancía regresó por una DN de devolución (is_return=1) y NO por la
    nota de crédito. Asociación con vínculos reales de ERPNext:
      SI → DN de salida : Sales Invoice Item.delivery_note  ∪  Delivery Note Item.against_sales_invoice
      DN de salida → DN de retorno : Delivery Note.is_return=1 AND return_against ∈ DN de salida
    Deduplica por voucher_no y excluye DN ya contadas dentro de get_costo_ventas_si(nota).
    """
    # DN de salida (is_return=0, docstatus=1) ligadas a la factura por cualquiera de las dos rutas.
    fwd = set(
        frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": invoice_name, "delivery_note": ["!=", ""]},
            pluck="delivery_note",
        )
    )
    fwd |= set(
        frappe.get_all(
            "Delivery Note Item",
            filters={"against_sales_invoice": invoice_name},
            pluck="parent",
        )
    )
    fwd = [d for d in fwd if d]
    if not fwd:
        return 0.0
    fwd_ok = frappe.get_all(
        "Delivery Note",
        filters={"name": ["in", fwd], "is_return": 0, "docstatus": 1},
        pluck="name",
    )
    if not fwd_ok:
        return 0.0

    ret_dns = frappe.get_all(
        "Delivery Note",
        filters={"is_return": 1, "docstatus": 1, "return_against": ["in", fwd_ok]},
        pluck="name",
    )
    total, seen = 0.0, set()
    for rdn in ret_dns:
        if rdn in exclude_dn or rdn in seen:
            continue
        seen.add(rdn)
        total += _dn_cogs_gl(rdn)
    return total


def _es_descuento_persistente(nota_name):
    """True si la nota de crédito lleva los marcadores persistentes de la acción
    "Aplicar como Descuento / Bonificación" de facturacion_mexico (Issue #137).

    Marcadores deterministas escritos por esa acción (no inferencia):
      - update_stock == 0 (un descuento no mueve inventario), y
      - TODAS las líneas usan income_account == cuenta de descuentos configurada para la empresa.
    Si facturacion_mexico / la cuenta no están disponibles (p. ej. sitio sin la app), no se puede
    afirmar descuento → False (se tratará como devolución con COGS medido del inventario real).
    """
    try:
        doc = frappe.get_doc("Sales Invoice", nota_name)
        if doc.get("update_stock"):
            return False
        cuenta = get_cuenta_descuentos(doc.get("company"))
        if not cuenta:
            return False
        return credit_note_lines_use_discount_account(doc, cuenta)
    except Exception:
        return False


def _build_credit_note_adjustments(invoice_names):
    """Consolida las notas de crédito VÁLIDAS por factura de origen (motivo 01 y 03).

    Una sola consulta batch para todas las notas y otra para su clasificación fiscal, evitando
    N+1. Solo considera notas emitidas y no canceladas (docstatus=1, is_return=1) ligadas por
    return_against a alguna de las facturas dadas.

    COGS revertido (motivo 03) = costo que regresa a inventario, sumando:
      - get_costo_ventas_si(nota) — reverso registrado por la propia nota (nota con update_stock), y
      - Delivery Notes de retorno (is_return=1) ligadas a las DN de salida de la factura, cuando el
        inventario regresó por una DN de devolución y no por la nota (deduplicado por voucher_no).

    Devuelve: {factura: {"bonif_01": <signed>, "dev_03": <signed>, "cogs_revertido": <>=0>}}
      - bonif_01 / dev_03: suma de base_net_total de las notas (NEGATIVO en ERPNext → reduce).
      - cogs_revertido: magnitud (>=0) del costo que regresa a inventario por devoluciones.

    Clasificación por evidencia documental (nunca detiene el cálculo): motivo FFM explícito →
    marcadores persistentes de la acción de descuento (cuenta + update_stock) → por defecto
    devolución con COGS medido del inventario real.
    """
    out = {}
    if not invoice_names:
        return out

    notas = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "is_return": 1,
            "return_against": ["in", list(invoice_names)],
        },
        fields=["name", "return_against", "base_net_total", "fm_factura_fiscal_mx"],
    )
    if not notas:
        return out

    # Batch: clasificación fiscal (motivo) desde Factura Fiscal Mexico.fm_tipo_nota_credito
    ffm_names = list({n.fm_factura_fiscal_mx for n in notas if n.fm_factura_fiscal_mx})
    tipo_by_ffm = _ffm_tipo_map(ffm_names)

    for n in notas:
        tipo = tipo_by_ffm.get(n.fm_factura_fiscal_mx, "")
        entry = out.setdefault(
            n.return_against, {"bonif_01": 0.0, "dev_03": 0.0, "cogs_revertido": 0.0}
        )
        # Clasificación por EVIDENCIA DOCUMENTAL, en orden de prioridad:
        #   1) motivo explícito en FFM (fm_tipo_nota_credito), cuando exista;
        #   2) marcadores persistentes de la acción "Aplicar como Descuento" (cuenta + update_stock);
        #   3) por defecto: devolución → el COGS revertido se MIDE del inventario real
        #      (nota con stock + Delivery Notes de retorno). Nunca se detiene el cálculo.
        es_descuento = tipo == NOTA_CREDITO_DESCUENTO or (
            not tipo and _es_descuento_persistente(n.name)
        )
        if es_descuento:
            # Descuento/bonificación: baja el ingreso, el COGS se mantiene (mercancía con el cliente).
            entry["bonif_01"] += flt(n.base_net_total)
        else:
            # Devolución (FFM=03, o sin motivo y sin marcadores de descuento): baja el ingreso y
            # revierte el costo realmente devuelto por la propia nota (si movió stock).
            entry["dev_03"] += flt(n.base_net_total)
            entry["cogs_revertido"] += flt(get_costo_ventas_si(n.name))

    # Netear DN de retorno del inventario (retorno registrado por una Delivery Note de devolución
    # y no por la nota de crédito). Se excluyen las DN ya contadas dentro de get_costo_ventas_si(nota)
    # para no duplicar por voucher_no.
    nota_names = [n.name for n in notas]
    dn_de_notas = (
        set(
            frappe.get_all(
                "Delivery Note Item",
                filters={"against_sales_invoice": ["in", nota_names]},
                pluck="parent",
            )
        )
        if nota_names
        else set()
    )
    for inv, entry in out.items():
        entry["cogs_revertido"] += _cogs_revertido_return_dn(inv, dn_de_notas)

    return out


def _net_from_credit_notes(ingreso_original, cogs_original, adj):
    """Aplica el ajuste consolidado de notas de crédito a una factura (función pura, testeable).

    adj: dict con bonif_01, dev_03 (signed, negativos) y cogs_revertido (>=0). Respeta los signos
    reales de ERPNext (las notas vienen negativas): sumarlas reduce el ingreso.

    Retorna (ingreso_neto, cogs_neto, utilidad_neta).
    """
    bonif_01 = flt((adj or {}).get("bonif_01", 0.0))
    dev_03 = flt((adj or {}).get("dev_03", 0.0))
    cogs_revertido = flt((adj or {}).get("cogs_revertido", 0.0))

    ingreso_neto = flt(ingreso_original) + bonif_01 + dev_03
    cogs_neto = flt(cogs_original) - cogs_revertido
    utilidad_neta = ingreso_neto - cogs_neto
    return ingreso_neto, cogs_neto, utilidad_neta


@frappe.whitelist()
def get_commission_rows(
    sucursal, fecha_inicial, fecha_final, docname=None, rates_by_cc=None
):
    invoices = get_sales_invoices(sucursal, fecha_inicial, fecha_final)
    if not invoices:
        return {"rows": [], "total": 0, "count": 0}

    # --- NUEVO: excluir facturas sin Sales Team ---
    si_names = [si["name"] for si in invoices]
    if si_names:
        with_team = frappe.get_all(
            "Sales Team", filters={"parent": ["in", si_names]}, pluck="parent"
        )
        allowed = set(with_team)
        invoices = [si for si in invoices if si["name"] in allowed]
    # ----------------------------------------------

    # Ajuste consolidado por notas de crédito (motivo 01/03), en batch para evitar N+1.
    credit_adjustments = _build_credit_note_adjustments([si["name"] for si in invoices])

    blacklist = _build_blacklist_with_dates()

    # default global (fallback cuando no hay tasa por sucursal)
    settings = frappe.get_single("Comisiones Settings")
    default_rate = flt(getattr(settings, "porcentaje_sobre_utilidad"))
    negative_policy = (
        getattr(settings, "negative_commission_policy", "Contabilizar como cero")
        or "Contabilizar como cero"
    ).strip()

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
                for r in doc.comisiones_por_sucursal or []:
                    if r.cost_center:
                        rates_doc[r.cost_center] = (
                            flt(r.porcentaje_comision)
                            if r.porcentaje_comision is not None
                            else None
                        )
            except Exception:
                # doc aún no existe (new-...): seguimos sin romper
                pass

        # completar con settings específicas
        specific = {}
        for row in getattr(settings, "tasas_por_sucursal", None) or []:
            cc = (row.cost_center or "").strip()
            if cc:
                specific[cc] = (
                    flt(row.porcentaje_comision)
                    if row.porcentaje_comision is not None
                    else None
                )

        def _rate_for(cc):
            val = rates_doc.get(cc) if rates_doc else None
            if val is None:
                val = specific.get(cc)
            return val if val is not None else default_rate

    # ===== resto de lógica actual (SIN tocar) =====
    rows, total_sum = [], 0
    subtotal_negativas = 0.0  # NUEVO: informativo, suma de comisiones negativas brutas

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

        ingreso_original = si.get("base_net_total")
        if ingreso_original is None:
            ingreso_original = si.get("net_total")
        if ingreso_original is None:
            frappe.throw(
                f"Ingreso no disponible en Sales Invoice {si.get('name')} (base_net_total / net_total)."
            )
        ingreso_original = flt(ingreso_original)

        cogs_original = flt(get_costo_ventas_si(si["name"]))

        # Ajuste consolidado por notas de crédito (motivo 01/03).
        # Sin notas → los netos son idénticos a los originales (facturas normales no cambian).
        adj = credit_adjustments.get(si["name"], {})
        ingreso_neto, cogs_neto, utilidad = _net_from_credit_notes(
            ingreso_original, cogs_original, adj
        )

        cc = si.get("cost_center")
        rate_cc = _rate_for(cc)
        folio = get_invoice_uuid(si_doc.name) or ""

        # Desglose informativo a nivel factura, adjunto a cada fila (contrato existente intacto).
        breakdown = {
            "ingreso_original": ingreso_original,
            "bonificaciones_01": flt(adj.get("bonif_01", 0.0)),
            "devoluciones_03": flt(adj.get("dev_03", 0.0)),
            "ingreso_neto": ingreso_neto,
            "cogs_original": cogs_original,
            "cogs_revertido": flt(adj.get("cogs_revertido", 0.0)),
            "cogs_neto": cogs_neto,
            "utilidad_neta": utilidad,
            "tasa_comision": rate_cc,
        }

        if not si_doc.sales_team:
            bruto = utilidad * (rate_cc / 100.0)
            total_comision = _apply_policy(bruto)
            row = {
                "sales_invoice_id": si["name"],
                "posting_date": si["posting_date"],
                "cost_center": cc,
                "persona_de_ventas": "",
                "porcentaje_comision": 0.0,
                "ingreso": ingreso_neto,
                "costo_de_ventas": cogs_neto,
                "utilidad_transaccion": utilidad,
                "total_comision": total_comision,
                "folio_fiscal": folio,
                "comision_neta": total_comision,
            }
            row.update(breakdown)
            rows.append(row)
            total_sum += total_comision
            continue

        for sp in si_doc.sales_team:
            alloc = flt(sp.allocated_percentage or 0)
            person_utilidad = utilidad * (alloc / 100.0) if alloc else utilidad
            bruto = person_utilidad * (rate_cc / 100.0)
            total_comision = _apply_policy(bruto)
            row = {
                "sales_invoice_id": si["name"],
                "posting_date": si["posting_date"],
                "cost_center": cc,
                "persona_de_ventas": sp.sales_person,
                "porcentaje_comision": alloc,
                "ingreso": ingreso_neto,
                "costo_de_ventas": cogs_neto,
                "utilidad_transaccion": person_utilidad,
                "total_comision": total_comision,
                "folio_fiscal": folio,
                "comision_neta": total_comision,
            }
            row.update(breakdown)
            rows.append(row)
            total_sum += total_comision

    # Normalizar sucursal a lista de CC
    if isinstance(sucursal, str):
        try:
            suc_list = json.loads(sucursal or "[]")
        except Exception:
            suc_list = [sucursal] if sucursal else []
    else:
        suc_list = sucursal or []
    suc_list = [cc for cc in suc_list if cc]

    return {
        "rows": rows,
        "total": total_sum,
        "count": len(rows),
        "subtotal_negativas": subtotal_negativas,
    }


@frappe.whitelist()
def sync_rates_from_settings(cost_centers):
    if isinstance(cost_centers, str):
        cost_centers = json.loads(cost_centers or "[]")
    cost_centers = [cc for cc in (cost_centers or []) if cc]

    settings = frappe.get_single("Comisiones Settings")
    default_rate = flt(getattr(settings, "porcentaje_sobre_utilidad"))

    # tasas específicas por CC (si una fila no tiene tasa, cae al default)
    specific = {}
    for row in getattr(settings, "tasas_por_sucursal", None) or []:
        cc = (row.cost_center or "").strip()
        if cc:
            specific[cc] = (
                flt(row.porcentaje_comision)
                if row.porcentaje_comision is not None
                else default_rate
            )

    rows = [
        {"cost_center": cc, "porcentaje_comision": specific.get(cc, default_rate)}
        for cc in cost_centers
    ]

    return {"rows": rows, "applied": len(rows), "default_rate": default_rate}


@frappe.whitelist()
def get_costo_ventas_sales_invoice(sales_invoice_id):

    cogs = 0
    cogs += get_costo_ventas_si(sales_invoice_id)
    cogs += get_costo_ventas_dn(sales_invoice_id)

    return cogs
