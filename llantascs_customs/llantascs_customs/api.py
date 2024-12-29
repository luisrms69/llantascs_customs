import frappe
import json

# Variables globales llantas Customs
estados_comisiones = ['Sin Enviar','Enviado','Pagada']
cogs_accounts = ['501-000-001 - Costo de Llantas - LLCS']

def get_sales_invoices_id(fecha_inicial, fecha_final):
    sales_invoice_list = frappe.db.get_list(
        'Sales Invoice', 
        filters = { 
            'status': 'paid', 
            'custom_status_comisiones':estados_comisiones[0], 
            'posting_date': ['between',[fecha_inicial,fecha_final]]
            },
            pluck = 'name')
    
    return sales_invoice_list


@frappe.whitelist()
def get_sales_invoices(fecha_inicial,fecha_final):
    sales_invoice_id_list = get_sales_invoices_id(fecha_inicial, fecha_final)
    sales_invoices = []
    for sales_invoice in sales_invoice_id_list:
        sales_invoices.append(frappe.get_doc('Sales Invoice', sales_invoice))
    
    return sales_invoices

@frappe.whitelist()
def get_costo_ventas_sales_invoice(sales_invoice_id):
    gl_entries = frappe.db.get_list('GL Entry',
    filters = {
        'voucher_type' : 'Sales Invoice',
        'voucher_no' : sales_invoice_id,
        'account': ['in', cogs_accounts]},
        # 'account': ['in', ['501-000-001 - Costo de Llantas - LLCS', '401-000-001 - Ventas Nacionales - LLCS' ]]},
        pluck = 'name'
    )

    cogs = 0
    for entry in gl_entries:
        cogs += frappe.db.get_value('GL Entry', entry, 'debit')

    return cogs