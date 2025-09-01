# Changelog

## [v2.0.2] - 2025-09-01 - COMPLETE WITH LIVE UPDATES

### Added - Live Rate Updates System
- **before_save Hook**: Automatic commission recalculation using in-memory rates
- **Smart Rate Resolution**: DOC → Settings específico → Settings default (eliminado fallback a 0)
- **get_commission_rows Enhanced**: Now accepts `rates_by_cc` parameter for memory-based calculations
- **sync_rates_from_settings Improved**: Proper handling of specific rates per branch
- **Result**: Rate changes in upper table immediately reflect in commission calculations when saving

### Enhanced - Data Protection & UX
- **Grid Protections**: Prevent manual Add/Delete Row while preserving native pagination
- **Field-Level Controls**: Only `porcentaje_comision` editable in rates table
- **UI Consistency**: Both button workflow and save workflow use identical calculation logic
- **Error Prevention**: No zero fallbacks, always uses valid commission rates

### Status - Commission System Complete
- **✅ Part 1**: Rate synchronization from Comisiones Settings - WORKING
- **✅ Part 2**: Commission calculation with COGS integration - WORKING  
- **✅ Grid Pagination**: Native controls and navigation - WORKING
- **✅ Live Updates**: Rate changes instantly reflected on save - WORKING
- **✅ Data Protection**: User cannot break calculations accidentally - WORKING

---

## [v2.0.1] - 2025-09-01 - PAGINATION FIXED

### Fixed - Grid Pagination Issue
- **Root Cause Identified**: `comisiones_incluidas` field had `read_only: 1` in DocType JSON
- **Solution Applied**: Changed to `read_only: 0` in orden_de_pago_comisiones.json 
- **Result**: Native ERPNext pagination now works perfectly without any workarounds
- **Code Cleanup**: Removed all grid manipulation hacks, timeouts, and save+reload logic
- **Final Pattern**: Clean ERPNext standard: `clear_table` → `frm.add_child` → `refresh_field`

---

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

### Issues Resolved
- **Child Table Pagination**: **FIXED** - Root cause identified and resolved
  - **Issue**: `comisiones_incluidas` field had `read_only: 1` in DocType JSON, preventing Add Row and pagination
  - **Solution**: Changed `read_only: 0` in orden_de_pago_comisiones.json and applied migrate
  - **Result**: Native pagination now works correctly using pure ERPNext patterns
  - **Code Cleanup**: Removed all grid hacks, timeouts, save+reload workarounds

### Technical - Final Implementation v2.0.2
- **Complete Commission System**: All parts operational with live updates
- **Enhanced API**: `get_commission_rows` with `rates_by_cc` parameter for memory-based calculations  
- **before_save Integration**: Automatic recalculation using in-memory rates before persistence
- **Rate Hierarchy**: DOC → Settings específico → Settings default (no zero fallbacks)
- **ERPNext Pure Pattern**: Standard `clear_table` → `frm.add_child` → `refresh_field` workflow
- **Enhanced COGS calculation**: 4-case fallback system with comprehensive error handling
- **Data Protection**: Grid restrictions prevent accidents while maintaining native pagination
- **Clean Architecture**: No grid hacks, internal APIs, or workarounds needed
- **Single Source of Truth**: Both button and save workflows use identical calculation logic