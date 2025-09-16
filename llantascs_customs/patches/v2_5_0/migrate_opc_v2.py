# -*- coding: utf-8 -*-
import frappe

# Doctypes / fieldnames EXACTOS (según lo que confirmaste)
DT_OPC  = "Orden de Pago Comisiones"          # padre (submitted)
DT_CLL  = "Comision LLCS"                     # child del OPC (renglones por SI)
DT_SI   = "Sales Invoice"
DT_ST   = "Sales Team"

# Child fields (fieldnames) en OPC
CH_SM_FIELD  = "sucursales_multi"             # child: Sucursales Multi
CH_CPS_FIELD = "comisiones_por_sucursal"      # child: OPC Comision Por Sucursal

# Campos en OPC (padre) - LEGACY
FLD_OPC_SUCURSAL = "sucursal"                 # Cost Center (legacy)
FLD_OPC_TASA     = "comision_sobre_utilidad_" # Float (%)

# Campos en CLL (child del OPC)
FLD_CLL_SP   = "persona_de_ventas"
FLD_CLL_SI   = "sales_invoice_id"
# Participación REAL en CLL (según tu hallazgo)
FLD_CLL_PART = "porcentaje_comision"          # Float (% participación por vendedor)

def execute():
    # 0) Selección de OPC legacy/mixtos (docstatus=1 y con sucursal legacy)
    opc_names = frappe.get_all(
        DT_OPC,
        filters={"docstatus": 1, FLD_OPC_SUCURSAL: ["!=", ""]},
        pluck="name",
    )

    sm_inserts  = 0
    cps_inserts = 0

    # 1) Migrar sucursal → sucursales_multi (si está vacío)
    for name in opc_names:
        opc = frappe.get_doc(DT_OPC, name)

        # si ya tiene renglones en sucursales_multi, no hacemos nada
        if not getattr(opc, CH_SM_FIELD, None):
            suc = getattr(opc, FLD_OPC_SUCURSAL, None)
            if suc:
                opc.flags.ignore_validate_update_after_submit = True
                opc.append(CH_SM_FIELD, {"cost_center": suc})
                opc.save(ignore_permissions=True)
                sm_inserts += 1

    # 2) Migrar tasa legacy (OPC.comision_sobre_utilidad_) → comisiones_por_sucursal (si está vacío)
    for name in opc_names:
        opc = frappe.get_doc(DT_OPC, name)

        # si ya tiene renglones en comisiones_por_sucursal, no hacemos nada
        if not getattr(opc, CH_CPS_FIELD, None):
            suc  = getattr(opc, FLD_OPC_SUCURSAL, None)
            tasa = getattr(opc, FLD_OPC_TASA, None)

            # reglas estrictas: sin inventos
            if suc and tasa is not None:
                opc.flags.ignore_validate_update_after_submit = True
                opc.append(CH_CPS_FIELD, {
                    "cost_center": suc,
                    "porcentaje_comision": tasa,
                })
                opc.save(ignore_permissions=True)
                cps_inserts += 1
            else:
                # Si falta alguno, simplemente no migra ese OPC (no "rellena")
                # Puedes cambiar a frappe.throw(...) si quieres abortar en este escenario.
                pass

    # 3) Backfill de % participación en CLL desde Sales Team.allocated_percentage
    #    - Solo cuando CLL.porcentaje_comision está NULL o 0
    #    - Match por SI + sales_person
    frappe.db.sql(f"""
        UPDATE `tab{DT_CLL}` c
        LEFT JOIN `tab{DT_SI}` si
            ON si.name = c.`{FLD_CLL_SI}`
        LEFT JOIN `tab{DT_ST}` st
            ON st.parent = si.name
           AND st.sales_person = c.`{FLD_CLL_SP}`
        SET c.`{FLD_CLL_PART}` = st.allocated_percentage
        WHERE (c.`{FLD_CLL_PART}` IS NULL OR c.`{FLD_CLL_PART}` = 0)
          AND st.allocated_percentage IS NOT NULL
    """)

    frappe.db.commit()

    # Log informativo
    try:
        frappe.logger("llantascs_customs.patches").info({
            "patch": "v2_5_0.migrate_opc_v2",
            "sucursales_multi_insertadas": sm_inserts,
            "comisiones_por_sucursal_insertadas": cps_inserts,
            "nota": "Backfill de participación ejecutado (update por join)"
        })
    except Exception:
        pass  # no permitimos que el log rompa la migración