# Database Migrations and Patches

This document describes database migration procedures and patch management for the Llantascs Customs application.

## Patch Management

### Post-Migration Patches

The following patches are executed after DocType migration:

#### Data Integrity Patches

- **`fix_opc_monto_total_corrected.py`**: Corrects `monto_total` field in OPC documents by calculating from child table sums
- **`fix_utilidad_transaccion_historico_v2.py`**: Populates `utilidad_transaccion` field from `ingreso - costo_de_ventas` calculation

#### Migration Patches

- **`migrate_opc_v2.py`**: Migrates OPC structure from legacy to new format

### Patch Execution

All patches are idempotent and safe to re-execute. They include protective WHERE clauses to avoid modifying correct data.

## Data Population Requirements

### Utilidad Transaccion Field

The `utilidad_transaccion` field in `Comision LLCS` requires population for proper report functionality:

- **Source**: Calculated from `ingreso - costo_de_ventas`
- **Scope**: Only submitted OPC documents (`docstatus = 1`)
- **Safety**: Only updates NULL or zero values, preserves existing data
- **Impact**: Required for "Comisiones por Vendedor Detalle" report and "Margen Promedio por Vendedor" chart

## Migration Verification

After migration, verify:

1. All patches executed successfully in `tabPatch Log`
2. `utilidad_transaccion` field populated where expected
3. Reports display correct utilidad values (> 0 where applicable)

## Troubleshooting

If reports show zero utilidad values after migration:

1. Check patch execution: `SELECT * FROM tabPatch Log WHERE patch_name LIKE '%utilidad%'`
2. Verify data population: `SELECT COUNT(*) FROM tabComision LLCS WHERE utilidad_transaccion > 0`
3. Re-run migration if needed: `bench --site <site> migrate`