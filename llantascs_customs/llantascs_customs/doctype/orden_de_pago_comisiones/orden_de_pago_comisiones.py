# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now
from llantascs_customs.llantascs_customs.api import *

class OrdendePagoComisiones(Document):	
	def before_save(self):
		"""Al guardar: asegurar tasas si están vacías y (si hay filtros) reconstruir comisiones."""
		self._ensure_rates_if_empty()
		self._rebuild_commissions_using_current_rates()

	def before_submit(self):
		"""Revalidar también al enviar, como doble capa de seguridad."""
		self._ensure_rates_if_empty()
		self._rebuild_commissions_using_current_rates()

	def _ensure_rates_if_empty(self):
		"""Solo poblar comisiones_por_sucursal si está VACÍA; no tocar si el usuario ya editó."""
		if self.comisiones_por_sucursal and len(self.comisiones_por_sucursal) > 0:
			return  # respetar ediciones del usuario

		# Construir desde sucursales_multi + Settings
		settings = frappe.get_single("Comisiones Settings")
		default_rate = flt(getattr(settings, "porcentaje_sobre_utilidad", 0))  # o 0 si no hay

		self.comisiones_por_sucursal = []
		for row in (self.sucursales_multi or []):
			if not row.cost_center:
				continue
			self.append("comisiones_por_sucursal", {
				"cost_center": row.cost_center,
				"porcentaje_comision": default_rate
			})

	def _rebuild_commissions_using_current_rates(self):
		"""Reconstruir comisiones_incluidas usando las tasas actuales del documento."""
		# Validaciones mínimas: si faltan filtros o sucursales, no calcular
		if not self.desde or not self.hasta_fecha:
			return
		suc_list = [r.cost_center for r in (self.sucursales_multi or []) if r.cost_center]
		if not suc_list:
			return

		# Mapear tasas desde la tabla del documento
		rates_map = {}
		for r in (self.comisiones_por_sucursal or []):
			if r.cost_center:
				rates_map[r.cost_center] = flt(r.porcentaje_comision)

		# Llamar API y manejar correctamente la estructura dict resultante
		data = get_commission_rows(
			suc_list,
			self.desde,
			self.hasta_fecha,
			rates_by_cc=rates_map,
			docname=None  # no pases self.name en documentos nuevos
		)

		# Data puede ser None o dict; si es dict, esperamos keys: rows, total, etc.
		rows = []
		total = 0.0
		subtotal_neg = 0.0

		if isinstance(data, dict):
			rows = data.get("rows", []) or []
			total = flt(data.get("total", 0))
			# si tu API devuelve subtotal de negativas:
			subtotal_neg = flt(data.get("subtotal_negativas", 0))

		# Reemplazar tabla comisiones_incluidas con las filas calculadas
		self.comisiones_incluidas = []
		for row in rows:
			# asegurar que row es dict
			if isinstance(row, dict):
				self.append("comisiones_incluidas", row)

		# Asignar totales si tus campos existen
		if hasattr(self, "monto_total"):
			self.monto_total = total
		if hasattr(self, "subtotal_comisiones_negativas"):
			self.subtotal_comisiones_negativas = subtotal_neg

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
