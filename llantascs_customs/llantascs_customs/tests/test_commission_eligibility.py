import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate
from frappe.utils import flt

from llantascs_customs.llantascs_customs.tests._utils import (
    create_minimal_sales_invoice,
    get_company_and_currency,
    get_leaf_cost_center,
)

class TestCommissionEligibility(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.local.lang = "es"

    def _new_order_with_row(self, si_name, base_comm=123.45):
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 4.0
        company, _ = get_company_and_currency()
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        row = opc.append("comisiones_incluidas", {})
        row.sales_invoice_id = si_name
        row.ingreso = 8000.0          # nuevo: ingreso de prueba (ajustado para margen=5000, comisión=200)
        row.costo_de_ventas = 3000.0  # nuevo: costo de ventas de prueba
        row.comision_post_reduccion = base_comm
        opc.save(ignore_permissions=True)
        return opc

    def test_eligibility_paid_and_service_delivered(self):
        # SI mínima de servicio
        si_name = create_minimal_sales_invoice(rate=1000.0, qty=1.0)

        opc = self._new_order_with_row(si_name, base_comm=200.0)

        # Settings: configuración mínima requerida
        ss = frappe.get_single("Comisiones Settings")
        ss.aplicar_reduccion_por_diferimiento = 1  # Para que populate margen_ajustado_raw
        ss.requerir_persona_comision = 0           # Desactivar requisito persona
        ss.validar_entrega_total = 0               # Test de servicios, desactivar gate
        ss.validar_pago_total = 1                  # Validar pago real
        ss.tolerancia_pago_monetaria = 0
        ss.politica_margen_negativo = "CERO"
        ss.save(ignore_permissions=True)

        # Crear Payment Entry para marcar SI como pagada
        si = frappe.get_doc("Sales Invoice", si_name)
        if si.docstatus == 0:
            si.submit()  # Debe estar submitted para crear Payment Entry
        
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        pe = get_payment_entry("Sales Invoice", si.name)
        pe.paid_amount = pe.received_amount = si.outstanding_amount
        pe.insert(ignore_permissions=True)
        pe.submit()
        si.reload()
        
        from llantascs_customs.llantascs_customs.api import apply_reduction, evaluate_eligibility
        
        # Ejecutar flujo real: reducción seguido de evaluación de elegibilidad
        apply_reduction(opc.name)
        evaluate_eligibility(opc.name)

        opc.reload()
        r = opc.comisiones_incluidas[0]
        self.assertEqual(int(r.elig_entregado_ok), 1)
        self.assertEqual(int(r.elig_pagado_ok), 1)
        self.assertEqual(int(r.eligible_para_pago), 1)
        self.assertAlmostEqual(flt(r.comision_a_pagar), 200.0, places=2)

    def test_eligibility_not_paid(self):
        # SI mínima de servicio no pagada
        si_name = create_minimal_sales_invoice(rate=1500.0, qty=1.0)

        opc = self._new_order_with_row(si_name, base_comm=180.0)

        ss = frappe.get_single("Comisiones Settings")
        ss.validar_entrega_total = 1
        ss.validar_pago_total = 1
        ss.tolerancia_pago_monetaria = 0
        ss.politica_margen_negativo = "CERO"
        ss.save(ignore_permissions=True)

        from llantascs_customs.llantascs_customs.api import apply_reduction, evaluate_eligibility
        apply_reduction(opc.name)  # Calcula margen_ajustado_raw antes de evaluar elegibilidad
        evaluate_eligibility(opc.name)

        opc.reload()
        r = opc.comisiones_incluidas[0]
        # Entregado OK (servicio), pagado NO
        self.assertEqual(int(r.elig_entregado_ok), 1)
        self.assertEqual(int(r.elig_pagado_ok), 0)
        self.assertEqual(int(r.eligible_para_pago), 0)
        self.assertAlmostEqual(flt(r.comision_a_pagar), 0.0, places=2)
        self.assertIn("No pagado", (r.elig_razon or ""))