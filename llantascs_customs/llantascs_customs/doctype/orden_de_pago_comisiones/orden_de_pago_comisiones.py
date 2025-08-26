# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint
from llantascs_customs.llantascs_customs.api import *

class OrdendePagoComisiones(Document):
	def before_insert(self):
		self._ensure_branch_rates_snapshot()

	def validate(self):
		"""B.4: Acumuladores y total pagable con política de negativos."""
		pos = 0.0
		neg = 0.0
		
		for row in (self.comisiones_incluidas or []):
			v = flt(getattr(row, "comision_a_pagar", None) or getattr(row, "total_comision", 0))
			if v >= 0:
				pos += v
			else:
				neg += v  # neg es <= 0

		self.total_comision_bruta = pos
		self.total_compensaciones_negativas = neg

		# Net pagable
		neto = pos + neg

		# Settings: cap o permitir negativo
		ss = frappe.get_single("Comisiones Settings")
		permitir_negativo = cint(getattr(ss, "permitir_total_orden_negativo", 0))

		# Si NO se permite negativo, cap en 0 para respetar non_negative del JSON
		self.monto_total = neto if permitir_negativo else max(0.0, neto)

	def _ensure_branch_rates_snapshot(self):
		"""Si no hay snapshot en la orden, copiar las tasas por sucursal desde Settings."""
		if self.get("rates_por_sucursal_orden"):
			return
		ss = frappe.get_single("Comisiones Settings")
		settings_rows = ss.get("rates_por_sucursal") or []
		for r in settings_rows:
			self.append("rates_por_sucursal_orden", {
				"cost_center": r.cost_center,
				"rate_percent": r.rate_percent,
			})
		# también puedes setear un % por defecto a nivel orden si aplica
		if not getattr(self, "comision_sobre_utilidad_", None):
			try:
				default_rate = frappe.db.get_single_value("Comisiones Settings", "porcentaje_sobre_utilidad") or 0
				self.comision_sobre_utilidad_ = default_rate
			except Exception:
				pass

	def create_orden_pago_comision(self):
		table = get_sales_invoices(self.sucursal,self.desde, self.hasta_fecha)
		for invoice in table:
			actualizar_status_sales_invoice(invoice.name,1)
			actualizar_orden_pago_sales_invoice(invoice.name, self.name)
		
		actualizar_status_orden_pago(self.name, 1)
		
	def on_submit(self):
		self.create_orden_pago_comision()
