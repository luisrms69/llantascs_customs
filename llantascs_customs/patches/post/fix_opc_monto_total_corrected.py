import frappe

def execute():
    """Fix monto_total for OPCs using direct UPDATE with JOIN - based on ChatGPT solution"""

    # Configuration - exact names verified via metadata
    PARENT_DT = "Orden de Pago Comisiones"
    PARENT_TOTAL_FIELD = "monto_total"
    CHILD_DT = "Comision LLCS"
    CHILD_COMM_FIELD = "total_comision"
    ALLOWED_DOCSTATUS = (1,)

    frappe.logger().info("[fix_opc_monto_total_final] Iniciando patch con lógica ChatGPT corregida")

    try:
        # Use direct UPDATE with JOIN (the method that works)
        # This avoids the get_all filtering issues from previous attempts
        query = f"""
            UPDATE `tab{PARENT_DT}` p
            JOIN (
              SELECT parent,
                     COALESCE(SUM(`{CHILD_COMM_FIELD}`), 0) AS child_sum
              FROM `tab{CHILD_DT}`
              GROUP BY parent
            ) s ON s.parent = p.name
            SET p.`{PARENT_TOTAL_FIELD}` = s.child_sum
            WHERE p.docstatus = 1
              AND (p.`{PARENT_TOTAL_FIELD}` IS NULL OR ABS(p.`{PARENT_TOTAL_FIELD}`) < 0.0000001)
              AND s.child_sum > 0
        """

        affected_rows = frappe.db.sql(query)

        frappe.db.commit()

        # Get final statistics
        stats_query = f"""
            SELECT
                COUNT(*) as total_opcs,
                COUNT(CASE WHEN `{PARENT_TOTAL_FIELD}` > 0 THEN 1 END) as positive_total,
                COUNT(CASE WHEN `{PARENT_TOTAL_FIELD}` IS NULL OR ABS(`{PARENT_TOTAL_FIELD}`) < 0.0000001 THEN 1 END) as zero_total
            FROM `tab{PARENT_DT}`
            WHERE docstatus = 1
        """
        final_stats = frappe.db.sql(stats_query, as_dict=True)[0]

        frappe.logger().info(f"[fix_opc_monto_total_final] UPDATE completado exitosamente")
        frappe.logger().info(f"[fix_opc_monto_total_final] Filas afectadas: {affected_rows}")
        frappe.logger().info(f"[fix_opc_monto_total_final] Estado final - Total: {final_stats.total_opcs}, Positivos: {final_stats.positive_total}, Ceros: {final_stats.zero_total}")

    except Exception as e:
        frappe.db.rollback()
        frappe.logger().error(f"[fix_opc_monto_total_final] Error en patch: {e}")
        import traceback
        frappe.logger().error(traceback.format_exc())
        raise