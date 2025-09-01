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

### Technical
- Enhanced COGS calculation with fallback mechanisms
- Improved error handling and user notifications
- Unit test coverage for commission calculation logic