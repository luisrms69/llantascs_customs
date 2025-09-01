# Settings Documentation - Comisiones Settings

## Overview
The Comisiones Settings DocType serves as the central configuration point for the commission calculation system. It defines global defaults, policies, and behavioral parameters that apply across all commission calculations.

## Field Documentation

### Basic Configuration
- **`porcentaje_comision`** (Float, %, Default: 0): Global default commission rate applied when no specific branch rate is configured
- **`tasas_por_sucursal`** (Table): Branch-specific commission rates that override the global default

### Negative Commission Policy (v2.1.0+)
- **`negative_commission_policy`** (Select, Required, Default: "Contabilizar como cero"): Controls how negative commission values are handled in calculations

#### Policy Options
1. **"Contabilizar como cero"** (Default):
   - Negative commission values are converted to 0 in final calculations
   - Conservative approach prevents negative commission payments
   - Original negative values still reported in audit trail (`subtotal_comisiones_negativas`)
   
2. **"Reduce del pago"**:
   - Negative commission values reduce the total payment amount
   - Accurate accounting approach for precise profit/loss tracking
   - All negative values pass through to final calculations

#### Default Rationale
The "Contabilizar como cero" policy is set as default because:
- Prevents accidental negative commission payments to sales staff
- Provides financial protection against data entry errors
- Maintains transparent audit trail while applying conservative calculations
- Most common business requirement for commission systems

### Rate Hierarchy and Resolution
The system resolves commission rates in the following priority order:
1. **Document-Level Rates**: Rates stored in individual OPC `comisiones_por_sucursal` table
2. **Settings Specific Rates**: Branch-specific rates from `tasas_por_sucursal` table  
3. **Global Default**: The `porcentaje_comision` global default rate
4. **No Zero Fallback**: System never defaults to 0%, always uses valid rate from hierarchy

## Usage and Effects

### Impact on Commission Calculations
- **Live Updates**: Changes to settings apply immediately to new calculations
- **Existing Documents**: Use "Actualiza Listado" button to apply policy changes to existing OPCs
- **Memory-First Processing**: Rate changes in OPC documents override settings until saved
- **before_save Integration**: Settings automatically consulted during document save operations

### Audit and Transparency
- **Subtotal Reporting**: `subtotal_comisiones_negativas` field always shows true negative sum regardless of policy
- **Rate Tracking**: Each OPC maintains snapshot of rates used for complete audit trail
- **Policy Visibility**: Current policy clearly displayed and documented in all calculations

## Version History

### v2.0.0
- Initial `porcentaje_comision` global default
- `tasas_por_sucursal` table for branch-specific rates
- Rate hierarchy and resolution system

### v2.1.0
- Added `negative_commission_policy` field
- Default policy set to "Contabilizar como cero"
- Enhanced audit trail with subtotal tracking
- Integration with before_save hooks for live updates

### v2.2.0 ⚠️ PENDING TESTS
- Settings unchanged - policy system integrates with new adjustment workflow
- Adjustment amounts NOT subject to negative commission policy (always deduct)
- Settings provide consistent behavior across cancellation recovery scenarios

## Configuration Best Practices

### Initial Setup
1. **Set Global Default**: Configure reasonable `porcentaje_comision` (e.g., 2.5%)
2. **Configure Policy**: Choose appropriate `negative_commission_policy` based on business needs
3. **Branch Rates**: Add specific rates in `tasas_por_sucursal` for branches requiring different rates
4. **Test Calculations**: Verify policy behavior with test data before production use

### Ongoing Management
- **Policy Changes**: Apply immediately but use "Actualiza Listado" to refresh existing documents
- **Rate Updates**: Changes reflect in new calculations and when existing OPCs are recalculated
- **Audit Reviews**: Regularly review `subtotal_comisiones_negativas` reports to understand negative commission patterns
- **Documentation**: Keep business rationale documented for policy choices

### Migration Considerations ⚠️ NOT IMPLEMENTED
For systems upgrading to v2.1+:
- Existing documents created before negative policy implementation may need recalculation
- Consider bulk refresh of historical documents if policy changes affect reporting
- Document pre-migration state for audit compliance

## Related Documentation
- See `docs/commission-policy.md` for detailed policy implementation and workflow
- See `docs/operations.md` for user procedures and troubleshooting
- See `docs/CHANGELOG.md` for version-specific changes and implementation notes