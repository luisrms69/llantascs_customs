# Reportes y acumuladores

Totales en Orden:
- `total_comision_bruta` – suma de positivos
- `total_compensaciones_negativas` – suma de negativos
- `monto_total` – neto pagable (cap a 0 por defecto)

Buenas prácticas:
- Reportar **comision_a_pagar** (no `total_comision` legacy).
- Transición: `IFNULL(comision_a_pagar, total_comision)` hasta completar backfill.
- KPIs: utilidad por sucursal, %comisiones, aging vs reducción, vendedor, etc.