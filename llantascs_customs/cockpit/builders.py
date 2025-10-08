# -*- coding: utf-8 -*-
"""
Cockpit Builders - Idempotent helpers for creating native ERPNext objects
"""

import json
import frappe


def _j(d):
    """JSON serializer helper"""
    return json.dumps(d or {}, separators=(",", ":"), ensure_ascii=False)


def ensure_number_card(c):
    """
    Creates/updates a Number Card (Report-based). Idempotent.

    Args:
        c (dict): {name, label, report_name, function, aggregate_field, filters, color}

    Returns:
        str: Name of the created/updated Number Card
    """
    name = c["name"]
    doc = frappe.get_doc("Number Card", name) if frappe.db.exists("Number Card", name) else frappe.new_doc("Number Card")

    doc.update({
        "doctype": "Number Card",
        "name": name,
        "label": c["label"],
        "type": "Report",
        "report_name": c["report_name"],
        "function": c.get("function", "Sum"),
        "aggregate_function_based_on": c["aggregate_field"],
        "filters_json": _j(c.get("filters")),
        "is_public": 1,
        "color": c.get("color") or "Blue"
    })

    if doc.name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    return name


def ensure_dashboard_chart(ch):
    """
    Creates/updates a Dashboard Chart (Report source). Idempotent.

    Args:
        ch (dict): {name, title, source_report, chart_type, time_interval, group_by_field, stacked, filters}

    Returns:
        str: Name of the created/updated Dashboard Chart
    """
    name = ch["name"]
    doc = frappe.get_doc("Dashboard Chart", name) if frappe.db.exists("Dashboard Chart", name) else frappe.new_doc("Dashboard Chart")

    doc.update({
        "doctype": "Dashboard Chart",
        "name": name,
        "chart_name": ch["title"],
        "source": "Report",
        "report_name": ch["source_report"],
        "type": ch.get("chart_type", "Bar"),
        "time_interval": ch.get("time_interval"),
        "timeseries": 1 if ch.get("time_interval") else 0,
        "group_by_type": "Group By" if ch.get("group_by_field") else "",
        "group_by_based_on": ch.get("group_by_field"),
        "is_stacked": 1 if ch.get("stacked") else 0,
        "filters_json": _j(ch.get("filters")),
        "is_public": 1
    })

    if doc.name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    return name


def _workspace_uses_children():
    """
    Detect if Workspace uses child tables (v15+) or content JSON (v14).

    Returns:
        bool: True if child tables are present
    """
    meta = frappe.get_meta("Workspace")
    fields = {df.fieldname for df in meta.fields}
    return any(x in fields for x in ("number_cards", "charts", "shortcuts", "links"))


def ensure_workspace(ws):
    """
    Creates/updates a Workspace with children appropriate for version (v14/v15). Idempotent.

    Args:
        ws (dict): {name, title, roles, number_cards, charts, shortcuts}

    Returns:
        str: Name of the created/updated Workspace
    """
    name = ws["name"]
    doc = frappe.get_doc("Workspace", name) if frappe.db.exists("Workspace", name) else frappe.new_doc("Workspace")

    doc.update({
        "doctype": "Workspace",
        "name": name,
        "title": ws["title"],
        "public": 1,
        "sequence_id": 10,
        "module": "Desk"
    })

    # Roles
    doc.set("roles", [])
    for r in ws.get("roles", []):
        doc.append("roles", {"role": r})

    if _workspace_uses_children():
        # v15+: child tables
        doc.set("number_cards", [])
        for nc in ws.get("number_cards", []):
            doc.append("number_cards", {"type": "Number Card", "number_card": nc})

        doc.set("charts", [])
        for ch in ws.get("charts", []):
            doc.append("charts", {"type": "Dashboard Chart", "chart": ch})

        doc.set("shortcuts", [])
        for s in ws.get("shortcuts", []):
            doc.append("shortcuts", {
                "type": s["type"],
                "link_to": s["name"],
                "label": s["label"]
            })
    else:
        # v14: content JSON
        content = []

        if ws.get("number_cards"):
            content.append({
                "type": "cards",
                "label": "KPIs",
                "items": [{"type": "number_card", "name": n} for n in ws["number_cards"]],
                "col": 12
            })

        if ws.get("charts"):
            content.append({
                "type": "charts",
                "label": "Tendencias",
                "items": [{"type": "dashboard_chart", "name": n} for n in ws["charts"]],
                "col": 12
            })

        if ws.get("shortcuts"):
            content.append({
                "type": "shortcuts",
                "label": "Atajos",
                "items": [{"type": "report", "label": s["label"], "name": s["name"]} for s in ws["shortcuts"]],
                "col": 12
            })

        doc.content = content

    if doc.name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    return name


def build_bundle(cards, charts, workspace_def):
    """
    Creates/updates a complete bundle: cards → charts → workspace.

    Args:
        cards (list): List of card definitions
        charts (list): List of chart definitions
        workspace_def (dict): Workspace definition
    """
    for c in cards:
        ensure_number_card(c)

    for ch in charts:
        ensure_dashboard_chart(ch)

    ensure_workspace(workspace_def)
