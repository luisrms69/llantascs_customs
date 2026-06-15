// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Invoice', {
    customer: function(frm){
        if (!frm.doc.customer) return;

        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: "Customer",
                filters: {
                    name: frm.doc.customer
                }
            },
            callback: function (r) {
                const sucursal = r.message && r.message.custom_sucursal_predeterminada;

                if (sucursal && !frm.doc.cost_center) {
                    frm.set_value('cost_center', sucursal);
                }
                // Si no hay sucursal predeterminada, no tocar cost_center.
                // Si ya hay cost_center, respetarlo.
            }
        });
    }
})