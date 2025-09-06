import frappe
from frappe import _

def execute(filters=None):
    filters = frappe._dict(filters or {})

    from_date = filters.get("from_date") or "2025-01-01"
    to_date = filters.get("to_date") or frappe.utils.today()
    sales_person = filters.get("sales_person")
    cost_center = filters.get("cost_center")

    where = [
        "opc.docstatus = 1",
        "si.docstatus = 1",
        "si.posting_date >= %(from_date)s",
        "si.posting_date <= %(to_date)s",
        "c.persona_de_ventas IS NOT NULL",
        "c.total_comision IS NOT NULL"
    ]
    params = {"from_date": from_date, "to_date": to_date}

    if sales_person:
        where.append("c.persona_de_ventas = %(sales_person)s")
        params["sales_person"] = sales_person
    if cost_center:
        where.append("COALESCE(si.cost_center, '') = %(cc)s")
        params["cc"] = cost_center

    sql = f"""
        SELECT
            c.persona_de_ventas AS sales_person,
            SUM(c.total_comision) AS commission_total
        FROM `tabComision LLCS` c
        INNER JOIN `tabOrden de Pago Comisiones` opc
            ON opc.name = c.parent
        LEFT JOIN `tabSales Invoice` si
            ON si.name = c.sales_invoice_id
        WHERE {" AND ".join(where)}
        GROUP BY c.persona_de_ventas
        ORDER BY commission_total DESC, c.persona_de_ventas ASC
    """

    data = frappe.db.sql(sql, params, as_dict=True)

    columns = [
        {"label": _("Vendedor"), "fieldname": "sales_person", "fieldtype": "Data", "width": 220},
        {"label": _("Comisión Total"), "fieldname": "commission_total", "fieldtype": "Currency", "width": 160},
    ]
    return columns, data