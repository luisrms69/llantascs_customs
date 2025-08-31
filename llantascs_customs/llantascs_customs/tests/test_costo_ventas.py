import frappe
import unittest
from llantascs_customs.llantascs_customs.api import get_costo_ventas_si

class TestCostoVentas(unittest.TestCase):

    def test_update_stock_si(self):
        class DummySI: 
            update_stock = 1
        class MockResult:
            total_cost = 500
        frappe.get_doc = lambda dt, name: DummySI()
        frappe.db.sql = lambda *a, **kw: [MockResult()]
        cost = get_costo_ventas_si("FAKE-SI")
        self.assertEqual(cost, 500)

    def test_si_con_delivery_notes(self):
        class DummySI: 
            update_stock = 0
        class MockDNItem:
            delivery_note = "DN-1"
            item_code = "ITEM-1" 
            qty = 2
        class MockCost:
            cost = 300
        frappe.get_doc = lambda dt, name: DummySI()
        frappe.get_all = lambda *a, **kw: [MockDNItem()]
        frappe.db.sql = lambda *a, **kw: [MockCost()]
        cost = get_costo_ventas_si("FAKE-SI")
        self.assertEqual(cost, 300)

    def test_si_con_devolucion(self):
        class DummySI: 
            update_stock = 0
        class MockReturn:
            name = "RETURN-SI"
        
        def mock_get_all(*args, **kwargs):
            if len(args) > 0:
                if "Sales Invoice Item" in args[0]:
                    return []  # No delivery notes
                elif "Sales Invoice" in args[0]:
                    return [MockReturn()]  # Return invoice found
            return []
        
        frappe.get_doc = lambda dt, name: DummySI()
        frappe.get_all = mock_get_all
        # simular recursión
        import llantascs_customs.llantascs_customs.api as api
        api.get_costo_ventas_si = lambda name: 100
        api._costo_bruto_factura = lambda name: 500
        cost = get_costo_ventas_si("FAKE-SI")
        self.assertEqual(cost, 400)

    def test_fallback_valido(self):
        class DummySI: 
            update_stock = 0
        class MockItem:
            base_rate = 100
            qty = 2
        
        def mock_get_all(*args, **kwargs):
            if len(args) > 0:
                if "Sales Invoice Item" in args[0] and "delivery_note" in str(kwargs):
                    return []  # No delivery notes
                elif "Sales Invoice" in args[0] and "is_return" in str(kwargs):
                    return []  # No returns
                elif "Sales Invoice Item" in args[0]:
                    return [MockItem()]  # For fallback calculation
            return []
        
        frappe.get_doc = lambda dt, name: DummySI()
        frappe.get_all = mock_get_all
        frappe.msgprint = lambda *a, **kw: None
        frappe.log_error = lambda *a, **kw: None
        cost = get_costo_ventas_si("FAKE-SI")
        self.assertEqual(cost, 200)

    def test_fallback_error(self):
        class DummySI: 
            update_stock = 0
        frappe.get_doc = lambda dt, name: DummySI()
        frappe.get_all = lambda *a, **kw: []
        frappe.log_error = lambda *a, **kw: None
        frappe.throw = lambda msg: (_ for _ in ()).throw(Exception(msg))
        with self.assertRaises(Exception):
            get_costo_ventas_si("FAKE-SI")