# Changelog

## [v2.0] - 2025-09-01

### Added - Multisucursal Support
- New `Sucursales Multi` child DocType for multi-branch selection
- `sucursales_multi` Table MultiSelect field (required) in Orden de Pago Comisiones
- "Todas las Sucursales" button for automatic branch population
- `selected_cost_centers()` JS helper function

### Enhanced - COGS Calculation System
- Completely refactored `get_costo_ventas_si` with 4 calculation cases:
  1. Update Stock: Stock Ledger Entry based
  2. Delivery Notes: DN item cost summation  
  3. Returns: Proportional return cost adjustment
  4. Fallback: base_rate * qty with warnings/errors
- Added `_costo_bruto_factura` helper function
- Comprehensive unit tests with mocking framework

### Changed - Manual Workflow Implementation
- **BREAKING**: Removed automatic field event handlers
- No automatic recalculation on field changes (dates, branches)
- Hidden original `sucursal` field for backward compatibility
- Button-driven commission calculation workflow

### Removed - Automatic Triggers
- `hasta_fecha` automatic event handler
- `desde` automatic event handler  
- `sucursales_multi` erroneous automatic event handler
- Field-based auto-recalculation functionality

### Added - Commission Rate Management
- New "Actualizar Comisiones" button with Clear+Rebuild functionality
- Pre-confirmation dialog to prevent accidental data loss
- `OPC Comision Por Sucursal` child DocType for rates snapshot in OPC
- `Comisiones Settings Sucursal` child DocType for future branch-specific rates
- `comisiones_por_sucursal` Table field in OPC for rate tracking
- `tasas_por_sucursal` Custom Field in Comisiones Settings
- `sync_rates_from_settings()` API endpoint for rate synchronization

### Enhanced - Complete Commission Calculation System
- **Part 1**: 1:1 synchronization between `sucursales_multi` and `comisiones_por_sucursal`
- **Part 2**: Complete commission calculation with COGS integration
- Clear+Rebuild pattern ensures data consistency for both rate and commission tables
- Automatic cleanup of commission tables and totals on sync
- Global default rate from Comisiones Settings as fallback
- Enhanced `get_sales_invoices()` with multisucursal support and service/stock logic
- New `get_commission_rows()` API endpoint for structured commission data
- Server-side calculation eliminates client-server divergence

### Enhanced - Business Logic Improvements
- **Service vs Stock Logic**: Service-only invoices exempt from delivery requirement
- **Multisucursal Filtering**: Enhanced `get_sales_invoices()` accepts array of cost centers
- **SQL Optimizations**: Single JOIN queries replace N+1 patterns for performance
- **Deterministic Results**: Stable sort order (`posting_date asc, name asc`) for consistency

### Removed - Legacy Client-Side Logic
- Deprecated `populate_child_sales()`, `create_order()`, `generate_order()` functions
- Eliminated client-side commission calculations and filtering
- Removed manual field update triggers and automatic recalculations
- Centralized all business logic to server-side for single source of truth

### Known Issues - Under Investigation
- **Child Table Pagination**: Pagination not updating after Clear+Rebuild operations (59 comisiones calculadas, solo 50 visibles)
- **Research Conducted**: Analyzed ERPNext Purchase Invoice patterns, tested grid.refresh() and grid.reset_grid()
- **Current Status**: Bug persists, investigating ERPNext core implementation patterns
- **User Workaround**: Page refresh (F5) displays pagination correctly

### Technical
- Enhanced COGS calculation with fallback mechanisms
- Improved error handling and user notifications
- Unit test coverage for commission calculation logic
- Rate management infrastructure with snapshot pattern
- Fixtures integration for Custom Fields deployment
- API endpoints follow single responsibility principle
- Child table operations following ERPNext core patterns