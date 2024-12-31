// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Orden de Pago Comisiones", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Orden de Pago Comisiones', {
    onload: function (frm) {
        // frm.refresh_field('comisiones_incluidas');
        // if (frm.doc.desde) {
            frappe.call({
                method: 'llantascs_customs.llantascs_customs.api.get_commission_rate',
                // args: {
                //     'sales_invoice_id': 'ACC-SINV-2024-00099'
                // },
                callback: function (r) {
                    if (r.message) {
                        // console.log(r.message)
                        commission_rate = r.message
                        frm.set_value('comision_sobre_utilidad_', commission_rate)
                    };
                }
            })
        // }
    }
}
)


// fix:voy a duplicar el codigo, deberia ser solo uno
frappe.ui.form.on('Orden de Pago Comisiones', {
    hasta_fecha: function (frm) {
        frm.refresh_field('comisiones_incluidas');
        if (frm.doc.hasta_fecha) {
            frappe.call({
                method: 'llantascs_customs.llantascs_customs.api.get_sales_invoices',
                args: {
                    'sucursal': frm.doc.sucursal,
                    'fecha_inicial': frm.doc.desde,
                    'fecha_final': frm.doc.hasta_fecha
                },
                callback: function (r) {
                    console.log("SE RECIBE EL MENSJAE INCIAL, NUMERO DE FACTURAS")
                    console.log(r.message);
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('comisiones_incluidas')
                        r.message.forEach(function (invoice) {
                            // console.log("empieza  el primer foreach, por factura")
                            // console.log(invoice)
                            // console.log(invoice.name)
                            // cogs = 0
                            frappe.call({
                                method: 'llantascs_customs.llantascs_customs.api.get_costo_ventas_sales_invoice',
                                args: {
                                    'sales_invoice_id': invoice.name
                                },
                                callback: function (s) {
                                    if (s.message) {
                                        // console.log(s.message)
                                        cogs = s.message * 1;
                                        // console.log("empezamos por costo")
                                        // console.log(cogs)
                                        for (i in invoice.sales_team) {
                                            var child = frm.add_child('comisiones_incluidas');
                                            child.sales_invoice_id = invoice.name;
                                            // console.log(child.sales_invoice_id)
                                            child.ingreso = invoice.amount_eligible_for_commission;
                                            child.persona_de_ventas = invoice.sales_team[i].sales_person;
                                            child.porcentaje_comision = invoice.sales_team[i].allocated_percentage;
                                            child.costo_de_ventas = cogs;
                                            child.utilidad_transaccion = invoice.amount_eligible_for_commission - cogs
                                            child.total_comision = (child.utilidad_transaccion * child.porcentaje_comision * commission_rate) / 10000
                                            frm.refresh_field('comisiones_incluidas');
                                        }
                                        // frm.refresh_field('comisiones_incluidas');
                                    }
                                    // frm.refresh_field('comisiones_incluidas');
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
    sucursal: function (frm) {
        frm.refresh_field('comisiones_incluidas');
        if (frm.doc.sucursal) {
            frappe.call({
                method: 'llantascs_customs.llantascs_customs.api.get_sales_invoices',
                args: {
                    'sucursal': frm.doc.sucursal,
                    'fecha_inicial': frm.doc.desde,
                    'fecha_final': frm.doc.hasta_fecha
                },
                callback: function (r) {
                    console.log("SE RECIBE EL MENSJAE INCIAL, NUMERO DE FACTURAS")
                    console.log(r.message);
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('comisiones_incluidas')
                        r.message.forEach(function (invoice) {
                            // console.log("empieza  el primer foreach, por factura")
                            // console.log(invoice)
                            // console.log(invoice.name)
                            // cogs = 0
                            frappe.call({
                                method: 'llantascs_customs.llantascs_customs.api.get_costo_ventas_sales_invoice',
                                args: {
                                    'sales_invoice_id': invoice.name
                                },
                                callback: function (s) {
                                    if (s.message) {
                                        // console.log(s.message)
                                        cogs = s.message * 1;
                                        // console.log("empezamos por costo")
                                        // console.log(cogs)
                                        for (i in invoice.sales_team) {
                                            var child = frm.add_child('comisiones_incluidas');
                                            child.sales_invoice_id = invoice.name;
                                            // console.log(child.sales_invoice_id)
                                            child.ingreso = invoice.amount_eligible_for_commission;
                                            child.persona_de_ventas = invoice.sales_team[i].sales_person;
                                            child.porcentaje_comision = invoice.sales_team[i].allocated_percentage;
                                            child.costo_de_ventas = cogs;
                                            child.utilidad_transaccion = invoice.amount_eligible_for_commission - cogs
                                            child.total_comision = (child.utilidad_transaccion * child.porcentaje_comision * commission_rate) / 10000
                                            frm.refresh_field('comisiones_incluidas');
                                        }
                                        // frm.refresh_field('comisiones_incluidas');
                                    }
                                    // frm.refresh_field('comisiones_incluidas');
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
                method: 'llantascs_customs.llantascs_customs.api.get_sales_invoices',
                args: {
                    'sucursal': frm.doc.sucursal,
                    'fecha_inicial': frm.doc.desde,
                    'fecha_final': frm.doc.hasta_fecha
                },
                callback: function (r) {
                    console.log("SE RECIBE EL MENSJAE INCIAL, NUMERO DE FACTURAS")
                    console.log(r.message);
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('comisiones_incluidas')
                        r.message.forEach(function (invoice) {
                            // console.log("empieza  el primer foreach, por factura")
                            // console.log(invoice)
                            // console.log(invoice.name)
                            // cogs = 0
                            frappe.call({
                                method: 'llantascs_customs.llantascs_customs.api.get_costo_ventas_sales_invoice',
                                args: {
                                    'sales_invoice_id': invoice.name
                                },
                                callback: function (s) {
                                    if (s.message) {
                                        // console.log(s.message)
                                        cogs = s.message * 1;
                                        // console.log("empezamos por costo")
                                        // console.log(cogs)
                                        for (i in invoice.sales_team) {
                                            var child = frm.add_child('comisiones_incluidas');
                                            child.sales_invoice_id = invoice.name;
                                            // console.log(child.sales_invoice_id)
                                            child.ingreso = invoice.amount_eligible_for_commission;
                                            child.persona_de_ventas = invoice.sales_team[i].sales_person;
                                            child.porcentaje_comision = invoice.sales_team[i].allocated_percentage;
                                            child.costo_de_ventas = cogs;
                                            child.utilidad_transaccion = invoice.amount_eligible_for_commission - cogs
                                            child.total_comision = (child.utilidad_transaccion * child.porcentaje_comision * commission_rate) / 10000
                                            frm.refresh_field('comisiones_incluidas');
                                        }
                                        // frm.refresh_field('comisiones_incluidas');
                                    }
                                    // frm.refresh_field('comisiones_incluidas');
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


// frappe.ui.form.on('Orden de Pago Comisiones', {
//     desde: function (frm) {
//         frm.refresh_field('comisiones_incluidas');
//         if (frm.doc.desde) {
//             frappe.call({
//                 method: 'llantascs_customs.llantascs_customs.api.get_delivery_note_for_sales_invoice',
//                 args: {
//                     'sales_invoice_id': 'ACC-SINV-2024-00099'
//                 },
//                 callback: function (r) {
//                     if (r.message) {
//                         console.log(r.message)
//                     };
//                 }
//             })
//         }
//     }
// }
// )



// Codigo que genera boton en la Factura para hacer el envio por correo y llama al método PY de envio
frappe.ui.form.on('Orden de Pago Comisiones', {
    refresh: function (frm) {
        if (frm.doc.docstatus == 1 && frm.doc.confirmacion_de_pago != "Pagada") {
            frm.add_custom_button(__('Confirmacion de Pago'), function () {
                let d = new frappe.ui.Dialog({
                    title: __('Al oprimir confirmar, las operaciones enlistadas en esta orden de pago se marcaran como pagadas. Deseas continuar?'),
                    primary_action_label: 'Confirmar el pago',
                    primary_action: function () {
                        var data = d.get_values();
                        frappe.call({
                            method: 'llantascs_customs.llantascs_customs.api.actualizar_sales_invoices_pagada',
                            args: {
                                orden_pago_id: frm.doc.name,
                                status: 2
                            },
                            callback: function (r) {
                                if (r.message) {
                                    console.log("#######server script message#########");
                                    console.log(r.message);
                                }
                                d.hide();
                            }
                        });
                    }
                });

                d.show();
            })
        }
    }
});