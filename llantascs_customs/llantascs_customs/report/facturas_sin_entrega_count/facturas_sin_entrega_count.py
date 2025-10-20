# -*- coding: utf-8 -*-
# Copyright (c) 2025, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	"""
	Reporte simple que retorna el COUNT de facturas sin entregar.

	Usa la misma lógica del Reporte Diario Director General para determinar
	qué facturas están sin entregar.

	Lógica:
	1. Factura submitted (docstatus = 1)
	2. NO es devolución (is_return = 0)
	3. NO fue entregada de ninguna forma:
	   - update_stock = 0 (no se entregó desde la factura directamente)
	   - Y NO tiene Delivery Note asociado
	4. NO es una factura 100% de servicios
	   (los servicios no requieren entrega física)
	5. NO es una factura de apertura de saldos (Opening Invoice)
	   (tienen item_code NULL)
	"""

	columns = [
		{
			"fieldname": "count",
			"label": _("Cantidad"),
			"fieldtype": "Int",
			"width": 150
		}
	]

	# Obtener el count usando la misma query del Reporte Diario DG
	count = get_undelivered_invoices_count(filters)

	data = [[count]]

	return columns, data


@frappe.whitelist()
def get_undelivered_invoices_count(filters=None):
	"""
	Obtener COUNT de Sales Invoices submitted pero sin entregar.

	Misma lógica que get_undelivered_invoices del Reporte Diario DG.
	"""

	# Construir filtro de centro de costos si se especifica
	cost_center_condition = ""
	if filters and filters.get("cost_center"):
		cost_center_condition = f"AND si.cost_center = '{filters['cost_center']}'"

	# Facturas sin entregar: submitted Y update_stock=0 Y sin DN Y NO solo servicios Y NO opening invoices
	result = frappe.db.sql(f"""
		SELECT COUNT(DISTINCT si.name) as count
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.is_return = 0
		  AND si.update_stock = 0
		  AND NOT EXISTS (
		  	SELECT 1
		  	FROM `tabDelivery Note Item` dni
		  	WHERE dni.against_sales_invoice = si.name
		  	AND dni.docstatus = 1
		  )
		  AND EXISTS (
		  	SELECT 1
		  	FROM `tabSales Invoice Item` sii
		  	LEFT JOIN `tabItem` i ON sii.item_code = i.name
		  	WHERE sii.parent = si.name
		  	  AND (i.item_group IS NULL OR i.item_group NOT LIKE '%Servicio%')
		  )
		  AND NOT EXISTS (
		  	SELECT 1
		  	FROM `tabSales Invoice Item` sii
		  	WHERE sii.parent = si.name
		  	  AND (sii.item_code IS NULL OR sii.item_code = '')
		  )
		  {cost_center_condition}
	""", as_dict=True)

	return result[0].count if result else 0
