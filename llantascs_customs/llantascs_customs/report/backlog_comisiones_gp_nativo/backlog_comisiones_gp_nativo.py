# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional, Iterable, Set
import frappe
from frappe.utils import add_months, getdate

# Import del reporte estándar Gross Profit (ajusta si tu versión usa otro path)
try:
    from erpnext.accounts.report.gross_profit.gross_profit import execute as gp_execute
except Exception:
    gp_execute = None


# ============
# UTILIDADES
# ============

def _as_date(d: Optional[str]) -> frappe.utils.date:
    return getdate(d) if d else getdate()


def _fetch_cc_tree_bounds(cc_names: Iterable[str]) -> Dict[str, Tuple[int, int]]:
    """Devuelve {cc_name: (lft, rgt)}; ignora nulos."""
    cc_names = [c for c in set(cc_names) if c]
    if not cc_names:
        return {}
    rows = frappe.db.sql("""
        SELECT name, lft, rgt
        FROM `tabCost Center`
        WHERE name IN %(n)s
    """, {"n": tuple(cc_names)}, as_dict=True)
    return {r["name"]: (r["lft"], r["rgt"]) for r in rows}


def _is_cc_inside(root_bounds: Tuple[int, int], child_cc: str, cache_bounds: Dict[str, Tuple[int, int]]) -> bool:
    """¿child_cc está dentro del árbol de root_bounds?"""
    if not child_cc or not root_bounds:
        return False
    b = cache_bounds.get(child_cc)
    if not b:
        # cargar on-demand para cc no presentes
        row = frappe.db.get_value("Cost Center", child_cc, ["lft", "rgt"], as_dict=True)
        if not row:
            return False
        cache_bounds[child_cc] = (row.lft, row.rgt)
        b = cache_bounds[child_cc]
    return (root_bounds[0] <= b[0] <= b[1] <= root_bounds[1])


def _map_si_detail_to_cc(si_detail_ids: Iterable[str]) -> Dict[str, Optional[str]]:
    """Mapea Sales Invoice Item.name -> cost_center"""
    ids = [i for i in set(si_detail_ids) if i]
    if not ids:
        return {}
    rows = frappe.db.sql("""
        SELECT name AS si_detail, cost_center
        FROM `tabSales Invoice Item`
        WHERE name IN %(ids)s
    """, {"ids": tuple(ids)}, as_dict=True)
    return {r["si_detail"]: r.get("cost_center") for r in rows}


def _map_invoice_to_cc(invoice_names: Iterable[str]) -> Dict[str, Optional[str]]:
    """Mapea Sales Invoice.name -> cost_center (fallback si el ítem no trae)"""
    names = [n for n in set(invoice_names) if n]
    if not names:
        return {}
    rows = frappe.db.sql("""
        SELECT name AS invoice, cost_center
        FROM `tabSales Invoice`
        WHERE name IN %(n)s
    """, {"n": tuple(names)}, as_dict=True)
    return {r["invoice"]: r.get("cost_center") for r in rows}


def _collect_cc_from_gp_rows(gp_rows: List[Dict[str, Any]]) -> Tuple[Set[str], Dict[str, Optional[str]], Dict[str, Optional[str]]]:
    """Extrae llaves (si_detail, invoice) y prepara mapas a cost_center."""
    si_details, invoices = set(), set()
    for d in gp_rows:
        sid = d.get("si_detail") or d.get("sales_invoice_item")
        inv = d.get("invoice") or d.get("sales_invoice")
        if sid: si_details.add(sid)
        if inv: invoices.add(inv)

    # mapas a CC
    cc_by_si_detail = _map_si_detail_to_cc(si_details)
    cc_by_invoice   = _map_invoice_to_cc(invoices)
    return invoices, cc_by_si_detail, cc_by_invoice


def _gross_profit_percent_of_row(d: Dict[str, Any]) -> Optional[float]:
    """Devuelve el porcentaje de margen que entrega el GP estándar en el renglón."""
    for k in ("gross_profit_percent", "gross_profit_percentage", "gp_percent", "gross_margin_percent"):
        val = d.get(k)
        try:
            return float(val) if val is not None else None
        except Exception:
            continue
    return None


# ======================================================
# 1) TRAER TODAS LAS COLUMNAS BASE DEL BACKLOG (SQL)
# ======================================================

# SQL ORIGINAL de "Backlog Comisiones Completo" (copiada tal cual)
SQL_BACKLOG = """
with
gl_90d AS (
    SELECT
        gle.cost_center,
        gle.account,
        gle.debit,
        gle.credit
    FROM `tabGL Entry` gle
    WHERE gle.posting_date BETWEEN DATE_SUB(%(to_date)s, INTERVAL 90 DAY) AND %(to_date)s
      AND gle.is_cancelled = 0
),
sales_cc AS (
    SELECT cost_center, SUM(credit - debit) AS selling_amount
    FROM gl_90d gle
    INNER JOIN `tabAccount` acc ON acc.name = gle.account
    WHERE acc.root_type = 'Income'
    GROUP BY cost_center
),
cogs_cc AS (
    SELECT cost_center, SUM(debit - credit) AS buying_amount
    FROM gl_90d gle
    INNER JOIN `tabAccount` acc ON acc.name = gle.account
    WHERE acc.account_type = 'Cost of Goods Sold'
    GROUP BY cost_center
),
cc_margin AS (
    SELECT
        s.cost_center,
        (s.selling_amount - IFNULL(c.buying_amount,0)) / NULLIF(s.selling_amount,0) AS avg_margin_rate
    FROM sales_cc s
    LEFT JOIN cogs_cc c ON c.cost_center = s.cost_center
),
rate_cc as (
  select
    cr.cost_center,
    cr.porcentaje_comision
  from `tabComisiones Settings Sucursal` cr
  where cr.parenttype  = 'Comisiones Settings'
    and cr.parent      = 'Comisiones Settings'
    and cr.parentfield = 'tasas_por_sucursal'
),
rate_default as (
  select (s.value + 0.0) as default_rate
  from `tabSingles` s
  where s.doctype='Comisiones Settings' and s.field='porcentaje_sobre_utilidad'
  limit 1
),
base_si as (
  select si.*
  from `tabSales Invoice` si
  where si.docstatus = 1
    and si.posting_date between %(from_date)s and %(to_date)s
    and (si.custom_status_comisiones IS NULL OR si.custom_status_comisiones = 'Sin Enviar')
    and not exists (
      select 1
      from `tabClientes Sin Comision` ex
      where ex.parenttype  = 'Comisiones Settings'
        and ex.parent      = 'Comisiones Settings'
        and ex.parentfield = 'clientes_sin_comision'
        and ex.customer    = si.customer
        and (ex.start_date is null or si.posting_date >= ex.start_date)
        and (ex.end_date   is null or si.posting_date <= ex.end_date)
    )
    and not exists (
      select 1
      from `tabComision LLCS` c
      inner join `tabOrden de Pago Comisiones` opc on opc.name = c.parent
      where opc.docstatus = 1
        and c.sales_invoice_id = si.name
    )
)
select
  si.name          as "Factura:Link/Sales Invoice:160",
  si.posting_date  as "Fecha:Date:95",
  si.customer      as "Cliente:Link/Customer:220",
  si.cost_center   as "Sucursal:Link/Cost Center:150",
  (select group_concat(distinct st.sales_person order by st.sales_person separator ', ')
   from `tabSales Team` st
   where st.parent = si.name) as "Vendedores:Data:200",
  ROUND(si.base_net_total, 2)  as "Venta (OPC def):Currency:120",
  ROUND(COALESCE(m.avg_margin_rate, 0) * 100.0, 2)   as "Margen pct CC:Percent:110",
  coalesce(r.porcentaje_comision, d.default_rate, 0)    as "Rate Comisión:Percent:110",
ROUND(
    si.base_net_total * IFNULL(m.avg_margin_rate,0) * (IFNULL(r.porcentaje_comision, d.default_rate) / 100.0),
    2
) AS "Comisión Estimada:Currency:120",
CASE WHEN si.outstanding_amount = 0 THEN 1 ELSE 0 END AS "Pago OK:Check:80",

CASE
  WHEN NOT EXISTS (
    SELECT 1 FROM `tabSales Invoice Item` sii
    INNER JOIN `tabItem` i ON i.name = sii.item_code
    WHERE sii.parent = si.name AND i.is_stock_item = 1
  ) THEN 1
  WHEN si.update_stock = 1 THEN 1
  WHEN EXISTS (
    SELECT 1 FROM `tabDelivery Note Item` dni
    INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent AND dn.docstatus = 1
    WHERE dni.against_sales_invoice = si.name
  ) THEN 1
  ELSE 0
END AS "Entrega OK:Check:80",

CASE WHEN EXISTS (
    SELECT 1 FROM `tabComision LLCS` c
    INNER JOIN `tabOrden de Pago Comisiones` opc
      ON opc.name = c.parent AND opc.docstatus = 1
    WHERE c.sales_invoice_id = si.name
) THEN 1 ELSE 0 END AS "Comisiones OK:Check:90"
from base_si si
left join cc_margin    m on m.cost_center = si.cost_center
left join rate_cc      r on r.cost_center = si.cost_center
left join rate_default d on 1=1
order by si.posting_date desc, si.name desc
"""

def _get_backlog_rows(filters: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Ejecuta la SQL ORIGINAL para devolver:
      - columns: metadatos (list[dict] con label, fieldname, fieldtype...)
      - rows:    list[dict] con todas las columnas actuales
    """
    rows = frappe.db.sql(SQL_BACKLOG, filters, as_dict=True)
    
    # Construir columnas en el mismo orden/labels que la SQL original
    columns = [
        {"fieldname": "name", "label": "Factura", "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
        {"fieldname": "posting_date", "label": "Fecha", "fieldtype": "Date", "width": 95},
        {"fieldname": "customer", "label": "Cliente", "fieldtype": "Link", "options": "Customer", "width": 220},
        {"fieldname": "cost_center", "label": "Sucursal", "fieldtype": "Link", "options": "Cost Center", "width": 150},
        {"fieldname": "vendedores", "label": "Vendedores", "fieldtype": "Data", "width": 200},
        {"fieldname": "venta_opc_def", "label": "Venta (OPC def)", "fieldtype": "Currency", "width": 120},
        {"fieldname": "margin_cc_6m_gp", "label": "Margen Sucursal 6m (GP nativo)", "fieldtype": "Percent", "precision": 2, "width": 160},
        {"fieldname": "rate_comision", "label": "Rate Comisión", "fieldtype": "Percent", "width": 110},
        {"fieldname": "comision_estimada_gp", "label": "Comisión Estimada GP nativo", "fieldtype": "Currency", "width": 130},
        {"fieldname": "pago_ok", "label": "Pago OK", "fieldtype": "Check", "width": 80},
        {"fieldname": "entrega_ok", "label": "Entrega OK", "fieldtype": "Check", "width": 80},
        {"fieldname": "comisiones_ok", "label": "Comisiones OK", "fieldtype": "Check", "width": 90},
    ]
    
    # Mapear resultados SQL a fieldnames esperados
    # Las keys reales del SQL incluyen el formato completo con tipos y anchos
    mapped_rows = []
    for row in rows:
        mapped_row = {
            "name": row.get("Factura:Link/Sales Invoice:160"),
            "posting_date": row.get("Fecha:Date:95"),
            "customer": row.get("Cliente:Link/Customer:220"),
            "cost_center": row.get("Sucursal:Link/Cost Center:150"),
            "vendedores": row.get("Vendedores:Data:200"),
            "venta_opc_def": row.get("Venta (OPC def):Currency:120"),
            "rate_comision": row.get("Rate Comisión:Percent:110"),
            "pago_ok": row.get("Pago OK:Check:80"),
            "entrega_ok": row.get("Entrega OK:Check:80"),
            "comisiones_ok": row.get("Comisiones OK:Check:90"),
        }
        mapped_rows.append(mapped_row)
    
    return columns, mapped_rows


# ======================================================
# 2) CALCULAR "MARGEN SUCURSAL 6M (GP NATIVO)" (PROMEDIO)
# ======================================================

def _gp_rows_last_6m(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Invoca el reporte estándar Gross Profit en el rango [to_date - 6m, to_date].
    Devuelve las filas crudas del GP (dicts) sin transformar.
    """
    if gp_execute is None:
        frappe.throw("No se pudo importar el reporte estándar 'Gross Profit'. Verifica la versión/ruta de ERPNext.")

    to_date = _as_date(filters.get("to_date"))
    from_date = add_months(to_date, -6)

    # Filtros que el GP estándar soporta (necesita company obligatorio)
    company = filters.get("company") or frappe.defaults.get_global_default("company")
    
    # ERPNext Gross Profit expects frappe._dict object, not dict
    gp_filters = frappe._dict({
        "company": company,
        "from_date": str(from_date),
        "to_date": str(to_date),
        "group_by": "Cost Center"  # Necesario para agrupar por Cost Center
    })

    gp_columns, gp_rows_raw = gp_execute(gp_filters)
    
    # Convert list rows to dict rows using column fieldnames
    if not gp_rows_raw or not gp_columns:
        return []
    
    # Extract fieldnames from columns
    field_names = [col.get('fieldname', f'col_{i}') for i, col in enumerate(gp_columns)]
    
    # Convert each row from list to dict
    gp_rows = []
    for row in gp_rows_raw:
        if isinstance(row, list):
            # Convert list to dict using field names
            row_dict = {}
            for i, value in enumerate(row):
                if i < len(field_names):
                    row_dict[field_names[i]] = value
            gp_rows.append(row_dict)
        else:
            # Already a dict, use as-is
            gp_rows.append(row)
    
    return gp_rows


def _build_margin_cc_6m_map(
    gp_rows: List[Dict[str, Any]],
    target_ccs: Iterable[str]
) -> Dict[str, Optional[float]]:
    """
    Calcula: para cada CC objetivo, 
    busca el margen directamente en los datos agrupados del GP por Cost Center.
    
    Retorna: {cc_name: margin_percent or None}
    """
    # Create direct mapping from GP data (already grouped by Cost Center)
    gp_margin_by_cc: Dict[str, float] = {}
    
    for row in gp_rows:
        cost_center = row.get('cost_center')
        margin_percent = row.get('gross_profit_%', row.get('gross_profit_percent'))  # Try both field names
        
        if cost_center and margin_percent is not None:
            gp_margin_by_cc[cost_center] = float(margin_percent)
    
    # Get tree bounds for hierarchical matching
    target_ccs_list = [c for c in target_ccs if c]
    if not target_ccs_list:
        return {}
        
    bounds_cache = _fetch_cc_tree_bounds(target_ccs_list + list(gp_margin_by_cc.keys()))
    
    # For each target CC, find matching margins from GP data
    result: Dict[str, Optional[float]] = {}
    for target_cc in target_ccs_list:
        target_bounds = bounds_cache.get(target_cc)
        if not target_bounds:
            result[target_cc] = None
            continue
            
        # Direct match first
        if target_cc in gp_margin_by_cc:
            result[target_cc] = gp_margin_by_cc[target_cc]
            continue
            
        # Hierarchical match - find child CCs
        matching_margins = []
        for gp_cc, margin in gp_margin_by_cc.items():
            if _is_cc_inside(target_bounds, gp_cc, bounds_cache):
                matching_margins.append(margin)
        
        # Average the matching margins
        result[target_cc] = (sum(matching_margins) / len(matching_margins)) if matching_margins else None
    
    return result


# ======================================================
# 3) EXECUTE: ENSAMBLAR TODO Y DEVOLVER
# ======================================================

def _apply_tree_filters(rows: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aplica post-filtros por árbol lft/rgt para Cost Center y Sales Person
    según propuesta ChatGPT
    """
    if not filters:
        return rows

    filters = frappe._dict(filters)
    cost_center_filter = filters.get('cost_center')
    sales_person_filter = filters.get('sales_person')

    # Si no hay filtros de árbol, retornar todas las filas
    if not cost_center_filter and not sales_person_filter:
        return rows

    filtered_rows = rows

    # 1. Filtro por Cost Center (Sucursal)
    if cost_center_filter:
        filtered_rows = _filter_by_cost_center_tree(filtered_rows, cost_center_filter)

    # 2. Filtro por Sales Person (Vendedor)
    if sales_person_filter:
        filtered_rows = _filter_by_sales_person_tree(filtered_rows, sales_person_filter)

    return filtered_rows


def _filter_by_cost_center_tree(rows: List[Dict[str, Any]], cost_center_name: str) -> List[Dict[str, Any]]:
    """
    Filtra filas por Cost Center usando lft/rgt tree (incluye nodos hijos)
    """
    try:
        # Obtener lft/rgt del cost center seleccionado
        cc_data = frappe.db.get_value("Cost Center", cost_center_name, ["lft", "rgt"], as_dict=True)
        if not cc_data:
            return []  # Cost center no existe

        # Obtener todos los cost centers en el árbol (incluye hijos)
        valid_cost_centers = frappe.db.sql("""
            SELECT name
            FROM `tabCost Center`
            WHERE lft >= %s AND rgt <= %s
        """, (cc_data.lft, cc_data.rgt), as_list=True)

        valid_cc_set = {cc[0] for cc in valid_cost_centers}

        # Filtrar filas que tengan cost_center en el árbol
        # Filas SIN sucursal quedan FUERA cuando hay filtro
        filtered = []
        for row in rows:
            row_cc = row.get('cost_center')
            if row_cc and row_cc in valid_cc_set:
                filtered.append(row)

        return filtered

    except Exception as e:
        frappe.log_error(f"Error filtering by cost center tree: {str(e)}")
        return rows  # En caso de error, retornar datos sin filtrar


def _filter_by_sales_person_tree(rows: List[Dict[str, Any]], sales_person_name: str) -> List[Dict[str, Any]]:
    """
    Filtra filas por Sales Person usando lft/rgt tree (incluye vendedores hijos)
    Construye set de facturas con Sales Team.sales_person en el árbol
    """
    try:
        # Obtener lft/rgt del sales person seleccionado
        sp_data = frappe.db.get_value("Sales Person", sales_person_name, ["lft", "rgt"], as_dict=True)
        if not sp_data:
            return []  # Sales person no existe

        # Obtener todos los sales persons en el árbol (incluye hijos)
        valid_sales_persons = frappe.db.sql("""
            SELECT name
            FROM `tabSales Person`
            WHERE lft >= %s AND rgt <= %s
        """, (sp_data.lft, sp_data.rgt), as_list=True)

        valid_sp_set = {sp[0] for sp in valid_sales_persons}

        # Obtener facturas que tienen Sales Team con sales_person en el árbol
        valid_invoices = frappe.db.sql("""
            SELECT DISTINCT st.parent
            FROM `tabSales Team` st
            WHERE st.sales_person IN %(valid_sales_persons)s
        """, {"valid_sales_persons": list(valid_sp_set)}, as_list=True)

        valid_invoice_set = {inv[0] for inv in valid_invoices}

        # Filtrar filas que tengan factura en el set
        # Facturas SIN vendedor quedan FUERA cuando hay filtro
        filtered = []
        for row in rows:
            row_invoice = row.get('name')  # fieldname 'name' contiene el ID de la factura
            if row_invoice and row_invoice in valid_invoice_set:
                filtered.append(row)

        return filtered

    except Exception as e:
        frappe.log_error(f"Error filtering by sales person tree: {str(e)}")
        return rows  # En caso de error, retornar datos sin filtrar


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    1) Trae TODAS las columnas del Backlog (idénticas a reportes viejos) usando la SQL original.
    2) Calcula "Margen Sucursal 6m (GP nativo)" vía reporte estándar Gross Profit (promedio simple).
    3) Añade la(s) columna(s) nueva(s) al final y retorna.
    """
    filters = filters or {}

    # 1) Backlog idéntico (columnas y filas)
    base_columns, base_rows = _get_backlog_rows(filters)

    # 2) Calcular margen sucursal 6m (GP nativo)
    gp_rows = _gp_rows_last_6m(filters)
    target_ccs = [r.get("cost_center") for r in base_rows]
    margin_by_cc = _build_margin_cc_6m_map(gp_rows, target_ccs)


    # Poblar valores
    for d in base_rows:
        cc = d.get("cost_center")
        d["margin_cc_6m_gp"] = margin_by_cc.get(cc)

        # Calcular Comisión Estimada GP nativo
        venta_opc_def = d.get("venta_opc_def")
        margin_cc_6m_gp = d.get("margin_cc_6m_gp")
        rate_comision = d.get("rate_comision")

        if venta_opc_def is not None and margin_cc_6m_gp is not None and rate_comision is not None:
            # Fórmula: venta_opc_def * (margin_cc_6m_gp / 100) * (rate_comision / 100)
            comision_estimada_gp = venta_opc_def * (margin_cc_6m_gp / 100) * (rate_comision / 100)
            d["comision_estimada_gp"] = round(comision_estimada_gp, 2)
        else:
            d["comision_estimada_gp"] = None

    # Aplicar post-filtros por árbol lft/rgt según propuesta ChatGPT
    filtered_rows = _apply_tree_filters(base_rows, filters)

    return base_columns, filtered_rows