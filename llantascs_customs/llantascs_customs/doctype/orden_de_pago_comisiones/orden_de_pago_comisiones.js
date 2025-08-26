// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

frappe.ui.form.on('Orden de Pago Comisiones', {
  onload: async function(frm) {
    // 1) Default de fechas desde Settings, solo si están vacías
    try {
      if (!frm.doc.desde) {
        const defStart = await frappe.db.get_single_value('Comisiones Settings', 'default_start_date');
        if (defStart) frm.set_value('desde', defStart);
      }
      if (!frm.doc.hasta_fecha) {
        const defEnd = await frappe.db.get_single_value('Comisiones Settings', 'default_end_date');
        if (defEnd) frm.set_value('hasta_fecha', defEnd);
      }
    } catch (e) {
      console.log('No se pudieron leer defaults de fechas', e);
    }

    // 2) Commission rate default según sucursal:
    //    Solo poner si es un doc nuevo o si el campo está vacío (no sobreescribir órdenes existentes)
    if (!frm.doc.comision_sobre_utilidad_ || frm.is_new()) {
      await set_commission_rate_from_branch(frm);
    }

    // 3) Reaccionar a cambios de sucursal: si el rate está vacío, sugerirlo
    frm.fields_dict.sucursal.df.onchange = async function() {
      if (!frm.doc.comision_sobre_utilidad_) {
        await set_commission_rate_from_branch(frm);
      }
    };
  }
});

async function set_commission_rate_from_branch(frm) {
  try {
    const sucursal = frm.doc.sucursal || null;
    const r = await frappe.call({
      method: 'llantascs_customs.llantascs_customs.api.get_commission_rate',
      args: { sucursal: sucursal }
    });
    if (r && r.message != null && (frm.is_new() || !frm.doc.comision_sobre_utilidad_)) {
      frm.set_value('comision_sobre_utilidad_', r.message);
    }
  } catch (e) {
    console.log('No se pudo obtener commission rate', e);
  }
}


function populate_child_sales(frm, invoice, cogs) {
    var child = frm.add_child('comisiones_incluidas');
    child.sales_invoice_id = invoice.name;
    child.folio_fiscal = invoice.custom_folio_fiscal;
    child.ingreso = invoice.amount_eligible_for_commission;
    child.persona_de_ventas = invoice.sales_team[i].sales_person;
    child.porcentaje_comision = invoice.sales_team[i].allocated_percentage;
    child.costo_de_ventas = cogs;
    child.utilidad_transaccion = invoice.amount_eligible_for_commission - cogs
    child.total_comision = (child.utilidad_transaccion * child.porcentaje_comision * commission_rate) / 10000
    frm.refresh_field('comisiones_incluidas');
    frm.doc.monto_total += child.total_comision
}

function create_order(frm, message) {
    frm.clear_table('comisiones_incluidas')
    message.forEach(function (invoice) {
        frappe.call({
            method: 'llantascs_customs.llantascs_customs.api.get_costo_ventas_sales_invoice',
            args: {
                'sales_invoice_id': invoice.name
            },
            callback: function (s) {
                if (Object.keys(s).length > 0) {
                    cogs = s.message;
                    for (i in invoice.sales_team) {
                        populate_child_sales(frm, invoice, cogs)
                    }
                }
            }
        })
    })
    frm.doc.monto_total = monto_total
}


function generate_order(frm) {
    frappe.call({
        method: 'llantascs_customs.llantascs_customs.api.get_sales_invoices',
        args: {
            'sucursal': frm.doc.sucursal,
            'fecha_inicial': frm.doc.desde,
            'fecha_final': frm.doc.hasta_fecha
        },
        callback: function (r) {
            if (r.message) {
                create_order(frm, r.message)
            };
        }
    })
}


frappe.ui.form.on('Orden de Pago Comisiones', {
    hasta_fecha: function (frm) {
        frm.refresh_field('comisiones_incluidas');
        monto_total = 0
        if (frm.doc.hasta_fecha) {
            generate_order(frm)
        }
    }
}
)

frappe.ui.form.on('Orden de Pago Comisiones', {
    sucursal: function (frm) {
        frm.refresh_field('comisiones_incluidas');
        monto_total = 0
        if (frm.doc.sucursal) {
            generate_order(frm)
        }
    }
}
)

frappe.ui.form.on('Orden de Pago Comisiones', {
    desde: function (frm) {
        frm.refresh_field('comisiones_incluidas');
        monto_total = 0
        if (frm.doc.desde) {
            generate_order(frm)
        }
    }
}
)


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
                            method: 'llantascs_customs.llantascs_customs.api.actualizar_status_orden_pago',
                            args: {
                                orden_pago_id: frm.doc.name,
                                status: Number(2),
                            },
                            callback: function (r) {
                                if (r.message) {
                                    frm.refresh()
                                }
                                d.hide();
                            }
                        });
                    }
                });
                d.show();
            })
        }

        // Botón Aplicar Reducción A.2
        if (frm.doc.name) {
            frm.add_custom_button(__('Aplicar Reducción'), async () => {
                frm.freeze(__('Aplicando...'));
                try {
                    const r = await frappe.call({
                        method: 'llantascs_customs.llantascs_customs.api.apply_reduction',
                        args: { opc_name: frm.doc.name }
                    });
                    await frm.reload_doc();
                    const m = r.message || {};
                    if (m.adjustments_applied === false) {
                        const why = m.reason === 'disabled_global'
                            ? __('Deshabilitada en Settings')
                            : (m.reason === 'disabled_order' ? __('Ignorada por esta orden') : __('Deshabilitada'));
                        frappe.msgprint({
                            title: __('Sin ajuste'),
                            message: __('Reducción no aplicada ({0}). Valores normalizados.', [why]),
                            indicator: 'blue'
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Reducción aplicada'),
                            message: __('Fuente: {0} | % mensual: {1} | Días de gracia: {2}', [
                                m.source, m.monthly_rate, m.grace_days
                            ])
                        });
                    }
                } catch (e) {
                    frappe.msgprint({ title: __('Error'), message: e.message || e, indicator: 'red' });
                } finally {
                    frm.unfreeze();
                }
            });
        }

        // Botón: refrescar tasas desde Settings (reemplaza snapshot) B.1
        if (frm.doc.name) {
            frm.add_custom_button(__('Refrescar tasas (Settings)'), async () => {
                const confirm = await frappe.confirm(__('Esto reemplazará las tasas de esta Orden con las de Settings. ¿Continuar?'));
                if (!confirm) return;
                frm.freeze(__('Actualizando tasas...'));
                try {
                    const r = await frappe.call({
                        method: 'llantascs_customs.llantascs_customs.api.refresh_order_branch_rates',
                        args: { opc_name: frm.doc.name, replace: 1 }
                    });
                    await frm.reload_doc();
                    frappe.msgprint(__('Tasas actualizadas ({0} filas).', [r.message.rows]));
                } catch (e) {
                    frappe.msgprint({ title: __('Error'), message: e.message || e, indicator: 'red' });
                } finally {
                    frm.unfreeze();
                }
            });
        }
    }
});