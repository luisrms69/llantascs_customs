import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from llantascs_customs.llantascs_customs.tests._utils import (
    get_company_and_currency,
    get_leaf_cost_center,
)


class TestMontoTotalAccumulator(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.local.lang = "es"

    def test_monto_total_accumulates_comision_a_pagar(self):
        """B.4: Hook calcula monto_total desde comision_a_pagar"""
        company, _ = get_company_and_currency()
        
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 4.0
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        # Agregar filas con comision_a_pagar
        row1 = opc.append("comisiones_incluidas", {})
        row1.comision_a_pagar = 100.50
        
        row2 = opc.append("comisiones_incluidas", {})
        row2.comision_a_pagar = 250.75

        # Trigger hook validate()
        opc.save(ignore_permissions=True)
        
        # Verificar acumulador
        expected_total = 100.50 + 250.75
        self.assertAlmostEqual(flt(opc.monto_total), expected_total, places=2)

    def test_monto_total_accumulates_total_comision_legacy(self):
        """B.4: Hook usa total_comision cuando comision_a_pagar está vacío (compatibilidad legacy)"""
        company, _ = get_company_and_currency()
        
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 4.0
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        # Agregar filas con total_comision (legacy)
        row1 = opc.append("comisiones_incluidas", {})
        row1.total_comision = 300.25
        # comision_a_pagar queda vacío/0
        
        row2 = opc.append("comisiones_incluidas", {})
        row2.total_comision = 150.75

        opc.save(ignore_permissions=True)
        
        expected_total = 300.25 + 150.75
        self.assertAlmostEqual(flt(opc.monto_total), expected_total, places=2)

    def test_monto_total_mixed_fields(self):
        """B.4: Hook prioriza comision_a_pagar sobre total_comision cuando ambos están presentes"""
        company, _ = get_company_and_currency()
        
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 4.0
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        # Fila 1: solo comision_a_pagar
        row1 = opc.append("comisiones_incluidas", {})
        row1.comision_a_pagar = 100.0
        
        # Fila 2: solo total_comision (legacy)
        row2 = opc.append("comisiones_incluidas", {})
        row2.total_comision = 200.0
        
        # Fila 3: ambos campos (debería usar comision_a_pagar)
        row3 = opc.append("comisiones_incluidas", {})
        row3.comision_a_pagar = 50.0
        row3.total_comision = 999.0  # Este se debe ignorar

        opc.save(ignore_permissions=True)
        
        # 100 (row1) + 200 (row2 legacy) + 50 (row3 prioridad) = 350
        expected_total = 350.0
        self.assertAlmostEqual(flt(opc.monto_total), expected_total, places=2)

    def test_monto_total_handles_zero_values(self):
        """B.4: Hook maneja correctamente valores en cero y campos vacíos"""
        company, _ = get_company_and_currency()
        
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 4.0
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        # Fila con valores explícitos en 0
        row1 = opc.append("comisiones_incluidas", {})
        row1.comision_a_pagar = 0.0
        row1.total_comision = 0.0
        
        # Fila sin valores (None/vacío)
        row2 = opc.append("comisiones_incluidas", {})
        # Campos quedan None/vacíos
        
        # Fila con valor positivo
        row3 = opc.append("comisiones_incluidas", {})
        row3.comision_a_pagar = 75.25

        opc.save(ignore_permissions=True)
        
        # Solo row3 contribuye: 75.25
        expected_total = 75.25
        self.assertAlmostEqual(flt(opc.monto_total), expected_total, places=2)