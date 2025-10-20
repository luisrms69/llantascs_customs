// Copyright (c) 2025, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

frappe.query_reports["Reporte Diario Director General"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"get_query": function() {
				return {
					"filters": {
						"disabled": 0,
						"is_group": 0
					}
				};
			}
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		// Custom formatter para valores monetarios
		value = default_formatter(value, row, column, data);

		if (column.fieldtype == "Currency") {
			if (value < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (value > 0) {
				value = "<span style='color:green'>" + value + "</span>";
			}
		}

		return value;
	},

	"onload": function(report) {
		// Este es un reporte con HTML personalizado, no tabular
		// Ocultar botones estándar que no aplican
		report.page.hide_menu();

		// Botón para generar PDF
		report.page.add_inner_button(__("Generate PDF"), function() {
			var filters = report.get_values();

			frappe.call({
				method: "llantascs_customs.llantascs_customs.report.reporte_diario_director_general.reporte_diario_director_general.generate_pdf",
				args: {
					"filters": filters
				},
				callback: function(r) {
					if (r.message) {
						window.open(r.message);
					}
				}
			});
		}, __("Actions"));

		// Botón para generar HTML
		report.page.add_inner_button(__("Generate HTML"), function() {
			var filters = report.get_values();

			frappe.call({
				method: "llantascs_customs.llantascs_customs.report.reporte_diario_director_general.reporte_diario_director_general.generate_html",
				args: {
					"filters": filters
				},
				callback: function(r) {
					if (r.message) {
						window.open(r.message);
					}
				}
			});
		}, __("Actions"));
	}
};
