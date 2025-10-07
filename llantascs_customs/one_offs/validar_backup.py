import frappe
import json
from pathlib import Path
from datetime import datetime

def run():
    """
    ETAPA 0: Valida la estructura del backup JSON para las 10 OPC.

    Verifica:
    - Archivo existe y es JSON válido
    - Contiene las 10 OPC esperadas
    - Cada OPC tiene estructura completa: sucursales[], sales_invoices[], comisiones[]
    - Campos de comisiones están completos
    """

    print("\n" + "="*80)
    print("ETAPA 0: VALIDACIÓN DEL BACKUP")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Cargar backup
    backup_path = Path(__file__).parent / "opc_backup.json"

    if not backup_path.exists():
        print(f"❌ ERROR: No se encontró el archivo de backup en {backup_path}")
        return {"error": "Backup file not found"}

    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: El archivo backup no es JSON válido: {e}")
        return {"error": f"Invalid JSON: {e}"}

    print(f"✅ Archivo backup cargado: {backup_path}\n")

    # Validar estructura
    resultado = {
        "fecha_validacion": datetime.now().isoformat(),
        "backup_path": str(backup_path),
        "total_opc": len(backup),
        "opc_validas": 0,
        "opc_invalidas": 0,
        "errores": [],
        "detalle_por_opc": {},
        "resumen": {
            "total_sucursales": 0,
            "total_sales_invoices": 0,
            "total_comisiones": 0,
            "monto_total": 0.0
        }
    }

    # Campos requeridos en comisiones
    campos_requeridos = [
        "sales_invoice_id", "posting_date", "cost_center",
        "persona_de_ventas", "porcentaje_comision",
        "ingreso", "costo_de_ventas", "utilidad_transaccion",
        "total_comision", "folio_fiscal"
    ]

    for opc_name, opc_data in backup.items():
        print("="*80)
        print(f"Validando: {opc_name}")
        print("="*80 + "\n")

        errores_opc = []

        # Verificar claves principales
        if "sucursales" not in opc_data:
            errores_opc.append("Falta clave 'sucursales'")
        if "sales_invoices" not in opc_data:
            errores_opc.append("Falta clave 'sales_invoices'")
        if "comisiones" not in opc_data:
            errores_opc.append("Falta clave 'comisiones'")

        if errores_opc:
            print(f"❌ Estructura inválida:")
            for err in errores_opc:
                print(f"   • {err}")
            resultado["opc_invalidas"] += 1
            resultado["errores"].append(f"{opc_name}: {', '.join(errores_opc)}")
            continue

        # Contar elementos
        num_sucursales = len(opc_data["sucursales"])
        num_si = len(opc_data["sales_invoices"])
        num_comisiones = len(opc_data["comisiones"])

        print(f"Sucursales: {num_sucursales}")
        print(f"Sales Invoices: {num_si}")
        print(f"Comisiones: {num_comisiones}")

        # Validar que número de comisiones == número de sales invoices
        if num_comisiones != num_si:
            errores_opc.append(f"Número de comisiones ({num_comisiones}) != sales_invoices ({num_si})")

        # Validar campos en comisiones
        comisiones_invalidas = []
        monto_total = 0.0

        for idx, comision in enumerate(opc_data["comisiones"]):
            campos_faltantes = [c for c in campos_requeridos if c not in comision]
            if campos_faltantes:
                comisiones_invalidas.append(f"Comisión {idx}: faltan campos {campos_faltantes}")
            else:
                monto_total += comision["total_comision"]

        if comisiones_invalidas:
            errores_opc.extend(comisiones_invalidas[:3])  # Mostrar solo primeras 3
            if len(comisiones_invalidas) > 3:
                errores_opc.append(f"... y {len(comisiones_invalidas) - 3} comisiones más con errores")

        print(f"Monto total calculado: ${monto_total:,.2f}\n")

        # Guardar detalle
        resultado["detalle_por_opc"][opc_name] = {
            "sucursales": num_sucursales,
            "sales_invoices": num_si,
            "comisiones": num_comisiones,
            "monto_total": monto_total,
            "valida": len(errores_opc) == 0,
            "errores": errores_opc
        }

        if len(errores_opc) == 0:
            print(f"✅ OPC válida\n")
            resultado["opc_validas"] += 1
            resultado["resumen"]["total_sucursales"] += num_sucursales
            resultado["resumen"]["total_sales_invoices"] += num_si
            resultado["resumen"]["total_comisiones"] += num_comisiones
            resultado["resumen"]["monto_total"] += monto_total
        else:
            print(f"❌ OPC inválida:")
            for err in errores_opc:
                print(f"   • {err}")
            print()
            resultado["opc_invalidas"] += 1
            resultado["errores"].append(f"{opc_name}: {len(errores_opc)} errores")

    # Resumen final
    print("="*80)
    print("RESUMEN DE VALIDACIÓN")
    print("="*80 + "\n")

    print(f"Total OPC en backup: {resultado['total_opc']}")
    print(f"OPC válidas: {resultado['opc_validas']} ✅")
    print(f"OPC inválidas: {resultado['opc_invalidas']}" + (" ❌" if resultado['opc_invalidas'] > 0 else ""))
    print()

    if resultado['opc_validas'] > 0:
        print(f"TOTALES (solo OPC válidas):")
        print(f"  Sucursales: {resultado['resumen']['total_sucursales']}")
        print(f"  Sales Invoices: {resultado['resumen']['total_sales_invoices']}")
        print(f"  Comisiones: {resultado['resumen']['total_comisiones']}")
        print(f"  Monto total: ${resultado['resumen']['monto_total']:,.2f}")
        print()

    if resultado['opc_invalidas'] > 0:
        print(f"⚠️ ERRORES ENCONTRADOS:")
        for err in resultado['errores']:
            print(f"   • {err}")
        print()

    # Guardar reporte
    output_path = Path(__file__).parent / "validacion_backup.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    print(f"✅ Reporte guardado en: {output_path}")
    print("="*80 + "\n")

    if resultado['opc_invalidas'] == 0:
        print("✅ ÉXITO: Backup válido para todas las OPC\n")
    else:
        print("⚠️ ADVERTENCIA: Algunas OPC tienen errores en el backup\n")

    return resultado
