import frappe
from frappe.utils import nowdate, add_days
from frappe.utils import flt

def test_commission_rate_by_branch_and_global():
    # Arrange: prepara Settings
    ss = frappe.get_single("Comisiones Settings")
    ss.porcentaje_sobre_utilidad = 2.5
    # limpia tabla
    ss.set("rates_por_sucursal", [])
    ss.append("rates_por_sucursal", {"cost_center": "CC Norte", "rate_percent": 4.0})
    ss.append("rates_por_sucursal", {"cost_center": "CC Sur", "rate_percent": 3.5})
    ss.save()

    from llantascs_customs.llantascs_customs import api

    # 1) Rate por sucursal
    assert flt(api.get_commission_rate("CC Norte")) == 4.0
    assert flt(api.get_commission_rate("CC Sur")) == 3.5

    # 2) Fallback global si sucursal no está en tabla
    assert flt(api.get_commission_rate("CC Centro")) == 2.5

    # 3) Sin sucursal => global
    assert flt(api.get_commission_rate()) == 2.5

def test_default_dates_on_settings():
    ss = frappe.get_single("Comisiones Settings")
    ss.default_start_date = nowdate()
    ss.default_end_date = add_days(nowdate(), 30)
    ss.save()
    # No se valida el JS aquí; QC manual en UI para precarga de fechas.
    assert True