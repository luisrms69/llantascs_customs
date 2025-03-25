import frappe
import json
from frappe.utils import now

# Variables globales llantas Customs
estados_comisiones = ['Sin Enviar','Enviado','Pagada']
# fix: esto no puede quedar asi, me esta ocasionando muchos problemas, necesito estandarizar
# fix: corregido el 2 de marzo 2025, se puede elimianr
# cogs_accounts = ['501-005-001 - COSTO DE VENTA LLANTAS   - LLCS', '501-005-002 - COSTO DE VENTA RINES  - LLCS', '501-005-003 - OTROS COSTO DE VENTA  - LLCS']

def get_cogs_account():
    cogs_accounts = frappe.db.get_list(
        'Account', 
        filters = { 
            'account_type': "Cost of Goods Sold"
            },
            pluck = 'name')

    return cogs_accounts


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

def is_delivered(sales_invoice):
    #  frappe.msgprint("entra a is delivered")
    #  frappe.msgprint(str(sales_invoice))
    if sales_invoice.update_stock == 0:
         for partida in sales_invoice.items:
              if partida.item_group == "Servicios":
                   return 1
              if (partida.delivered_qty + partida.delivered_by_supplier) < partida.qty:
                   return 0
    
    return 1

def get_costo_ventas_si(sales_invoice_id):
    cogs = 0
    cogs_accounts = get_cogs_account()

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
        cogs -= frappe.db.get_value('GL Entry', entry, 'credit')

    return cogs

def get_costo_ventas_dn(sales_invoice_id):
    # GL entries for Delivery Note cases

    cogs = 0
    dn_items_list = frappe.db.get_list(
            "Delivery Note Item",
            filters={'against_sales_invoice' : sales_invoice_id},
            pluck = 'name',
            ignore_permissions= True
        )

    for dn_item in dn_items_list:
        variables = frappe.db.get_value('Delivery Note Item', dn_item,['qty','grant_commission','incoming_rate'])

        cogs += variables[0]*variables[1]*variables[2]

    return cogs

def actualizar_status_sales_invoice(invoice_id, status):
           frappe.db.set_value("Sales Invoice", invoice_id,
                          'custom_status_comisiones', estados_comisiones[status])

def actualizar_orden_pago_sales_invoice(invoice_id, orden_de_pago):
           frappe.db.set_value("Sales Invoice", invoice_id,
                          'custom_orden_de_pago_comision', orden_de_pago)


@frappe.whitelist()
def actualizar_status_orden_pago(orden_pago_id, status):
      status_number = int(status)
      orden_pago = frappe.get_doc('Orden de Pago Comisiones', orden_pago_id)
      orden_pago.db_set({
            'confirmacion_de_pago': estados_comisiones[status_number],
            'fecha_confirmacion_pago': str(now())
      })
      for invoice in orden_pago.comisiones_incluidas:
          actualizar_status_sales_invoice(invoice.sales_invoice_id, status_number)
          actualizar_orden_pago_sales_invoice(invoice.sales_invoice_id, orden_pago_id)
          
      return estados_comisiones[2]


@frappe.whitelist()
def get_commission_rate():
    commission_rate = frappe.db.get_single_value('Comisiones Settings', 'porcentaje_sobre_utilidad')

    return commission_rate


@frappe.whitelist()
def get_sales_invoices(sucursal,fecha_inicial,fecha_final):
    sales_invoice_id_list = get_sales_invoices_id(sucursal,fecha_inicial, fecha_final)
    sales_invoices = []

    # frappe.msgprint("entro a get sales invoices")
    
    for sales_invoice in sales_invoice_id_list:
        sinv = frappe.get_doc('Sales Invoice', sales_invoice)
        # frappe.msgprint(str(sales_invoice))
        # frappe.msgprint(str(is_delivered(sinv)))
        if sinv.sales_team and is_delivered(sinv):
             sales_invoices.append(sinv)

    # frappe.msgprint("estas son las invoices")
    # frappe.msgprint(str(sales_invoices))

    return sales_invoices

@frappe.whitelist()
def get_costo_ventas_sales_invoice(sales_invoice_id):

    cogs = 0
    cogs += get_costo_ventas_si(sales_invoice_id)
    cogs += get_costo_ventas_dn(sales_invoice_id)

    return cogs
