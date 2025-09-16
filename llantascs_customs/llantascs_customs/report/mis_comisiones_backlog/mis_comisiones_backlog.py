import frappe
from frappe import _

def _has_col(dt, col):
    try:
        return frappe.db.has_column(dt, col)
    except Exception:
        return False

def _table_exists(table):
    try:
        return frappe.db.table_exists(table)
    except Exception:
        return False

def _user_sales_persons(user: str):
    sps = set()
    sp_by_name = frappe.db.get_value("Sales Person", {"name": user, "enabled": 1}, "name")
    if sp_by_name:
        sps.add(sp_by_name)
    emp = frappe.db.get_value("Employee", {"user_id": user, "status": ("!=", "Left")}, "name")
    if emp:
        sps_emp = frappe.get_all("Sales Person", filters={"employee": emp, "enabled": 1}, pluck="name")
        sps.update(sps_emp or [])
    return list(sps)

def execute(filters=None):
    filters = filters or {}
    user = frappe.session.user
    sp_override = filters.get("sales_person")
    sps = [sp_override] if sp_override else _user_sales_persons(user)

    columns = [
        {"label": _("Sales Person"),      "fieldname": "sales_person",    "fieldtype": "Data",                               "width": 180},
        {"label": _("Sales Invoice"),     "fieldname": "sales_invoice",   "fieldtype": "Link", "options": "Sales Invoice",   "width": 150},
        {"label": _("Fecha"),             "fieldname": "posting_date",    "fieldtype": "Date",                               "width": 100},
        {"label": _("Cliente"),           "fieldname": "customer",        "fieldtype": "Link", "options": "Customer",        "width": 180},
        {"label": _("Sucursal"),          "fieldname": "cost_center",     "fieldtype": "Link", "options": "Cost Center",     "width": 180},
        {"label": _("Ingreso"),           "fieldname": "ingreso",         "fieldtype": "Currency",                           "width": 120},
        {"label": _("Costo"),             "fieldname": "costo",           "fieldtype": "Currency",                           "width": 120},
        {"label": _("Utilidad"),          "fieldname": "utilidad",        "fieldtype": "Currency",                           "width": 120},
        {"label": _("% Sobre utilidad"),  "fieldname": "tasa",            "fieldtype": "Percent",                            "width": 110},
        {"label": _("% Participación"),   "fieldname": "participacion",   "fieldtype": "Percent",                            "width": 110},
        {"label": _("Comisión"),          "fieldname": "comision",        "fieldtype": "Currency",                           "width": 120},
        {"label": _("OPC"),               "fieldname": "opc",             "fieldtype": "Link", "options": "Orden de Pago Comisiones", "width": 190},
    ]

    dt_child = "Comision LLCS"
    has_sp_child  = _has_col(dt_child, "persona_de_ventas")
    has_cc_child  = _has_col(dt_child, "cost_center")
    has_ingreso   = _has_col(dt_child, "ingreso")
    has_costo     = _has_col(dt_child, "costo_de_ventas")
    has_utilidad  = _has_col(dt_child, "utilidad_transaccion")
    has_total     = _has_col(dt_child, "total_comision")

    # si el mapeo es por persona_de_ventas y el usuario no mapea → vacío
    if has_sp_child and not sps and not sp_override:
        return columns, []

    # tasas por sucursal
    cps_exists = _table_exists("OPC Comision Por Sucursal")
    has_cps_rate = cps_exists and _has_col("OPC Comision Por Sucursal", "porcentaje_comision") and _has_col("OPC Comision Por Sucursal", "cost_center")
    has_legacy_rate = _has_col("Orden de Pago Comisiones", "comision_sobre_utilidad_")

    # expresiones
    cost_center_expr = "c.cost_center" if has_cc_child else "si.cost_center"

    # tasa real (COALESCE tabla → legacy; nunca default)
    join_cps = ""
    if has_cps_rate:
        join_cps = (
            f" LEFT JOIN `tabOPC Comision Por Sucursal` cps"
            f"   ON cps.parent = c.parent"
            f"  AND cps.cost_center = {cost_center_expr}"
            f"  AND {cost_center_expr} IS NOT NULL"
            f"  AND {cost_center_expr} != ''"
        )
        tasa_expr = "COALESCE(cps.porcentaje_comision, opc.comision_sobre_utilidad_)" if has_legacy_rate else "cps.porcentaje_comision"
    elif has_legacy_rate:
        tasa_expr = "opc.comision_sobre_utilidad_"
    else:
        tasa_expr = "NULL"

    # participación (Sales Team) — join 1:1 por SI + persona_de_ventas
    join_st = ""
    participacion_expr = "NULL"
    if has_sp_child:
        join_st = (
            " LEFT JOIN `tabSales Team` st"
            "   ON st.parent = si.name"
            "  AND st.sales_person = c.persona_de_ventas"
        )
        participacion_expr = "st.allocated_percentage"

    parts = [
        ("sales_person",   "c.persona_de_ventas" if has_sp_child else "NULL"),
        ("sales_invoice",  "c.sales_invoice_id"),
        ("posting_date",   "si.posting_date"),
        ("customer",       "si.customer"),
        ("cost_center",    cost_center_expr),
        ("ingreso",        "c.ingreso" if has_ingreso else "NULL"),
        ("costo",          "c.costo_de_ventas" if has_costo else "NULL"),
        ("utilidad",       "c.utilidad_transaccion" if has_utilidad else "NULL"),
        ("tasa",           tasa_expr),
        ("participacion",  participacion_expr),
        ("comision",       "c.total_comision" if has_total else "NULL"),
        ("opc",            "c.parent"),
    ]
    select_sql = ",\n            ".join([f"{expr} AS {alias}" for alias, expr in parts])

    sql = f"""
        SELECT
            {select_sql}
        FROM `tab{dt_child}` c
        INNER JOIN `tabOrden de Pago Comisiones` opc
            ON opc.name = c.parent AND opc.docstatus = 1
        LEFT JOIN `tabSales Invoice` si
            ON si.name = c.sales_invoice_id AND si.docstatus = 1
        {join_cps}
        {join_st}
    """

    where, params = [], {}
    if has_sp_child and (sps or sp_override):
        params["sps"] = tuple(sps) if sps else (sp_override,)
        where.append("c.persona_de_ventas IN %(sps)s")

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY si.posting_date DESC, c.sales_invoice_id DESC"

    data = frappe.db.sql(sql, params, as_dict=True)
    return columns, data