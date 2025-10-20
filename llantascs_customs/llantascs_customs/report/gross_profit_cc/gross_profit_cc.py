# -*- coding: utf-8 -*-
# Copyright (c) 2025, Llantas CS and contributors
# For license information, please see license.txt

from erpnext.accounts.report.gross_profit.gross_profit import execute as gross_profit_execute

def execute(filters=None):
	"""
	Wrapper del reporte Gross Profit con group_by predefinido en Cost Center
	"""
	if not filters:
		filters = {}

	# Forzar group_by a Cost Center si no está establecido
	if not filters.get('group_by'):
		filters['group_by'] = 'Cost Center'

	return gross_profit_execute(filters)
