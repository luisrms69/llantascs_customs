# ADR-015: Utilidad Transaccion Data Migration Fix

## Status
Accepted

## Context
During post-migrate testing in staging environment, discovered that 4,608 out of 4,688 commission records had `utilidad_transaccion = 0` despite having valid `ingreso` and `costo_de_ventas` data. This caused:

1. "CH - Margen Promedio por Vendedor" chart to show zero values
2. "Comisiones por Vendedor Detalle" report to display zero utilidad column
3. Broken user experience in both Vendedores and Comisiones workspaces

### Root Cause Analysis
- Field `utilidad_transaccion` exists but is not automatically calculated during OPC creation
- Historical data has valid `ingreso` and `costo_de_ventas` but empty `utilidad_transaccion`
- Missing data population step during migration process
- Calculation logic: `utilidad_transaccion = ingreso - costo_de_ventas`

## Decision
Implement idempotent SQL patch to populate missing `utilidad_transaccion` values:

```sql
UPDATE `tabComision LLCS` c
JOIN `tabOrden de Pago Comisiones` o
  ON o.name = c.parent AND c.parenttype = 'Orden de Pago Comisiones'
SET c.utilidad_transaccion = (c.ingreso - c.costo_de_ventas)
WHERE o.docstatus = 1
  AND (c.utilidad_transaccion IS NULL OR ABS(c.utilidad_transaccion) < 1e-9)
  AND c.ingreso IS NOT NULL
  AND c.costo_de_ventas IS NOT NULL
```

## Consequences

### Positive
- **4,608 records corrected** from zero to proper calculated values
- Reports now display meaningful utilidad data
- Chart visualizations functional across all workspaces
- Idempotent patch safe for multiple executions
- Automatic deployment via migrate to all sites

### Protective Measures
- Only updates records with `docstatus = 1` (submitted OPCs)
- Preserves existing utilidad values > 0 (no data loss)
- Handles edge cases (NULL values, negative margins)
- Comprehensive WHERE clause prevents unintended modifications

### Technical Impact
- New patch file: `fix_utilidad_transaccion_historico_v2.py`
- Updated `patches.txt` for deployment pipeline
- Pattern established for future data population patches

## Implementation
- **Date**: 2025-09-16
- **Environment**: Tested in staging-llantascs.dev
- **Verification**: 4,608 records corrected, 1 edge case preserved
- **Deployment**: Ready for production via standard migrate process

## Notes
This follows the same pattern as `fix_opc_monto_total_corrected.py` using direct SQL UPDATE with JOIN for performance and reliability. Pattern proven effective for data population tasks in ERPNext environment.