# -*- coding: utf-8 -*-
import frappe
from frappe.utils import flt

def _is_stock_item(item_code: str) -> bool:
    try:
        return bool(int(frappe.get_cached_value("Item", item_code, "is_stock_item") or 0))
    except Exception:
        return False

def is_fully_delivered(si) -> (bool, list):
    """Entregado totalmente, excepto servicios.
       Reglas:
       - Si SI.update_stock=1 → se considera entregado para ítems stock.
       - Para cada Sales Invoice Item stock: delivered_qty >= qty (ERPNext mantiene delivered_qty vía DN/Drop Ship).
       - Ítems no-stock (servicio) se consideran entregados por definición.
    """
    notes = []
    if int(si.update_stock or 0) == 1:
        notes.append("update_stock=1: entregado por factura")
        return True, notes

    for it in si.items:
        if not it.item_code:
            # líneas como 'Descripción' sin ítem: ignora
            continue
        if not _is_stock_item(it.item_code):
            continue  # servicio → OK
        delivered = flt(getattr(it, "delivered_qty", 0))
        required = flt(it.qty or 0)
        if delivered + 1e-9 < required:
            notes.append(f"Pendiente entrega {it.item_code}: {delivered}/{required}")
            return False, notes
    if not notes:
        notes.append("Todos los ítems stock entregados; servicios excluidos")
    return True, notes

def is_fully_paid(si, tolerance_currency: float = 0.0) -> (bool, list):
    """Pagado totalmente.
       Reglas:
       - Preferimos si.status == 'Paid'
       - O bien outstanding_amount <= tolerancia y no es retorno/NC
    """
    notes = []
    status = (si.status or "").strip()
    outstanding = flt(si.outstanding_amount or 0)
    if status == "Paid":
        notes.append("Estado Paid")
        return True, notes

    if abs(outstanding) <= flt(tolerance_currency or 0):
        if int(si.is_return or 0) == 1 or status in ("Credit Note Issued", "Return"):
            notes.append(f"Outstanding {outstanding} pero estado={status} / retorno; no elegible")
            return False, notes
        notes.append(f"Outstanding <= tolerancia ({outstanding})")
        return True, notes

    notes.append(f"Pendiente de cobro: outstanding={outstanding}, status={status}")
    return False, notes

def resolve_sales_person_for_row(row, si):
    """Resuelve sales_person desde la fila o desde Sales Invoice.sales_team"""
    # 1) Si ya está en el row
    sp_name = getattr(row, "sales_person", None) or getattr(row, "persona_de_ventas", None)
    if sp_name:
        return sp_name
    
    # 2) Desde SI.sales_team (tomar el primero si hay varios)
    if si and si.get("sales_team"):
        for st in si.sales_team:
            if st.get("sales_person"):
                return st.sales_person
    
    return None