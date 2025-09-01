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


def get_costo_ventas_si(sales_invoice: str) -> float:
    """
    Calcula el costo de ventas de una Sales Invoice con 4 casos:
    1) update_stock = 1 → usa Stock Ledger Entry
    2) sin update_stock con Delivery Notes vinculados → usa DN Items
    3) devoluciones referenciadas → ajusta contra costo original
    4) fallback: base_rate * qty
       - si > 0 → retorna y avisa (warning)
       - si = 0 → lanza error
    """
    si = frappe.get_doc("Sales Invoice", sales_invoice)

    # Caso 1: con Update Stock
    if getattr(si, "update_stock", 0):
        sle_cost = frappe.db.sql("""
            SELECT SUM(stock_value_difference) as total_cost
            FROM `tabStock Ledger Entry`
            WHERE voucher_type='Sales Invoice'
              AND voucher_no=%s
        """, (sales_invoice,), as_dict=True)[0].total_cost or 0
        if sle_cost:
            return abs(flt(sle_cost))

    # Caso 2: con Delivery Notes vinculados
    dn_items = frappe.get_all(
        "Sales Invoice Item",
        filters={"parent": sales_invoice, "delivery_note": ["!=", ""]},
        fields=["delivery_note", "item_code", "qty"]
    )
    if dn_items:
        dn_cost = 0
        for dn_row in dn_items:
            cost = frappe.db.sql("""
                SELECT SUM(base_net_rate * qty) as cost
                FROM `tabDelivery Note Item`
                WHERE parent=%s AND item_code=%s
            """, (dn_row.delivery_note, dn_row.item_code), as_dict=True)[0].cost or 0
            dn_cost += flt(cost)
        if dn_cost:
            return dn_cost

    # Caso 3: devoluciones
    return_si = frappe.get_all(
        "Sales Invoice",
        filters={"is_return": 1, "return_against": sales_invoice},
        fields=["name"]
    )
    total_return_cost = 0
    for r in return_si:
        total_return_cost += get_costo_ventas_si(r.name)

    if total_return_cost:
        original_cost = _costo_bruto_factura(sales_invoice)
        return max(0, original_cost - total_return_cost)

    # Caso 4: fallback
    calculated = _costo_bruto_factura(sales_invoice)
    if calculated:
        msg = f"[OPC.COSTO] Fallback usado para {sales_invoice}. Costo estimado = {calculated}"
        frappe.msgprint(msg, alert=True, indicator="orange")
        frappe.log_error(title="CostoVentasFallback", message=msg)
        return calculated
    else:
        msg = f"[OPC.COSTO] ERROR: fallback devolvió 0 para {sales_invoice}"
        frappe.log_error(title="CostoVentasFallback", message=msg)
        frappe.throw(msg)


def _costo_bruto_factura(sales_invoice: str) -> float:
    """Costo bruto: base_rate * qty de los items."""
    rows = frappe.get_all("Sales Invoice Item",
                          filters={"parent": sales_invoice},
                          fields=["base_rate", "qty"])
    return sum(flt(r.base_rate) * flt(r.qty) for r in rows)


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
