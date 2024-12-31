# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from llantascs_customs.llantascs_customs.api import *

class OrdendePagoComisiones(Document):	
	def create_orden_pago_comision(self):
		table = get_sales_invoices(self.sucursal,self.desde, self.hasta_fecha)
		for invoice in table:
			actualizar_status_sales_invoice(invoice.name,1)
			actualizar_orden_pago_sales_invoice(invoice.name, self.name)
		
	def on_submit(self):
		self.create_orden_pago_comision()
