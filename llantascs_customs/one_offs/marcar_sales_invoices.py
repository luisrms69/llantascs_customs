import frappe
import json
from pathlib import Path
from datetime import datetime

def run(dry_run=1):
    """
    ETAPA 3-4: Marca las Sales Invoices correctas desde el backup.

    Por SQL (bypass hooks):
    - Marca SI originales (del backup) como "Enviado" + vincula a OPC
    - Limpia SI adicionales (NO en backup) como "Sin Enviar" + desvincula

    Implementa Condición 4:
    - Solo limpia SI donde custom_orden_de_pago_comision = <OPC>
      Y NO están en el backup de esa OPC
    - Así no toca SIs de otras OPC
    """

    mode = "🔍 DRY-RUN (simulación)" if dry_run else "⚡ EJECUCIÓN REAL"
    print("\n" + "="*80)
    print(f"ETAPA 3-4: MARCADO DE SALES INVOICES - {mode}")
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
        "modo": mode,
        "total_opc": len(backup),
        "opc_exitosas": 0,
        "opc_con_errores": 0,
        "total_si_originales": 0,
        "total_si_adicionales": 0,
        "detalle_por_opc": {}
    }

    for opc_name, opc_backup in backup.items():
        print("="*80)
        print(f"📋 PROCESANDO: {opc_name}")
        print("="*80 + "\n")

        resultado_opc = {
            "opc": opc_name,
            "exito": False,
            "errores": []
        }

        try:
            # 1. Obtener Sales Invoices originales del backup
            si_originales = set(opc_backup['sales_invoices'])
            print(f"📌 SALES INVOICES ORIGINALES (del backup):")
            print(f"   Total: {len(si_originales)}\n")

            # 2. Identificar Sales Invoices adicionales
            # Condición 4: Solo SI que están vinculadas a ESTA OPC específica
            si_vinculadas = frappe.db.sql("""
                SELECT name
                FROM `tabSales Invoice`
                WHERE custom_orden_de_pago_comision = %s
            """, (opc_name,), as_dict=True)

            si_vinculadas_set = set(s.name for s in si_vinculadas)
            si_adicionales = si_vinculadas_set - si_originales

            print(f"📌 SALES INVOICES ADICIONALES (vinculadas pero NO en backup):")
            print(f"   Total: {len(si_adicionales)}")
            if len(si_adicionales) > 0:
                print(f"   Lista:")
                for si in sorted(si_adicionales):
                    print(f"      • {si}")
            print()

            # 3. Verificar estado ANTES
            print(f"🔍 ESTADO ANTES DE MARCAR:\n")

            if len(si_originales) > 0:
                si_originales_antes = frappe.db.sql("""
                    SELECT name, custom_status_comisiones, custom_orden_de_pago_comision
                    FROM `tabSales Invoice`
                    WHERE name IN ({})
                """.format(','.join(['%s']*len(si_originales))), tuple(si_originales), as_dict=True)

                originales_correctas_antes = sum(1 for s in si_originales_antes
                                                  if s.custom_status_comisiones == "Enviado"
                                                  and s.custom_orden_de_pago_comision == opc_name)
                originales_incorrectas_antes = len(si_originales_antes) - originales_correctas_antes

                print(f"   Originales correctas: {originales_correctas_antes}/{len(si_originales)}")
                print(f"   Originales incorrectas: {originales_incorrectas_antes}/{len(si_originales)}")
            else:
                originales_correctas_antes = 0
                originales_incorrectas_antes = 0

            if len(si_adicionales) > 0:
                si_adicionales_antes = frappe.db.sql("""
                    SELECT name, custom_status_comisiones, custom_orden_de_pago_comision
                    FROM `tabSales Invoice`
                    WHERE name IN ({})
                """.format(','.join(['%s']*len(si_adicionales))), tuple(si_adicionales), as_dict=True)

                adicionales_correctas_antes = sum(1 for s in si_adicionales_antes
                                                   if (s.custom_status_comisiones == "Sin Enviar" or s.custom_status_comisiones is None)
                                                   and s.custom_orden_de_pago_comision is None)
                adicionales_incorrectas_antes = len(si_adicionales_antes) - adicionales_correctas_antes

                print(f"   Adicionales correctas: {adicionales_correctas_antes}/{len(si_adicionales)}")
                print(f"   Adicionales incorrectas: {adicionales_incorrectas_antes}/{len(si_adicionales)}")
            else:
                adicionales_correctas_antes = 0
                adicionales_incorrectas_antes = 0

            print()

            if dry_run:
                print(f"🔍 DRY-RUN: Se ejecutarían las siguientes operaciones:\n")
                if len(si_originales) > 0:
                    print(f"   1. UPDATE {len(si_originales)} SI originales:")
                    print(f"      • custom_status_comisiones = 'Enviado'")
                    print(f"      • custom_orden_de_pago_comision = '{opc_name}'")
                if len(si_adicionales) > 0:
                    print(f"   2. UPDATE {len(si_adicionales)} SI adicionales:")
                    print(f"      • custom_status_comisiones = 'Sin Enviar'")
                    print(f"      • custom_orden_de_pago_comision = NULL")
                print(f"   3. COMMIT\n")

                resultado_opc["exito"] = True
                resultado_opc["simulacion"] = {
                    "si_originales_a_marcar": len(si_originales),
                    "si_adicionales_a_limpiar": len(si_adicionales)
                }
                resultados["opc_exitosas"] += 1
                resultados["total_si_originales"] += len(si_originales)
                resultados["total_si_adicionales"] += len(si_adicionales)

            else:
                print(f"⚡ EJECUTANDO MARCADO:\n")

                # 4. Marcar originales como "Enviado" + vincular
                if len(si_originales) > 0:
                    print(f"   1. Marcando {len(si_originales)} SI originales como 'Enviado'...")
                    frappe.db.sql("""
                        UPDATE `tabSales Invoice`
                        SET custom_status_comisiones = 'Enviado',
                            custom_orden_de_pago_comision = %s,
                            modified = NOW()
                        WHERE name IN ({})
                    """.format(','.join(['%s']*len(si_originales))), (opc_name,) + tuple(si_originales))
                    print(f"      ✅ Marcadas\n")

                # 5. Limpiar adicionales como "Sin Enviar" + desvincular
                if len(si_adicionales) > 0:
                    print(f"   2. Limpiando {len(si_adicionales)} SI adicionales...")
                    frappe.db.sql("""
                        UPDATE `tabSales Invoice`
                        SET custom_status_comisiones = 'Sin Enviar',
                            custom_orden_de_pago_comision = NULL,
                            modified = NOW()
                        WHERE name IN ({})
                    """.format(','.join(['%s']*len(si_adicionales))), tuple(si_adicionales))
                    print(f"      ✅ Limpiadas\n")

                # 6. COMMIT
                print(f"   3. Confirmando cambios (COMMIT)...")
                frappe.db.commit()
                print(f"      ✅ Cambios confirmados\n")

                # 7. VERIFICACIÓN FINAL
                print(f"🔍 ESTADO DESPUÉS DE MARCAR:\n")

                if len(si_originales) > 0:
                    si_originales_despues = frappe.db.sql("""
                        SELECT name, custom_status_comisiones, custom_orden_de_pago_comision
                        FROM `tabSales Invoice`
                        WHERE name IN ({})
                    """.format(','.join(['%s']*len(si_originales))), tuple(si_originales), as_dict=True)

                    originales_correctas_despues = sum(1 for s in si_originales_despues
                                                        if s.custom_status_comisiones == "Enviado"
                                                        and s.custom_orden_de_pago_comision == opc_name)
                    originales_incorrectas_despues = len(si_originales_despues) - originales_correctas_despues

                    print(f"   Originales correctas: {originales_correctas_despues}/{len(si_originales)} {'✅' if originales_incorrectas_despues == 0 else '❌'}")
                    print(f"   Originales incorrectas: {originales_incorrectas_despues}/{len(si_originales)}")
                else:
                    originales_correctas_despues = 0
                    originales_incorrectas_despues = 0

                if len(si_adicionales) > 0:
                    si_adicionales_despues = frappe.db.sql("""
                        SELECT name, custom_status_comisiones, custom_orden_de_pago_comision
                        FROM `tabSales Invoice`
                        WHERE name IN ({})
                    """.format(','.join(['%s']*len(si_adicionales))), tuple(si_adicionales), as_dict=True)

                    adicionales_correctas_despues = sum(1 for s in si_adicionales_despues
                                                         if (s.custom_status_comisiones == "Sin Enviar" or s.custom_status_comisiones is None)
                                                         and s.custom_orden_de_pago_comision is None)
                    adicionales_incorrectas_despues = len(si_adicionales_despues) - adicionales_correctas_despues

                    print(f"   Adicionales correctas: {adicionales_correctas_despues}/{len(si_adicionales)} {'✅' if adicionales_incorrectas_despues == 0 else '❌'}")
                    print(f"   Adicionales incorrectas: {adicionales_incorrectas_despues}/{len(si_adicionales)}")
                else:
                    adicionales_correctas_despues = 0
                    adicionales_incorrectas_despues = 0

                print()

                match_originales = originales_incorrectas_despues == 0
                match_adicionales = adicionales_incorrectas_despues == 0

                if match_originales and match_adicionales:
                    print(f"✅ ÉXITO: Sales Invoices marcadas correctamente\n")
                    resultado_opc["exito"] = True
                    resultado_opc["marcado"] = {
                        "si_originales_marcadas": len(si_originales),
                        "si_adicionales_limpiadas": len(si_adicionales),
                        "estado_antes": {
                            "originales_correctas": originales_correctas_antes,
                            "originales_incorrectas": originales_incorrectas_antes,
                            "adicionales_correctas": adicionales_correctas_antes,
                            "adicionales_incorrectas": adicionales_incorrectas_antes
                        },
                        "estado_despues": {
                            "originales_correctas": originales_correctas_despues,
                            "originales_incorrectas": originales_incorrectas_despues,
                            "adicionales_correctas": adicionales_correctas_despues,
                            "adicionales_incorrectas": adicionales_incorrectas_despues
                        }
                    }
                    resultados["opc_exitosas"] += 1
                    resultados["total_si_originales"] += len(si_originales)
                    resultados["total_si_adicionales"] += len(si_adicionales)
                else:
                    error = "Verificación falló: algunas SI no tienen estado correcto"
                    print(f"❌ ERROR: {error}\n")
                    resultado_opc["errores"].append(error)
                    resultados["opc_con_errores"] += 1

        except Exception as e:
            error = f"Excepción durante procesamiento: {str(e)}"
            print(f"❌ ERROR: {error}\n")
            resultado_opc["errores"].append(error)
            resultados["opc_con_errores"] += 1
            if not dry_run:
                frappe.db.rollback()
                print(f"   🔄 Rollback ejecutado\n")

        resultados["detalle_por_opc"][opc_name] = resultado_opc

    # Resumen final
    print("="*80)
    print("📊 RESUMEN FINAL")
    print("="*80 + "\n")

    print(f"Total OPC procesadas: {resultados['total_opc']}")
    print(f"OPC exitosas: {resultados['opc_exitosas']} ✅")
    print(f"OPC con errores: {resultados['opc_con_errores']}" + (" ❌" if resultados['opc_con_errores'] > 0 else ""))
    print()
    print(f"Total SI originales: {resultados['total_si_originales']}")
    print(f"Total SI adicionales: {resultados['total_si_adicionales']}")
    print()

    # Guardar reporte
    output_path = Path(__file__).parent / "reporte_marcado_si.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"✅ Reporte guardado en: {output_path}")
    print("="*80 + "\n")

    if dry_run:
        print("ℹ️  Ejecuta con dry_run=0 para aplicar cambios reales\n")

    return resultados
