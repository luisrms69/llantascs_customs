# Commission Policy & Workflow

## Current Implementation (v2.0)

### Manual Workflow
The commission calculation system operates on a fully manual workflow:

1. **Branch Selection**: Use "Todas las Sucursales" button or manually select branches
2. **Date Range**: Set fecha_inicial and hasta_fecha (no automatic triggers)
3. **Complete Calculation**: Use "Actualizar Comisiones" button with confirmation dialog
   - **Part 1**: Synchronizes commission rates from Comisiones Settings
   - **Part 2**: Generates complete commission table with COGS calculations
4. **Review & Adjust**: Manually edit rates or commission data if needed
5. **Save Document**: Persist all changes to database
6. **Payment Processing**: Use "Confirmación de Pago" for submitted documents

### Commission Calculation Logic

#### Cost of Goods Sold (COGS) Resolution
The `get_costo_ventas_si` function implements a hierarchical approach:

1. **Primary**: Stock Ledger Entry (`update_stock = 1`)
2. **Secondary**: Delivery Note item costs (linked DN items)  
3. **Tertiary**: Return adjustment calculations
4. **Fallback**: Item base_rate * qty (with warnings)

#### Commission Calculation (Enhanced)
- **Single Source**: All calculations performed server-side via `get_commission_rows()`
- **Rate Resolution**: Specific branch rates or global default from Comisiones Settings
- **Formula**: `(Ingreso - COGS) * Sales_Person_Percentage * Branch_Rate / 10000`
- **Multi-Person Support**: Proportional calculation per `allocated_percentage`
- **Service Logic**: Service-only invoices exempt from delivery requirement
- **Stock Logic**: Stock items require delivery confirmation (update_stock or Delivery Note)

### Rate Management System
- **Source of Truth**: Comisiones Settings holds global default rate
- **Rate Snapshot**: `comisiones_por_sucursal` table stores rates used per order
- **Synchronization**: "Actualizar Comisiones" button syncs rates with confirmation
- **Clear+Rebuild Pattern**: Ensures 1:1 consistency between branches and rates
- **Data Protection**: User confirmation prevents accidental loss of manual changes

### Field Behavior & Data Flow
- **No Automatic Recalculation**: Field changes don't trigger calculations
- **Button-Driven**: All actions require explicit user interaction
- **Server-Side Processing**: All business logic centralized in Python
- **Clear+Rebuild Pattern**: Ensures data consistency and eliminates orphaned records
- **Multi-Branch Support**: Select multiple cost centers simultaneously
- **Backward Compatibility**: Original sucursal field preserved (hidden)
- **Rate Tracking**: Each OPC maintains snapshot of rates used for audit trail
- **Memory-First**: All changes stay in memory until user saves document
- **Live Rate Updates**: Commission calculations automatically update when rates are modified and saved
- **Smart Rate Resolution**: Document rates override Settings; specific Settings override default
- **Native Grid UX**: Standard ERPNext pagination and controls with protective restrictions
- **Data Integrity**: Zero fallbacks eliminated; always uses valid commission rates from hierarchy