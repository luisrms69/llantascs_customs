import frappe
import json
from frappe.utils import now

# Variables globales llantas Customs
estados_comisiones = ['Sin Enviar','Enviado','Pagada']
# fix: esto no puede quedar asi, me esta ocasionando muchos problemas, necesito estandarizar
cogs_accounts = ['501-005-001 - COSTO DE VENTA LLANTAS   - LLCS', '501-005-002 - COSTO DE VENTA RINES  - LLCS', '501-005-003 - OTROS COSTO DE VENTA  - LLCS']

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
    # frappe.msgprint("entrada get costo ventas si")
    # frappe.msgprint(str(sales_invoice_id))
    # GL entries for Sales Invoice, no delivery note
    gl_entries_invoice = frappe.db.get_list('GL Entry',
    filters = {
        'voucher_type' : 'Sales Invoice',
        'voucher_no' : sales_invoice_id,
        'account': ['in', cogs_accounts]},
        pluck = 'name'
    )
    # frappe.msgprint("glentries invoice")
    # frappe.msgprint(str(gl_entries_invoice))


    for entry in gl_entries_invoice:
        # frappe.msgprint("debe entrar si hay Si")
        # frappe.msgprint(str(entry))
        cogs += frappe.db.get_value('GL Entry', entry, 'debit')

    # frappe.msgprint("salida get costo ventas si")
    # frappe.msgprint(str(cogs))
    # frappe.msgprint("salida get costo ventas si")

    return cogs

def get_costo_ventas_dn(sales_invoice_id):
    # GL entries for Delivery Note cases


    # frappe.msgprint("entrada get costo ventas dn")
    # frappe.msgprint(str(sales_invoice_id))


    cogs = 0
    dn_items_list = frappe.db.get_list(
            "Delivery Note Item",
            filters={'against_sales_invoice' : sales_invoice_id},
            pluck = 'name'
        )

    for dn_item in dn_items_list:
        # frappe.msgprint("entra al loop dn item list")
        # frappe.msgprint(dn_item)
        variables = frappe.db.get_value('Delivery Note Item', dn_item,['qty','grant_commission','incoming_rate'])
        
        # frappe.msgprint("variables")
        # frappe.msgprint(str(variables[0]))
        # frappe.msgprint(str(variables[1]))
        # frappe.msgprint(str(variables[2]))

        
        cogs += variables[0]*variables[1]*variables[2]

    # frappe.msgprint("salida get costo ventas dn")
    # frappe.msgprint(str(cogs))
    # frappe.msgprint("salida get costo ventas dn")


    return cogs

def actualizar_status_sales_invoice(invoice_id, status):
           frappe.db.set_value("Sales Invoice", invoice_id,
                          'custom_status_comisiones', estados_comisiones[status])

def actualizar_orden_pago_sales_invoice(invoice_id, orden_de_pago):
           frappe.db.set_value("Sales Invoice", invoice_id,
                          'custom_orden_de_pago_comision', orden_de_pago)


@frappe.whitelist()
def actualizar_status_orden_pago(orden_pago_id, status):
    #   frappe.msgprint("entering actualizar prinicipio")
    #   frappe.msgprint(str(status))
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
    for sales_invoice in sales_invoice_id_list:
        sales_invoices.append(frappe.get_doc('Sales Invoice', sales_invoice))
    
    return sales_invoices

@frappe.whitelist()
def get_costo_ventas_sales_invoice(sales_invoice_id):
    # frappe.msgprint("entrada get costo sales invocie")
    # frappe.msgprint(str(sales_invoice_id))
    cogs = 0
    cogs += get_costo_ventas_si(sales_invoice_id)
    cogs += get_costo_ventas_dn(sales_invoice_id)

    # frappe.msgprint("salida get costo sales invocie")
    # frappe.msgprint(str(cogs))
    # frappe.msgprint("salida get costo sales invocie")

    return cogs
