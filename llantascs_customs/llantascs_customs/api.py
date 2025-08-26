import frappe
import json
from frappe.utils import now
from frappe.utils import flt

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


def get_costo_ventas_si(sales_invoice_id):
    cogs = 0
    cogs_accounts = get_cogs_account()

    # GL entries for Sales Invoice, no delivery note
    gl_entries_invoice = frappe.db.get_list(
        "GL Entry",
        filters={
            "voucher_type": "Sales Invoice",
            "voucher_no": sales_invoice_id,
            "account": ["in", cogs_accounts],
        },
        pluck="name",
    )

    for entry in gl_entries_invoice:
        cogs += frappe.db.get_value("GL Entry", entry, "debit")
        cogs -= frappe.db.get_value("GL Entry", entry, "credit")

    return cogs


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
def get_commission_rate(sucursal: str | None = None):
    """Devuelve el rate de comisión por sucursal si existe; si no, el global."""
    global_rate = frappe.db.get_single_value("Comisiones Settings", "porcentaje_sobre_utilidad") or 0

    if sucursal:
        rows = frappe.get_all(
            "Comisiones Rate Sucursal",
            fields=["cost_center", "rate_percent"],
            filters={
                "parenttype": "Comisiones Settings",
                "parent": "Comisiones Settings"
            }
        )
        by_cc = {r["cost_center"]: flt(r["rate_percent"]) for r in rows}
        if sucursal in by_cc and by_cc[sucursal] is not None:
            return by_cc[sucursal]

    return global_rate


@frappe.whitelist()
def get_sales_invoices(sucursal, fecha_inicial, fecha_final):
    sales_invoice_id_list = get_sales_invoices_id(sucursal, fecha_inicial, fecha_final)
    sales_invoices = []

    # frappe.msgprint("entro a get sales invoices")

    for sales_invoice in sales_invoice_id_list:
        sinv = frappe.get_doc("Sales Invoice", sales_invoice)
        # frappe.msgprint(str(sales_invoice))
        # frappe.msgprint(str(is_delivered(sinv)))
        if sinv.sales_team and is_delivered(sinv):
            sales_invoices.append(sinv)

    # frappe.msgprint("estas son las invoices")
    # frappe.msgprint(str(sales_invoices))

    return sales_invoices


@frappe.whitelist()
def get_costo_ventas_sales_invoice(sales_invoice_id):

    cogs = 0
    cogs += get_costo_ventas_si(sales_invoice_id)
    cogs += get_costo_ventas_dn(sales_invoice_id)

    return cogs


@frappe.whitelist()
def refresh_order_branch_rates(opc_name: str, replace: int = 1):
    """Copia tasas de Settings a la Orden. Si replace=1 (default), reemplaza el snapshot existente."""
    opc = frappe.get_doc("Orden de Pago Comisiones", opc_name)
    ss = frappe.get_single("Comisiones Settings")
    settings_rows = ss.get("rates_por_sucursal") or []

    if int(replace or 0):
        opc.set("rates_por_sucursal_orden", [])

    for r in settings_rows:
        # evita duplicados si replace=0
        exists = any((row.cost_center == r.cost_center) for row in opc.get("rates_por_sucursal_orden"))
        if not exists:
            opc.append("rates_por_sucursal_orden", {
                "cost_center": r.cost_center,
                "rate_percent": r.rate_percent,
            })
    opc.save()
    return {"status": "OK", "replaced": bool(int(replace or 0)), "rows": len(opc.get("rates_por_sucursal_orden") or [])}


@frappe.whitelist()
def apply_reduction(opc_name: str):
    """Aplica reducción por diferimiento:
       - Si está DESACTIVADA (Settings o override por Orden), normaliza a valores sin ajuste.
       - Si está ACTIVADA, aplica reducción SOBRE INGRESO, recalcula margen y comisión (% comisión constante).
       Idempotente: parte de ingreso_original/margen_original si existen; si no, los fija la 1ª vez.
    """
    from frappe.utils import getdate, nowdate, flt
    from llantascs_customs.llantascs_customs.commissions_service import (
        compute_reduction_percent,
        resolve_revenue_original,
        resolve_cost_original,
        resolve_commission_rate_percent,
    )

    ss = frappe.get_single("Comisiones Settings")
    monthly = flt(ss.porcentaje_reduccion_mensual or 0)
    grace   = int(ss.dias_gracia_reduccion or 0)
    src     = ss.fecha_base_reduccion or "Due Date"  # "Due Date" | "Posting Date"
    global_on = bool(int(ss.aplicar_reduccion_por_diferimiento or 0))

    opc = frappe.get_doc("Orden de Pago Comisiones", opc_name)
    order_override_off = bool(int(getattr(opc, "sin_ajuste_en_esta_orden", 0) or 0))
    today = getdate(nowdate())

    changed = False
    applied = False
    reason = None

    def normalize_row_no_adjust(row):
        """Deja el renglón sin ajuste, recalculando comisión con el % actual y bases originales."""
        # B.2: Si no hay costo en el renglón, resolverlo con el nuevo sistema
        if not flt(getattr(row, "costo_de_ventas", 0)):
            from llantascs_customs.llantascs_customs.delivery_cogs_resolver import resolve_cogs_for_row
            info = resolve_cogs_for_row(opc, row)
            row.costo_de_ventas = info["cogs"]
            row.cogs_resuelto = info["cogs"]
            row.cogs_source = info["source"]
            row.delivered_via = info["delivered_via"]
            try:
                row.cogs_refs = json.dumps(info["refs"], ensure_ascii=False)
            except Exception:
                row.cogs_refs = ""

        R_base = resolve_revenue_original(row)
        if not flt(getattr(row, "ingreso_original", 0)):
            row.ingreso_original = R_base

        C_base = resolve_cost_original(row, R_base)
        if not flt(getattr(row, "margen_original", 0)):
            row.margen_original = max(0.0, R_base - C_base)

        # Valores sin reducción
        row.reduccion_ingreso_pct = 0.0
        row.monto_reduccion_ingreso = 0.0
        row.ingreso_ajustado = R_base
        row.margen_ajustado = max(0.0, R_base - C_base)
        row.monto_reduccion_margen = 0.0
        row.reduccion_margen_pct = 0.0
        # días transcurridos se conservan si ya estaban; si no, calcularlos no es necesario

        rc = resolve_commission_rate_percent(opc, row)
        row.comision_post_reduccion = row.margen_ajustado * (rc / 100.0)

    # Si el ajuste está globalmente OFF o override en la orden -> normaliza y retorna
    if (not global_on) or order_override_off:
        for row in opc.get("comisiones_incluidas", []):
            normalize_row_no_adjust(row)
            changed = True
        if changed:
            opc.flags.ignore_validate_update_after_submit = True
            opc.save()
        return {
            "status": "OK",
            "adjustments_applied": False,
            "reason": "disabled_global" if not global_on else "disabled_order",
            "monthly_rate": monthly,
            "grace_days": grace,
            "source": src,
        }

    # Ajuste ACTIVADO: aplicar reducción sobre INGRESO
    for row in opc.get("comisiones_incluidas", []):
        # B.2: Si no hay costo en el renglón, resolverlo con el nuevo sistema
        if not flt(getattr(row, "costo_de_ventas", 0)):
            from llantascs_customs.llantascs_customs.delivery_cogs_resolver import resolve_cogs_for_row
            info = resolve_cogs_for_row(opc, row)
            row.costo_de_ventas = info["cogs"]
            row.cogs_resuelto = info["cogs"]
            row.cogs_source = info["source"]
            row.delivered_via = info["delivered_via"]
            try:
                row.cogs_refs = json.dumps(info["refs"], ensure_ascii=False)
            except Exception:
                row.cogs_refs = ""
        # 1) Fecha base (solo informativo + cálculo de días)
        base_date = row.get("fecha_programada_de_pago")
        if not base_date:
            si_vals = None
            if row.get("sales_invoice_id"):
                try:
                    si_vals = frappe.get_cached_value(
                        "Sales Invoice",
                        row.get("sales_invoice_id"),
                        ["due_date", "posting_date"],
                        as_dict=True,
                    )
                except Exception:
                    si_vals = None
            if src == "Due Date" and si_vals and si_vals.get("due_date"):
                base_date = si_vals["due_date"]
            elif si_vals and si_vals.get("posting_date"):
                base_date = si_vals["posting_date"]
            else:
                base_date = today
            row.fecha_programada_de_pago = base_date

        dias = (today - getdate(base_date)).days if getdate(base_date) <= today else 0
        row.dias_transcurridos = dias
        effective_days = max(0, dias - grace)

        # 2) % reducción sobre INGRESO
        rho_pct = compute_reduction_percent(monthly, effective_days)  # 0..100
        delta = rho_pct / 100.0
        row.reduccion_ingreso_pct = rho_pct

        # 3) Bases idempotentes
        R_base = resolve_revenue_original(row)
        if not flt(getattr(row, "ingreso_original", 0)):
            row.ingreso_original = R_base

        C_base = resolve_cost_original(row, R_base)
        if not flt(getattr(row, "margen_original", 0)):
            row.margen_original = max(0.0, R_base - C_base)

        # 4) Ajustes
        R_aj = max(0.0, R_base * (1.0 - delta))
        M_aj = max(0.0, R_aj - C_base)

        row.ingreso_ajustado = R_aj
        row.margen_ajustado = M_aj
        row.monto_reduccion_ingreso = max(0.0, R_base - R_aj)
        row.monto_reduccion_margen = row.monto_reduccion_ingreso

        if flt(row.margen_original):
            row.reduccion_margen_pct = round((row.monto_reduccion_margen / row.margen_original) * 100.0, 6)
        else:
            row.reduccion_margen_pct = 0.0

        rc = resolve_commission_rate_percent(opc, row)
        row.comision_post_reduccion = M_aj * (rc / 100.0)

        changed = True
        applied = True

    if changed:
        opc.flags.ignore_validate_update_after_submit = True
        opc.save()

    return {
        "status": "OK",
        "adjustments_applied": applied,
        "reason": None,
        "monthly_rate": monthly,
        "grace_days": grace,
        "source": src,
    }
