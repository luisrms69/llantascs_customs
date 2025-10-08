# -*- coding: utf-8 -*-
"""
Cockpit Installer - Orchestrator for creating cockpit objects
"""

import frappe
from .builders import build_bundle
from .bundles import BUNDLES


def _materialize(items, company, branch):
    """
    Materializes filter lambdas into dict (injects company/branch).

    Args:
        items (list): List of card/chart definitions with lambda filters
        company (str): Company name
        branch (str): Branch name (optional)

    Returns:
        list: Items with materialized filters
    """
    out = []
    for it in items:
        it = it.copy()
        if callable(it.get("filters")):
            it["filters"] = it["filters"](company, branch)
        out.append(it)
    return out


def run(company, branch=None, roles_override=None, only=None):
    """
    Install/update Cockpit objects (Number Cards, Dashboard Charts, Workspaces).

    Args:
        company (str): Company name for filters
        branch (str, optional): Branch name for filters
        roles_override (dict, optional): Override roles per workspace {bundle_key: [roles]}
        only (str, optional): Install only specific bundle (dg|cfo|admin|sucursal)
    """
    frappe.only_for(("System Manager", "Administrator"))

    keys = [only] if only else list(BUNDLES.keys())

    for k in keys:
        b = BUNDLES[k]

        # Materialize filters
        cards = _materialize(b["cards"], company, branch)
        charts = _materialize(b["charts"], company, branch)

        # Get workspace with roles
        ws = b["workspace"](roles_override.get(k) if roles_override else None)

        # Build bundle
        print(f"\n📦 Installing bundle: {k.upper()}")
        build_bundle(cards, charts, ws)
        print(f"✅ Bundle {k.upper()} installed successfully\n")

    frappe.db.commit()
