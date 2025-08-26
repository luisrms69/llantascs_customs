import uuid
import frappe
from frappe.utils import flt
from frappe.tests.utils import FrappeTestCase

from llantascs_customs.llantascs_customs.tests._utils import (
    set_lang_es_temporarily,
    require_any_company,
    get_or_create_cost_center,
    safe_delete,
)

class TestCommissionRates(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_lang_es_temporarily()  # sólo contexto de test

        # Requiere que exista al menos un Company en el sitio
        cls.company = require_any_company()

        # Creamos 2 CC de prueba (si existen, los reutilizamos)
        suffix = uuid.uuid4().hex[:6].upper()
        cls.cc_a_name = f"__TEST__CC_NORTE_{suffix}"
        cls.cc_b_name = f"__TEST__CC_SUR_{suffix}"

        cls.cc_a = get_or_create_cost_center(cls.cc_a_name, cls.company)
        cls.cc_b = get_or_create_cost_center(cls.cc_b_name, cls.company)

    @classmethod
    def tearDownClass(cls):
        # Limpia los CC de prueba (si no tienen dependencias)
        safe_delete("Cost Center", cls.cc_a)
        safe_delete("Cost Center", cls.cc_b)
        super().tearDownClass()

    def test_commission_rate_by_branch_and_global(self):
        # Arrange: configura Comisiones Settings
        ss = frappe.get_single("Comisiones Settings")
        ss.porcentaje_sobre_utilidad = 2.5  # global default
        ss.set("rates_por_sucursal", [])
        ss.append("rates_por_sucursal", {
            "cost_center": self.cc_a,
            "rate_percent": 4.0
        })
        ss.save(ignore_permissions=True)

        # Act
        from llantascs_customs.llantascs_customs.api import get_commission_rate

        rate_a = flt(get_commission_rate(self.cc_a))
        rate_b = flt(get_commission_rate(self.cc_b))     # no está en tabla -> usa global
        rate_global = flt(get_commission_rate())         # sin sucursal -> global

        # Assert
        self.assertEqual(rate_a, 4.0)
        self.assertEqual(rate_b, 2.5)
        self.assertEqual(rate_global, 2.5)