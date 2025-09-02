# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now
from llantascs_customs.llantascs_customs.api import *

class OrdendePagoComisiones(Document):	
	def before_save(self):
		"""Siempre recalcular ambas tablas al guardar, aunque el usuario no presione 'Actualizar Listado'."""
		self._force_update_comisiones()

	def before_submit(self):
		"""Revalidar también al enviar, como doble capa de seguridad."""
		self._force_update_comisiones()

	def _force_update_comisiones(self):
		"""Reusa la lógica del botón Actualizar Listado para poblar SIEMPRE ambas tablas."""
		sucursales = []
		if isinstance(self.sucursales_multi, list):
			sucursales = [r.cost_center for r in self.sucursales_multi if r.cost_center]
		elif self.sucursales_multi:
			try:
				import json
				sucursales = json.loads(self.sucursales_multi)
			except Exception:
				pass

		if not sucursales:
			frappe.throw("Debe seleccionar al menos una sucursal antes de guardar la OPC.")

		# === 1. Poblar tasas por sucursal ===
		rates = sync_rates_from_settings(sucursales)
		self.set("comisiones_por_sucursal", [])
		for row in rates.get("rows", []):
			self.append("comisiones_por_sucursal", row)

		# === 2. Poblar comisiones incluidas ===
		rates_map = {
			r.cost_center: flt(r.porcentaje_comision)
			for r in self.comisiones_por_sucursal if r.cost_center
		}

		data = get_commission_rows(
			sucursales,
			self.desde,
			self.hasta_fecha,
			rates_by_cc=rates_map  # <-- ya no usamos docname
		)

		self.set("comisiones_incluidas", [])
		for row in data.get("rows", []):
			self.append("comisiones_incluidas", row)

		# Subtotales
		self.subtotal_comisiones_negativas = data.get("subtotal_negativas", 0)
		self.monto_total = data.get("total", 0)

	def create_orden_pago_comision(self):
		# Multisucursal: normalizar desde la tabla sucursales_multi
		selected_cc = [r.cost_center for r in (self.sucursales_multi or []) if r.cost_center]
		if not (self.desde and self.hasta_fecha and selected_cc):
			frappe.throw("Faltan filtros obligatorios: sucursales, fecha inicial y fecha final.")

		# Reusar fuente única de filtros
		invoices = get_sales_invoices(selected_cc, self.desde, self.hasta_fecha)

		# Actualizar estatus/enlace en cada SI incluida
		for si in (invoices or []):
			inv_name = si.get("name") or getattr(si, "name", None)
			if not inv_name:
				continue
			actualizar_status_sales_invoice(inv_name, 1)            # "Enviado"
			actualizar_orden_pago_sales_invoice(inv_name, self.name)

		# Estado de la propia OPC (si tu flujo lo usa)
		actualizar_status_orden_pago(self.name, 1)
		
	def on_submit(self):
		self.create_orden_pago_comision()

	def before_cancel(self):
		"""Bloquear cancelación de OPC si existen Sales Invoices vinculadas activas"""
		# 1) SI referenciadas desde la tabla hija (comisiones_incluidas)
		si_names = [r.sales_invoice_id for r in (self.comisiones_incluidas or []) if r.sales_invoice_id]
		si_names = list({s for s in si_names if s})  # únicos, no vacíos

		linked_active = 0
		if si_names:
			linked_active = frappe.db.count(
				"Sales Invoice",
				filters={"name": ["in", si_names], "docstatus": 1}  # 1 = Submitted (activa)
			)

		# 2) (Opcional) SI referenciada por campo en SI (si aún lo usas como Data/Link)
		if not linked_active:
			extra_linked = frappe.db.count(
				"Sales Invoice",
				filters={"custom_orden_de_pago_comision": self.name, "docstatus": 1}
			)
			linked_active += extra_linked

		if linked_active > 0:
			frappe.throw(
				f"""
				<div>
				  <h5 style="margin:0 0 6px 0;">Cancelación bloqueada</h5>
				  <div>Esta Orden de Pago de Comisiones tiene <b>{linked_active}</b> factura(s) de venta vinculada(s) activas.</div>
				  <div style="margin-top:8px;">
				    Para ajustar comisiones, cancele las facturas individuales. Los <i>ajustes de comisión</i> se generarán automáticamente.
				  </div>
				</div>
				""",
				title="No se puede cancelar la OPC"
			)
