// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

function selected_cost_centers(frm) {
  return (frm.doc.sucursales_multi || [])
    .map(r => r.cost_center)
    .filter(Boolean);
}

frappe.ui.form.on('Orden de Pago Comisiones', {
    onload: function (frm) {
        frappe.call({
            method: 'llantascs_customs.llantascs_customs.api.get_commission_rate',
            callback: function (r) {
                if (r.message) {
                    commission_rate = r.message
                    frm.set_value('comision_sobre_utilidad_', commission_rate)
                };
            }
        })
        // }
    }
}
)


// LEGACY FUNCTIONS - DEPRECATED (replaced by Actualizar Comisiones button)
// Keeping for reference, will be removed in future version

/*
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
            'sucursal': selected_cost_centers(frm),
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
*/






// Codigo que genera boton en la Factura para hacer el envio por correo y llama al método PY de envio
frappe.ui.form.on('Orden de Pago Comisiones', {
    refresh: function (frm) {
        // === Protecciones UI ===
        // Tabla de comisiones: totalmente read-only
        const g1 = frm.get_field('comisiones_incluidas')?.grid;
        if (g1) {
            g1.cannot_add_rows = true;
            g1.cannot_delete_rows = true;
        }
        // Tabla de tasas: sin altas/bajas, solo editar porcentaje
        const g2 = frm.get_field('comisiones_por_sucursal')?.grid;
        if (g2) {
            g2.cannot_add_rows = true;
            g2.cannot_delete_rows = true;
        }
        // Botones visibles solo si el documento está en Draft y ya guardado
        if (frm.doc.name && frm.doc.docstatus === 0) {
            // Botón "Todas las Sucursales"
            frm.add_custom_button('Todas las Sucursales', async () => {
                const r = await frappe.call({
                    method: 'llantascs_customs.llantascs_customs.api.get_all_cost_centers',
                    freeze: true,
                    freeze_message: 'Cargando sucursales...'
                });
                const centers = r.message || [];
                if (!centers.length) {
                    frappe.msgprint('No se encontraron Cost Centers activos.');
                    return;
                }
                // Vacía y rellena la tabla de sucursales_multi
                frm.clear_table('sucursales_multi');
                centers.forEach(cc => frm.add_child('sucursales_multi', { cost_center: cc }));
                frm.refresh_field('sucursales_multi');
                frappe.show_alert({
                    message: `Se agregaron ${centers.length} sucursales.`,
                    indicator: 'green'
                });
            });

            // Botón "Actualizar Comisiones" (Clear + Rebuild con confirmación)
            frm.add_custom_button('Actualiza Listado', async () => {
                const selected = (frm.doc.sucursales_multi || [])
                    .map(r => r.cost_center)
                    .filter(Boolean);

                if (!selected.length) {
                    frappe.msgprint('Selecciona al menos una sucursal en "Sucursales".');
                    return;
                }

                // ⚠️ Confirmación previa
                frappe.confirm(
                    'Cada vez que presiones "Actualiza Listado", <b>se perderán</b> los cambios manuales ' +
                    'en la <b>tabla de tasas</b> y en la <b>tabla de comisiones</b>. ¿Deseas continuar?',
                    async () => {
                        // Usuario CONFIRMÓ → proceder

                        // 1) Limpiar tablas (tasas y comisiones) y resetear total
                        frm.clear_table('comisiones_por_sucursal');
                        frm.clear_table('comisiones_incluidas'); // la llenarás en la Parte 2
                        frm.set_value('monto_total', 0);
                        frm.refresh_field('comisiones_por_sucursal');
                        frm.refresh_field('comisiones_incluidas');

                        // 2) Pedir tasas a Settings (específica por sucursal o default)
                        const r = await frappe.call({
                            method: 'llantascs_customs.llantascs_customs.api.sync_rates_from_settings',
                            args: { cost_centers: selected },
                            freeze: true,
                            freeze_message: 'Sincronizando tasas desde Settings…'
                        });

                        const payload = r.message || {};
                        const rows = payload.rows || [];

                        // 3) Rebuild 1:1 con las sucursales seleccionadas
                        rows.forEach(x => {
                            frm.add_child('comisiones_por_sucursal', {
                                cost_center: x.cost_center,
                                porcentaje_comision: x.porcentaje_comision
                            });
                        });
                        frm.refresh_field('comisiones_por_sucursal');

                        // === Parte 2: construir tabla de comisiones (Clean & Rebuild) ===
                        // Validar fechas
                        if (!frm.doc.desde || !frm.doc.hasta_fecha) {
                            frappe.msgprint('Define el rango de fechas: "Desde" y "Hasta".');
                            return;
                        }

                        // construir mapa de tasas desde la tabla del DOC (en memoria)
                        const ratesByCC = {};
                        (frm.doc.comisiones_por_sucursal || []).forEach(r => {
                            if (r.cost_center) ratesByCC[r.cost_center] = Number(r.porcentaje_comision);
                        });

                        // armar args base
                        const args = {
                            sucursal: selected,
                            fecha_inicial: frm.doc.desde,
                            fecha_final: frm.doc.hasta_fecha
                        };

                        // si el documento es nuevo, NO mandes docname (no existe en BD)
                        const isNew = frm.is_new() || ((frm.doc.name || '').startsWith('new-'));
                        if (isNew) {
                            args.rates_by_cc = ratesByCC;     // ← usar tasas en memoria
                        } else {
                            args.docname = frm.doc.name;      // ← doc guardado: se puede usar docname
                        }

                        // Pedir filas calculadas al backend usando función existente optimizada
                        const r2 = await frappe.call({
                            method: 'llantascs_customs.llantascs_customs.api.get_commission_rows',
                            args,
                            freeze: true,
                            freeze_message: 'Actualizando listado…'
                        });

                        const payload2 = r2.message || {};
                        const rows2 = payload2.rows || [];
                        const total2 = payload2.total || 0;
                        const subtotal_negativas = payload2.subtotal_negativas || 0;

                        // === Nivel 1: Patrón ERPNext Puro ===
                        frm.clear_table('comisiones_incluidas');
                        (rows2 || []).forEach(row => {
                            const d = frm.add_child('comisiones_incluidas');
                            for (const key in row) {
                                if (row[key] != null && key !== 'doctype' && key !== 'name') {
                                    d[key] = row[key];
                                }
                            }
                        });
                        frm.refresh_field('comisiones_incluidas');

                        frm.set_value('monto_total', total2 || 0);
                        frm.set_value('subtotal_comisiones_negativas', subtotal_negativas);
                        frm.refresh_fields(['monto_total', 'subtotal_comisiones_negativas']);

                        frappe.show_alert({
                            message: `Listado actualizado → Tasas: ${rows.length}, Comisiones: ${rows2.length}, Total: ${format_currency(total2, frm.doc.currency || 'MXN')}`,
                            indicator: 'green'
                        });
                    },
                    () => {
                        // Usuario CANCELÓ → no hacer nada
                    }
                );
            });
        }
        
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

        // Botón para Reporte Detallado PDF - solo si está guardado (no nuevo)
        if (frm.doc.name && !frm.is_new() && !frm.doc.name.startsWith('new-')) {
            frm.add_custom_button('📄 Reporte Detallado', () => {
                const url = `/api/method/frappe.utils.print_format.download_pdf`
                    + `?doctype=Orden%20de%20Pago%20Comisiones`
                    + `&name=${encodeURIComponent(frm.doc.name)}`
                    + `&format=opc_detallado`
                    + `&no_letterhead=0`;
                window.open(url);
            }).addClass('btn-primary');
        }
    }
});