# Commission Policy & Workflow

## Current Implementation (v2.0)

### Manual Workflow
The commission calculation system operates on a fully manual workflow:

1. **Branch Selection**: Use "Todas las Sucursales" button or manually select branches
2. **Date Range**: Set fecha_inicial and hasta_fecha (no automatic triggers)
3. **Manual Calculation**: Will use upcoming "Actualizar Comisiones" button
4. **Payment Processing**: Use "Confirmación de Pago" for submitted documents

### Commission Calculation Logic

#### Cost of Goods Sold (COGS) Resolution
The `get_costo_ventas_si` function implements a hierarchical approach:

1. **Primary**: Stock Ledger Entry (`update_stock = 1`)
2. **Secondary**: Delivery Note item costs (linked DN items)  
3. **Tertiary**: Return adjustment calculations
4. **Fallback**: Item base_rate * qty (with warnings)

#### Commission Calculation
- Base commission rate from Comisiones Settings
- Applied to: `(Ingreso - COGS) * Percentage * Rate / 10000`
- Supports multiple sales persons per invoice
- Handles allocated percentages properly

### Field Behavior
- **No Automatic Recalculation**: Field changes don't trigger calculations
- **Button-Driven**: All actions require explicit user interaction
- **Multi-Branch Support**: Select multiple cost centers simultaneously
- **Backward Compatibility**: Original sucursal field preserved (hidden)