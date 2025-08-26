import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate
from llantascs_customs.llantascs_customs.tests._utils import (
    require_any_company,
    get_or_create_cost_center,
    safe_delete,
)

class TestCommissionRatesSnapshot(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.local.lang = "es"

    def test_snapshot_is_copied_on_insert_and_is_independent(self):
        # 1) Settings: definir dos sucursales A/B con tasas distintas
        ss = frappe.get_single("Comisiones Settings")
        ss.set("rates_por_sucursal", [])
        # Usa cost centers reales del sitio; para la prueba, intenta obtener cualquiera
        company = require_any_company()
        cc_a = get_or_create_cost_center("Test CC A B1", company)
        cc_b = get_or_create_cost_center("Test CC B B1", company)
        ss.append("rates_por_sucursal", {"cost_center": cc_a, "rate_percent": 3.5})
        ss.append("rates_por_sucursal", {"cost_center": cc_b, "rate_percent": 4.0})
        ss.porcentaje_sobre_utilidad = 2.0
        ss.save(ignore_permissions=True)

        # 2) Crear Orden -> debe copiar snapshot
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.sucursal = cc_a
        opc.insert(ignore_permissions=True)

        self.assertTrue(len(opc.get("rates_por_sucursal_orden") or []) >= 1)
        rate_a_in_order = next((r.rate_percent for r in opc.rates_por_sucursal_orden if r.cost_center == cc_a), None)
        self.assertEqual(rate_a_in_order, 3.5)

        # 3) Cambiar Settings NO debe afectar la Orden ya creada
        ss.set("rates_por_sucursal", [])
        ss.append("rates_por_sucursal", {"cost_center": cc_a, "rate_percent": 9.0})
        ss.save(ignore_permissions=True)

        opc.reload()
        rate_a_in_order_again = next((r.rate_percent for r in opc.rates_por_sucursal_orden if r.cost_center == cc_a), None)
        self.assertEqual(rate_a_in_order_again, 3.5)  # se mantiene el snapshot

        # Cleanup
        safe_delete("Cost Center", cc_a)
        safe_delete("Cost Center", cc_b)

    def test_precedence_uses_row_applied_then_order_snapshot_then_order_level_then_settings(self):
        from llantascs_customs.llantascs_customs.commissions_service import resolve_commission_rate_percent

        ss = frappe.get_single("Comisiones Settings")
        ss.porcentaje_sobre_utilidad = 1.5
        ss.set("rates_por_sucursal", [])
        ss.save(ignore_permissions=True)

        company = require_any_company()
        cc = get_or_create_cost_center("Test CC Precedence B1", company)

        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.sucursal = cc
        opc.comision_sobre_utilidad_ = 2.5
        opc.insert(ignore_permissions=True)

        # snapshot vacío inicialmente -> lo llenamos manualmente con CC ficticio
        opc.append("rates_por_sucursal_orden", {"cost_center": cc, "rate_percent": 4.0})
        opc.save(ignore_permissions=True)
        opc.reload()

        # Simula un renglón
        class Row: pass
        row = Row()
        row.cost_center = cc
        # 1) aplicado en row
        row.applied_rate = 7.0
        self.assertEqual(resolve_commission_rate_percent(opc, row), 7.0)

        # 2) sin applied_rate -> snapshot de la orden
        row.applied_rate = 0.0
        self.assertEqual(resolve_commission_rate_percent(opc, row), 4.0)

        # 3) sin snapshot para esa sucursal -> usa nivel de Orden
        opc.set("rates_por_sucursal_orden", [])
        opc.save()
        self.assertEqual(resolve_commission_rate_percent(opc, row), 2.5)

        # 4) sin nivel Orden -> usa Settings global
        opc.comision_sobre_utilidad_ = 0.0
        self.assertEqual(resolve_commission_rate_percent(opc, row), 1.5)

        # Cleanup
        safe_delete("Cost Center", cc)