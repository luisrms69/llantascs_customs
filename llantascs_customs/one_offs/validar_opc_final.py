import frappe
import json
from pathlib import Path
from datetime import datetime

def run():
    """
    ETAPA 5: Valida las OPC por SQL (bypass hooks).

    Cambia docstatus de 0 a 1 directamente en BD, SIN ejecutar hooks.

    Implementa Condición 6:
    - Verifica antes de validar:
      - docstatus = 0
      - Comisiones coinciden con backup
      - Monto coincide con backup
      - Sales Invoices originales marcadas correctamente
    - Si no empata: NO valida esa OPC
    """

    print("\n" + "="*80)
    print("ETAPA 5: VALIDACIÓN DE OPC POR SQL (BYPASS HOOKS)")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Cargar backup
    backup_path = Path(__file__).parent / "opc_backup.json"
    with open(backup_path, 'r', encoding='utf-8') as f:
        backup = json.load(f)

    print(f"📦 Backup cargado: {len(backup)} OPC\n")

    resultados = {
        "fecha_ejecucion": datetime.now().isoformat(),
        "total_opc": len(backup),
        "opc_validadas": 0,
        "opc_no_validadas": 0,
        "detalle_por_opc": {}
    }

    opc_a_validar = []

    # Fase 1: VERIFICACIÓN PREVIA (Condición 6)
    print("="*80)
    print("FASE 1: VERIFICACIÓN PREVIA")
    print("="*80 + "\n")

    for opc_name, opc_backup in backup.items():
        print(f"📋 Verificando: {opc_name}\n")

        resultado_opc = {
            "opc": opc_name,
            "validada": False,
            "errores": []
        }

        try:
            # 1. Verificar docstatus = 0
            docstatus = frappe.db.get_value("Orden de Pago Comisiones", opc_name, "docstatus")
            if docstatus is None:
                error = "OPC no existe"
                print(f"   ❌ {error}\n")
                resultado_opc["errores"].append(error)
                resultados["opc_no_validadas"] += 1
                resultados["detalle_por_opc"][opc_name] = resultado_opc
                continue

            if docstatus != 0:
                error = f"OPC no está en borrador (docstatus={docstatus})"
                print(f"   ❌ {error}\n")
                resultado_opc["errores"].append(error)
                resultados["opc_no_validadas"] += 1
                resultados["detalle_por_opc"][opc_name] = resultado_opc
                continue

            print(f"   ✅ docstatus = 0 (borrador)")

            # 2. Verificar comisiones
            comisiones_actual = frappe.db.sql("""
                SELECT COUNT(*) as count, COALESCE(SUM(total_comision), 0) as suma
                FROM `tabComision LLCS`
                WHERE parent = %s
            """, (opc_name,), as_dict=True)[0]

            comisiones_backup = len(opc_backup['comisiones'])
            monto_backup = sum(c['total_comision'] for c in opc_backup['comisiones'])

            match_comisiones = comisiones_actual.count == comisiones_backup
            match_suma = abs(float(comisiones_actual.suma) - monto_backup) <= 0.01

            print(f"   {'✅' if match_comisiones else '❌'} Comisiones: {comisiones_actual.count}/{comisiones_backup}")
            print(f"   {'✅' if match_suma else '❌'} Suma comisiones: ${comisiones_actual.suma:,.2f}/${monto_backup:,.2f}")

            if not match_comisiones:
                error = f"Número de comisiones no coincide: {comisiones_actual.count} != {comisiones_backup}"
                resultado_opc["errores"].append(error)

            if not match_suma:
                error = f"Suma de comisiones no coincide: ${comisiones_actual.suma:,.2f} != ${monto_backup:,.2f}"
                resultado_opc["errores"].append(error)

            # 3. Verificar monto_total
            monto_total = frappe.db.get_value("Orden de Pago Comisiones", opc_name, "monto_total")
            match_monto = abs(float(monto_total) - monto_backup) <= 0.01

            print(f"   {'✅' if match_monto else '❌'} Monto total: ${monto_total:,.2f}/${monto_backup:,.2f}")

            if not match_monto:
                error = f"Monto total no coincide: ${monto_total:,.2f} != ${monto_backup:,.2f}"
                resultado_opc["errores"].append(error)

            # 4. Verificar Sales Invoices originales
            si_originales = set(opc_backup['sales_invoices'])

            if len(si_originales) > 0:
                si_originales_estado = frappe.db.sql("""
                    SELECT name, custom_status_comisiones, custom_orden_de_pago_comision
                    FROM `tabSales Invoice`
                    WHERE name IN ({})
                """.format(','.join(['%s']*len(si_originales))), tuple(si_originales), as_dict=True)

                si_originales_correctas = sum(1 for s in si_originales_estado
                                               if s.custom_status_comisiones == "Enviado"
                                               and s.custom_orden_de_pago_comision == opc_name)

                match_si = si_originales_correctas == len(si_originales)

                print(f"   {'✅' if match_si else '❌'} SI originales: {si_originales_correctas}/{len(si_originales)} con estado 'Enviado'")

                if not match_si:
                    error = f"Sales Invoices originales incorrectas: {si_originales_correctas}/{len(si_originales)}"
                    resultado_opc["errores"].append(error)
            else:
                match_si = True
                print(f"   ✅ SI originales: 0 (ninguna)")

            # Decisión: ¿validar o no?
            if len(resultado_opc["errores"]) == 0:
                print(f"\n   ✅ LISTA PARA VALIDAR\n")
                opc_a_validar.append(opc_name)
                resultado_opc["lista_para_validar"] = True
            else:
                print(f"\n   ❌ NO SE VALIDARÁ (errores encontrados)\n")
                resultado_opc["lista_para_validar"] = False
                resultados["opc_no_validadas"] += 1

        except Exception as e:
            error = f"Excepción durante verificación: {str(e)}"
            print(f"   ❌ {error}\n")
            resultado_opc["errores"].append(error)
            resultado_opc["lista_para_validar"] = False
            resultados["opc_no_validadas"] += 1

        resultados["detalle_por_opc"][opc_name] = resultado_opc

    # Fase 2: VALIDACIÓN POR SQL
    if len(opc_a_validar) > 0:
        print("="*80)
        print("FASE 2: VALIDACIÓN POR SQL")
        print("="*80 + "\n")

        print(f"Validando {len(opc_a_validar)} OPC por SQL (bypass hooks)...\n")

        try:
            # Validar todas las OPC aprobadas en una sola operación
            frappe.db.sql("""
                UPDATE `tabOrden de Pago Comisiones`
                SET docstatus = 1, modified = NOW()
                WHERE name IN ({})
            """.format(','.join(['%s']*len(opc_a_validar))), tuple(opc_a_validar))

            frappe.db.commit()

            print(f"✅ {len(opc_a_validar)} OPC validadas exitosamente\n")

            # Verificar estado final
            print("Verificando estado final...\n")

            for opc_name in opc_a_validar:
                docstatus_final = frappe.db.get_value("Orden de Pago Comisiones", opc_name, "docstatus")
                if docstatus_final == 1:
                    print(f"   ✅ {opc_name}: docstatus = 1")
                    resultados["detalle_por_opc"][opc_name]["validada"] = True
                    resultados["opc_validadas"] += 1
                else:
                    print(f"   ❌ {opc_name}: docstatus = {docstatus_final} (esperado: 1)")
                    resultados["detalle_por_opc"][opc_name]["errores"].append(f"docstatus final = {docstatus_final}")
                    resultados["opc_no_validadas"] += 1

            print()

        except Exception as e:
            error = f"Error al validar OPC: {str(e)}"
            print(f"❌ ERROR: {error}\n")
            frappe.db.rollback()
            print(f"🔄 Rollback ejecutado\n")

            for opc_name in opc_a_validar:
                resultados["detalle_por_opc"][opc_name]["errores"].append(error)
                resultados["opc_no_validadas"] += 1

    else:
        print("="*80)
        print("⚠️ NINGUNA OPC LISTA PARA VALIDAR")
        print("="*80 + "\n")
        print("Todas las OPC tienen errores. Revisa los reportes anteriores.\n")

    # Resumen final
    print("="*80)
    print("📊 RESUMEN FINAL")
    print("="*80 + "\n")

    print(f"Total OPC: {resultados['total_opc']}")
    print(f"OPC validadas: {resultados['opc_validadas']} ✅")
    print(f"OPC no validadas: {resultados['opc_no_validadas']}" + (" ❌" if resultados['opc_no_validadas'] > 0 else ""))
    print()

    # Guardar reporte
    output_path = Path(__file__).parent / "reporte_validacion_final.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"✅ Reporte guardado en: {output_path}")
    print("="*80 + "\n")

    return resultados
