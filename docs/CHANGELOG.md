# Changelog

## [v2.2.0] - 2025-09-01 - INVESTIGATION: NATIVE CANCEL DIALOG ISSUE

### 🔍 Issue Investigation - Native "Cancel All Documents" Dialog
**Problem**: Sales Invoice cancellation shows ERPNext native dialog "¿Desea cancelar todos los documentos vinculados?" causing user confusion and risk of accidental OPC cancellation.

### ❌ Failed Implementation Attempts

#### Attempt 1: Hybrid JavaScript + Server-Side Interceptor
- **Approach**: Client Script to intercept `before_cancel` + server-side link breaking
- **Implementation**: 
  - Client Script "Sales Invoice Cancellation Guard" created
  - `pre_cancel_break_opc_link()` server function implemented
  - Hooks registered in `doc_events`
- **Result**: ❌ **FAILED** - Native dialog still appeared
- **Root Cause**: ERPNext executes `savecancel()` BEFORE any Client Script `before_cancel` hooks

#### Attempt 2: Link → Data Field Conversion
- **Approach**: Convert `custom_orden_de_pago_comision` from Link to Data field to eliminate automatic link detection
- **Implementation**:
  - Patch `convert_opc_link_to_data.py` created and executed successfully
  - Field converted: `Fieldtype: Link → Data`, `Options: "Orden de Pago Comisiones" → ""`
  - 4,458 Sales Invoices with preserved values
- **Result**: ❌ **FAILED** - Native dialog still appeared
- **Root Cause**: ERPNext detects links via **child table references** (`Comision LLCS.sales_invoice_id`), not just parent Link fields

### 🔬 Technical Investigation Findings

#### ERPNext Link Detection Mechanism
ERPNext's `get_submitted_linked_docs()` function detects document relationships through:
1. **Direct Link Fields** (successfully eliminated)
2. **Child Table References** ← **This is the actual cause**
3. **Dynamic Links** (not applicable in this case)

#### Evidence
```
Sales Invoice ACC-SINV-2025-03089 is linked with 
Orden de Pago Comisiones COMISIONES-2025-08-31-07064

Child table references found:
- 9 records in Comision LLCS.sales_invoice_id referencing the SI
- 1 submitted OPC (COMISIONES-2025-08-31-07064) containing the SI
```

### ✅ Successfully Implemented (Partial)

#### Adjustment System Components
- **DocType Created**: `Ajuste Comision Pendiente` for tracking cancelled commission adjustments
- **Server Hooks**: `on_sales_invoice_cancel`, `before_opc_cancel` functional
- **Triple Fallback Search**: `_find_opc_by_sales_invoice()` working correctly
- **OPC Protection**: Successfully blocks OPC cancellation when active SIs exist

### 📊 Current System Status

#### Working Components ✅
- **v2.1 Features**: All negative commission policy and new document support functional
- **Adjustment Creation**: Automatic adjustment records generated on SI cancellation
- **Adjustment Consumption**: Pending adjustments integrated into next OPC generation  
- **OPC Protection**: Cannot accidentally cancel OPCs with active invoices
- **Legacy Field Fix**: OPC submission works correctly after `sucursal` migration

#### Failing Components ❌
- **Native Dialog Prevention**: Still shows "Cancel all documents" dialog
- **User Experience**: Confusing dialog persists, risk of accidental OPC cancellation remains

### 💭 Investigation Conclusion: Problem May Be Unsolvable

#### Technical Constraints Identified
1. **ERPNext Core Limitation**: Link detection via child tables cannot be easily overridden
2. **Bidirectional References**: Eliminating child table references would break commission functionality
3. **Framework Limitations**: Client-side interception occurs too late in cancellation flow

#### Proposed Alternative Approaches (Not Yet Accepted)
1. **Accept Native Dialog**: Improve user training and documentation
2. **Server-Side Messaging**: Add informative messages before native dialog
3. **Focus on Adjustment System**: Perfect the automatic adjustment workflow
4. **Seek ERPNext Expert**: Consult framework specialists for advanced solutions

### ✅ IMMEDIATE FIX IMPLEMENTED - OPC Protection Active

**Current State**: OPC protection successfully implemented and tested ✅
**Immediate Security**: OPCs cannot be cancelled if Sales Invoices are active
**UX Issue**: Native dialog still appears but data is now protected
**GitHub Issue**: Created for framework-level solution investigation

### 🛡️ IMMEDIATE PROTECTION DETAILS

#### Implementation (2025-09-01)
- **OPC Class Method**: `before_cancel()` added to `OrdenDePagoComisiones`
- **Protection Logic**: Counts active Sales Invoices from both child table and custom field
- **Error Message**: Clear Spanish dialog explaining why cancellation is blocked
- **Deployment**: Implemented via DocType method (no hooks.py changes needed)
- **Testing**: ✅ Verified working on multiple OPCs with active SIs

#### Protection Triggers
1. **Child Table Check**: `Comision LLCS.sales_invoice_id` references with `docstatus = 1`
2. **Custom Field Check**: `custom_orden_de_pago_comision` back-references with `docstatus = 1`
3. **Combined Count**: Total active Sales Invoices linked to OPC

#### User Experience
- **Clear Message**: "Esta Orden de Pago de Comisiones tiene X factura(s) de venta vinculada(s) activas"
- **Guidance**: "Para ajustar comisiones, cancele las facturas individuales"
- **Process**: Automatic adjustment generation mentioned

### ⚠️ REMAINING: Testing of Adjustment System
Adjustment system components still require comprehensive testing:
- User acceptance testing of adjustment creation/consumption workflow
- Production data validation of automatic adjustment generation
- Edge case testing for concurrent SI cancellation operations

---

## [v2.1.0] - 2025-09-01 - NEGATIVE COMMISSION POLICY & NEW DOCUMENT FIX

### Added - Negative Commission Policy System
- **Comisiones Settings**: Campo `negative_commission_policy` (Select) con opciones:
  - "Reduce del pago": Comisiones negativas se restan del total (comportamiento original)
  - "Contabilizar como cero": Comisiones negativas se convierten a 0 (DEFAULT)
- **OPC Informativo**: Campo `subtotal_comisiones_negativas` (Currency, read-only) para auditoría
- **Lógica Unificada**: Función `_apply_policy()` acumula negativos brutos antes de aplicar política
- **Ambos Flujos**: Botón "Actualiza Listado" y before_save usan lógica idéntica

### Fixed - New Document Error
- **Root Cause**: Documentos nuevos ("new-xxx") no existen en BD, causaban error al buscar docname
- **JS Solution**: Botón detecta `frm.is_new()` y usa `rates_by_cc` en lugar de `docname`
- **API Tolerance**: `get_commission_rows()` maneja graceful docnames inexistentes con try/catch
- **before_save Safe**: Siempre usa `rates_by_cc` para evitar problemas en primer guardado

### Enhanced - Subtotal Assignment
- **JS Button**: Extrae `subtotal_negativas` del API response y asigna al campo
- **before_save**: Asigna `self.subtotal_comisiones_negativas` automáticamente
- **API Return**: Incluye `subtotal_negativas` en response para ambos flujos

### Status - Commission System v2.1 Complete
- **✅ Part 1**: Rate synchronization from Comisiones Settings - WORKING
- **✅ Part 2**: Commission calculation with COGS integration - WORKING  
- **✅ Grid Pagination**: Native controls and navigation - WORKING
- **✅ Live Updates**: Rate changes instantly reflected on save - WORKING
- **✅ Data Protection**: User cannot break calculations accidentally - WORKING
- **✅ UX Polish**: Clear, intuitive button naming and messaging - WORKING
- **✅ Negative Policy**: Configurable handling of negative commissions - WORKING
- **✅ New Documents**: Error-free creation and calculation - WORKING
- **✅ Audit Trail**: Negative commissions always reported for transparency - WORKING

---

## [v2.0.3] - 2025-09-01 - UX IMPROVEMENTS

### Enhanced - User Experience
- **Button Rename**: "Actualizar Comisiones" → "Actualiza Listado" for clearer user intent
- **Improved Messaging**: "Listado actualizado → Tasas: X, Comisiones: Y, Total: Z" for better feedback
- **Consistent Loading Text**: "Actualizando listado…" aligns with button name
- **Confirmation Dialog**: Updated text references to match new button name

---

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