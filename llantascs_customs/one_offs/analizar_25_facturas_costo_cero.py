#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis detallado de las 25 facturas con costo cero en OPC-08552
"""

import frappe
import json
from pathlib import Path

def run():
    """
    Analiza en detalle las 25 facturas con costo cero
    """

    opc_name = "COMISIONES-2025-10-07-08552"

    print("\n" + "="*80)
    print(f"ANÁLISIS DETALLADO: 25 FACTURAS CON COSTO CERO EN {opc_name}")
    print("="*80 + "\n")

    # 1. Obtener TODAS las comisiones con costo cero
    comisiones_cero = frappe.db.sql("""
        SELECT
            name,
            sales_invoice_id,
            ingreso,
            costo_de_ventas,
            utilidad_transaccion,
            total_comision,
            persona_de_ventas,
            porcentaje_comision
        FROM `tabComision LLCS`
        WHERE parent = %s
        AND (costo_de_ventas = 0 OR costo_de_ventas IS NULL)
        ORDER BY sales_invoice_id
    """, (opc_name,), as_dict=True)

    print(f"TOTAL COMISIONES CON COSTO CERO: {len(comisiones_cero)}\n")

    # 2. Obtener cuentas COGS
    cogs_accounts = frappe.db.sql("""
        SELECT name
        FROM `tabAccount`
        WHERE account_type = 'Cost of Goods Sold'
        AND disabled = 0
    """, as_dict=True)
    cogs_account_names = [acc.name for acc in cogs_accounts]

    # 3. Analizar cada factura
    resultados = []

    for com in comisiones_cero:
        si_name = com.sales_invoice_id

        # Info básica de la factura
        si_info = frappe.db.sql("""
            SELECT
                name,
                posting_date,
                customer,
                grand_total
            FROM `tabSales Invoice`
            WHERE name = %s
        """, (si_name,), as_dict=True)

        if not si_info:
            resultado = {
                "factura": si_name,
                "existe": False,
                "tiene_dn": False,
                "dn_tiene_cogs": False,
                "cogs_amount": 0,
                "ingreso": com.ingreso,
                "comision_pagada": com.total_comision,
                "vendedor": com.persona_de_ventas
            }
            resultados.append(resultado)
            continue

        si = si_info[0]

        # Obtener items de la factura para verificar si son productos o servicios
        items = frappe.db.sql("""
            SELECT
                item_code,
                qty,
                rate,
                amount,
                (SELECT is_stock_item FROM `tabItem` WHERE name = si_item.item_code) as is_stock_item
            FROM `tabSales Invoice Item` si_item
            WHERE parent = %s
        """, (si_name,), as_dict=True)

        # Clasificar factura
        tiene_productos = any(item.is_stock_item == 1 for item in items if item.is_stock_item is not None)
        es_solo_servicios = all(item.is_stock_item == 0 for item in items if item.is_stock_item is not None)

        # Buscar GL Entries de COGS en la factura
        si_cogs = frappe.db.sql("""
            SELECT COALESCE(SUM(debit), 0) as total_cogs
            FROM `tabGL Entry`
            WHERE voucher_no = %s
            AND is_cancelled = 0
            AND account IN ({})
        """.format(','.join(['%s']*len(cogs_account_names))), tuple([si_name] + cogs_account_names), as_dict=True)

        si_cogs_amount = si_cogs[0].total_cogs if si_cogs else 0

        # Buscar Delivery Note asociado
        dn_links = frappe.db.sql("""
            SELECT
                dni.parent as delivery_note,
                dn.docstatus,
                dn.posting_date
            FROM `tabDelivery Note Item` dni
            JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dni.against_sales_invoice = %s
            ORDER BY dn.posting_date DESC
            LIMIT 1
        """, (si_name,), as_dict=True)

        tiene_dn = len(dn_links) > 0
        dn_name = dn_links[0].delivery_note if tiene_dn else None
        dn_date = dn_links[0].posting_date if tiene_dn else None
        dn_docstatus = dn_links[0].docstatus if tiene_dn else None

        # Buscar GL Entries de COGS en el DN
        dn_cogs_amount = 0
        if tiene_dn:
            dn_cogs = frappe.db.sql("""
                SELECT COALESCE(SUM(debit), 0) as total_cogs
                FROM `tabGL Entry`
                WHERE voucher_no = %s
                AND is_cancelled = 0
                AND account IN ({})
            """.format(','.join(['%s']*len(cogs_account_names))), tuple([dn_name] + cogs_account_names), as_dict=True)

            dn_cogs_amount = dn_cogs[0].total_cogs if dn_cogs else 0

        # Calcular comisión correcta
        costo_real = si_cogs_amount + dn_cogs_amount
        utilidad_real = com.ingreso - costo_real
        comision_correcta = utilidad_real * (com.porcentaje_comision / 100)
        sobrepago = com.total_comision - comision_correcta

        # Determinar si el costo cero es legítimo (servicios) o problema (productos)
        costo_cero_legitimo = es_solo_servicios and not tiene_productos
        es_problema = tiene_productos and costo_real == 0

        resultado = {
            "factura": si_name,
            "existe": True,
            "fecha_factura": str(si.posting_date) if si.posting_date else None,
            "cliente": si.customer,
            "total_factura": float(si.grand_total),
            "tiene_productos": tiene_productos,
            "es_solo_servicios": es_solo_servicios,
            "costo_cero_legitimo": costo_cero_legitimo,
            "es_problema": es_problema,
            "tiene_dn": tiene_dn,
            "dn_name": dn_name,
            "dn_fecha": str(dn_date) if dn_date else None,
            "dn_docstatus": dn_docstatus,
            "si_cogs": float(si_cogs_amount),
            "dn_cogs": float(dn_cogs_amount),
            "costo_real": float(costo_real),
            "ingreso": float(com.ingreso),
            "utilidad_real": float(utilidad_real),
            "comision_pagada": float(com.total_comision),
            "comision_correcta": float(comision_correcta),
            "sobrepago": float(sobrepago),
            "vendedor": com.persona_de_ventas,
            "porcentaje": float(com.porcentaje_comision)
        }

        resultados.append(resultado)

    # 4. Análisis estadístico
    print("ESTADÍSTICAS:")
    print("-" * 80)

    facturas_con_dn = sum(1 for r in resultados if r.get("tiene_dn", False))
    facturas_sin_dn = len(resultados) - facturas_con_dn

    facturas_dn_con_cogs = sum(1 for r in resultados if r.get("dn_cogs", 0) > 0)
    facturas_dn_sin_cogs = facturas_con_dn - facturas_dn_con_cogs

    facturas_solo_servicios = sum(1 for r in resultados if r.get("es_solo_servicios", False))
    facturas_con_productos = sum(1 for r in resultados if r.get("tiene_productos", False))
    facturas_problema = sum(1 for r in resultados if r.get("es_problema", False))

    total_sobrepago = sum(r.get("sobrepago", 0) for r in resultados)
    sobrepago_problematicas = sum(r.get("sobrepago", 0) for r in resultados if r.get("es_problema", False))

    print(f"Total facturas analizadas: {len(resultados)}")
    print(f"\nPOR TIPO:")
    print(f"  Facturas con PRODUCTOS: {facturas_con_productos} ⚠️")
    print(f"  Facturas solo SERVICIOS: {facturas_solo_servicios} (costo cero legítimo)")
    print(f"\nPROBLEMÁTICAS:")
    print(f"  Facturas con productos pero costo cero: {facturas_problema} 🔴")
    print(f"\nPOR DELIVERY NOTE:")
    print(f"  Facturas CON Delivery Note: {facturas_con_dn}")
    print(f"  Facturas SIN Delivery Note: {facturas_sin_dn}")
    print(f"    - DN con COGS: {facturas_dn_con_cogs}")
    print(f"    - DN sin COGS: {facturas_dn_sin_cogs}")
    print(f"\nIMPACTO FINANCIERO:")
    print(f"  Sobrepago total (todas): ${total_sobrepago:,.2f}")
    print(f"  Sobrepago REAL (solo problemáticas): ${sobrepago_problematicas:,.2f} 🔴")
    print()

    # 5. Detalle por factura
    print("DETALLE POR FACTURA:")
    print("-" * 80)
    print()

    for r in resultados:
        # Indicador de problema
        indicador = "🔴 PROBLEMA" if r.get('es_problema', False) else ("✅ OK (servicio)" if r.get('costo_cero_legitimo', False) else "⚠️")

        print(f"Factura: {r['factura']} {indicador}")
        if not r['existe']:
            print("  ❌ No existe en el sistema")
            print()
            continue

        print(f"  Cliente: {r['cliente']}")
        print(f"  Fecha factura: {r['fecha_factura']}")
        print(f"  Total: ${r['total_factura']:,.2f}")
        print(f"  Tipo: {'Solo SERVICIOS' if r['es_solo_servicios'] else 'Contiene PRODUCTOS'}")

        if r['tiene_dn']:
            from datetime import datetime
            fecha_factura = datetime.strptime(r['fecha_factura'], '%Y-%m-%d') if r['fecha_factura'] else None
            fecha_dn = datetime.strptime(r['dn_fecha'], '%Y-%m-%d') if r['dn_fecha'] else None
            dias_diferencia = (fecha_dn - fecha_factura).days if fecha_dn and fecha_factura else 0
            print(f"  ✅ Delivery Note: {r['dn_name']}")
            print(f"     Fecha DN: {r['dn_fecha']} ({dias_diferencia} días después)")
            print(f"     Estado DN: {r['dn_docstatus']}")
            print(f"     COGS en DN: ${r['dn_cogs']:,.2f}")
        else:
            print(f"  ❌ NO tiene Delivery Note")

        print(f"  COGS en SI: ${r.get('si_cogs', 0):,.2f}")
        print(f"  COGS REAL: ${r.get('costo_real', 0):,.2f}")
        print(f"  Ingreso: ${r['ingreso']:,.2f}")
        print(f"  Utilidad REAL: ${r.get('utilidad_real', 0):,.2f}")
        print(f"  Vendedor: {r['vendedor']} ({r.get('porcentaje', 0)}%)")
        print(f"  Comisión pagada: ${r['comision_pagada']:,.2f}")
        print(f"  Comisión correcta: ${r.get('comision_correcta', 0):,.2f}")
        sobrepago = r.get('sobrepago', 0)
        if r.get('es_problema', False):
            print(f"  SOBREPAGO: ${sobrepago:,.2f} 🔴")
        else:
            print(f"  Diferencia: ${sobrepago:,.2f} (OK para servicios)")
        print()

    # 6. Guardar JSON
    output_file = Path("/home/erpnext/frappe-bench/apps/llantascs_customs/llantascs_customs/one_offs/analisis_25_facturas.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "fecha_analisis": str(frappe.utils.now()),
            "opc": opc_name,
            "total_facturas": len(resultados),
            "estadisticas": {
                "con_dn": facturas_con_dn,
                "sin_dn": facturas_sin_dn,
                "dn_con_cogs": facturas_dn_con_cogs,
                "dn_sin_cogs": facturas_dn_sin_cogs,
                "solo_servicios": facturas_solo_servicios,
                "con_productos": facturas_con_productos,
                "problematicas": facturas_problema,
                "sobrepago_total": float(total_sobrepago),
                "sobrepago_real": float(sobrepago_problematicas)
            },
            "facturas": resultados
        }, f, indent=2, ensure_ascii=False)

    print("="*80)
    print(f"Análisis guardado en: {output_file}")
    print("="*80)

if __name__ == "__main__":
    run()
