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
                    console.log("#######r message#########")
                    console.log(r.message);
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('comisiones_incluidas')
                        r.message.forEach(function (invoice) {
                            // console.log("entra a primer loop")
                            // console.log(invoice.sales_team)
                            for (i in invoice.sales_team) {
                                var child = frm.add_child('comisiones_incluidas');
                                // console.log("entra a  loop interno")
                                // console.log(invoice.name)
                                // console.log(invoice.sales_team[i].sales_person)
                                // console.log(invoice.sales_team[i].allocated_percentage)
                                child.sales_invoice_id = invoice.name;
                                child.ingreso = invoice.amount_eligible_for_commission;
                                child.persona_de_ventas = invoice.sales_team[i].sales_person;
                                child.porcentaje_comision = invoice.sales_team[i].allocated_percentage;
                            }
                        })
                        // console.log("siguiente")
                    };
                }
            })
        }
    }
}
)