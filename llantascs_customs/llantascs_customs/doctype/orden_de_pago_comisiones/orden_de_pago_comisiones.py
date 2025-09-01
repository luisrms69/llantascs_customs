# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from llantascs_customs.llantascs_customs.api import *

class OrdendePagoComisiones(Document):	
	def before_save(self):
		selected_cc = [r.cost_center for r in (self.sucursales_multi or []) if r.cost_center]
		if not (self.desde and self.hasta_fecha and selected_cc):
			return

		rates_map = {r.cost_center: flt(r.porcentaje_comision)
					 for r in (self.comisiones_por_sucursal or []) if r.cost_center}

		out = get_commission_rows(
			selected_cc,
			self.desde,
			self.hasta_fecha,
			# clave: usar tasas del doc EN MEMORIA (no BD)
			rates_by_cc=rates_map
		)

		self.set("comisiones_incluidas", [])
		for row in out.get("rows", []):
			self.append("comisiones_incluidas", row)
		self.monto_total = flt(out.get("total", 0))
		self.subtotal_comisiones_negativas = flt(out.get("subtotal_negativas", 0))

	def create_orden_pago_comision(self):
		table = get_sales_invoices(self.sucursal,self.desde, self.hasta_fecha)
		for invoice in table:
			actualizar_status_sales_invoice(invoice.name,1)
			actualizar_orden_pago_sales_invoice(invoice.name, self.name)
		
		actualizar_status_orden_pago(self.name, 1)
		
	def on_submit(self):
		self.create_orden_pago_comision()
