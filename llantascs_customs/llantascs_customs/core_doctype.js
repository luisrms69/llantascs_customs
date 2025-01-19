// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Invoice', {
    customer: function(frm){
        if (frm.doc.customer) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: "Customer",
                    filters: {
                        name: frm.doc.customer
                    }
                },
                callback: function (r) {
                    // console.log("#######r message#########")
                    // console.log(r.message);
                    if (r.message.custom_sucursal_predeterminada) {
                        frm.set_value('cost_center', r.message.custom_sucursal_predeterminada);
                    } else {
                        frm.set_value('cost_center', null);
                    }
                }
            });
        }
    }
})