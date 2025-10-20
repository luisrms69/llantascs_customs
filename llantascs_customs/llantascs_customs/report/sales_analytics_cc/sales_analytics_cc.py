# -*- coding: utf-8 -*-
# Copyright (c) 2025, Llantas CS and contributors
# For license information, please see license.txt

from erpnext.selling.report.sales_analytics.sales_analytics import execute as sales_analytics_execute

def execute(filters=None):
	"""
	Wrapper del reporte Sales Analytics
	NOTA: Sales Analytics nativo NO soporta Cost Center como tree_type.
	Opciones válidas: Customer, Customer Group, Item, Item Group, Territory, Order Type, Project
	"""
	if not filters:
		filters = {}

	# Asegurar tree_type requerido con default a Customer
	if not filters.get('tree_type'):
		filters['tree_type'] = 'Customer'

	# Asegurar doc_type con default a Sales Invoice
	if not filters.get('doc_type'):
		filters['doc_type'] = 'Sales Invoice'

	return sales_analytics_execute(filters)
