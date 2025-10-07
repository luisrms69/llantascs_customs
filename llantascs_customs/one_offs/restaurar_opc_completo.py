import frappe
import json
from pathlib import Path
from datetime import datetime
import uuid

def run(dry_run=1):
    """
    ETAPA 1-2: Restaura el estado completo de las OPC desde el backup.

    Restaura por SQL (bypass hooks):
    - Sucursales (desde backup)
    - Comisiones (desde backup)
    - Monto total (calculado desde comisiones)

    Implementa las 6 condiciones clave:
    1. parentfield exacto en hijos
    2. name único (UUID) en tablas hijas
    3. Columnas 1:1 con DocType hijo
    4. N/A (este script no toca SIs)
    5. Transacción por OPC + commit
    6. Verificación previa y final

    Sugerencias adicionales:
    - Snapshot JSON por OPC (antes de tocar)
    - idx secuencial en hijos
    """

    mode = "🔍 DRY-RUN (simulación)" if dry_run else "⚡ EJECUCIÓN REAL"
    print("\n" + "="*80)
    print(f"ETAPA 1-2: RESTAURACIÓN COMPLETA DE OPC - {mode}")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Cargar backup
    backup_path = Path(__file__).parent / "opc_backup.json"
    with open(backup_path, 'r', encoding='utf-8') as f:
        backup = json.load(f)

    print(f"📦 Backup cargado: {len(backup)} OPC\n")

    # Crear directorio para snapshots
    snapshots_dir = Path(__file__).parent / "snapshots"
    if not dry_run:
        snapshots_dir.mkdir(exist_ok=True)

    resultados = {
        "fecha_ejecucion": datetime.now().isoformat(),
        "modo": mode,
        "total_opc": len(backup),
        "opc_exitosas": 0,
        "opc_con_errores": 0,
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
            # Verificar docstatus = 0
            docstatus = frappe.db.get_value("Orden de Pago Comisiones", opc_name, "docstatus")
            if docstatus is None:
                error = f"OPC no existe en la base de datos"
                print(f"❌ ERROR: {error}\n")
                resultado_opc["errores"].append(error)
                resultados["opc_con_errores"] += 1
                resultados["detalle_por_opc"][opc_name] = resultado_opc
                continue

            if docstatus != 0:
                error = f"OPC no está en borrador (docstatus={docstatus})"
                print(f"❌ ERROR: {error}\n")
                resultado_opc["errores"].append(error)
                resultados["opc_con_errores"] += 1
                resultados["detalle_por_opc"][opc_name] = resultado_opc
                continue

            # Capturar estado actual (SNAPSHOT)
            estado_actual = {
                "sucursales": [],
                "comisiones": [],
                "monto_total": 0.0
            }

            sucursales_actual = frappe.db.sql("""
                SELECT name, cost_center
                FROM `tabSucursales Multi`
                WHERE parent = %s
                ORDER BY idx
            """, (opc_name,), as_dict=True)

            comisiones_actual = frappe.db.sql("""
                SELECT name, sales_invoice_id, total_comision
                FROM `tabComision LLCS`
                WHERE parent = %s
                ORDER BY idx
            """, (opc_name,), as_dict=True)

            monto_actual = frappe.db.get_value("Orden de Pago Comisiones", opc_name, "monto_total") or 0

            estado_actual["sucursales"] = [s.cost_center for s in sucursales_actual]
            estado_actual["comisiones"] = [{"si": c.sales_invoice_id, "monto": float(c.total_comision)} for c in comisiones_actual]
            estado_actual["monto_total"] = float(monto_actual)

            print(f"📊 ESTADO ACTUAL:")
            print(f"   Sucursales: {len(sucursales_actual)}")
            print(f"   Comisiones: {len(comisiones_actual)}")
            print(f"   Monto total: ${monto_actual:,.2f}\n")

            print(f"📦 ESTADO BACKUP:")
            print(f"   Sucursales: {len(opc_backup['sucursales'])}")
            print(f"   Comisiones: {len(opc_backup['comisiones'])}")
            monto_backup = sum(c['total_comision'] for c in opc_backup['comisiones'])
            print(f"   Monto total: ${monto_backup:,.2f}\n")

            # Guardar snapshot (antes de modificar)
            if not dry_run:
                snapshot_path = snapshots_dir / f"pre_{opc_name}.json"
                with open(snapshot_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "opc": opc_name,
                        "timestamp": datetime.now().isoformat(),
                        "estado_actual": estado_actual
                    }, f, indent=2, ensure_ascii=False)
                print(f"📸 Snapshot guardado: {snapshot_path}\n")

            if dry_run:
                print(f"🔍 DRY-RUN: Se ejecutarían las siguientes operaciones:")
                print(f"   1. DELETE {len(sucursales_actual)} sucursales actuales")
                print(f"   2. INSERT {len(opc_backup['sucursales'])} sucursales desde backup")
                print(f"   3. DELETE {len(comisiones_actual)} comisiones actuales")
                print(f"   4. INSERT {len(opc_backup['comisiones'])} comisiones desde backup")
                print(f"   5. UPDATE monto_total: ${monto_actual:,.2f} → ${monto_backup:,.2f}")
                print(f"   6. COMMIT\n")

                resultado_opc["exito"] = True
                resultado_opc["simulacion"] = {
                    "sucursales_a_restaurar": len(opc_backup['sucursales']),
                    "comisiones_a_restaurar": len(opc_backup['comisiones']),
                    "monto_a_restaurar": monto_backup
                }
                resultados["opc_exitosas"] += 1

            else:
                print(f"⚡ EJECUTANDO RESTAURACIÓN:\n")

                # ============================================================
                # TRANSACCIÓN POR OPC (Condición 5)
                # ============================================================

                # 1. DELETE sucursales actuales
                print(f"   1. Eliminando {len(sucursales_actual)} sucursales actuales...")
                frappe.db.sql("DELETE FROM `tabSucursales Multi` WHERE parent = %s", (opc_name,))
                print(f"      ✅ Eliminadas\n")

                # 2. INSERT sucursales desde backup (Condiciones 1, 2, sugerencia B)
                print(f"   2. Insertando {len(opc_backup['sucursales'])} sucursales desde backup...")
                for idx, cost_center in enumerate(opc_backup['sucursales'], start=1):
                    frappe.db.sql("""
                        INSERT INTO `tabSucursales Multi`
                        (name, parent, parenttype, parentfield, idx, cost_center,
                         creation, modified, modified_by, owner, docstatus)
                        VALUES (uuid(), %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, 0)
                    """, (
                        opc_name,
                        "Orden de Pago Comisiones",  # Condición 1: parenttype exacto
                        "sucursales_multi",           # Condición 1: parentfield exacto
                        idx,                          # Sugerencia B: idx secuencial
                        cost_center,
                        frappe.session.user,
                        frappe.session.user
                    ))
                print(f"      ✅ Insertadas {len(opc_backup['sucursales'])} sucursales\n")

                # 3. DELETE comisiones actuales
                print(f"   3. Eliminando {len(comisiones_actual)} comisiones actuales...")
                frappe.db.sql("DELETE FROM `tabComision LLCS` WHERE parent = %s", (opc_name,))
                print(f"      ✅ Eliminadas\n")

                # 4. INSERT comisiones desde backup (Condiciones 1, 2, 3, sugerencia B)
                print(f"   4. Insertando {len(opc_backup['comisiones'])} comisiones desde backup...")
                for idx, comision in enumerate(opc_backup['comisiones'], start=1):
                    frappe.db.sql("""
                        INSERT INTO `tabComision LLCS`
                        (name, parent, parenttype, parentfield, idx,
                         sales_invoice_id, persona_de_ventas, porcentaje_comision,
                         ingreso, costo_de_ventas, utilidad_transaccion, total_comision, folio_fiscal,
                         creation, modified, modified_by, owner, docstatus)
                        VALUES (uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, 0)
                    """, (
                        opc_name,
                        "Orden de Pago Comisiones",  # Condición 1: parenttype exacto
                        "comisiones_incluidas",       # Condición 1: parentfield exacto
                        idx,                          # Sugerencia B: idx secuencial
                        comision["sales_invoice_id"],
                        comision["persona_de_ventas"],
                        comision["porcentaje_comision"],
                        comision["ingreso"],
                        comision["costo_de_ventas"],
                        comision["utilidad_transaccion"],
                        comision["total_comision"],
                        comision["folio_fiscal"],
                        frappe.session.user,
                        frappe.session.user
                    ))
                print(f"      ✅ Insertadas {len(opc_backup['comisiones'])} comisiones\n")

                # 5. UPDATE monto_total
                print(f"   5. Actualizando monto_total: ${monto_actual:,.2f} → ${monto_backup:,.2f}...")
                frappe.db.sql("""
                    UPDATE `tabOrden de Pago Comisiones`
                    SET monto_total = %s, modified = NOW()
                    WHERE name = %s
                """, (monto_backup, opc_name))
                print(f"      ✅ Actualizado\n")

                # 6. COMMIT (Condición 5: transacción por OPC)
                print(f"   6. Confirmando cambios (COMMIT)...")
                frappe.db.commit()
                print(f"      ✅ Cambios confirmados\n")

                # ============================================================
                # VERIFICACIÓN FINAL (Condición 6)
                # ============================================================
                print(f"🔍 VERIFICACIÓN FINAL:\n")

                sucursales_verificadas = frappe.db.sql("""
                    SELECT COUNT(*) as count
                    FROM `tabSucursales Multi`
                    WHERE parent = %s
                """, (opc_name,), as_dict=True)[0].count

                comisiones_verificadas = frappe.db.sql("""
                    SELECT COUNT(*) as count, COALESCE(SUM(total_comision), 0) as suma
                    FROM `tabComision LLCS`
                    WHERE parent = %s
                """, (opc_name,), as_dict=True)[0]

                monto_verificado = frappe.db.get_value("Orden de Pago Comisiones", opc_name, "monto_total")

                match_sucursales = sucursales_verificadas == len(opc_backup['sucursales'])
                match_comisiones = comisiones_verificadas.count == len(opc_backup['comisiones'])
                match_monto = abs(float(comisiones_verificadas.suma) - monto_backup) <= 0.01
                match_monto_parent = abs(float(monto_verificado) - monto_backup) <= 0.01

                print(f"   Sucursales: {sucursales_verificadas}/{len(opc_backup['sucursales'])} {'✅' if match_sucursales else '❌'}")
                print(f"   Comisiones: {comisiones_verificadas.count}/{len(opc_backup['comisiones'])} {'✅' if match_comisiones else '❌'}")
                print(f"   Suma comisiones: ${comisiones_verificadas.suma:,.2f} {'✅' if match_monto else '❌'}")
                print(f"   Monto parent: ${monto_verificado:,.2f} {'✅' if match_monto_parent else '❌'}")
                print()

                if match_sucursales and match_comisiones and match_monto and match_monto_parent:
                    print(f"✅ ÉXITO: OPC restaurada correctamente\n")
                    resultado_opc["exito"] = True
                    resultado_opc["restauracion"] = {
                        "sucursales_restauradas": sucursales_verificadas,
                        "comisiones_restauradas": comisiones_verificadas.count,
                        "monto_restaurado": float(monto_verificado)
                    }
                    resultados["opc_exitosas"] += 1
                else:
                    error = "Verificación falló: datos no coinciden con backup"
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

    # Guardar reporte
    output_path = Path(__file__).parent / "reporte_restauracion_completa.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"✅ Reporte guardado en: {output_path}")
    print("="*80 + "\n")

    if dry_run:
        print("ℹ️  Ejecuta con dry_run=0 para aplicar cambios reales\n")

    return resultados
