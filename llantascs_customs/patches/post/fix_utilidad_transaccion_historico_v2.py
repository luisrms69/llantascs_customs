import frappe

def execute():
    # Pobla utilidad_transaccion solo donde hoy está vacía/cero, en OPC enviadas (docstatus=1).
    # Idempotente: re-ejecutar no cambia filas ya pobladas.
    frappe.db.sql("""
        UPDATE `tabComision LLCS` c
        JOIN `tabOrden de Pago Comisiones` o
          ON o.name = c.parent
         AND c.parenttype = 'Orden de Pago Comisiones'
        SET c.utilidad_transaccion = (c.ingreso - c.costo_de_ventas)
        WHERE o.docstatus = 1
          AND (c.utilidad_transaccion IS NULL OR ABS(c.utilidad_transaccion) < 1e-9)
          AND c.ingreso IS NOT NULL
          AND c.costo_de_ventas IS NOT NULL
    """)