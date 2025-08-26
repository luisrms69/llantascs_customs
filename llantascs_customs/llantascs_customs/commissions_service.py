# llantascs_customs/llantascs_customs/commissions_service.py
import frappe
from frappe.utils import getdate, nowdate, flt

def compute_reduction_percent(monthly_rate_percent: float, effective_days: int) -> float:
    """% de reducción lineal sobre el ingreso: (rate/30) * días. Acotado 0..100."""
    if flt(monthly_rate_percent) <= 0 or effective_days <= 0:
        return 0.0
    rho = (flt(monthly_rate_percent) / 30.0) * effective_days
    return max(0.0, min(100.0, round(rho, 6)))

def resolve_revenue_original(row) -> float:
    """Ingreso base del renglón:
       prioridad: ingreso_original -> ingreso -> (margen_original + costo_de_ventas) -> 0
    """
    if flt(getattr(row, "ingreso_original", 0)):
        return flt(row.ingreso_original)
    if flt(getattr(row, "ingreso", 0)):
        return flt(row.ingreso)
    m = flt(getattr(row, "margen_original", 0))
    c = flt(getattr(row, "costo_de_ventas", 0))
    if m or c:
        return max(0.0, m + c)
    return 0.0

def resolve_cost_original(row, revenue_base: float | None = None) -> float:
    """Costo base del renglón:
       prioridad: costo_de_ventas -> (ingreso_base - margen_original, si ambos existen) -> 0
    """
    c = flt(getattr(row, "costo_de_ventas", 0))
    if c:
        return c
    m = flt(getattr(row, "margen_original", 0))
    r = revenue_base if revenue_base is not None else flt(getattr(row, "ingreso", 0))
    if r and (m or m == 0):
        return max(0.0, r - m)
    return 0.0

def resolve_commission_rate_percent(opc, row) -> float:
    """Precedencia:
       1) row.applied_rate (si existe)
       2) snapshot de la Orden (rates_por_sucursal_orden) por cost_center del renglón (o sucursal/opc.sucursal)
       3) % a nivel Orden (comision_sobre_utilidad_)
       4) Settings por sucursal (rates_por_sucursal en Settings)
       5) Settings global (porcentaje_sobre_utilidad)
    """
    # 1) por renglón
    if flt(getattr(row, "applied_rate", 0)):
        return flt(row.applied_rate)

    # clave de sucursal/cost center en el renglón u orden
    cc = getattr(row, "cost_center", None) or getattr(row, "sucursal", None) or getattr(opc, "sucursal", None)

    # 2) snapshot de la Orden
    try:
        for r in (opc.get("rates_por_sucursal_orden") or []):
            if r.cost_center == cc and flt(r.rate_percent):
                return flt(r.rate_percent)
    except Exception:
        pass

    # 3) a nivel de Orden
    if flt(getattr(opc, "comision_sobre_utilidad_", 0)):
        return flt(opc.comision_sobre_utilidad_)

    # 4) Settings por sucursal
    try:
        ss = frappe.get_single("Comisiones Settings")
        for r in (ss.get("rates_por_sucursal") or []):
            if r.cost_center == cc and flt(r.rate_percent):
                return flt(r.rate_percent)
    except Exception:
        pass

    # 5) Settings global
    try:
        return flt(frappe.db.get_single_value("Comisiones Settings", "porcentaje_sobre_utilidad") or 0)
    except Exception:
        return 0.0