#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación de costos calculados vs GL Entries de ERPNext
Para las 25 facturas con costo cero en OPC-08552
"""

import frappe
from frappe.utils import flt
import json
from pathlib import Path

def run():
    """
    Compara el costo calculado por nuestro resolver vs los GL Entries de COGS
    """

    opc_name = "COMISIONES-2025-10-07-08552"

    print("\n" + "="*80)
    print(f"VERIFICACIÓN: COSTOS CALCULADOS VS GL ENTRIES")
    print(f"OPC: {opc_name}")
    print("="*80 + "\n")

    # Obtener las 25 comisiones con costo cero
    comisiones_cero = frappe.db.sql("""
        SELECT
            name,
            sales_invoice_id,
            costo_de_ventas as costo_actual
        FROM `tabComision LLCS`
        WHERE parent = %s
        AND (costo_de_ventas = 0 OR costo_de_ventas IS NULL)
        ORDER BY sales_invoice_id
    """, (opc_name,), as_dict=True)

    print(f"Total facturas a verificar: {len(comisiones_cero)}\n")

    # Obtener cuentas COGS
    cogs_accounts = frappe.db.sql("""
        SELECT name
        FROM `tabAccount`
        WHERE account_type = 'Cost of Goods Sold'
        AND disabled = 0
    """, as_dict=True)
    cogs_account_names = [acc.name for acc in cogs_accounts]

    resultados = []

    for com in comisiones_cero:
        si_name = com.sales_invoice_id

        print(f"Factura: {si_name}")
        print("-" * 80)

        # 1. Costo actual en comisión
        costo_comision = flt(com.costo_actual)
        print(f"  Costo en comisión (actual): ${costo_comision:,.2f}")

        # 2. Costo calculado por resolver (NUEVO)
        try:
            from llantascs_customs.llantascs_customs.api import get_costo_ventas_si
            costo_resolver = flt(get_costo_ventas_si(si_name))
            print(f"  Costo por resolver (nuevo): ${costo_resolver:,.2f}")
        except Exception as e:
            print(f"  ❌ Error al calcular costo: {e}")
            import traceback
            traceback.print_exc()
            costo_resolver = 0

        # 3. Costo en GL Entries (SI + DN)
        # GL de la Sales Invoice
        si_gl = frappe.db.sql("""
            SELECT COALESCE(SUM(debit), 0) as cogs
            FROM `tabGL Entry`
            WHERE voucher_no = %s
            AND is_cancelled = 0
            AND account IN ({})
        """.format(','.join(['%s']*len(cogs_account_names))),
        tuple([si_name] + cogs_account_names), as_dict=True)

        costo_si_gl = flt(si_gl[0].cogs) if si_gl else 0

        # GL del Delivery Note
        dn_links = frappe.db.sql("""
            SELECT DISTINCT parent as dn_name
            FROM `tabDelivery Note Item`
            WHERE against_sales_invoice = %s
        """, (si_name,), as_dict=True)

        costo_dn_gl = 0
        dn_names = []
        for dn in dn_links:
            dn_name = dn.dn_name
            dn_names.append(dn_name)
            dn_gl = frappe.db.sql("""
                SELECT COALESCE(SUM(debit), 0) as cogs
                FROM `tabGL Entry`
                WHERE voucher_no = %s
                AND is_cancelled = 0
                AND account IN ({})
            """.format(','.join(['%s']*len(cogs_account_names))),
            tuple([dn_name] + cogs_account_names), as_dict=True)

            if dn_gl:
                costo_dn_gl += flt(dn_gl[0].cogs)

        costo_total_gl = costo_si_gl + costo_dn_gl

        print(f"  Costo en GL (SI): ${costo_si_gl:,.2f}")
        print(f"  Costo en GL (DN): ${costo_dn_gl:,.2f}")
        if dn_names:
            print(f"    DN encontrados: {', '.join(dn_names)}")
        print(f"  Costo TOTAL GL: ${costo_total_gl:,.2f}")

        # 4. Comparación
        diferencia_resolver_gl = costo_resolver - costo_total_gl
        match_resolver_gl = abs(diferencia_resolver_gl) < 0.01

        if match_resolver_gl:
            print(f"  ✅ MATCH: Resolver coincide con GL")
        else:
            print(f"  ⚠️ DIFERENCIA: ${diferencia_resolver_gl:,.2f}")

        resultado = {
            "factura": si_name,
            "costo_comision_actual": float(costo_comision),
            "costo_resolver_nuevo": float(costo_resolver),
            "costo_gl_si": float(costo_si_gl),
            "costo_gl_dn": float(costo_dn_gl),
            "costo_gl_total": float(costo_total_gl),
            "diferencia_resolver_gl": float(diferencia_resolver_gl),
            "match_resolver_gl": match_resolver_gl,
            "dn_encontrados": dn_names
        }

        resultados.append(resultado)
        print()

    # Resumen
    print("="*80)
    print("RESUMEN")
    print("="*80)

    total_facturas = len(resultados)
    facturas_match = sum(1 for r in resultados if r["match_resolver_gl"])
    facturas_no_match = total_facturas - facturas_match

    facturas_corregidas = sum(1 for r in resultados if r["costo_resolver_nuevo"] > 0 and r["costo_comision_actual"] == 0)

    print(f"\nTotal facturas verificadas: {total_facturas}")
    print(f"Resolver coincide con GL: {facturas_match} ✅")
    print(f"Resolver NO coincide con GL: {facturas_no_match} ⚠️")
    print(f"\nFacturas CORREGIDAS (costo 0 → costo > 0): {facturas_corregidas}")

    # Guardar resultados
    output_file = Path("/home/erpnext/frappe-bench/apps/llantascs_customs/llantascs_customs/one_offs/verificacion_costos_vs_gl.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "fecha_verificacion": str(frappe.utils.now()),
            "opc": opc_name,
            "total_facturas": total_facturas,
            "facturas_match": facturas_match,
            "facturas_no_match": facturas_no_match,
            "facturas_corregidas": facturas_corregidas,
            "resultados": resultados
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultados guardados en: {output_file}")
    print("="*80 + "\n")

if __name__ == "__main__":
    run()
