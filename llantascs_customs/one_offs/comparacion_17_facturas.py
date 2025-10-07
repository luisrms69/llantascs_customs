#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparación detallada de las 17 facturas corregidas
Nuestro cálculo vs ERPNext
"""

import json
from pathlib import Path

def run():
    """
    Lee el JSON y genera comparación de las 17 facturas corregidas
    """

    json_path = Path("/home/erpnext/frappe-bench/apps/llantascs_customs/llantascs_customs/one_offs/verificacion_costos_vs_gl.json")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n" + "="*100)
    print("COMPARACIÓN DETALLADA: 17 FACTURAS CORREGIDAS")
    print("Nuestro Cálculo vs COGS de ERPNext (GL Entries)")
    print("="*100 + "\n")

    # Filtrar solo las facturas corregidas (costo_resolver_nuevo > 0 y costo_comision_actual == 0)
    facturas_corregidas = [
        r for r in data["resultados"]
        if r["costo_resolver_nuevo"] > 0 and r["costo_comision_actual"] == 0
    ]

    print(f"Total facturas corregidas: {len(facturas_corregidas)}\n")
    print("-"*100)
    print(f"{'#':<3} {'Factura':<30} {'Nuestro Cálculo':>20} {'COGS ERPNext':>20} {'Diferencia':>15} {'Match':>8}")
    print("-"*100)

    for idx, factura in enumerate(facturas_corregidas, 1):
        nombre = factura["factura"]
        nuestro = factura["costo_resolver_nuevo"]
        erpnext = factura["costo_gl_total"]
        diferencia = factura["diferencia_resolver_gl"]
        match = "✅" if factura["match_resolver_gl"] else "❌"

        print(f"{idx:<3} {nombre:<30} ${nuestro:>18,.2f} ${erpnext:>18,.2f} ${diferencia:>13,.2f} {match:>8}")

    print("-"*100)

    # Estadísticas
    total_nuestro = sum(f["costo_resolver_nuevo"] for f in facturas_corregidas)
    total_erpnext = sum(f["costo_gl_total"] for f in facturas_corregidas)
    total_diferencia = total_nuestro - total_erpnext

    print(f"\n{'TOTALES:':<34} ${total_nuestro:>18,.2f} ${total_erpnext:>18,.2f} ${total_diferencia:>13,.2f}")

    # Verificar si todas coinciden
    todas_match = all(f["match_resolver_gl"] for f in facturas_corregidas)

    print("\n" + "="*100)
    if todas_match:
        print("✅ RESULTADO: Todas las facturas coinciden EXACTAMENTE con ERPNext")
    else:
        print("⚠️ RESULTADO: Hay diferencias con ERPNext")
    print("="*100 + "\n")

    # Detalle de DN encontrados
    print("\nDETALLE DE DELIVERY NOTES POR FACTURA:")
    print("-"*100)

    for idx, factura in enumerate(facturas_corregidas, 1):
        nombre = factura["factura"]
        dn_list = factura.get("dn_encontrados", [])

        print(f"\n{idx}. {nombre}")
        if dn_list:
            print(f"   Delivery Notes vinculados: {', '.join(dn_list)}")
            print(f"   Total DN: {len(dn_list)}")
        else:
            print("   ⚠️ No tiene DN vinculados (no debería estar en esta lista)")

    print("\n" + "="*100)

if __name__ == "__main__":
    run()
