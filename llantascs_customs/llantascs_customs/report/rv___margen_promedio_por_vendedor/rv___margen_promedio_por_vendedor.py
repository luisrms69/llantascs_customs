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
        "c.utilidad_transaccion IS NOT NULL",
        "c.ingreso IS NOT NULL",
        "c.ingreso > 0"
    ]
    params = {"from_date": from_date, "to_date": to_date}

    if sales_person:
        where.append("c.persona_de_ventas = %(sales_person)s")
        params["sales_person"] = sales_person
    if cost_center:
        where.append("COALESCE(si.cost_center, '') = %(cc)s")
        params["cc"] = cost_center

    # promedio ponderado por ingreso
    sql = f"""
        SELECT
            c.persona_de_ventas AS sales_person,
            CASE
                WHEN SUM(c.ingreso) > 0
                THEN (SUM(c.utilidad_transaccion) / SUM(c.ingreso)) * 100.0
                ELSE NULL
            END AS margen_promedio
        FROM `tabComision LLCS` c
        INNER JOIN `tabOrden de Pago Comisiones` opc
            ON opc.name = c.parent
        LEFT JOIN `tabSales Invoice` si
            ON si.name = c.sales_invoice_id
        WHERE {" AND ".join(where)}
        GROUP BY c.persona_de_ventas
        ORDER BY margen_promedio DESC, c.persona_de_ventas ASC
    """

    data = frappe.db.sql(sql, params, as_dict=True)

    if not data:
        frappe.throw(_("Sin datos válidos para calcular margen (revise ingreso/utilidad)."))

    columns = [
        {"label": _("Vendedor"), "fieldname": "sales_person", "fieldtype": "Data", "width": 220},
        {"label": _("% Margen Promedio"), "fieldname": "margen_promedio", "fieldtype": "Percent", "width": 160},
    ]
    return columns, data