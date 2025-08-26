import frappe
from frappe.utils import getdate, nowdate, add_days
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt
from llantascs_customs.llantascs_customs.tests._utils import (
    require_any_company,
    get_or_create_cost_center,
    safe_delete,
)

class TestCommissionReduction(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.local.lang = "es"

    def test_compute_reduction_percent(self):
        from llantascs_customs.llantascs_customs.commissions_service import compute_reduction_percent
        # 6% mensual, 15 días efectivos => 3%
        self.assertAlmostEqual(compute_reduction_percent(6.0, 15), 3.0, places=6)

    def test_apply_reduction_on_revenue(self):
        # Settings
        ss = frappe.get_single("Comisiones Settings")
        ss.aplicar_reduccion_por_diferimiento = 1  # Enable global toggle
        ss.porcentaje_reduccion_mensual = 6.0
        ss.dias_gracia_reduccion = 5
        ss.fecha_base_reduccion = "Due Date"
        ss.save(ignore_permissions=True)

        # Need a dummy Cost Center for sucursal
        company = require_any_company()
        cc = get_or_create_cost_center("Test CC Revenue", company)

        # Orden mínima
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 4.0  # % comisión
        opc.sucursal = cc
        opc.insert(ignore_permissions=True)

        # Renglón con ingreso y costo explícitos
        row = opc.append("comisiones_incluidas", {})
        row.ingreso = 10000.0
        row.costo_de_ventas = 7000.0
        row.fecha_programada_de_pago = add_days(getdate(nowdate()), -20)  # 15 días efectivos
        opc.save(ignore_permissions=True)

        from llantascs_customs.llantascs_customs.api import apply_reduction
        apply_reduction(opc.name)

        opc.reload()
        r = opc.comisiones_incluidas[0]

        # delta = 3% sobre ingreso -> R_aj=9700; M_aj=2700; comisión=108.00
        self.assertAlmostEqual(flt(r.reduccion_ingreso_pct), 3.0, places=2)
        self.assertAlmostEqual(flt(r.ingreso_original), 10000.0, places=2)
        self.assertAlmostEqual(flt(r.ingreso_ajustado), 9700.0, places=2)
        self.assertAlmostEqual(flt(r.margen_ajustado), 2700.0, places=2)
        self.assertAlmostEqual(flt(r.monto_reduccion_ingreso), 300.0, places=2)
        self.assertAlmostEqual(flt(r.monto_reduccion_margen), 300.0, places=2)
        self.assertAlmostEqual(flt(r.comision_post_reduccion), 108.0, places=2)

        # Idempotencia
        apply_reduction(opc.name)
        opc.reload()
        r2 = opc.comisiones_incluidas[0]
        self.assertAlmostEqual(flt(r2.ingreso_ajustado), 9700.0, places=2)
        self.assertAlmostEqual(flt(r2.comision_post_reduccion), 108.0, places=2)

        # Cleanup
        safe_delete("Cost Center", cc)

    def test_negative_margin_results_in_zero_commission(self):
        ss = frappe.get_single("Comisiones Settings")
        ss.aplicar_reduccion_por_diferimiento = 1  # Enable global toggle
        ss.porcentaje_reduccion_mensual = 50.0
        ss.dias_gracia_reduccion = 0
        ss.fecha_base_reduccion = "Posting Date"
        ss.save(ignore_permissions=True)

        company = require_any_company()
        cc = get_or_create_cost_center("Test CC Zero Commission", company)

        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 10.0
        opc.sucursal = cc
        opc.insert(ignore_permissions=True)

        row = opc.append("comisiones_incluidas", {})
        row.ingreso = 100.0
        row.costo_de_ventas = 120.0  # margen original negativo
        row.fecha_programada_de_pago = add_days(getdate(nowdate()), -40)  # delta grande
        opc.save(ignore_permissions=True)

        from llantascs_customs.llantascs_customs.api import apply_reduction
        apply_reduction(opc.name)

        opc.reload()
        r = opc.comisiones_incluidas[0]
        self.assertEqual(flt(r.margen_ajustado), 0.0)
        self.assertEqual(flt(r.comision_post_reduccion), 0.0)

        # Cleanup
        safe_delete("Cost Center", cc)