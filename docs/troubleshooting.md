# Troubleshooting

- **DocType huérfano**: `frappe.reload_doc(...)` o creación programática + export JSON.
- **LinkValidationError** en tests: crear documentos mínimos (SI, Customer, Price List, Payment Entry).
- **Moneda mismatch**: asegurar cuenta por cobrar en moneda de la SI.
- **Total negativo**: error por `non_negative=1` → cap en hook o activar switch.
- **Flags vacíos (legacy)**: usar botones o backfill en migración final.