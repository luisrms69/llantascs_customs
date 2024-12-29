// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Orden de Pago Comisiones", {
// 	refresh(frm) {

// 	},
// });

// fix:voy a duplicar el codigo, deberia ser solo uno
frappe.ui.form.on('Orden de Pago Comisiones', {
    hasta_fecha: function (frm) {
        frm.refresh_field('comisiones_incluidas');
        if (frm.doc.hasta_fecha) {
            frappe.call({
                method: 'llantascs_customs.llantascs_customs.api.get_sales_invoices',
                args: {
                    'fecha_inicial': frm.doc.desde,
                    'fecha_final': frm.doc.hasta_fecha
                },
                callback: function (r) {
                    // frm.refresh_field('comisiones_incluidas');
                    console.log("SE RECIBE EL MENSJAE INCIAL, NUMERO DE FACTURAS")
                    console.log(r.message);
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('comisiones_incluidas')
                        r.message.forEach(function (invoice) {
                            // console.log("empieza  el primer foreach, por factura")
                            console.log(invoice)
                            console.log(invoice.name)
                            // cogs = 0
                            frappe.call({
                                method: 'llantascs_customs.llantascs_customs.api.get_costo_ventas_sales_invoice',
                                args: {
                                    'sales_invoice_id': invoice.name
                                },
                                callback: function (s) {
                                    if (s.message) {
                                        console.log(s.message)
                                        cogs = s.message * 1;
                                        console.log("empezamos por costo")
                                        console.log(cogs)
                                        for (i in invoice.sales_team) {
                                            var child = frm.add_child('comisiones_incluidas');
                                            child.sales_invoice_id = invoice.name;
                                            console.log(child.sales_invoice_id)
                                            child.ingreso = invoice.amount_eligible_for_commission;
                                            child.persona_de_ventas = invoice.sales_team[i].sales_person;
                                            child.porcentaje_comision = invoice.sales_team[i].allocated_percentage;
                                            child.costo_de_ventas = cogs;
                                            child.utilidad_transaccion = invoice.amount_eligible_for_commission - cogs
                                            child.total_comision = (child.utilidad_transaccion * child.porcentaje_comision) / 100
                                            frm.refresh_field('comisiones_incluidas');
                                        }
                                        frm.refresh_field('comisiones_incluidas');
                                    }
                                    frm.refresh_field('comisiones_incluidas');
                                }
                            })
                        })
                    };
                }
            })
        }
    }
}
)

frappe.ui.form.on('Orden de Pago Comisiones', {
    desde: function (frm) {
        frm.refresh_field('comisiones_incluidas');
        if (frm.doc.desde) {
            frappe.call({
                method: 'llantascs_customs.llantascs_customs.api.get_delivery_note_for_sales_invoice',
                args: {
                    'sales_invoice_id': 'ACC-SINV-2024-00099'
                },
                callback: function (r) {
                    if (r.message) {
                        console.log(r.message)
                    };
                }
            })
        }
    }
}
)