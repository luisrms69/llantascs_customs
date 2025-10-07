import frappe
import json
from pathlib import Path
from datetime import datetime

def run():
    """
    ETAPA 6: Verificación final completa.

    Genera reporte detallado del estado final de las 9 OPC:
    - Estado de la OPC (docstatus, comisiones, monto)
    - Estado de Sales Invoices (originales y adicionales)
    - Comparación con backup
    - Resultado general por OPC

    Implementa sugerencia C:
    - Clear cache al final
    """

    print("\n" + "="*80)
    print("ETAPA 6: VERIFICACIÓN FINAL COMPLETA")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Cargar backup
    backup_path = Path(__file__).parent / "opc_backup.json"
    with open(backup_path, 'r', encoding='utf-8') as f:
        backup = json.load(f)

    print(f"📦 Backup cargado: {len(backup)} OPC\n")

    resultados = {
        "fecha_verificacion": datetime.now().isoformat(),
        "modo": "VERIFICACIÓN FINAL COMPLETA",
        "resumen_general": {
            "total_opc_procesadas": len(backup),
            "opc_exitosas": 0,
            "opc_con_errores": 0,
            "total_comisiones_backup": 0,
            "total_comisiones_actual": 0,
            "match_comisiones_global": True,
            "total_monto_backup": 0.0,
            "total_monto_actual": 0.0,
            "match_monto_global": True,
            "diferencia_total": 0.0,
            "total_si_originales": 0,
            "si_originales_correctas": 0,
            "total_si_adicionales": 0,
            "si_adicionales_correctas": 0,
            "exito_total": True
        },
        "detalle_por_opc": {}
    }

    reporte_txt = []
    reporte_txt.append("="*80)
    reporte_txt.append("REPORTE FINAL - MIGRACIÓN DE 9 OPC HISTÓRICAS")
    reporte_txt.append("="*80)
    reporte_txt.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte_txt.append(f"Modo: VERIFICACIÓN FINAL COMPLETA")
    reporte_txt.append("")

    for opc_name, opc_backup in backup.items():
        print("="*80)
        print(f"📋 {opc_name}")
        print("="*80 + "\n")

        reporte_txt.append("-"*80)
        reporte_txt.append(f"OPC: {opc_name}")
        reporte_txt.append("-"*80)

        resultado_opc = {
            "opc": {
                "name": opc_name,
                "docstatus": None,
                "comisiones_backup": len(opc_backup['comisiones']),
                "comisiones_actual": 0,
                "match_comisiones": False,
                "monto_backup": sum(c['total_comision'] for c in opc_backup['comisiones']),
                "monto_actual": 0.0,
                "match_monto": False,
                "diferencia": 0.0,
                "sucursales_actuales": 0
            },
            "sales_invoices": {
                "originales": {
                    "total": len(opc_backup['sales_invoices']),
                    "correctas": 0,
                    "incorrectas": 0
                },
                "adicionales": {
                    "total": 0,
                    "correctas": 0,
                    "incorrectas": 0
                }
            },
            "validacion": {
                "match_comisiones": False,
                "match_monto": False,
                "match_si_originales": False,
                "match_si_adicionales": False,
                "exito_total": False
            },
            "errores": []
        }

        try:
            # 1. Estado de la OPC
            opc_data = frappe.db.sql("""
                SELECT docstatus, monto_total,
                       (SELECT COUNT(*) FROM `tabComision LLCS` WHERE parent = %s) as comisiones,
                       (SELECT COALESCE(SUM(total_comision), 0) FROM `tabComision LLCS` WHERE parent = %s) as suma_comisiones,
                       (SELECT COUNT(*) FROM `tabSucursales Multi` WHERE parent = %s) as sucursales
                FROM `tabOrden de Pago Comisiones`
                WHERE name = %s
            """, (opc_name, opc_name, opc_name, opc_name), as_dict=True)

            if not opc_data:
                error = "OPC no existe"
                print(f"❌ ERROR: {error}\n")
                resultado_opc["errores"].append(error)
                resultados["resumen_general"]["opc_con_errores"] += 1
                resultados["resumen_general"]["exito_total"] = False
                resultados["detalle_por_opc"][opc_name] = resultado_opc
                reporte_txt.append(f"❌ ERROR: {error}")
                reporte_txt.append("")
                continue

            opc = opc_data[0]

            resultado_opc["opc"]["docstatus"] = opc.docstatus
            resultado_opc["opc"]["comisiones_actual"] = opc.comisiones
            resultado_opc["opc"]["monto_actual"] = float(opc.monto_total)
            resultado_opc["opc"]["sucursales_actuales"] = opc.sucursales
            resultado_opc["opc"]["diferencia"] = float(opc.monto_total) - resultado_opc["opc"]["monto_backup"]

            match_comisiones = opc.comisiones == resultado_opc["opc"]["comisiones_backup"]
            match_monto = abs(float(opc.monto_total) - resultado_opc["opc"]["monto_backup"]) <= 0.01

            resultado_opc["opc"]["match_comisiones"] = match_comisiones
            resultado_opc["opc"]["match_monto"] = match_monto
            resultado_opc["validacion"]["match_comisiones"] = match_comisiones
            resultado_opc["validacion"]["match_monto"] = match_monto

            print(f"📊 ESTADO DE LA OPC:")
            print(f"   Estado: {'Validada' if opc.docstatus == 1 else 'Borrador'} (docstatus={opc.docstatus}) {'✅' if opc.docstatus == 1 else '❌'}")
            print(f"   Sucursales: {opc.sucursales}")
            print(f"   Comisiones: {opc.comisiones} (backup: {resultado_opc['opc']['comisiones_backup']}) {'✅' if match_comisiones else '❌'}")
            print(f"   Monto: ${opc.monto_total:,.2f} (backup: ${resultado_opc['opc']['monto_backup']:,.2f}) {'✅' if match_monto else '❌'}")
            print(f"   Diferencia: ${resultado_opc['opc']['diferencia']:,.2f}")
            print()

            reporte_txt.append(f"Estado: {'Validada' if opc.docstatus == 1 else 'Borrador'} (docstatus={opc.docstatus}) {'✅' if opc.docstatus == 1 else '❌'}")
            reporte_txt.append("")
            reporte_txt.append("OPC:")
            reporte_txt.append(f"  Sucursales: {opc.sucursales}")
            reporte_txt.append(f"  Comisiones: {opc.comisiones} (backup) → {opc.comisiones} (actual) {'✅' if match_comisiones else '❌'}")
            reporte_txt.append(f"  Monto: ${resultado_opc['opc']['monto_backup']:,.2f} (backup) → ${opc.monto_total:,.2f} (actual) {'✅' if match_monto else '❌'}")
            reporte_txt.append(f"  Diferencia: ${resultado_opc['opc']['diferencia']:,.2f}")
            reporte_txt.append("")

            # 2. Sales Invoices originales
            si_originales = set(opc_backup['sales_invoices'])

            if len(si_originales) > 0:
                si_originales_estado = frappe.db.sql("""
                    SELECT name, custom_status_comisiones, custom_orden_de_pago_comision
                    FROM `tabSales Invoice`
                    WHERE name IN ({})
                """.format(','.join(['%s']*len(si_originales))), tuple(si_originales), as_dict=True)

                originales_correctas = sum(1 for s in si_originales_estado
                                           if s.custom_status_comisiones == "Enviado"
                                           and s.custom_orden_de_pago_comision == opc_name)

                resultado_opc["sales_invoices"]["originales"]["correctas"] = originales_correctas
                resultado_opc["sales_invoices"]["originales"]["incorrectas"] = len(si_originales) - originales_correctas

                match_si_originales = originales_correctas == len(si_originales)
                resultado_opc["validacion"]["match_si_originales"] = match_si_originales

                print(f"📊 SALES INVOICES ORIGINALES:")
                print(f"   Total: {len(si_originales)}")
                print(f"   Correctas: {originales_correctas}/{len(si_originales)} {'✅' if match_si_originales else '❌'}")
                print(f"   Incorrectas: {resultado_opc['sales_invoices']['originales']['incorrectas']}")
                print()

                reporte_txt.append("Sales Invoices:")
                reporte_txt.append(f"  Originales: {originales_correctas}/{len(si_originales)} con estado 'Enviado' {'✅' if match_si_originales else '❌'}")

                resultados["resumen_general"]["total_si_originales"] += len(si_originales)
                resultados["resumen_general"]["si_originales_correctas"] += originales_correctas
            else:
                resultado_opc["validacion"]["match_si_originales"] = True
                match_si_originales = True
                reporte_txt.append("Sales Invoices:")
                reporte_txt.append(f"  Originales: 0 (ninguna)")

            # 3. Sales Invoices adicionales
            si_vinculadas = frappe.db.sql("""
                SELECT name
                FROM `tabSales Invoice`
                WHERE custom_orden_de_pago_comision = %s
            """, (opc_name,), as_dict=True)

            si_vinculadas_set = set(s.name for s in si_vinculadas)
            si_adicionales = si_vinculadas_set - si_originales

            resultado_opc["sales_invoices"]["adicionales"]["total"] = len(si_adicionales)

            if len(si_adicionales) > 0:
                si_adicionales_estado = frappe.db.sql("""
                    SELECT name, custom_status_comisiones, custom_orden_de_pago_comision
                    FROM `tabSales Invoice`
                    WHERE name IN ({})
                """.format(','.join(['%s']*len(si_adicionales))), tuple(si_adicionales), as_dict=True)

                adicionales_correctas = sum(1 for s in si_adicionales_estado
                                             if (s.custom_status_comisiones == "Sin Enviar" or s.custom_status_comisiones is None)
                                             and s.custom_orden_de_pago_comision is None)

                resultado_opc["sales_invoices"]["adicionales"]["correctas"] = adicionales_correctas
                resultado_opc["sales_invoices"]["adicionales"]["incorrectas"] = len(si_adicionales) - adicionales_correctas

                match_si_adicionales = adicionales_correctas == len(si_adicionales)
                resultado_opc["validacion"]["match_si_adicionales"] = match_si_adicionales

                print(f"📊 SALES INVOICES ADICIONALES:")
                print(f"   Total: {len(si_adicionales)}")
                print(f"   Correctas: {adicionales_correctas}/{len(si_adicionales)} {'✅' if match_si_adicionales else '❌'}")
                print(f"   Incorrectas: {resultado_opc['sales_invoices']['adicionales']['incorrectas']}")
                print()

                reporte_txt.append(f"  Adicionales: {adicionales_correctas}/{len(si_adicionales)} con estado 'Sin Enviar' {'✅' if match_si_adicionales else '❌'}")

                resultados["resumen_general"]["total_si_adicionales"] += len(si_adicionales)
                resultados["resumen_general"]["si_adicionales_correctas"] += adicionales_correctas
            else:
                resultado_opc["validacion"]["match_si_adicionales"] = True
                match_si_adicionales = True
                reporte_txt.append(f"  Adicionales: 0 (ninguna identificada)")

            reporte_txt.append("")

            # 4. Resultado general
            exito_total = (opc.docstatus == 1 and match_comisiones and match_monto and
                          match_si_originales and match_si_adicionales)

            resultado_opc["validacion"]["exito_total"] = exito_total

            if exito_total:
                print(f"✅ RESULTADO: ÉXITO TOTAL\n")
                reporte_txt.append("Resultado: ✅ ÉXITO TOTAL")
                resultados["resumen_general"]["opc_exitosas"] += 1
            else:
                print(f"❌ RESULTADO: HAY ERRORES\n")
                reporte_txt.append("Resultado: ❌ HAY ERRORES")
                resultados["resumen_general"]["opc_con_errores"] += 1
                resultados["resumen_general"]["exito_total"] = False

            reporte_txt.append("")

            # Actualizar totales
            resultados["resumen_general"]["total_comisiones_backup"] += resultado_opc["opc"]["comisiones_backup"]
            resultados["resumen_general"]["total_comisiones_actual"] += opc.comisiones
            resultados["resumen_general"]["total_monto_backup"] += resultado_opc["opc"]["monto_backup"]
            resultados["resumen_general"]["total_monto_actual"] += float(opc.monto_total)

        except Exception as e:
            error = f"Excepción durante verificación: {str(e)}"
            print(f"❌ ERROR: {error}\n")
            resultado_opc["errores"].append(error)
            reporte_txt.append(f"❌ ERROR: {error}")
            reporte_txt.append("")
            resultados["resumen_general"]["opc_con_errores"] += 1
            resultados["resumen_general"]["exito_total"] = False

        resultados["detalle_por_opc"][opc_name] = resultado_opc

    # Resumen general
    resultados["resumen_general"]["match_comisiones_global"] = (
        resultados["resumen_general"]["total_comisiones_backup"] ==
        resultados["resumen_general"]["total_comisiones_actual"]
    )

    resultados["resumen_general"]["diferencia_total"] = (
        resultados["resumen_general"]["total_monto_actual"] -
        resultados["resumen_general"]["total_monto_backup"]
    )

    resultados["resumen_general"]["match_monto_global"] = (
        abs(resultados["resumen_general"]["diferencia_total"]) <= 0.01
    )

    print("="*80)
    print("📊 RESUMEN GENERAL")
    print("="*80 + "\n")

    print(f"Total OPC procesadas: {resultados['resumen_general']['total_opc_procesadas']}")
    print(f"OPC exitosas: {resultados['resumen_general']['opc_exitosas']} ✅")
    print(f"OPC con errores: {resultados['resumen_general']['opc_con_errores']}" + (" ❌" if resultados['resumen_general']['opc_con_errores'] > 0 else ""))
    print()
    print(f"TOTALES:")
    print(f"  Comisiones (backup): {resultados['resumen_general']['total_comisiones_backup']}")
    print(f"  Comisiones (actual): {resultados['resumen_general']['total_comisiones_actual']} {'✅' if resultados['resumen_general']['match_comisiones_global'] else '❌'}")
    print()
    print(f"  Monto total (backup): ${resultados['resumen_general']['total_monto_backup']:,.2f}")
    print(f"  Monto total (actual): ${resultados['resumen_general']['total_monto_actual']:,.2f} {'✅' if resultados['resumen_general']['match_monto_global'] else '❌'}")
    print(f"  Diferencia: ${resultados['resumen_general']['diferencia_total']:,.2f}")
    print()
    print(f"SALES INVOICES:")
    print(f"  Originales totales: {resultados['resumen_general']['total_si_originales']}")
    print(f"  Originales correctas: {resultados['resumen_general']['si_originales_correctas']}/{resultados['resumen_general']['total_si_originales']} ✅")
    print()
    print(f"  Adicionales totales: {resultados['resumen_general']['total_si_adicionales']}")
    print(f"  Adicionales correctas: {resultados['resumen_general']['si_adicionales_correctas']}/{resultados['resumen_general']['total_si_adicionales']} ✅")
    print()

    if resultados['resumen_general']['exito_total']:
        print("✅ RESULTADO GENERAL: ÉXITO TOTAL")
    else:
        print("⚠️ RESULTADO GENERAL: HAY ERRORES EN ALGUNAS OPC")

    print()

    # Reporte TXT
    reporte_txt.insert(1, "")
    reporte_txt.insert(2, "RESUMEN GENERAL:")
    reporte_txt.insert(3, "="*80)
    reporte_txt.insert(4, f"Total OPC procesadas: {resultados['resumen_general']['total_opc_procesadas']}")
    reporte_txt.insert(5, f"OPC exitosas: {resultados['resumen_general']['opc_exitosas']} ✅")
    reporte_txt.insert(6, f"OPC con errores: {resultados['resumen_general']['opc_con_errores']}" + (" ❌" if resultados['resumen_general']['opc_con_errores'] > 0 else ""))
    reporte_txt.insert(7, "")
    reporte_txt.insert(8, "TOTALES:")
    reporte_txt.insert(9, f"  Comisiones (backup): {resultados['resumen_general']['total_comisiones_backup']}")
    reporte_txt.insert(10, f"  Comisiones (actual): {resultados['resumen_general']['total_comisiones_actual']} {'✅' if resultados['resumen_general']['match_comisiones_global'] else '❌'}")
    reporte_txt.insert(11, "")
    reporte_txt.insert(12, f"  Monto total (backup): ${resultados['resumen_general']['total_monto_backup']:,.2f}")
    reporte_txt.insert(13, f"  Monto total (actual): ${resultados['resumen_general']['total_monto_actual']:,.2f} {'✅' if resultados['resumen_general']['match_monto_global'] else '❌'}")
    reporte_txt.insert(14, f"  Diferencia: ${resultados['resumen_general']['diferencia_total']:,.2f}")
    reporte_txt.insert(15, "")
    reporte_txt.insert(16, "SALES INVOICES:")
    reporte_txt.insert(17, f"  Originales totales: {resultados['resumen_general']['total_si_originales']}")
    reporte_txt.insert(18, f"  Originales correctas: {resultados['resumen_general']['si_originales_correctas']}/{resultados['resumen_general']['total_si_originales']} ✅")
    reporte_txt.insert(19, "")
    reporte_txt.insert(20, f"  Adicionales totales: {resultados['resumen_general']['total_si_adicionales']}")
    reporte_txt.insert(21, f"  Adicionales correctas: {resultados['resumen_general']['si_adicionales_correctas']}/{resultados['resumen_general']['total_si_adicionales']} ✅")
    reporte_txt.insert(22, "")
    reporte_txt.insert(23, "RESULTADO GENERAL: " + ("✅ ÉXITO TOTAL" if resultados['resumen_general']['exito_total'] else "⚠️ HAY ERRORES EN ALGUNAS OPC"))
    reporte_txt.insert(24, "")
    reporte_txt.insert(25, "="*80)
    reporte_txt.insert(26, "DETALLE POR OPC")
    reporte_txt.insert(27, "="*80)
    reporte_txt.insert(28, "")

    reporte_txt.append("="*80)
    reporte_txt.append("FIN DEL REPORTE")
    reporte_txt.append("="*80)

    # Guardar reportes
    output_json = Path(__file__).parent / "reporte_final_9opc.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    output_txt = Path(__file__).parent / "reporte_final_9opc.txt"
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(reporte_txt))

    print(f"✅ Reporte JSON guardado en: {output_json}")
    print(f"✅ Reporte TXT guardado en: {output_txt}")
    print("="*80 + "\n")

    # Sugerencia C: Clear cache
    print("🔄 Limpiando cache de Frappe...")
    frappe.clear_cache(doctype="Orden de Pago Comisiones")
    print("   ✅ Cache limpiado\n")

    return resultados
