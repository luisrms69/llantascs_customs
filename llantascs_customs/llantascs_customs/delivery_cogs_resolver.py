# -*- coding: utf-8 -*-
import json
import frappe
from frappe.utils import flt

def _sum_cogs_from_sle(filters):
    sle = frappe.get_all(
        "Stock Ledger Entry",
        filters={**filters, "is_cancelled": 0},
        fields=["stock_value_difference"]
    )
    if not sle:
        return 0.0, []
    # Para issues de salida: stock_value_difference suele ser negativo.
    total = 0.0
    refs = []
    for r in sle:
        val = flt(r.stock_value_difference)
        total += (-val)  # cost as positive
        refs.append({"doctype": "Stock Ledger Entry", "name": None, "value": r.stock_value_difference})
    return max(0.0, round(total, 6)), refs

def _get_si(si_name):
    return frappe.get_doc("Sales Invoice", si_name)

def _match_si_items(si, row):
    """Intenta encontrar ítems de SI relevantes para el renglón de comisión.
    Estrategia:
      1) Coincidencia por 'si_item'/'sales_invoice_item'
      2) Por 'item_code' si existe en el row
      3) Si no hay match, devuelve todos (para prorrateo posterior)
    """
    targets = []
    si_item_name = getattr(row, "si_item", None) or getattr(row, "sales_invoice_item", None)
    item_code = getattr(row, "item_code", None)
    for it in si.items:
        if si_item_name and it.name == si_item_name:
            targets = [it]; break
    if not targets and item_code:
        targets = [it for it in si.items if it.item_code == item_code]
    if not targets:
        targets = list(si.items)
    return targets

def _is_update_stock_si(si):
    return bool(int(getattr(si, "update_stock", 0) or 0))

def _cogs_from_si_update_stock(si, items):
    """COGS directo desde SLE de la SI (por detalle si es posible)."""
    total = 0.0; all_refs = []
    for it in items:
        cogs, refs = _sum_cogs_from_sle({
            "voucher_type": "Sales Invoice",
            "voucher_no": si.name,
            "voucher_detail_no": it.name
        })
        total += cogs; all_refs += refs
    src = "SI_UPDATE_STOCK"
    return total, src, "SI", all_refs

def _dn_items_by_si(si, items):
    """Busca DN Items ligados a la SI (directo)."""
    dn_items = []
    for it in items:
        q = frappe.get_all("Delivery Note Item",
            filters={"docstatus": 1, "si_detail": it.name},
            fields=["name","parent","item_code","qty"])
        if not q:
            # fallback por against_sales_invoice
            q = frappe.get_all("Delivery Note Item",
                filters={"docstatus": 1, "against_sales_invoice": si.name, "item_code": it.item_code},
                fields=["name","parent","item_code","qty"])
        dn_items += q
    return dn_items

def _cogs_from_dn_items(dn_items):
    total = 0.0; refs = []
    for d in dn_items:
        cogs, sle_refs = _sum_cogs_from_sle({
            "voucher_type": "Delivery Note",
            "voucher_no": d["parent"],
            "voucher_detail_no": d["name"]
        })
        total += cogs
        refs.append({"doctype":"Delivery Note Item", "name": d["name"], "parent": d["parent"], "sle": sle_refs})
    return total, refs

def _dn_items_by_so(si_items):
    """Cuando la SI no enlaza DN, buscamos DN por relación con SO/SO Item."""
    so_details = []
    for it in si_items:
        so_detail = getattr(it, "so_detail", None)
        so = getattr(it, "sales_order", None)
        if so_detail:
            so_details.append({"so": so, "so_detail": so_detail, "item_code": it.item_code})
    dn_items = []
    for ref in so_details:
        q = frappe.get_all("Delivery Note Item",
            filters={"docstatus":1, "so_detail": ref["so_detail"]},
            fields=["name","parent","item_code","qty"])
        if not q and ref["so"]:
            q = frappe.get_all("Delivery Note Item",
                filters={"docstatus":1, "against_sales_order": ref["so"], "item_code": ref["item_code"]},
                fields=["name","parent","item_code","qty"])
        dn_items += q
    return dn_items

def _is_drop_ship(si_items):
    """Detecta drop ship por banderas en SO Item (delivered_by_supplier)."""
    for it in si_items:
        so_detail = getattr(it, "so_detail", None)
        if not so_detail: 
            continue
        try:
            val = frappe.get_value("Sales Order Item", so_detail, "delivered_by_supplier")
            if int(val or 0) == 1:
                return True
        except Exception:
            pass
    return False

def _cogs_from_purchases_via_so(si_items):
    """Para drop ship: buscar costo en PI/PR/PO vinculados a SO Item."""
    # Orden de preferencia: PI -> PR -> PO
    total = 0.0; refs = []; source = None
    # 1) PI
    pil = []
    for it in si_items:
        so_detail = getattr(it, "so_detail", None)
        if not so_detail: 
            continue
        r = frappe.get_all("Purchase Invoice Item",
            filters={"docstatus":1, "so_detail": so_detail},
            fields=["parent","name","item_code","qty","base_net_amount","base_net_rate"])
        pil += r
    if pil:
        for r in pil:
            amt = flt(r.get("base_net_amount") or 0)
            if not amt and r.get("base_net_rate") and r.get("qty"):
                amt = flt(r["base_net_rate"]) * flt(r["qty"])
            total += max(0.0, amt)
            refs.append({"doctype":"Purchase Invoice Item","parent":r["parent"],"name":r["name"]})
        source = "DROP_SHIP_PI"
        return total, source, "DROP_SHIP", refs

    # 2) PR
    prl = []
    for it in si_items:
        so_detail = getattr(it, "so_detail", None)
        if not so_detail: 
            continue
        # PR no siempre enlaza directo a SO Item; revisa vía PO Item
        po_detail = frappe.db.get_value("Purchase Order Item", {"so_detail": so_detail}, "name")
        if po_detail:
            r = frappe.get_all("Purchase Receipt Item",
                filters={"docstatus":1, "po_detail": po_detail},
                fields=["parent","name","item_code","qty","base_net_amount","base_net_rate"])
            prl += r
    if prl:
        for r in prl:
            amt = flt(r.get("base_net_amount") or 0)
            if not amt and r.get("base_net_rate") and r.get("qty"):
                amt = flt(r["base_net_rate"]) * flt(r["qty"])
            total += max(0.0, amt)
            refs.append({"doctype":"Purchase Receipt Item","parent":r["parent"],"name":r["name"]})
        source = "DROP_SHIP_PR"
        return total, source, "DROP_SHIP", refs

    # 3) PO (último para drop ship)
    pol = []
    for it in si_items:
        so_detail = getattr(it, "so_detail", None)
        if not so_detail: 
            continue
        r = frappe.get_all("Purchase Order Item",
            filters={"docstatus":1, "so_detail": so_detail},
            fields=["parent","name","item_code","qty","base_net_amount","base_net_rate"])
        pol += r
    if pol:
        for r in pol:
            amt = flt(r.get("base_net_amount") or 0)
            if not amt and r.get("base_net_rate") and r.get("qty"):
                amt = flt(r["base_net_rate"]) * flt(r["qty"])
            total += max(0.0, amt)
            refs.append({"doctype":"Purchase Order Item","parent":r["parent"],"name":r["name"]})
        source = "DROP_SHIP_PO"
        return total, source, "DROP_SHIP", refs

    return 0.0, None, "DROP_SHIP", []

def _cogs_from_gl_fallback(si):
    """Último recurso: GL de la SI. Se prorrateará fuera por ingreso."""
    gl = frappe.get_all("GL Entry",
        filters={"docstatus":1, "voucher_type":"Sales Invoice", "voucher_no":si.name},
        fields=["name","account","debit","credit"])
    total = 0.0
    refs = [{"doctype":"GL Entry","name": r["name"], "account": r["account"], "debit": r["debit"], "credit": r["credit"]} for r in gl]
    # Heurística: sumar débitos en cuentas de gasto directas (COGS)
    # Si no tienes mapeo de cuentas, puedes tomar sum(debit) - sum(credit) sobre cuentas con root_type Expense.
    # Para simplificar aquí: total = sum(debit)
    for r in gl:
        total += flt(r["debit"])
    return max(0.0, round(total, 6)), "GL_FALLBACK", "N/A", refs

def resolve_cogs_for_row(opc, row):
    """Devuelve dict con costo de ventas resuelto y metadatos.
       Orden: SI(update_stock) → DN directo → DN vía SO → DROP_SHIP (PI/PR/PO) → GL SI.
       Si no encontramos nada, cogs=0 con fuente 'N/A'.
    """
    si_name = getattr(row, "sales_invoice_id", None) or getattr(row, "sales_invoice", None)
    if not si_name:
        return {"cogs": 0.0, "source": "N/A", "delivered_via":"N/A", "refs":[]}

    si = _get_si(si_name)
    si_items = _match_si_items(si, row)

    # A) SI con update_stock
    if _is_update_stock_si(si):
        cogs, src, via, refs = _cogs_from_si_update_stock(si, si_items)
        if cogs > 0:
            return {"cogs": cogs, "source": src, "delivered_via": via, "refs": refs}

    # B1) DN directo
    dn_items = _dn_items_by_si(si, si_items)
    if dn_items:
        cogs, refs = _cogs_from_dn_items(dn_items)
        if cogs > 0:
            return {"cogs": cogs, "source": "DN_DIRECT", "delivered_via":"DN", "refs": refs}

    # B2) DN vía SO
    dn_items = _dn_items_by_so(si_items)
    if dn_items:
        cogs, refs = _cogs_from_dn_items(dn_items)
        if cogs > 0:
            return {"cogs": cogs, "source": "DN_VIA_SO", "delivered_via":"DN", "refs": refs}

    # C) Drop Ship
    if _is_drop_ship(si_items):
        cogs, src, via, refs = _cogs_from_purchases_via_so(si_items)
        if cogs > 0 and src:
            return {"cogs": cogs, "source": src, "delivered_via": via, "refs": refs}

    # D) GL fallback (si nada funcionó)
    cogs, src, via, refs = _cogs_from_gl_fallback(si)
    if cogs > 0:
        return {"cogs": cogs, "source": src, "delivered_via": via, "refs": refs}

    return {"cogs": 0.0, "source": "N/A", "delivered_via":"N/A", "refs":[]}