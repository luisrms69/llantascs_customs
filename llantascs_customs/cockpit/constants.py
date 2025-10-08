# -*- coding: utf-8 -*-
"""
Cockpit Constants - Catalog of cards, charts and workspaces
"""


def _auto(company, branch=None):
    """Helper to inject company/branch into filters"""
    return {"company": company, "branch": branch} if branch else {"company": company}


# ============================================================================
# DIRECCIÓN GENERAL (DG)
# ============================================================================

DG_CARDS = [
    dict(
        name="card_dg_ventas_mes",
        label="DG | Ventas Mes",
        report_name="Sales Analytics",
        function="Sum",
        aggregate_field="base_net_total",
        filters=lambda c, b: {
            **_auto(c, b),
            "from_date": "auto:month_start",
            "to_date": "auto:month_end",
            "group_by": "Month",
            "docstatus": 1
        },
        color="Blue"
    ),
    dict(
        name="card_dg_margen_mes",
        label="DG | Margen Bruto (Mes)",
        report_name="Gross Profit",
        function="Sum",
        aggregate_field="gross_profit",
        filters=lambda c, b: {
            **_auto(c, b),
            "from_date": "auto:month_start",
            "to_date": "auto:month_end",
            "docstatus": 1
        },
        color="Green"
    ),
    dict(
        name="card_dg_cartera_30",
        label="DG | Cartera >30d",
        report_name="Accounts Receivable Summary",
        function="Sum",
        aggregate_field="outstanding_amount",
        filters=lambda c, b: {
            **_auto(c, b),
            "docstatus": 1,
            "ageing_based_on": "Posting Date",
            "range1": 30
        },
        color="Red"
    ),
    dict(
        name="card_dg_stock_value",
        label="DG | Inventario (Valor)",
        report_name="Stock Balance",
        function="Sum",
        aggregate_field="stock_value",
        filters=lambda c, b: {
            **_auto(c, b),
            "to_date": "auto:today"
        },
        color="Yellow"
    ),
]

DG_CHARTS = [
    dict(
        name="chart_dg_sales_by_branch_12m",
        title="DG | Ventas por Sucursal (12M)",
        source_report="Sales Analytics",
        chart_type="Bar",
        time_interval="Monthly",
        stacked=1,
        group_by_field="branch",
        filters=lambda c, b: {
            **_auto(c, b),
            "from_date": "auto:today-365",
            "to_date": "auto:today",
            "group_by": "Month",
            "docstatus": 1
        }
    ),
    dict(
        name="chart_dg_gp_by_branch_12m",
        title="DG | Margen por Sucursal (12M)",
        source_report="Gross Profit",
        chart_type="Line",
        time_interval="Monthly",
        stacked=0,
        group_by_field="branch",
        filters=lambda c, b: {
            **_auto(c, b),
            "from_date": "auto:today-365",
            "to_date": "auto:today",
            "docstatus": 1
        }
    ),
    dict(
        name="chart_dg_ar_aging_buckets",
        title="DG | AR por Bucket",
        source_report="Accounts Receivable Summary",
        chart_type="Bar",
        time_interval=None,
        stacked=0,
        group_by_field=None,
        filters=lambda c, b: {
            **_auto(c, b),
            "docstatus": 1
        }
    ),
    dict(
        name="chart_dg_stock_by_itemgroup",
        title="DG | Inventario por Familia",
        source_report="Stock Balance",
        chart_type="Bar",
        time_interval=None,
        stacked=0,
        group_by_field="item_group",
        filters=lambda c, b: {
            **_auto(c, b),
            "to_date": "auto:today"
        }
    ),
]

DG_WORKSPACE = lambda roles: dict(
    name="ws_cockpit_dg",
    title="Cockpit — Dirección General",
    roles=roles or ["System Manager"],
    number_cards=[x["name"] for x in DG_CARDS],
    charts=[x["name"] for x in DG_CHARTS],
    shortcuts=[
        dict(label="Sales Analytics (12M)", type="Report", name="Sales Analytics"),
        dict(label="Gross Profit (YTD)", type="Report", name="Gross Profit"),
        dict(label="AR Summary (Aging)", type="Report", name="Accounts Receivable Summary"),
        dict(label="Stock Balance", type="Report", name="Stock Balance"),
        dict(label="Profit and Loss", type="Report", name="Profit and Loss"),
        dict(label="DN To Bill", type="Report", name="Delivery Note"),
    ],
)


# ============================================================================
# CFO
# ============================================================================

CFO_CARDS = [
    dict(
        name="card_cfo_ar_total",
        label="CFO | AR Total",
        report_name="Accounts Receivable Summary",
        function="Sum",
        aggregate_field="outstanding_amount",
        filters=lambda c, b: {
            **_auto(c, b),
            "docstatus": 1
        },
        color="Red"
    ),
    dict(
        name="card_cfo_ap_total",
        label="CFO | AP Total",
        report_name="Accounts Payable Summary",
        function="Sum",
        aggregate_field="outstanding_amount",
        filters=lambda c, b: {
            **_auto(c, b),
            "docstatus": 1
        },
        color="Purple"
    ),
    dict(
        name="card_cfo_stock_180",
        label="CFO | Inventario >180d",
        report_name="Stock Ageing",
        function="Sum",
        aggregate_field="stock_value",
        filters=lambda c, b: {
            **_auto(c, b),
            "to_date": "auto:today",
            "age_greater_than": 180
        },
        color="Yellow"
    ),
]

CFO_CHARTS = [
    dict(
        name="chart_cfo_cash_inout_weekly",
        title="CFO | Cash In/Out (Semanas)",
        source_report="Payment Entry",
        chart_type="Bar",
        time_interval="Weekly",
        stacked=1,
        group_by_field="payment_type",
        filters=lambda c, b: {
            **_auto(c, b),
            "docstatus": 1
        }
    ),
    dict(
        name="chart_cfo_gp_by_itemgroup_12m",
        title="CFO | GP por Familia (12M)",
        source_report="Gross Profit",
        chart_type="Bar",
        time_interval="Monthly",
        stacked=1,
        group_by_field="item_group",
        filters=lambda c, b: {
            **_auto(c, b),
            "from_date": "auto:today-365",
            "to_date": "auto:today",
            "docstatus": 1
        }
    ),
]

CFO_WORKSPACE = lambda roles: dict(
    name="ws_cockpit_cfo",
    title="Cockpit — CFO",
    roles=roles or ["Finance Manager", "Accounts Manager"],
    number_cards=[x["name"] for x in CFO_CARDS],
    charts=[x["name"] for x in CFO_CHARTS],
    shortcuts=[
        dict(label="Trial Balance", type="Report", name="Trial Balance"),
        dict(label="General Ledger", type="Report", name="General Ledger"),
        dict(label="Profit and Loss", type="Report", name="Profit and Loss"),
        dict(label="Cash Flow", type="Report", name="Cash Flow"),
        dict(label="Balance Sheet", type="Report", name="Balance Sheet"),
        dict(label="Bank Reconciliation", type="Report", name="Bank Reconciliation Statement"),
    ],
)
