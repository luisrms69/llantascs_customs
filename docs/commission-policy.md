# Commission Policy & Workflow

## Current Implementation (v2.0)

### Manual Workflow
The commission calculation system operates on a fully manual workflow:

1. **Branch Selection**: Use "Todas las Sucursales" button or manually select branches
2. **Date Range**: Set fecha_inicial and hasta_fecha (no automatic triggers)
3. **Complete Calculation**: Use "Actualiza Listado" button with confirmation dialog
   - **Part 1**: Synchronizes commission rates from Comisiones Settings
   - **Part 2**: Generates complete commission table with COGS calculations
4. **Review & Adjust**: Manually edit rates or commission data if needed
5. **Save Document**: Persist all changes to database (triggers live rate updates)
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
- **Synchronization**: "Actualiza Listado" button syncs rates with confirmation
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
- **Negative Commission Policy**: Configurable handling via Comisiones Settings with audit trail
- **New Document Support**: Error-free creation and calculation for unsaved documents

### Negative Commission Policy (v2.1+)

#### Configuration
**Location**: Comisiones Settings → "Política de Comisiones Negativas"

**Options**:
- **"Contabilizar como cero" (Default)**: Negative commissions are converted to 0 in calculations
- **"Reduce del pago"**: Negative commissions reduce the total payment amount

#### Implementation Logic
1. **Brute Calculation**: `utilidad * (rate_cc / 100.0)` calculated first
2. **Negative Accumulation**: All negative values accumulated in `subtotal_negativas` before policy
3. **Policy Application**: `_apply_policy()` function applies configured policy:
   - "Contabilizar como cero": `max(bruto, 0.0)`
   - "Reduce del pago": `bruto` (unchanged)
4. **Audit Trail**: `subtotal_comisiones_negativas` field always shows original negative sum

#### Usage Scenarios
- **Conservative Approach**: Use "Contabilizar como cero" to prevent negative payments
- **Accurate Accounting**: Use "Reduce del pago" for precise profit/loss tracking
- **Audit Compliance**: `subtotal_comisiones_negativas` provides transparency regardless of policy

#### Data Flow
- **Button Workflow**: Policy applied during "Actualiza Listado" execution
- **Save Workflow**: Policy applied during before_save hook
- **Consistency**: Both workflows use identical `get_commission_rows()` logic

### Sales Invoice Cancellation System (v2.2.0) ⚠️ CRITICAL ISSUE UNRESOLVED

#### Investigation Status: FAILED
The commission cancellation system investigation has **FAILED**. Multiple technical approaches were attempted but the core issue remains unresolved.

#### 🚨 Problem Statement
**Issue**: Native ERPNext dialog "¿Desea cancelar todos los documentos vinculados?" still appears when cancelling Sales Invoices with commission payments
**Impact**: User confusion and risk of accidental OPC cancellation
**Status**: **UNRESOLVED** after extensive technical investigation

#### ❌ Failed Technical Approaches

**Approach 1: JavaScript Interception (FAILED)**
- **Goal**: Intercept cancellation before ERPNext shows native dialog
- **Implementation**: Client Script "Sales Invoice Cancellation Guard" created
- **Result**: ❌ Native dialog still appeared
- **Cause**: ERPNext's `savecancel()` executes BEFORE Client Script hooks

**Approach 2: Field Type Conversion (FAILED)**  
- **Goal**: Convert Link field to Data to eliminate link detection
- **Implementation**: Patch converted `custom_orden_de_pago_comision` from Link to Data
- **Result**: ❌ Native dialog still appeared
- **Cause**: ERPNext detects links via child table references (`Comision LLCS.sales_invoice_id`)

#### 🔬 Root Cause Analysis
**Technical Constraint**: ERPNext's `get_submitted_linked_docs()` detects relationships through:
1. **Parent Link Fields** ← Successfully eliminated
2. **Child Table References** ← **Cannot eliminate without breaking functionality**
3. **Dynamic Links** ← Not applicable

**Evidence**: Sales Invoice ACC-SINV-2025-03089 detected as linked because:
- Child table Comision LLCS contains 9 records with sales_invoice_id = "ACC-SINV-2025-03089"
- Parent OPC has docstatus = 1 (submitted)
- ERPNext considers this a "submitted linked document"

#### ✅ Working Components (Partial Success)
**Adjustment System**: Successfully implemented but blocked by UX issue
- **Triple Fallback Search**: Server-side OPC detection mechanisms working
- **Automatic Adjustment Creation**: `Ajuste Comision Pendiente` generation functional
- **OPC Protection System**: Prevention of accidental OPC cancellation working
- **Adjustment Consumption**: Integration with next OPC generation (requires testing)

#### 🛠️ Current System Status (Blocked Implementation)
**Adjustment System Components** (Ready but UX-blocked):
1. **DocType Created**: `Ajuste Comision Pendiente` for tracking cancelled commission adjustments
2. **Server Hooks**: `on_sales_invoice_cancel`, `before_opc_cancel` implemented and functional
3. **Triple Fallback Search**: `_find_opc_by_sales_invoice()` working correctly
4. **OPC Protection**: Successfully blocks OPC cancellation when active SIs exist

**Theoretical Adjustment Workflow** (If UX issue were resolved):
1. **SI Cancellation**: User cancels Sales Invoice with OPC link
2. **Link Removal**: SI unlinked from OPC, status reset to "Sin Enviar"
3. **Adjustment Creation**: Negative adjustment records created in `Ajuste Comision Pendiente`
4. **Next OPC Integration**: Pending adjustments automatically included in next OPC generation
5. **Policy Exclusion**: Adjustments NOT subject to negative commission policy (always deduct)
6. **Closure**: Adjustments marked "Aplicado" when new OPC is submitted

**⚠️ CRITICAL BLOCKER**: Native dialog issue prevents safe user operation

#### OPC Protection System
**before_cancel Hook**: Prevents OPC cancellation if active Sales Invoices are linked
- Error message guides user to cancel individual SIs instead
- Protects commission integrity and maintains audit trail

#### Adjustment DocType Structure
**Ajuste Comision Pendiente**:
- `sales_invoice_id`: Link to cancelled Sales Invoice
- `cost_center`: Branch where commission was earned  
- `persona_de_ventas`: Salesperson who earned commission
- `monto_ajuste`: Negative amount to deduct (always negative)
- `motivo`: Reason for adjustment
- `source_opc`: Original OPC where commission was paid
- `status`: "Pendiente" → "Aplicado"
- `applied_in_opc`: OPC where adjustment was consumed
- `applied_date`: When adjustment was applied

#### 🚨 Current User Experience (Problematic)
**What Users Currently Face**:
1. **User clicks Cancel** on Sales Invoice with commissions
2. **Native Dialog Appears**: "¿Desea cancelar todos los documentos vinculados?"
   - Lists: "Orden de Pago Comisiones: [OPC_NAME]"
   - Asks: "¿Desea cancelar todos los documentos vinculados?"
3. **Critical User Decision**:
   - **"Cancel All"**: ⚠️ **DANGEROUS** - Will cancel OPC and lose commission payment record
   - **"No"**: Cancellation is aborted, SI remains active

**🚨 Emergency User Training Required**:
- **ALWAYS click "No"** in the native dialog
- **DO NOT** click "Cancel All" - this will destroy commission payment records
- **Report the issue** if cancellation is truly needed

#### 💭 Investigation Conclusion
**Status**: Problem may be **technically unsolvable** with current approach
**Constraint**: ERPNext's core link detection cannot be overridden without breaking commission functionality
**Recommendation**: Consider alternative approaches or accept current limitations with improved user training

#### ⚠️ Testing Status
Even with UX issue unresolved, adjustment system components require comprehensive testing:
- User acceptance testing of adjustment creation/consumption workflow
- Production data validation 
- Edge case testing for concurrent operations
- Performance testing with large commission datasets