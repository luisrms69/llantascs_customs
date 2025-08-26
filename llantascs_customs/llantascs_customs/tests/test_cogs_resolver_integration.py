# llantascs_customs/llantascs_customs/tests/test_cogs_resolver_integration.py
import json
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, flt

from llantascs_customs.llantascs_customs.tests._utils import (
    create_minimal_sales_invoice,
    get_company_and_currency,
    get_leaf_cost_center,
)

class TestCOGSResolverIntegration(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.local.lang = "es"

    def test_resolver_sets_cost_and_metadata_when_missing(self, monkeypatch=None):
        # Crear SI real mínima (servicio) para satisfacer Link validation
        si_name = create_minimal_sales_invoice(rate=1000.0, qty=1.0)

        # Crear Orden y renglón
        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 4.0
        company, _ = get_company_and_currency()
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        row = opc.append("comisiones_incluidas", {})
        row.sales_invoice_id = si_name     # <-- ahora existe
        row.ingreso = 1000.0
        row.costo_de_ventas = 0.0
        opc.save(ignore_permissions=True)

        # Monkeypatch del resolver para no depender de inventario real
        def fake_resolver(_opc, _row):
            return {
                "cogs": 350.0,
                "source": "DN_DIRECT",
                "delivered_via": "DN",
                "refs": [{"doctype":"Delivery Note Item","name":"DNI-001"}]
            }

        from llantascs_customs.llantascs_customs import delivery_cogs_resolver as rmod
        original_resolver = rmod.resolve_cogs_for_row
        if monkeypatch:
            monkeypatch.setattr(rmod, "resolve_cogs_for_row", fake_resolver)
        else:
            rmod.resolve_cogs_for_row = fake_resolver

        try:
            # Desactiva reducción para aislar costo
            ss = frappe.get_single("Comisiones Settings")
            ss.aplicar_reduccion_por_diferimiento = 0
            ss.save(ignore_permissions=True)

            # Ejecuta cálculo
            from llantascs_customs.llantascs_customs.api import apply_reduction
            apply_reduction(opc.name)

            opc.reload()
            r = opc.comisiones_incluidas[0]
            assert flt(r.costo_de_ventas) == 350.0
            assert r.cogs_source == "DN_DIRECT"
            assert r.delivered_via == "DN"
            assert json.loads(r.cogs_refs)[0]["doctype"] == "Delivery Note Item"
        finally:
            # Restore original resolver
            rmod.resolve_cogs_for_row = original_resolver

    def test_gl_fallback_path_is_used_when_all_else_missing(self, monkeypatch=None):
        # Otra SI mínima
        si_name = create_minimal_sales_invoice(rate=2000.0, qty=1.0)

        opc = frappe.new_doc("Orden de Pago Comisiones")
        opc.desde = nowdate()
        opc.hasta_fecha = nowdate()
        opc.comision_sobre_utilidad_ = 5.0
        company, _ = get_company_and_currency()
        opc.sucursal = get_leaf_cost_center(company)
        opc.insert(ignore_permissions=True)

        row = opc.append("comisiones_incluidas", {})
        row.sales_invoice_id = si_name     # <-- existe
        row.ingreso = 2000.0
        row.costo_de_ventas = 0.0
        opc.save(ignore_permissions=True)

        def fake_resolver(_opc, _row):
            return {
                "cogs": 600.0,
                "source": "GL_FALLBACK",
                "delivered_via": "N/A",
                "refs": [{"doctype":"GL Entry","name":"GLE-XYZ"}]
            }
        from llantascs_customs.llantascs_customs import delivery_cogs_resolver as rmod
        original_resolver = rmod.resolve_cogs_for_row
        if monkeypatch:
            monkeypatch.setattr(rmod, "resolve_cogs_for_row", fake_resolver)
        else:
            rmod.resolve_cogs_for_row = fake_resolver

        try:
            ss = frappe.get_single("Comisiones Settings")
            ss.aplicar_reduccion_por_diferimiento = 0
            ss.save(ignore_permissions=True)

            from llantascs_customs.llantascs_customs.api import apply_reduction
            apply_reduction(opc.name)

            opc.reload()
            r = opc.comisiones_incluidas[0]
            assert flt(r.costo_de_ventas) == 600.0
            assert r.cogs_source == "GL_FALLBACK"
            assert r.delivered_via == "N/A"
            assert "GL Entry" in r.cogs_refs
        finally:
            # Restore original resolver
            rmod.resolve_cogs_for_row = original_resolver