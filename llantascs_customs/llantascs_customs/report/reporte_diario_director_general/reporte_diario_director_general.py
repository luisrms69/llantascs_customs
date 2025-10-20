# -*- coding: utf-8 -*-
# Copyright (c) 2025, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, get_first_day, formatdate
from datetime import datetime, timedelta


def execute(filters=None):
	"""
	Reporte Diario para Director General

	Incluye:
	- Resultados Financieros (consolidado + por sucursal)
	- Cobranza
	- Cuentas por Pagar
	- Stock/Inventario
	"""
	if not filters:
		filters = {}

	# Validar filtros
	filters = validate_filters(filters)

	# Este reporte usa template HTML personalizado
	# No retorna datos tabulares tradicionales
	columns = []
	data = []

	# Retornar formato compatible con Query Report UI
	# El PDF se genera mediante el método generate_pdf()
	return columns, data


def validate_filters(filters):
	"""Validar y configurar filtros por defecto"""
	if not filters.get("from_date"):
		# Primer día del mes actual
		filters["from_date"] = get_first_day(getdate())

	if not filters.get("to_date"):
		# Día anterior (para "dato del día anterior")
		filters["to_date"] = add_days(getdate(), -1)

	if not filters.get("cost_center"):
		# Si no hay centro de costos, usar consolidado
		filters["cost_center"] = None

	# Calcular fecha del día anterior para comparaciones
	filters["previous_day"] = add_days(filters["to_date"], -1)

	# Primer día del mes para cálculos acumulados
	filters["month_start"] = get_first_day(filters["to_date"])

	return filters


def get_report_data(filters):
	"""Obtener todos los datos del reporte"""

	data = {
		"filters": filters,
		"company": frappe.defaults.get_global_default("company") or "Llantas de Calidad Star",
		"generated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
	}

	# DATOS CONSOLIDADOS
	data["consolidated"] = get_consolidated_data(filters)

	# DATOS POR SUCURSAL
	if filters.get("cost_center"):
		# Si se especificó un centro de costos, solo ese
		data["branches"] = [get_branch_data(filters, filters["cost_center"])]
	else:
		# Todos los centros de costos (sucursales)
		data["branches"] = get_all_branches_data(filters)

	return data


def get_consolidated_data(filters):
	"""Obtener datos consolidados de toda la empresa"""

	consolidated = {}

	# 1. RESULTADOS FINANCIEROS
	consolidated["financials"] = get_financial_results(filters, None)

	# 2. COBRANZA
	consolidated["receivables"] = get_receivables_data(filters, None)

	# 3. CUENTAS POR PAGAR
	consolidated["payables"] = get_payables_data(filters, None)

	# 4. STOCK/INVENTARIO
	consolidated["inventory"] = get_inventory_data(filters, None)

	# 5. COMPRAS PENDIENTES (POs y PRs)
	consolidated["pending_purchases"] = get_pending_purchases(filters, None)

	# 6. FACTURAS SIN ENTREGAR
	consolidated["undelivered_invoices"] = get_undelivered_invoices(filters, None)

	return consolidated


def get_all_branches_data(filters):
	"""Obtener datos de todas las sucursales"""

	# Obtener lista de centros de costos (sucursales) ordenados alfabéticamente
	cost_centers = frappe.db.sql("""
		SELECT name, cost_center_name
		FROM `tabCost Center`
		WHERE disabled = 0
		  AND parent_cost_center IS NOT NULL
		  AND name NOT LIKE '%Consigna%'
		  AND name NOT LIKE '%Administrativa%'
		ORDER BY cost_center_name ASC
	""", as_dict=True)

	branches = []
	for cc in cost_centers:
		branch_data = get_branch_data(filters, cc.name)
		branch_data["cost_center_name"] = cc.cost_center_name
		branches.append(branch_data)

	return branches


def get_branch_data(filters, cost_center):
	"""Obtener datos de una sucursal específica"""

	branch = {
		"cost_center": cost_center,
	}

	# 1. RESULTADOS FINANCIEROS
	branch["financials"] = get_financial_results(filters, cost_center)

	# 2. COBRANZA
	branch["receivables"] = get_receivables_data(filters, cost_center)

	# 3. CUENTAS POR PAGAR
	branch["payables"] = get_payables_data(filters, cost_center)

	# 4. STOCK/INVENTARIO
	branch["inventory"] = get_inventory_data(filters, cost_center)

	# 5. COMPRAS PENDIENTES (POs y PRs)
	branch["pending_purchases"] = get_pending_purchases(filters, cost_center)

	# 6. FACTURAS SIN ENTREGAR
	branch["undelivered_invoices"] = get_undelivered_invoices(filters, cost_center)

	return branch


# ================================================================================
# SECCIÓN 1: RESULTADOS FINANCIEROS
# ================================================================================

def get_financial_results(filters, cost_center=None):
	"""
	Obtener resultados financieros:
	- Ventas (acumulado mes + día anterior)
	- Margen Bruto (dinero y %)
	- Desglose ventas por grupo de items
	- Ventas por persona de ventas
	"""

	financials = {}

	# Construir filtro de centro de costos
	cost_center_condition = ""
	if cost_center:
		cost_center_condition = f"AND si.cost_center = '{cost_center}'"

	# 1. VENTAS ACUMULADAS DEL MES
	sales_month = frappe.db.sql(f"""
		SELECT
			SUM(si.base_net_total) as sales,
			SUM(si.base_total - si.base_net_total) as taxes,
			SUM(si.base_grand_total) as grand_total,
			COUNT(DISTINCT si.name) as invoice_count
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.posting_date BETWEEN %(month_start)s AND %(to_date)s
		  {cost_center_condition}
	""", filters, as_dict=True)[0]

	# 2. VENTAS DÍA ANTERIOR
	sales_yesterday = frappe.db.sql(f"""
		SELECT
			SUM(si.base_net_total) as sales,
			COUNT(DISTINCT si.name) as invoice_count
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.posting_date = %(previous_day)s
		  {cost_center_condition}
	""", filters, as_dict=True)[0]

	# 3. COGS (Cost of Goods Sold) - Del mes
	cogs_month = get_cogs_for_period(filters["month_start"], filters["to_date"], cost_center)

	# 4. COGS - Día anterior
	cogs_yesterday = get_cogs_for_period(filters["previous_day"], filters["previous_day"], cost_center)

	# Calcular márgenes
	sales_month_value = flt(sales_month.sales, 2)
	cogs_month_value = flt(cogs_month, 2)
	gross_profit_month = sales_month_value - cogs_month_value
	gross_margin_pct_month = (gross_profit_month / sales_month_value * 100) if sales_month_value > 0 else 0

	sales_yesterday_value = flt(sales_yesterday.sales, 2)
	cogs_yesterday_value = flt(cogs_yesterday, 2)
	gross_profit_yesterday = sales_yesterday_value - cogs_yesterday_value
	gross_margin_pct_yesterday = (gross_profit_yesterday / sales_yesterday_value * 100) if sales_yesterday_value > 0 else 0

	financials["sales_month"] = {
		"sales": sales_month_value,
		"cogs": cogs_month_value,
		"gross_profit": gross_profit_month,
		"gross_margin_pct": gross_margin_pct_month,
		"invoice_count": sales_month.invoice_count or 0
	}

	financials["sales_yesterday"] = {
		"sales": sales_yesterday_value,
		"cogs": cogs_yesterday_value,
		"gross_profit": gross_profit_yesterday,
		"gross_margin_pct": gross_margin_pct_yesterday,
		"invoice_count": sales_yesterday.invoice_count or 0
	}

	# 5. DESGLOSE POR GRUPO DE ITEMS (mes acumulado)
	sales_by_item_group = frappe.db.sql(f"""
		SELECT
			COALESCE(i.item_group, 'Sin Grupo') as item_group,
			SUM(sii.base_net_amount) as amount,
			SUM(sii.qty) as qty
		FROM `tabSales Invoice Item` sii
		INNER JOIN `tabSales Invoice` si ON sii.parent = si.name
		LEFT JOIN `tabItem` i ON sii.item_code = i.name
		WHERE si.docstatus = 1
		  AND si.posting_date BETWEEN %(month_start)s AND %(to_date)s
		  {cost_center_condition}
		GROUP BY i.item_group
		ORDER BY amount DESC
	""", filters, as_dict=True)

	financials["sales_by_item_group"] = sales_by_item_group

	# 5b. DESGLOSE POR GRUPO DE ITEMS (día anterior)
	sales_by_item_group_yesterday = frappe.db.sql(f"""
		SELECT
			COALESCE(i.item_group, 'Sin Grupo') as item_group,
			SUM(sii.base_net_amount) as amount,
			SUM(sii.qty) as qty
		FROM `tabSales Invoice Item` sii
		INNER JOIN `tabSales Invoice` si ON sii.parent = si.name
		LEFT JOIN `tabItem` i ON sii.item_code = i.name
		WHERE si.docstatus = 1
		  AND si.posting_date = %(previous_day)s
		  {cost_center_condition}
		GROUP BY i.item_group
		ORDER BY amount DESC
	""", filters, as_dict=True)

	financials["sales_by_item_group_yesterday"] = sales_by_item_group_yesterday

	# 6. VENTAS POR PERSONA DE VENTAS (mes acumulado)
	sales_by_person = frappe.db.sql(f"""
		SELECT
			st.sales_person,
			SUM(st.allocated_amount) as amount,
			COUNT(DISTINCT st.parent) as invoice_count
		FROM `tabSales Team` st
		INNER JOIN `tabSales Invoice` si ON st.parent = si.name
		WHERE si.docstatus = 1
		  AND si.posting_date BETWEEN %(month_start)s AND %(to_date)s
		  {cost_center_condition}
		GROUP BY st.sales_person
		ORDER BY amount DESC
	""", filters, as_dict=True)

	financials["sales_by_person"] = sales_by_person

	return financials


def get_cogs_for_period(from_date, to_date, cost_center=None):
	"""Calcular COGS para un período dado"""

	cost_center_condition = ""
	if cost_center:
		cost_center_condition = f"AND si.cost_center = '{cost_center}'"

	# Método 1: Desde GL Entry (más preciso)
	cogs = frappe.db.sql(f"""
		SELECT
			SUM(ABS(gle.debit - gle.credit)) as cogs
		FROM `tabGL Entry` gle
		INNER JOIN `tabSales Invoice` si ON gle.voucher_no = si.name AND gle.voucher_type = 'Sales Invoice'
		INNER JOIN `tabAccount` acc ON gle.account = acc.name
		WHERE si.docstatus = 1
		  AND si.posting_date BETWEEN '{from_date}' AND '{to_date}'
		  AND acc.account_type = 'Cost of Goods Sold'
		  {cost_center_condition}
	""", as_dict=True)

	return flt(cogs[0].cogs if cogs and cogs[0].cogs else 0, 2)


# ================================================================================
# SECCIÓN 2: COBRANZA
# ================================================================================

def get_receivables_data(filters, cost_center=None):
	"""
	Obtener datos de cobranza:
	- Cuentas por cobrar totales
	- Cuentas por cobrar vencidas
	- Top 10 cuentas más antiguas
	- Top 10 clientes con cuentas más grandes
	"""

	receivables = {}

	cost_center_condition = ""
	if cost_center:
		cost_center_condition = f"AND si.cost_center = '{cost_center}'"

	# 1. TOTAL CUENTAS POR COBRAR
	total_receivables = frappe.db.sql(f"""
		SELECT
			SUM(outstanding_amount) as amount,
			COUNT(*) as count
		FROM `tabSales Invoice` si
		WHERE docstatus = 1
		  AND outstanding_amount > 0
		  {cost_center_condition}
	""", as_dict=True)[0]

	receivables["total"] = {
		"amount": flt(total_receivables.amount, 2),
		"count": total_receivables.count or 0
	}

	# 2. CUENTAS POR COBRAR VENCIDAS
	overdue_receivables = frappe.db.sql(f"""
		SELECT
			SUM(outstanding_amount) as amount,
			COUNT(*) as count
		FROM `tabSales Invoice` si
		WHERE docstatus = 1
		  AND outstanding_amount > 0
		  AND due_date < CURDATE()
		  {cost_center_condition}
	""", as_dict=True)[0]

	receivables["overdue"] = {
		"amount": flt(overdue_receivables.amount, 2),
		"count": overdue_receivables.count or 0
	}

	# 3. TOP 10 CUENTAS MÁS ANTIGUAS
	oldest_invoices = frappe.db.sql(f"""
		SELECT
			si.name,
			si.customer,
			si.posting_date,
			si.due_date,
			si.outstanding_amount,
			DATEDIFF(CURDATE(), si.due_date) as days_overdue
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.outstanding_amount > 0
		  AND si.due_date < CURDATE()
		  {cost_center_condition}
		ORDER BY si.due_date ASC
		LIMIT 10
	""", as_dict=True)

	receivables["oldest"] = oldest_invoices

	# 4. TOP 10 CLIENTES CON CUENTAS MÁS GRANDES
	largest_customers = frappe.db.sql(f"""
		SELECT
			si.customer,
			SUM(si.outstanding_amount) as amount,
			COUNT(*) as invoice_count
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.outstanding_amount > 0
		  {cost_center_condition}
		GROUP BY si.customer
		ORDER BY amount DESC
		LIMIT 10
	""", as_dict=True)

	receivables["largest_customers"] = largest_customers

	return receivables


# ================================================================================
# SECCIÓN 3: CUENTAS POR PAGAR
# ================================================================================

def get_payables_data(filters, cost_center=None):
	"""
	Obtener datos de cuentas por pagar:
	- Total cuentas por pagar
	- Stock recibido pero no facturado
	- Total adeudos
	- Cuentas por pagar vencidas
	- Top 10 facturas más antiguas sin pago
	- Top 10 facturas más grandes sin pago
	"""

	payables = {}

	cost_center_condition = ""
	if cost_center:
		cost_center_condition = f"AND pi.cost_center = '{cost_center}'"

	# 1. TOTAL CUENTAS POR PAGAR
	total_payables = frappe.db.sql(f"""
		SELECT
			SUM(outstanding_amount) as amount,
			COUNT(*) as count
		FROM `tabPurchase Invoice` pi
		WHERE docstatus = 1
		  AND outstanding_amount > 0
		  {cost_center_condition}
	""", as_dict=True)[0]

	payables["total"] = {
		"amount": flt(total_payables.amount, 2),
		"count": total_payables.count or 0
	}

	# 2. STOCK RECIBIDO PERO NO FACTURADO
	# Construir condición de cost_center para Purchase Receipt
	pr_cost_center_condition = ""
	if cost_center:
		pr_cost_center_condition = f"AND pr.cost_center = '{cost_center}'"

	stock_received_not_billed = frappe.db.sql(f"""
		SELECT
			SUM(pr.base_grand_total - COALESCE(pr.per_billed, 0) / 100 * pr.base_grand_total) as amount,
			COUNT(*) as count
		FROM `tabPurchase Receipt` pr
		WHERE pr.docstatus = 1
		  AND pr.status = 'To Bill'
		  AND pr.per_billed < 100
		  {pr_cost_center_condition}
	""", as_dict=True)[0]

	payables["stock_not_billed"] = {
		"amount": flt(stock_received_not_billed.amount, 2),
		"count": stock_received_not_billed.count or 0
	}

	# 3. TOTAL ADEUDOS (suma de ambos)
	payables["total_debt"] = {
		"amount": payables["total"]["amount"] + payables["stock_not_billed"]["amount"]
	}

	# 4. CUENTAS POR PAGAR VENCIDAS
	overdue_payables = frappe.db.sql(f"""
		SELECT
			SUM(outstanding_amount) as amount,
			COUNT(*) as count
		FROM `tabPurchase Invoice` pi
		WHERE docstatus = 1
		  AND outstanding_amount > 0
		  AND due_date < CURDATE()
		  {cost_center_condition}
	""", as_dict=True)[0]

	payables["overdue"] = {
		"amount": flt(overdue_payables.amount, 2),
		"count": overdue_payables.count or 0
	}

	# 5. TOP 10 FACTURAS MÁS ANTIGUAS SIN PAGO
	oldest_invoices = frappe.db.sql(f"""
		SELECT
			pi.name,
			pi.supplier,
			pi.posting_date,
			pi.due_date,
			pi.outstanding_amount,
			DATEDIFF(CURDATE(), pi.due_date) as days_overdue
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1
		  AND pi.outstanding_amount > 0
		  AND pi.due_date < CURDATE()
		  {cost_center_condition}
		ORDER BY pi.due_date ASC
		LIMIT 10
	""", as_dict=True)

	payables["oldest"] = oldest_invoices

	# 6. TOP 10 FACTURAS MÁS GRANDES SIN PAGO
	largest_invoices = frappe.db.sql(f"""
		SELECT
			pi.name,
			pi.supplier,
			pi.posting_date,
			pi.due_date,
			pi.outstanding_amount
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1
		  AND pi.outstanding_amount > 0
		  {cost_center_condition}
		ORDER BY pi.outstanding_amount DESC
		LIMIT 10
	""", as_dict=True)

	payables["largest"] = largest_invoices

	return payables


# ================================================================================
# SECCIÓN 4: STOCK/INVENTARIO
# ================================================================================

def get_inventory_data(filters, cost_center=None):
	"""
	Obtener datos de inventario:
	- Valor total del inventario
	- Valor por item group
	- Cantidad llantas
	- Top llantas por valor
	- Top llantas por antigüedad
	- Desglose por almacén
	- Tendencia valor inventario
	"""

	inventory = {}

	# Para filtro de warehouse por centro de costos
	warehouse_condition = ""
	if cost_center:
		# Mapear centro de costos a warehouse(s)
		warehouses = get_warehouses_for_cost_center(cost_center)
		if warehouses:
			warehouse_list = "', '".join(warehouses)
			warehouse_condition = f"AND bin.warehouse IN ('{warehouse_list}')"

	# 1. VALOR TOTAL DEL INVENTARIO
	total_inventory = frappe.db.sql(f"""
		SELECT
			SUM(bin.stock_value) as value,
			SUM(bin.actual_qty) as qty
		FROM `tabBin` bin
		WHERE bin.actual_qty > 0
		  {warehouse_condition}
	""", as_dict=True)[0]

	inventory["total"] = {
		"value": flt(total_inventory.value, 2),
		"qty": flt(total_inventory.qty, 2)
	}

	# 2. VALOR POR ITEM GROUP
	value_by_item_group = frappe.db.sql(f"""
		SELECT
			COALESCE(i.item_group, 'Sin Grupo') as item_group,
			SUM(bin.stock_value) as value,
			SUM(bin.actual_qty) as qty
		FROM `tabBin` bin
		INNER JOIN `tabItem` i ON bin.item_code = i.name
		WHERE bin.actual_qty > 0
		  {warehouse_condition}
		GROUP BY i.item_group
		ORDER BY value DESC
	""", as_dict=True)

	inventory["by_item_group"] = value_by_item_group

	# 3. CANTIDAD TOTAL LLANTAS
	llantas_qty = frappe.db.sql(f"""
		SELECT
			SUM(bin.actual_qty) as qty,
			SUM(bin.stock_value) as value
		FROM `tabBin` bin
		INNER JOIN `tabItem` i ON bin.item_code = i.name
		WHERE bin.actual_qty > 0
		  AND i.item_group = 'Llantas'
		  {warehouse_condition}
	""", as_dict=True)[0]

	inventory["llantas"] = {
		"qty": flt(llantas_qty.qty, 2),
		"value": flt(llantas_qty.value, 2)
	}

	# 4. TOP 10 LLANTAS POR VALOR
	top_llantas_value = frappe.db.sql(f"""
		SELECT
			bin.item_code,
			i.item_name,
			bin.warehouse,
			bin.actual_qty as qty,
			bin.stock_value as value,
			bin.valuation_rate
		FROM `tabBin` bin
		INNER JOIN `tabItem` i ON bin.item_code = i.name
		WHERE bin.actual_qty > 0
		  AND i.item_group = 'Llantas'
		  {warehouse_condition}
		ORDER BY bin.stock_value DESC
		LIMIT 10
	""", as_dict=True)

	inventory["top_llantas_value"] = top_llantas_value

	# 5. TOP 10 LLANTAS POR ANTIGÜEDAD
	# Usamos Stock Ledger Entry para obtener fecha de entrada más antigua
	oldest_llantas = frappe.db.sql(f"""
		SELECT
			sle.item_code,
			i.item_name,
			sle.warehouse,
			MIN(sle.posting_date) as oldest_date,
			DATEDIFF(CURDATE(), MIN(sle.posting_date)) as days_old,
			SUM(CASE WHEN sle.actual_qty > 0 THEN sle.actual_qty ELSE 0 END) as qty
		FROM `tabStock Ledger Entry` sle
		INNER JOIN `tabItem` i ON sle.item_code = i.name
		WHERE i.item_group = 'Llantas'
		  AND sle.actual_qty != 0
		  {warehouse_condition.replace('bin.', 'sle.')}
		GROUP BY sle.item_code, sle.warehouse
		HAVING qty > 0
		ORDER BY oldest_date ASC
		LIMIT 10
	""", as_dict=True)

	inventory["oldest_llantas"] = oldest_llantas

	# 6. DESGLOSE POR ALMACÉN
	by_warehouse = frappe.db.sql(f"""
		SELECT
			bin.warehouse,
			SUM(bin.stock_value) as value,
			SUM(bin.actual_qty) as qty
		FROM `tabBin` bin
		WHERE bin.actual_qty > 0
		  {warehouse_condition}
		GROUP BY bin.warehouse
		ORDER BY value DESC
	""", as_dict=True)

	inventory["by_warehouse"] = by_warehouse

	# 7. TENDENCIA VALOR INVENTARIO (primer día de cada mes, últimos 12 meses)
	inventory_trend = get_inventory_trend(warehouse_condition)
	inventory["trend"] = inventory_trend

	return inventory


def get_warehouses_for_cost_center(cost_center):
	"""Mapear centro de costos a warehouses correspondientes"""

	# Mapeo manual basado en nombres (puede ajustarse)
	# Formato: "101 - COATZA AUTOS 1 - LLCS" -> "Almacen Coatza Autos 1 - LLCS"

	cost_center_name = cost_center.split(" - ")[1] if " - " in cost_center else cost_center

	warehouses = frappe.db.sql("""
		SELECT name
		FROM `tabWarehouse`
		WHERE disabled = 0
		  AND (
		    warehouse_name LIKE %s
		    OR name LIKE %s
		  )
	""", (f"%{cost_center_name}%", f"%{cost_center_name}%"), as_list=True)

	return [w[0] for w in warehouses] if warehouses else []


def get_inventory_trend(warehouse_condition):
	"""Obtener tendencia de valor de inventario (último día de cada mes, últimos 12 meses)"""

	from dateutil.relativedelta import relativedelta

	trend = []
	current_date = getdate()

	# Últimos 12 meses
	for i in range(11, -1, -1):
		# Último día del mes
		target_date = current_date - relativedelta(months=i)
		month_end = add_days(get_first_day(target_date) + relativedelta(months=1), -1)

		# Si el mes es el actual, usar la fecha actual
		if i == 0:
			month_end = current_date

		# Calcular valor del inventario acumulado hasta esa fecha
		# Suma acumulada de todos los stock_value_difference hasta esa fecha
		value = frappe.db.sql(f"""
			SELECT
				SUM(sle.stock_value_difference) as cumulative_value
			FROM `tabStock Ledger Entry` sle
			WHERE sle.posting_date <= '{month_end}'
			  AND sle.is_cancelled = 0
			  {warehouse_condition.replace('bin.', 'sle.') if warehouse_condition else ''}
		""", as_dict=True)

		cumulative_value = flt(value[0].cumulative_value if value and value[0].cumulative_value else 0, 2)

		trend.append({
			"date": month_end,
			"month": formatdate(month_end, "MMM yyyy"),
			"value": cumulative_value
		})

	return trend


# ================================================================================
# SECCIÓN 5: PURCHASE ORDERS Y PURCHASE RECEIPTS PENDIENTES
# ================================================================================

def get_pending_purchases(filters, cost_center=None):
	"""
	Obtener compras pendientes:
	- Purchase Orders no recibidas
	- Purchase Receipts to bill / partially billed
	"""

	pending = {}

	# Construir filtro de centro de costos para Purchase Orders
	po_cost_center_condition = ""
	if cost_center:
		po_cost_center_condition = f"AND po.cost_center = '{cost_center}'"

	# 1. PURCHASE ORDERS PENDIENTES (no recibidas completamente)
	pending_pos = frappe.db.sql(f"""
		SELECT
			po.name,
			po.supplier,
			po.transaction_date,
			po.schedule_date,
			po.base_grand_total,
			po.per_received,
			(po.base_grand_total * (100 - COALESCE(po.per_received, 0)) / 100) as pending_amount
		FROM `tabPurchase Order` po
		WHERE po.docstatus = 1
		  AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')
		  AND COALESCE(po.per_received, 0) < 100
		  {po_cost_center_condition}
		ORDER BY po.transaction_date ASC
	""", as_dict=True)

	pending["purchase_orders"] = {
		"list": pending_pos,
		"count": len(pending_pos),
		"total_amount": sum([flt(po.pending_amount, 2) for po in pending_pos])
	}

	# Construir filtro de centro de costos para Purchase Receipts
	pr_cost_center_condition = ""
	if cost_center:
		pr_cost_center_condition = f"AND pr.cost_center = '{cost_center}'"

	# 2. PURCHASE RECEIPTS TO BILL / PARTIALLY BILLED
	pending_prs = frappe.db.sql(f"""
		SELECT
			pr.name,
			pr.supplier,
			pr.posting_date,
			pr.base_grand_total,
			pr.per_billed,
			pr.status,
			(pr.base_grand_total * (100 - COALESCE(pr.per_billed, 0)) / 100) as pending_amount
		FROM `tabPurchase Receipt` pr
		WHERE pr.docstatus = 1
		  AND pr.status IN ('To Bill', 'Partly Billed')
		  AND COALESCE(pr.per_billed, 0) < 100
		  {pr_cost_center_condition}
		ORDER BY pr.posting_date ASC
	""", as_dict=True)

	pending["purchase_receipts"] = {
		"list": pending_prs,
		"count": len(pending_prs),
		"total_amount": sum([flt(pr.pending_amount, 2) for pr in pending_prs])
	}

	return pending


# ================================================================================
# SECCIÓN 6: SALES INVOICES SIN ENTREGAR
# ================================================================================

def get_undelivered_invoices(filters, cost_center=None):
	"""
	Obtener Sales Invoices submitted pero sin entregar.

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

	No se considera el status de pago ni límites de tiempo.
	"""

	# Construir filtro de centro de costos
	cost_center_condition = ""
	if cost_center:
		cost_center_condition = f"AND si.cost_center = '{cost_center}'"

	# Facturas sin entregar: submitted Y update_stock=0 Y sin DN Y NO solo servicios Y NO opening invoices
	undelivered = frappe.db.sql(f"""
		SELECT
			si.name,
			si.customer,
			si.posting_date,
			si.base_grand_total,
			si.status,
			si.update_stock
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
		ORDER BY si.posting_date DESC
	""", as_dict=True)

	return {
		"list": undelivered,
		"count": len(undelivered),
		"total_amount": sum([flt(inv.base_grand_total, 2) for inv in undelivered])
	}


# ================================================================================
# PDF/HTML GENERATION
# ================================================================================

def get_html(filters=None):
	"""
	Método para obtener HTML del reporte.

	Retorna el HTML renderizado del reporte usando el template Jinja2.
	"""
	if not filters:
		filters = {}

	# Validar filtros
	filters = validate_filters(filters)

	# Obtener datos del reporte
	report_data = get_report_data(filters)

	# Renderizar template HTML
	html = frappe.render_template(
		"llantascs_customs/report/reporte_diario_director_general/reporte_diario_director_general.html",
		{"data": report_data}
	)

	return html


@frappe.whitelist()
def generate_pdf(filters=None):
	"""
	Método para generar PDF desde la interfaz de ERPNext.

	Genera el PDF y lo guarda temporalmente, retornando la URL para descarga.
	"""
	import json
	import os

	if isinstance(filters, str):
		filters = json.loads(filters)

	# Obtener HTML del reporte
	html = get_html(filters)

	# Usar la función de Frappe para generar PDF desde HTML
	from frappe.utils.pdf import get_pdf
	from frappe.utils import now_datetime, get_site_path

	pdf = get_pdf(html)

	# Crear nombre de archivo
	filename = f"Reporte_Director_General_{now_datetime().strftime('%Y%m%d_%H%M%S')}.pdf"

	# Guardar en directorio temporal del sitio
	file_path = os.path.join(get_site_path(), 'public', 'files', filename)

	with open(file_path, 'wb') as f:
		f.write(pdf)

	# Retornar URL del archivo
	return f"/files/{filename}"


@frappe.whitelist()
def generate_html(filters=None):
	"""
	Método para generar HTML desde la interfaz de ERPNext.

	Genera el HTML y lo guarda temporalmente, retornando la URL para visualización.
	"""
	import json
	import os

	if isinstance(filters, str):
		filters = json.loads(filters)

	# Obtener HTML del reporte
	html = get_html(filters)

	# Crear nombre de archivo
	from frappe.utils import now_datetime, get_site_path
	filename = f"Reporte_Director_General_{now_datetime().strftime('%Y%m%d_%H%M%S')}.html"

	# Guardar en directorio temporal del sitio
	file_path = os.path.join(get_site_path(), 'public', 'files', filename)

	with open(file_path, 'w', encoding='utf-8') as f:
		f.write(html)

	# Retornar URL del archivo
	return f"/files/{filename}"
