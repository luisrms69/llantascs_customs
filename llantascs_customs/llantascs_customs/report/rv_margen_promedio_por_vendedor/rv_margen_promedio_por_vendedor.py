# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import nowdate, getdate

DT_CHILD = "Comision LLCS"
DT_OPC   = "Orden de Pago Comisiones"
DT_SI    = "Sales Invoice"

CLL_SP       = "persona_de_ventas"
CLL_SI       = "sales_invoice_id"
CLL_INGRESO  = "ingreso"
CLL_UTIL     = "utilidad_transaccion"
SI_POSTING   = "posting_date"
SI_CC        = "cost_center"

def execute(filters=None):
    filters = filters or {}
    vendedor  = filters.get("vendedor")
    sucursal  = filters.get("sucursal")
    from_date = filters.get("from_date") or "2025-01-01"
    to_date   = filters.get("to_date") or nowdate()

    if getdate(from_date) > getdate(to_date):
        frappe.throw(_("Rango inválido: desde {0} > hasta {1}").format(from_date, to_date))

    where = [
        "opc.docstatus = 1",
        "si.docstatus = 1",
        f"si.{SI_POSTING} BETWEEN %(from_date)s AND %(to_date)s",
        f"COALESCE(c.`{CLL_INGRESO}`,0) > 0"
    ]
    params = {"from_date": from_date, "to_date": to_date}

    if vendedor:
        where.append(f"c.`{CLL_SP}` = %(vendedor)s")
        params["vendedor"] = vendedor
    if sucursal:
        where.append(f"si.{SI_CC} = %(sucursal)s")
        params["sucursal"] = sucursal

    # Promedio del % margen por vendedor: promedio de (utilidad/ingreso)*100
    sql = f"""
        SELECT
            COALESCE(c.`{CLL_SP}`,'(Sin vendedor)') AS sales_person,
            AVG( (COALESCE(c.`{CLL_UTIL}`,0) / NULLIF(c.`{CLL_INGRESO}`,0)) * 100.0 ) AS value
        FROM `tab{DT_CHILD}` c
        JOIN `tab{DT_OPC}` opc ON opc.name = c.parent AND opc.docstatus = 1
        JOIN `tab{DT_SI}`  si  ON si.name  = c.`{CLL_SI}` AND si.docstatus = 1
        WHERE {" AND ".join(where)}
        GROUP BY COALESCE(c.`{CLL_SP}`,'(Sin vendedor)')
        ORDER BY value DESC
    """
    data = frappe.db.sql(sql, params, as_dict=True)

    columns = [
        {"label": _("Vendedor"),           "fieldname": "sales_person", "fieldtype": "Data",    "width": 220},
        {"label": _("% Margen Promedio"),  "fieldname": "value",        "fieldtype": "Percent", "width": 140}
    ]
    return columns, data