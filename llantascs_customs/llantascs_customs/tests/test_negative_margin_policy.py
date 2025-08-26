import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate
from frappe.utils import flt

from llantascs_customs.llantascs_customs.tests._utils import (
    create_minimal_sales_invoice, get_company_and_currency, get_leaf_cost_center
)

class TestNegativeMarginPolicy(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.local.lang = "es"

    def _make_order_row(self, M_original_raw, M_aj_raw, base_comm=100.0, rate_percent=10.0):
        """Crea una Orden con una fila ya elegible (servicio y Paid), y fija raw margins."""
        si_name = create_minimal_sales_invoice(rate=1000.0, qty=1.0)
        frappe.db.set_value("Sales Invoice", si_name, {"status":"Paid", "outstanding_amount":0})

        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate(); opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = rate_percent
        company, _ = get_company_and_currency()
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        row = opc.append("comisiones_incluidas", {})
        row.sales_invoice_id = si_name
        # seteos mínimos para la política
        row.margen_original = max(0, M_original_raw)
        row.margen_ajustado = max(0, M_aj_raw)
        row.margen_ajustado_raw = M_aj_raw
        row.margen_original_negativo = 1 if M_original_raw < 0 else 0
        row.margen_ajustado_negativo = 1 if M_aj_raw < 0 else 0
        row.negativo_por = "ORIGINAL" if M_original_raw < 0 else ("AJUSTE" if M_aj_raw < 0 else None)
        row.comision_post_reduccion = max(0, M_aj_raw) * (rate_percent/100.0)
        # marcar elegible
        row.elig_entregado_ok = 1
        row.elig_pagado_ok = 1
        row.eligible_para_pago = 1
        opc.save(ignore_permissions=True)
        return opc

    def _run_eval(self, policy, only_if_original):
        ss = frappe.get_single("Comisiones Settings")
        ss.politica_margen_negativo = policy
        ss.permitir_negativo_solo_si_margen_original = 1 if only_if_original else 0
        ss.save(ignore_permissions=True)

    def test_policy_cero_sets_zero(self):
        opc = self._make_order_row(M_original_raw=-100, M_aj_raw=-80, base_comm=0, rate_percent=10)
        self._run_eval("CERO", True)
        from llantascs_customs.llantascs_customs.api import evaluate_eligibility
        evaluate_eligibility(opc.name)
        opc.reload()
        r = opc.comisiones_incluidas[0]
        self.assertEqual(flt(r.comision_a_pagar), 0.0)

    def test_policy_compensa_only_if_original(self):
        # margen original positivo, se vuelve negativo por ajuste
        opc = self._make_order_row(M_original_raw=100, M_aj_raw=-20, base_comm=0, rate_percent=10)
        self._run_eval("NEGATIVO_COMPENSA", True)
        from llantascs_customs.llantascs_customs.api import evaluate_eligibility
        evaluate_eligibility(opc.name)
        opc.reload()
        r = opc.comisiones_incluidas[0]
        # no compensa porque negativo es por AJUSTE y la regla exige ORIGINAL
        self.assertEqual(flt(r.comision_a_pagar), 0.0)

    def test_policy_compensa_when_original_negative(self):
        opc = self._make_order_row(M_original_raw=-50, M_aj_raw=-30, base_comm=0, rate_percent=10)
        self._run_eval("NEGATIVO_COMPENSA", True)
        from llantascs_customs.llantascs_customs.api import evaluate_eligibility
        evaluate_eligibility(opc.name)
        opc.reload()
        # Trigger validate() para calcular buckets
        opc.save(ignore_permissions=True)
        opc.reload()
        r = opc.comisiones_incluidas[0]
        # comision = M_raw * rate = -30 * 10% = -3.0
        self.assertAlmostEqual(flt(r.comision_a_pagar), -3.0, places=2)
        
        # B.4: Validar buckets en la orden (cap por defecto)
        self.assertEqual(flt(opc.total_comision_bruta), 0.0)  # No hay positivos
        self.assertAlmostEqual(flt(opc.total_compensaciones_negativas), -3.0, places=2)  # Solo negativos
        self.assertEqual(flt(opc.monto_total), 0.0)  # Cap por defecto (permitir_total_orden_negativo=0)

    def test_policy_requires_approval(self):
        opc = self._make_order_row(M_original_raw=10, M_aj_raw=-5, base_comm=0, rate_percent=10)
        self._run_eval("REQUIERE_APROBACION", False)
        from llantascs_customs.llantascs_customs.api import evaluate_eligibility
        evaluate_eligibility(opc.name)
        opc.reload()
        r = opc.comisiones_incluidas[0]
        self.assertEqual(flt(r.comision_a_pagar), 0.0)
        self.assertEqual(int(r.requiere_aprobacion or 0), 1)