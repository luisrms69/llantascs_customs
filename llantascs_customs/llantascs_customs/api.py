import frappe
import json

# Variables globales llantas Customs
estados_comisiones = ['Sin Enviar','Enviado','Pagada']
cogs_accounts = ['501-000-001 - Costo de Llantas - LLCS']

def get_sales_invoices_id(sucursal, fecha_inicial, fecha_final):
    sales_invoice_list = frappe.db.get_list(
        'Sales Invoice', 
        filters = { 
            'status': 'paid', 
            'custom_status_comisiones':estados_comisiones[0], 
            'posting_date': ['between',[fecha_inicial,fecha_final]],
            'cost_center': sucursal
            },
            pluck = 'name')
    
    return sales_invoice_list

def get_costo_ventas_si(sales_invoice_id):
    cogs = 0
    # GL entries for Sales Invoice, no delivery note
    gl_entries_invoice = frappe.db.get_list('GL Entry',
    filters = {
        'voucher_type' : 'Sales Invoice',
        'voucher_no' : sales_invoice_id,
        'account': ['in', cogs_accounts]},
        pluck = 'name'
    )

    for entry in gl_entries_invoice:
        cogs += frappe.db.get_value('GL Entry', entry, 'debit')

    return cogs

def get_costo_ventas_dn(sales_invoice_id):
    # GL entries for Delivery Note cases
    cogs = 0
    dn_items_list = frappe.db.get_list(
            "Delivery Note Item",
            filters={'against_sales_invoice' : sales_invoice_id},
            pluck = 'name'
        )

    for dn_item in dn_items_list:
        variables = frappe.db.get_value('Delivery Note Item', dn_item,['qty','grant_commission','incoming_rate'])
        cogs += variables[0]*variables[1]*variables[2]

    return cogs

# fix: no se ocupa, unicamente en pruebas, borrar
@frappe.whitelist()
def get_delivery_note_for_sales_invoice(sales_invoice_id):

    dn_items_list = frappe.db.get_list(
            "Delivery Note Item",
            filters={'against_sales_invoice' : sales_invoice_id},
            pluck = 'name'
        )

    for dn_item in dn_items_list:
        cogs = 0
        variables = frappe.db.get_value('Delivery Note Item', dn_item,['qty','grant_commission','incoming_rate'])
        cogs += variables[0]*variables[1]*variables[2]

    return variables, cogs

@frappe.whitelist()
def get_sales_invoices(sucursal,fecha_inicial,fecha_final):
    sales_invoice_id_list = get_sales_invoices_id(sucursal,fecha_inicial, fecha_final)
    sales_invoices = []
    for sales_invoice in sales_invoice_id_list:
        sales_invoices.append(frappe.get_doc('Sales Invoice', sales_invoice))
    
    return sales_invoices

@frappe.whitelist()
def get_costo_ventas_sales_invoice(sales_invoice_id):
    cogs = 0
    cogs += get_costo_ventas_si(sales_invoice_id)
    cogs += get_costo_ventas_dn(sales_invoice_id)

    return cogs