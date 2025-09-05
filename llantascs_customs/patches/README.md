# Patches Directory

This directory contains database migration patches for the llantascs_customs app.

## Current Structure

### v2.5.0 - Current Active Patches
- **migrate_opc_v2.py**: Complete commission system migration
  - Migrates legacy `sucursal` field to `sucursales_multi` child table
  - Migrates legacy `comision_sobre_utilidad_` to `comisiones_por_sucursal` child table  
  - Backfills `porcentaje_comision` in `Comision LLCS` from Sales Team data
  - Status: ✅ Active and functional
  - Executed: 2025-09-05
  - Documents processed: 302/302

## Legacy Patches (Removed)

The following patch versions have been **removed** as they were obsoleted by v2.5.0:

- **v2.4.1**: `migrate_legacy_commission_system` - Replaced by v2.5.0
- **v2.4.1**: `create_performance_index` - Never executed, obsolete
- **v2.4.2**: `migrate_commission_legacy_to_v2` - Replaced by v2.5.0

## Migration History

| Version | Date | Status | Documents | Notes |
|---------|------|--------|-----------|-------|
| v2.4.1 | 2025-09-04 | ✅ Completed | Partial | Legacy migration (obsolete) |
| v2.4.2 | 2025-09-04 | ✅ Completed | Partial | Legacy migration (obsolete) |
| v2.5.0 | 2025-09-05 | ✅ Active | 302/302 | Complete migration, replaces all previous |

## Notes

- **v2.5.0 is the single source of truth** for commission system migrations
- All legacy patches completed successfully and were safely removed
- System is clean with only one active patch version
- No data loss occurred during cleanup

## Maintenance

- Only modify v2.5.0 patches if absolutely necessary
- Always backup database before making changes
- Use idempotent patch patterns to allow safe re-execution