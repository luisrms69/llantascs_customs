# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
# from frappe import _
# from frappe.model.document import Document
# import requests  # Se utiliza para hacer el http request
# from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
from llantascs_customs.llantascs_customs.api import *

class OrdendePagoComisiones(Document):	
	def create_orden_pago_comision(self):
		table = get_sales_invoices(self.sucursal,self.desde, self.hasta_fecha)
		for invoice in table:
			actualizar_status_sales_invoice(invoice.name,1)
			actualizar_orden_pago_sales_invoice(invoice.name, self.name)

        # frappe.db.set_value("Sales Invoice", invoice_id,
        #                   'custom_orden_de_pago_comision', orden_de_pago)

		# self.fecha_envio = Now
		# get_costo_ventas_sales_invoice('ACC-SINV-2024-00096')


		# Se obtienen los datos de producto, estan en un child table
	# get_sales_invoices(invoice_data)

		# frappe.msgprint(str(table))
		
	def on_submit(self):
		self.create_orden_pago_comision()


 
#Metodo que se corre para validar si los campos son correctos
# refactor: si es lo mismo en receipts, crear funcion que agrupe todo   
# def validate(self):
#         validate_data_invoice(self)

# #Metodo que se corre al enviar (submit) solicitar creacion de la factura
#     def on_update(self):
#         self.create_cfdi()



	# def test(doc, method):
	# 	frappe.msgprint("Im in")
	# 	frappe.msgprint(str(doc))
	# 	frappe.msgprint(str(method))
	# 	calcula_monto_comision(doc)

	# def get_cogs_sales_invoice(doc_name):
	# 	cogs = frappe.db.get_value('Stock Ledger Entry', {'voucher_no': 'ACC-SINV-2024-00096'},'stock_value_difference')


	# 	frappe.msgprint(str(cogs))
	# 	frappe.msgprint(str(doc_name))
	# 	return cogs



	# def calcula_monto_comision(doc):
	# 	income = doc.amount_eligible_for_commission
	# 	cogs = get_cogs_sales_invoice(doc.name)
	# 	# for item in doc.items:
	# 	#     if item.grant_commission == 1:
	# 	#         income = income + item.base_net_amount
	# 	#         cogs = cogs + (item.qty * item.incoming_rate)
		
		
		
	# 	# frappe.msgprint(str(doc.amount_eligible_for_commission))
	# 	frappe.msgprint(str(income))
	# 	frappe.msgprint(str(cogs))
	
        
# #Metodo para solicitar la creacion de una factura
#     def create_cfdi(self):
# #Primero solicita la definicion de variables del documento actual   
#         current_document = self.get_title()
#         sales_invoice_id = frappe.db.get_value(
#             'Factura', current_document, 'sales_invoice_id')
#         invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id)
#         cliente = get_cliente(invoice_data)
#         datos_direccion = get_datos_direccion_facturacion(cliente)
#         use = get_uso_cfdi(cliente)
#         tax_id = get_tax_id(cliente)
#         email_id = datos_direccion.email_id
#         tipo = frappe.db.get_value('Tipo de Comprobante', frappe.db.get_value(
#             'Factura', current_document, 'tipo'), 'tipo_de_comprobante') 


# # Pendiente configuración o automatización
#         type = tipo
#         folio_number = 0
#         series = ""
#         # addenda = "<?xml version='1.0' encoding='UTF-8'?> <root></root>"
#         pdf_custom_section = ""
#         payment_related_ids =[]
#         payment_method = frappe.db.get_value('Metodo de Pago', frappe.db.get_value('Factura', current_document, 'metodo_pago_sat'), 'metodo_pago')

# # Pendiente configuración de estos campos, NO SE VAN A OCUPAR, SE DEJA EL PLACER
#         currency = "MXN"
#         exchange = 1  # ESTO DEBERA CONFIGURARSE DE OTRA MANERA
#         conditions = ""
#         related_documents = []
#         export = "01"
#         complements = []
#         status = "pending"
#         date = "" # ESTE CAMPO NO LO VOY A CONFIGURAR, EL DEFAULT ES NOW
#         address = {}
#         external_id = ""
#         idempotency_key = ""
#         namespaces = []
#         pdf_options = {}

# #Despues se arma el http request. endpoint, headers y data. Los valores de headers y endpoint se toman de settings
# #Los valores de data se arman en este metodo, hacen llamadas a los metodos de la clase creada (Factura)
#         facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_facturas')
#         api_token = get_api_token_live()
#         # api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
#         headers = {"Authorization": f"Bearer {api_token}"}
#         data = {
#             "payment_form": frappe.db.get_value('Factura', current_document, 'foma_de_pago_sat'),
#             "use": use,
#             "payment_method": payment_method,
#             "type": type,
#             # "currency": currency, VIENE POR DEFAULT
#             # "exchange": exchange, VIENE POR DEFAULT
#             # "conditions": conditions, NO VIENE PORQUE NO SE ENVIA, NO LO TENGO INCLUIDO EN LA DEFINICION DE INVOICE OBJECT
#             "related_documents": related_documents,
#             "export": export,
#             "complements": complements,
#             # "status": status,
#             "external_id": external_id,
#             # "folio_number": folio_number,
#             # "series": series,
#             "pdf_custom_section": pdf_custom_section,
#             # "addenda": addenda,
#             "namespaces": namespaces,
#             # "pdf_options": pdf_options,
#             "idempotency_key" : idempotency_key,
#             # "payment_related_ids": payment_related_ids, SOLO LO ACEPTA CUANDO SE TRATA DE PPD
#             "customer": {
#                 "legal_name": cliente,
#                 "tax_id": tax_id,
#                 "tax_system": get_regimen_fiscal(cliente),
#                 "email": email_id,
#                 "address": {
#                     "zip": datos_direccion.pincode
#                 },
#             },
#             "items": get_items_info(invoice_data)
#         }

#         response = requests.post(
#             facturapi_endpoint, json=data, headers=headers)

#         status_doc , status_sales_invoice = respuesta_pac_factura(self, response)

#         actualizar_status_doc(self,status_doc)
#         actualizar_status_sales_invoice(self.sales_invoice_id,status_sales_invoice)