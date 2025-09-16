# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import today

# Doctypes
DT_CHILD = "Comision LLCS"
DT_OPC   = "Orden de Pago Comisiones"
DT_CPS   = "OPC Comision Por Sucursal"

# Campos fijos en Comision LLCS (ajusta SOLO si tu esquema difiere)
COL_SALES_PERSON   = "persona_de_ventas"
COL_SI_ID          = "sales_invoice_id"
COL_COST_CENTER    = "cost_center"            # si tu child NO tiene cost_center, usa SI abajo
COL_INGRESO        = "ingreso"
COL_COSTO          = "costo_de_ventas"
COL_UTILIDAD       = "utilidad_transaccion"
COL_TOTAL_COMISION = "total_comision"
PARTICIPACION_FIELD = "porcentaje_comision"  # <-- si tu campo se llama distinto, cámbialo aquí

def _require_column(dt: str, col: str):
    if not frappe.db.has_column(dt, col):
        frappe.throw(
            _("Falta la columna '{0}' en '{1}'. Ajusta el nombre en el código o crea el campo.")
            .format(col, dt),
            title=_("Esquema incompleto")
        )

def _get_from_date(filters) -> str:
    # Único default autorizado
    if filters.get("from_date"):
        return str(filters.get("from_date"))
    return "2025-01-17"

def execute(filters=None):
    filters = frappe._dict(filters or {})

    # Validar columnas del child (nombres fijos)
    for col in (
        COL_SALES_PERSON, COL_SI_ID,
        COL_INGRESO, COL_COSTO, COL_UTILIDAD, COL_TOTAL_COMISION,
        PARTICIPACION_FIELD
    ):
        _require_column(DT_CHILD, col)
    # Si realmente usas cost_center en child, exige la columna:
    has_child_cc = frappe.db.has_column(DT_CHILD, COL_COST_CENTER)

    from_date = _get_from_date(filters)
    to_date   = str(filters.get("to_date") or today())

    sales_person = filters.get("sales_person")
    cost_center  = filters.get("cost_center")

    # Columnas del reporte
    columns = [
        {"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Data", "width": 180},
        {"label": _("Sales Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": _("Fecha"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": _("Cliente"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Sucursal"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 180},
        {"label": _("Ingreso"), "fieldname": "ingreso", "fieldtype": "Currency", "precision": 2, "width": 120},
        {"label": _("Costo"), "fieldname": "costo", "fieldtype": "Currency", "precision": 2, "width": 120},
        {"label": _("Utilidad"), "fieldname": "utilidad", "fieldtype": "Currency", "precision": 2, "width": 120},
        {"label": _("% Comisión sobre utilidad (OPC)"), "fieldname": "tasa_opc", "fieldtype": "Percent", "width": 170},
        {"label": _("% Participación"), "fieldname": "participacion", "fieldtype": "Percent", "width": 120},
        {"label": _("Comisión"), "fieldname": "comision", "fieldtype": "Currency", "precision": 2, "width": 120},
        {"label": _("OPC"), "fieldname": "opc", "fieldtype": "Link", "options": DT_OPC, "width": 200},
    ]

    # Fuente única de tasa: tabla por sucursal (CPS). Sin legacy.
    # Cost Center para el match: si existe en child, usa child; si no, usa el de la Sales Invoice.
    cc_expr_for_join = f"c.`{COL_COST_CENTER}`" if has_child_cc else "si.cost_center"
    cc_expr_for_select = cc_expr_for_join  # lo mostramos tal cual

    sql = f"""
        SELECT
            c.`{COL_SALES_PERSON}`   AS sales_person,
            c.`{COL_SI_ID}`          AS sales_invoice,
            si.posting_date          AS posting_date,
            si.customer              AS customer,
            {cc_expr_for_select}     AS cost_center,
            c.`{COL_INGRESO}`        AS ingreso,
            c.`{COL_COSTO}`          AS costo,
            c.`{COL_UTILIDAD}`       AS utilidad,
            cps.porcentaje_comision  AS tasa_opc,        -- SOLO tabla de tasas (CPS)
            c.`{PARTICIPACION_FIELD}` AS participacion,
            c.`{COL_TOTAL_COMISION}`  AS comision,
            c.parent                  AS opc,
            c.name                    AS row_id
        FROM `tab{DT_CHILD}` c
        INNER JOIN `tab{DT_OPC}` opc
            ON opc.name = c.parent AND opc.docstatus = 1
        LEFT JOIN `tabSales Invoice` si
            ON si.name = c.`{COL_SI_ID}` AND si.docstatus = 1
        LEFT JOIN `tab{DT_CPS}` cps
            ON cps.parent = opc.name
           AND cps.cost_center = {cc_expr_for_join}
    """

    where = ["si.posting_date >= %(from_date)s", "si.posting_date <= %(to_date)s"]
    params = {"from_date": from_date, "to_date": to_date}

    if sales_person:
        where.append(f"c.`{COL_SALES_PERSON}` = %(sp)s")
        params["sp"] = sales_person

    if cost_center:
        where.append(f"{cc_expr_for_select} = %(cc)s")
        params["cc"] = cost_center

    sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY c.name"
    sql += f" ORDER BY si.posting_date DESC, c.`{COL_SI_ID}` DESC"

    data = frappe.db.sql(sql, params, as_dict=True)

    # Validación dura: si falta tasa_opc (no hay fila CPS que machee), TRONAR
    missing_tasa = [d for d in data if d.get("tasa_opc") in (None, "")]
    if missing_tasa:
        examples = ", ".join([f"{m.get('opc') or '-'} / {m.get('cost_center') or '-'}" for m in missing_tasa[:5]])
        frappe.throw(
            _("Faltan tasas de comisión en OPC (tabla 'OPC Comision Por Sucursal'). "
              "Ejemplos sin tasa: {0}.").format(examples),
            title=_("Tasa OPC ausente")
        )

    return columns, data