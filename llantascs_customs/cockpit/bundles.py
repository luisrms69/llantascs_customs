# -*- coding: utf-8 -*-
"""
Cockpit Bundles - Bundle definitions for each role
"""

from .constants import (
    DG_CARDS, DG_CHARTS, DG_WORKSPACE,
    CFO_CARDS, CFO_CHARTS, CFO_WORKSPACE
)

BUNDLES = {
    "dg": dict(
        cards=DG_CARDS,
        charts=DG_CHARTS,
        workspace=DG_WORKSPACE
    ),
    "cfo": dict(
        cards=CFO_CARDS,
        charts=CFO_CHARTS,
        workspace=CFO_WORKSPACE
    ),
    # Phase 2: admin, sucursal
}
