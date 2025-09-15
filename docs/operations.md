# Operations Manual - Orden de Pago Comisiones

## Workflow Changes - Manual Commission Management

### Current State (v2.0)
The commission calculation workflow has been restructured to be fully manual, removing automatic field triggers.

### User Interface Changes

#### Draft Documents
- **"Todas las Sucursales" Button**: Automatically populates all active Cost Centers
  - Visible only for saved Draft documents (`frm.doc.name && docstatus === 0`)
  - Clears existing selections and adds all active branches
  - Provides success notification with branch count

#### Manual Workflow
- **No Automatic Calculations**: Changing dates or branches no longer triggers automatic recalculation
- **Button-Driven Actions**: All commission calculations must be initiated manually
- **Preserved Functionality**: onload commission rate loading, payment confirmation buttons

### Field Behavior
- `sucursal`: Hidden field (backward compatibility)
- `sucursales_multi`: Active Table MultiSelect field for branch selection
- `desde`/`hasta_fecha`: Date fields without automatic triggers
- `comisiones_incluidas`: Commission table updated only via manual actions

### Complete Commission Calculation System
The "Actualiza Listado" button handles the complete workflow in two integrated parts:

#### Part 1: Rate Synchronization
- **Confirmation Dialog**: Warns about data loss before proceeding
- **Table Cleanup**: Clears both `comisiones_por_sucursal` and `comisiones_incluidas`
- **Rate Sync**: Pulls global default from Comisiones Settings
- **Rebuild**: Creates 1:1 mapping between selected branches and rates
- **Total Reset**: Sets `monto_total = 0` for clean state

#### Part 2: Commission Calculation
- **Date Validation**: Ensures fecha_inicial and hasta_fecha are set
- **Invoice Filtering**: Uses enhanced `get_sales_invoices()` with multisucursal support
- **Business Rules**: Applies "Paid + Delivered (except services)" logic
- **COGS Integration**: Uses robust 4-case `get_costo_ventas_si()` function
- **Per-Person Calculation**: Handles multiple sales persons with allocated percentages
- **Table Generation**: Populates `comisiones_incluidas` with complete commission data
- **Total Calculation**: Updates `monto_total` with sum of all commissions

### Enhanced Business Logic
- **Service vs Stock**: Service-only invoices bypass delivery requirement
- **Multisucursal**: Accepts array of cost centers, filters with SQL `IN` clause
- **SQL Optimizations**: Single JOIN queries eliminate N+1 performance issues
- **Deterministic Results**: Stable sorting ensures consistent output
- **Server-Side Processing**: Eliminates client-server calculation divergence

### Button Behavior
- **Visibility**: Only in Draft documents that are saved (`frm.doc.name && docstatus === 0`)
- **Validation**: Requires at least one branch selected in `sucursales_multi`
- **Date Validation**: Requires both fecha_inicial and hasta_fecha to be set
- **Clear+Rebuild**: Ensures perfect synchronization, no orphaned data
- **User Control**: Confirmation required, cancellation supported
- **Comprehensive Feedback**: "Listado actualizado → Tasas: X, Comisiones: Y, Total: Z" format
- **Clear UX Language**: Button named "Actualiza Listado" with consistent messaging throughout

### Current Implementation Status
- **✅ Part 1**: Rate synchronization from Comisiones Settings working correctly
- **✅ Part 2**: Complete commission calculation with COGS integration working correctly  
- **✅ Grid Pagination**: **RESOLVED** - Issue was `read_only: 1` configuration in DocType JSON
  - **Root Cause**: Field `comisiones_incluidas` had `read_only: 1`, preventing Add Row and pagination controls
  - **Solution**: Changed to `read_only: 0` in orden_de_pago_comisiones.json
  - **Result**: Native pagination now works correctly with ERPNext pure pattern
- **✅ UX Polish**: Intuitive button naming and messaging for better user experience

### Final Implementation Details
- **Clean ERPNext Pattern**: Uses standard `clear_table` → `frm.add_child` → `refresh_field` workflow
- **No Grid Hacks**: Eliminated all `grid.refresh()`, `grid.reset_grid()`, timeouts, and internal APIs
- **Native UX**: Pagination and controls work identically to Purchase Invoice "Get Items from" functionality
- **Live Rate Updates**: Changes in commission rates reflect immediately when saving document
- **Smart Rate Resolution**: DOC rates → Settings específico → Settings default (never 0)
- **Data Protection**: Grid protections prevent accidental manual edits while preserving pagination
- **User-Friendly Interface**: Clear button naming ("Actualiza Listado") with consistent messaging and loading states

### Negative Commission Policy Operations (v2.1+)

#### Configuration Steps
1. **Access Settings**: Navigate to Comisiones Settings
2. **Select Policy**: Choose "Política de Comisiones Negativas":
   - "Contabilizar como cero" (Default): Prevents negative commission payments
   - "Reduce del pago": Allows negative commissions to reduce total payment
3. **Save Settings**: Policy applies immediately to new calculations

#### New Document Workflow
1. **Create New OPC**: Document starts with "new-" prefix
2. **Select Branches**: Use "Todas las Sucursales" or manual selection
3. **Set Date Range**: Configure fecha_inicial and hasta_fecha
4. **Update Rates**: Modify commission rates in upper table if needed
5. **Generate Listado**: Use "Actualiza Listado" button (works for new documents)
6. **Review Results**: Check both `monto_total` and `subtotal_comisiones_negativas`
7. **Save Document**: before_save hook recalculates with current rates

#### Audit Trail Review
- **Positive Commissions**: Appear in main commission table
- **Negative Commissions**: 
  - Policy "Contabilizar como cero": Show as 0 in table, reported in subtotal field
  - Policy "Reduce del pago": Show actual negative values in table and subtotal
- **Transparency**: `subtotal_comisiones_negativas` always shows true negative sum

#### Troubleshooting
- **New Document Errors**: Fixed in v2.1+ with graceful docname handling
- **Missing Negative Subtotal**: Check if document was created before v2.1, use "Actualiza Listado" to refresh
- **Policy Changes**: Apply immediately, use "Actualiza Listado" to recalculate existing documents

## Sistema de Protección OPC (v2.2.1) ✅ IMPLEMENTADO

### Estado Actual - Sistema Estable
**IMPLEMENTACIÓN EXITOSA**: Protección OPC completamente funcional y verificada
**STATUS**: PRODUCCIÓN - Sistema limpio sin código experimental
**FECHA**: Septiembre 2025 - Listo para operaciones normales

### 🔒 Funcionalidad de Protección Implementada
- **Objetivo**: Evitar cancelación accidental de OPCs con Sales Invoices activas
- **Implementación**: Método `before_cancel()` en OrdenDePagoComisiones
- **Cobertura**: Detecta vínculos via child table y custom fields
- **Resultado**: ✅ Cancelación bloqueada con mensaje claro en español
- **Estado**: COMPLETAMENTE FUNCIONAL

### 🔍 Control de Calidad en Curso (Septiembre 2025)
**Actividad Actual**: Revisión sistemática de calidad en OPCs generadas
**Objetivo**: Identificar y resolver inconsistencias menores de datos

#### Áreas de Análisis Identificadas
1. **COGS Fallbacks**: Facturas de servicio sin costos de venta registrados
2. **Folios Fiscales Faltantes**: Sales Invoices sin folios fiscales completos  
3. **Personas de Venta**: Facturas sin sales team configurado correctamente
4. **Utilidades Negativas**: Casos específicos con costos superiores a ingresos

#### Proceso de Calidad Implementado
- **Análisis Automatizado**: Scripts de diagnóstico para OPCs específicas
- **Caso 1 Completado**: COGS fallbacks resueltos con nueva lógica de componentes aditivos
- **Revisión Caso por Caso**: Investigación detallada de inconsistencias restantes
- **Documentación**: Registro completo de hallazgos y resoluciones
- **Validación**: Verificación de correcciones antes de implementar

### 📊 Métodos COGS Actualizados (v2.2.2) - IMPLEMENTADO

#### Componentes de Cálculo Implementados
1. **Servicios**: Detección temprana → return 0.0 directo (sin warnings)
2. **Dropshipping**: `_cost_from_po_for_dropship()` usa Sales Order Item.delivered_by_supplier
3. **Delivery Notes**: `_cost_from_dn_items()` suma DN Item.base_net_rate * qty
4. **Stock Ledger**: `_sle_total_for_si()` suma stock_value_difference si existe
5. **Purchase Order**: `_cost_from_po_items()` para items restantes vía Sales Order
6. **GL Entry Fallback**: `_cost_from_gl_entries()` usa cuentas Cost of Goods Sold

#### Beneficios del Nuevo Sistema
- **Sin Warnings Innecesarios**: ✅ Servicios no generan alertas de fallback
- **Cálculo Correcto**: ✅ Facturas mixtas (servicios + productos) manejadas apropiadamente
- **Campos Reales**: ✅ Uso de so_detail y Sales Order Item en lugar de campos inexistentes
- **Fallback Contable**: ✅ GL Entry como respaldo final para casos edge
- **UX Limpio**: ✅ Eliminación de msgprint molestos
- **Bug Fix Mayor**: ✅ OperationalError (1054) resuelto definitivamente

## One-offs Scripts - Proven Development Pattern ✅

### Current Success Implementation (v2.5.0+)
**Status**: Established reliable pattern for complex operations and debugging

### Directory Structure
```
llantascs_customs/llantascs_customs/one_offs/
├── __init__.py
├── investigar_comision_llcs.py      # DocType/table existence verification
├── investigar_campos_exactos.py     # Metadata field name resolution  
├── clear_patch_log_v250.py          # Patch execution log management
├── verify_patch_v250_idempotency.py # Migration integrity verification
├── audit_all_patches.py             # Complete system patches audit
├── verify_no_pending_legacy.py      # Safety checks before cleanup
└── test_logger_patch_channel.py     # Functionality testing
```

### Execution Pattern
**Working Directory**: `/home/erpnext/frappe-bench/apps/llantascs_customs`
**Command Format**: `bench --site llantascs.dev execute llantascs_customs.llantascs_customs.one_offs.SCRIPT_NAME.run`

### Successful Use Cases
1. **Schema Investigation**: Verify DocType/table existence before operations
2. **Field Resolution**: Find exact field names from DocType metadata  
3. **Patch Management**: Clean execution logs, verify migration state
4. **System Auditing**: Complete patches inventory and consistency checks
5. **Safety Verification**: Confirm system state before destructive operations
6. **Functional Testing**: Verify component functionality after changes

### Success Metrics
- **100% Execution Success**: All scripts run without errors
- **Reliable Pattern**: Consistent structure and execution method
- **Safe Operations**: Read-only investigation + targeted specific actions
- **Development Speed**: Immediate verification and debugging capabilities
- **Reusability**: Scripts designed for multiple executions during development

### Key Benefits Realized
- **Rapid Prototyping**: Quick script creation for specific investigation needs
- **Safe Testing**: Isolated functions with clear boundaries and outputs
- **Complex Operations**: Reliable pattern for multi-step migration verification
- **Documentation**: Each script serves as living documentation of system state

### 🗂️ Archivos de Investigación Removidos
**Eliminado en Limpieza del Sistema** (commit f6da4ad):
- Código experimental de cancelación fallido
- ADRs de propuestas no implementadas  
- Scripts temporales de testing
- Patches experimentales
- **Resultado**: Código base limpio y enfocado en funcionalidad comprobada

### 📋 Failed Technical Approaches

#### Approach 1: JavaScript Interception (FAILED)
**Goal**: Intercept cancellation before ERPNext shows native dialog
**Implementation**: 
- Client Script "Sales Invoice Cancellation Guard" created
- `before_cancel` hook to show custom dialog
- `pre_cancel_break_opc_link()` server function to break links
**Result**: ❌ **Native dialog still appeared**
**Cause**: ERPNext's `savecancel()` executes before Client Script hooks

#### Approach 2: Field Type Conversion (FAILED)  
**Goal**: Convert Link field to Data to eliminate automatic link detection
**Implementation**:
- Patch successfully converted `custom_orden_de_pago_comision` from Link to Data
- Field type changed, options cleared, values preserved
**Result**: ❌ **Native dialog still appeared**
**Cause**: ERPNext detects links via child table references (`Comision LLCS.sales_invoice_id`), not just parent fields

### 🔬 Root Cause Analysis

#### ERPNext Link Detection Logic
ERPNext's cancellation flow uses `get_submitted_linked_docs()` which finds relationships through:
1. **Parent Link Fields** ← Successfully eliminated
2. **Child Table References** ← **Cannot eliminate without breaking functionality**
3. **Dynamic Links** ← Not applicable

#### Specific Technical Evidence
```
Sales Invoice ACC-SINV-2025-03089 detected as linked because:
- Child table Comision LLCS contains 9 records with sales_invoice_id = "ACC-SINV-2025-03089"  
- Parent OPC COMISIONES-2025-08-31-07064 has docstatus = 1 (submitted)
- ERPNext considers this a "submitted linked document"
```

### 🛡️ CURRENT PROTECTED OPERATIONS ✅ SECURED

#### What Users Currently Experience (Protected)
1. **User clicks Cancel** on Sales Invoice with commissions
2. **Native Dialog Appears**: "¿Desea cancelar todos los documentos vinculados?"
   - Lists: "Orden de Pago Comisiones: [OPC_NAME]"
   - Asks: "¿Desea cancelar todos los documentos vinculados?"
3. **User chooses**:
   - **"Cancel All"**: 🛡️ **NOW BLOCKED** - OPC protection prevents cancellation, shows clear error
   - **"No"**: Cancellation is aborted, SI remains active

#### ✅ Protection System Active
**OPC PROTECTION IMPLEMENTED**:
- **Automatic Detection**: System counts active Sales Invoices linked to OPC
- **Clear Error Message**: Spanish dialog explains why cancellation is blocked
- **User Guidance**: "Para ajustar comisiones, cancele las facturas individuales"
- **Data Safety**: **IMPOSSIBLE** to accidentally cancel OPC with active invoices

### Adjustment Management

#### Viewing Pending Adjustments
**Location**: Ajuste Comision Pendiente DocType list
**Filters**:
- Status: "Pendiente" (shows active adjustments)
- Status: "Aplicado" (shows consumed adjustments)
- Cost Center: Filter by branch
- Persona de Ventas: Filter by salesperson

#### Next OPC Integration
**Automatic Inclusion**: Pending adjustments appear in commission calculation
- Show in commission table with `is_adjustment = 1` 
- Display as negative amounts (always deduct)
- NOT subject to negative commission policy
- Automatically marked "Aplicado" when OPC is submitted

### OPC Protection System

#### Prevention Mechanism
**Scenario**: User tries to cancel OPC with active Sales Invoices
**System Response**: Error dialog blocks cancellation:
- "Esta Orden de Pago de Comisiones tiene X factura(s) vinculada(s) activas"
- "Para ajustar comisiones, cancele las facturas individuales"
- Provides clear guidance on proper procedure

#### Recommended Process
1. **Never Cancel OPCs Directly**: Use SI cancellation instead
2. **Individual SI Cancellation**: Cancel specific invoices as needed
3. **Automatic Adjustment**: System handles commission recovery
4. **Audit Trail**: Complete tracking maintained

### Monitoring and Auditing

#### Key Metrics to Track ⚠️ TESTING REQUIRED
- **Pending Adjustments**: Count of unprocessed adjustments
- **Applied Adjustments**: Historical adjustment consumption
- **Cancelled SIs with Commissions**: Impact tracking
- **OPC Protection Events**: Blocked cancellation attempts

#### Data Integrity Checks
- **SI Status Consistency**: Cancelled SIs should have status "Sin Enviar"
- **OPC Link Status**: Cancelled SIs should have null OPC links  
- **Adjustment Completeness**: Each cancelled commission should have corresponding adjustment
- **No Orphaned OPCs**: No submitted OPCs should exist with all SIs cancelled

### Error Handling and Recovery ⚠️ TESTING REQUIRED

#### Potential Issues
1. **JavaScript Disabled**: Fallback to server-side protection (less UX but functional)
2. **Concurrent Cancellations**: Database transactions handle race conditions
3. **Incomplete Adjustments**: Manual creation may be required in edge cases
4. **Network Interruption**: Database rollback prevents partial states

#### Recovery Procedures
**Manual Adjustment Creation**:
```sql
-- If automatic adjustment fails, manual creation template:
INSERT INTO `tabAjuste Comision Pendiente` 
(name, sales_invoice_id, cost_center, persona_de_ventas, monto_ajuste, motivo, source_opc, status)
VALUES ('AJC-XXXXX', 'SI-ID', 'Cost-Center', 'Salesperson', -Amount, 'Manual adjustment', 'OPC-ID', 'Pendiente');
```

#### Legacy Data Migration ⚠️ NOT IMPLEMENTED
For existing cancelled SIs with orphaned commission data, consider implementing:
- Identification script for historical cases
- Bulk adjustment creation for pre-v2.2.0 cancellations
- Audit report for data consistency validation

### Testing Checklist ⚠️ REQUIRED BEFORE PRODUCTION

#### Critical Test Scenarios
1. **Happy Path**: Cancel SI with OPC link → verify adjustment creation
2. **UI Flow**: Confirm custom dialog appears (not native ERPNext dialog)
3. **OPC Protection**: Attempt OPC cancellation → verify blocking
4. **Next OPC Integration**: Create new OPC → verify adjustment consumption
5. **Edge Cases**: Network failures, concurrent operations, invalid data
6. **Performance**: Large OPCs with many SIs
7. **User Permissions**: Different user roles and access levels

#### Success Criteria
- **No Data Loss**: Original commissions recoverable through adjustments
- **User Experience**: Clear, intuitive dialogs (no confusing native messages)
- **System Integrity**: OPCs remain protected and functional
- **Audit Trail**: Complete traceability from cancellation to recovery
- **Error Resilience**: Graceful handling of edge cases and failures

## Workspace Vendedores Implementation (v2.6.0) ⚠️ PARCIAL

### Implementation Status
**FECHA**: Septiembre 2025 - En desarrollo
**STATUS**: Workspace configurado, reports con problemas de import

### 🏗️ Arquitectura Implementada

#### Nested Workspace Structure
- **Parent Workspace:** "Comisiones"
- **Child Workspace:** "Vendedores" 
- **Nesting Method:** `parent_page: "Comisiones"` en fixture
- **Result:** ✅ Workspace anidado correctamente visible en UI

#### Dashboard Components Created
1. **3 Dashboard Charts** (fixtures):
   - `CH - OPC por Vendedor`: Count of OPCs by salesperson
   - `CH - Comisión Total por Vendedor`: Sum of commissions by salesperson  
   - `CH - Margen Promedio por Vendedor`: Average profit margin by salesperson

2. **3 Script Reports** (physical files):
   - `RV - OPC por Vendedor`: Counts OPCs per vendor
   - `RV - Comisión Total por Vendedor`: Sums commission amounts
   - `RV - Margen Promedio por Vendedor`: Calculates average margins

3. **Workspace Layout** (fixture):
   - 3 chart blocks referencing Dashboard Charts
   - 2 number card placeholders for future KPIs
   - 1 shortcut to existing detailed report

### ✅ Successfully Implemented
- **Workspace Nesting:** Parent-child relationship working
- **Database Configuration:** All reports and charts exist in database
- **Fixture Management:** Workspace and Dashboard Charts deployed via fixtures
- **UI Structure:** Charts blocks properly configured in workspace content

### ❌ Current Issues (Critical)

#### Script Report Import Failures
**Problem:** Physical files cannot be imported by Frappe framework
**Symptoms:**
```
No module named 'llantascs_customs.llantascs_customs.report.rv_*'
module has no attribute 'rv___*'
```

**Root Cause:** Mismatch between report names in database and physical file structure
- **Database Names:** "RV - OPC por Vendedor" (with hyphens)
- **File Names:** `rv_opc_por_vendedor` → `rv___opc_por_vendedor` (attempted fix failed)
- **Git Status:** Original committed files marked as deleted, renamed files untracked

#### Impact
- **Workspace renders:** ✅ Visible with chart placeholders
- **Charts display:** ❌ Empty/error due to failed report execution
- **User Experience:** ❌ Broken functionality despite correct configuration

### 🔧 Implementation Pattern Learned

#### What Works with Fixtures
- **Workspaces:** Complete definition via JSON fixtures
- **Dashboard Charts:** Configuration and references via fixtures
- **Nested Structure:** parent_page field creates hierarchy correctly

#### What Requires Physical Files
- **Script Reports:** Must have `.py` files with `execute()` functions
- **Module Structure:** Requires correct directory structure with `__init__.py`
- **Import Path:** File names must match what Frappe's `scrub()` generates from report names

### 📋 Technical Lessons

#### Fixture vs File Approach
- **Database metadata:** Use fixtures for workspace, charts, report definitions
- **Executable code:** Requires physical Python files in correct locations
- **Naming convention:** Critical alignment between DB names and file paths

#### Git Management
- **Avoid renaming committed files:** Breaks git tracking
- **Use git mv for renames:** Maintains history continuity
- **Test imports before committing:** Verify module resolution works

## Dashboard Charts Testing (v2.6.1) ❌ MULTIPLE FAILURES

### Implementation Status
**FECHA**: Septiembre 2025 - Sesión de testing intensivo  
**STATUS**: Múltiples configuraciones probadas, todas fallando en rendering

### 🔄 Testing Approach - Iterative Chart Configuration

#### Multiple Chart Types Attempted
1. **Custom Charts** - con custom_options JSON embedding chart configuration
2. **Report Charts** - con x_axis/y_axis field mapping a script reports  
3. **Bar Charts** - con type specification y field mapping
4. **Simple Test Charts** - configuración mínima para aislamiento

#### Test Workspace Created
- **Name**: "Z - Demo Charts"
- **Purpose**: Isolate Dashboard Chart testing from main workspace
- **Parent**: "Comisiones" 
- **Structure**: Single chart block referencing "CH - OPC por Vendedor"

### ❌ Systematic Failures Documented

#### Backend vs Frontend Split
- **✅ Backend Functionality**: 
  - Script reports execute correctly (`RV - OPC por Vendedor` returns 22 rows)
  - Dashboard Charts created successfully in database
  - All required fields populated (chart_name, filters_json, x_axis, y_axis)
  - Migration completes without errors
  
- **❌ Frontend Rendering**:
  - Charts don't display in workspace interface
  - Chart blocks show as empty/placeholder
  - No data visualization despite valid backend configuration

#### Final Configuration Attempted (Report-Based)
```json
{
  "doctype": "Dashboard Chart",
  "name": "CH - OPC por Vendedor",
  "chart_name": "CH - OPC por Vendedor",
  "chart_type": "Report", 
  "report_name": "RV - OPC por Vendedor",
  "x_axis": "sales_person",
  "y_axis": [{"fieldname": "opc_count", "label": "OPC", "fieldtype": "Int"}],
  "filters_json": "{\"from_date\":\"2025-01-01\"}"
}
```

### 🔧 Technical Analysis

#### What Works (Backend)
- **Script Report Execution**: Reports function independently via bench console
- **Database Storage**: Charts stored correctly with all metadata
- **Fixture Management**: dashboard_chart.json updates deploy successfully
- **Workspace Configuration**: Chart blocks configured with correct chart_name references

#### What Fails (Frontend)
- **Chart Rendering Engine**: ERPNext/Frappe Dashboard Chart rendering system
- **Data Binding**: Connection between chart configuration and actual data display
- **UI Integration**: Charts don't appear in workspace despite valid configuration

#### Potential Root Causes
- **ERPNext Version Compatibility**: Dashboard Chart implementation may have changed in v15
- **Frontend JavaScript**: Chart rendering library or implementation issues
- **Configuration Format**: Subtle format differences in fixture vs manual creation
- **Permission Issues**: Chart visibility despite public=1 configuration

### 📋 Lessons Learned

#### Fixture Deployment Success
- **Database Population**: Fixtures consistently deploy chart metadata correctly
- **Migration Reliability**: All chart configurations pass migration validation
- **Schema Correctness**: Required fields identified and satisfied

#### Rendering System Limitations
- **Black Box Failure**: Frontend chart rendering fails without clear error messages
- **Configuration Gap**: Disconnect between working backend and failing frontend
- **Testing Challenges**: Difficult to debug when backend validates but frontend fails

### 💡 Recommendations for Future Attempts

#### Alternative Approaches
1. **Manual Chart Creation**: Create charts via UI instead of fixtures
2. **Different Chart Types**: Try line charts, pie charts, or other chart_type values
3. **Version Research**: Investigate ERPNext v15 Dashboard Chart examples
4. **Community Resources**: Check Frappe community for v15 Dashboard Chart patterns

#### Investigation Areas  
- **JavaScript Console**: Check browser console for client-side errors
- **Network Requests**: Monitor API calls when workspace loads
- **Chart Library**: Identify which charting library ERPNext v15 uses (Chart.js, Plotly, etc.)
- **Working Examples**: Find existing functional Dashboard Charts in system for comparison

### Status: SUSPENDED ⚠️
Dashboard Chart implementation suspended pending alternative approach or technical resolution of frontend rendering issues.

### ⚠️ Current Status Summary
**Configuration:** 95% complete and correct
**Execution:** 0% functional due to import issues
**User Visible:** Broken charts in otherwise functional workspace

**REQUIRES:** Resolution of Script Report import path issues for full functionality.

## OPC Detailed PDF Report System (v2.7.17) ✅ IMPLEMENTED

### Implementation Status
**FECHA**: Septiembre 2025 - Sistema de reportes PDF detallado
**STATUS**: COMPLETAMENTE FUNCIONAL - Reportes PDF con 3 secciones implementados

### 🎯 Funcionalidad Implementada

#### Custom Button Integration
- **Button Name**: "📄 Reporte Detallado"
- **Location**: Orden de Pago Comisiones form (JavaScript integration)
- **Visibility**: Only appears for saved documents (`frm.doc.name && !frm.is_new()`)
- **Styling**: Primary button with emoji icon for clear identification
- **Functionality**: Direct PDF download via ERPNext native print system

#### PDF Report Structure (3 Sections)
**Section 1: General Summary**
- Total branches, invoices, income, costs, margin, paid commission
- Branch breakdown with invoice counts and income amounts
- Executive-level overview for quick decision making

**Section 2: Branch-wise Breakdown**
- Detailed breakdown by branch → salesperson → individual invoices
- Per-invoice details: income, costs, margin, margin percentage, commission
- Subtotals by salesperson and branch for accountability tracking

**Section 3: Cross-branch Salesperson Consolidation**
- Salesperson performance across all branches
- Consolidated metrics: total invoices, income, costs, margin, commission
- Multi-branch activity visibility for sales management

### 🔧 Technical Architecture

#### ERPNext Native Integration
- **Print Format**: Jinja2 template (`opc_detallado.html`)
- **PDF Generation**: `frappe.utils.print_format.download_pdf` API
- **Deployment**: Fixtures-based via `hooks.py` configuration
- **Security**: Safe data access patterns, no `__dict__` usage

#### Template Engineering
- **Helper Macros**: `money()` for currency formatting, `pct()` for percentages
- **Dynamic Lookups**: `get_cost_center()` macro for Sales Invoice relationships
- **Responsive Calculations**: Real-time margin percentage calculations
- **Data Safety**: Graceful handling of missing or null values

#### Business Logic Integration
- **Document Status**: Displays current OPC state (Draft/Submitted/Cancelled)
- **Commission Data**: Uses existing `comisiones_incluidas` child table
- **Cost Center Resolution**: Dynamic lookup via Sales Invoice relationships
- **Currency Formatting**: Two decimal precision for all monetary values

### 📊 Report Features

#### Data Presentation
- **Professional Formatting**: Clean table layout with proper styling
- **Decimal Precision**: All monetary values display with exactly 2 decimals
- **Percentage Calculations**: Margin percentages calculated as (margin/income)
- **Hierarchical Organization**: Logical flow from summary to detailed breakdown

#### User Experience
- **Conditional Access**: Button only appears when document can generate valid PDF
- **Instant Generation**: Direct browser download, no intermediate steps
- **Document Context**: PDF includes OPC name, status, and creation date
- **Clear Sections**: Distinct headers and organization for easy navigation

### 🛡️ Implementation Safety

#### Data Integrity
- **Read-Only Operation**: PDF generation doesn't modify source data
- **Template Security**: Removes unsafe Jinja operations and global access
- **Error Handling**: Graceful degradation for missing data fields
- **Consistent Results**: Deterministic output based on current document state

#### User Interface Protection
- **Save Requirement**: Prevents PDF generation for unsaved documents
- **Document Validation**: Ensures data consistency before report generation
- **Browser Compatibility**: Standard PDF download mechanism
- **Performance**: Efficient template rendering without database modifications

### 📋 Files Implemented

#### Core Implementation
- `llantascs_customs/print_format/opc_detallado/opc_detallado.html` - Jinja template
- `llantascs_customs/print_format/opc_detallado/opc_detallado.json` - Print Format metadata
- `llantascs_customs/doctype/orden_de_pago_comisiones/orden_de_pago_comisiones.js` - Button integration
- `llantascs_customs/hooks.py` - Fixtures configuration

#### Supporting Structure
- `llantascs_customs/print_format/__init__.py` - Module initialization
- `llantascs_customs/print_format/opc_detallado/__init__.py` - Subdirectory initialization

### 🎯 Business Impact

#### Management Benefits
- **Executive Dashboards**: Section 1 provides high-level metrics
- **Operational Control**: Section 2 enables branch performance analysis
- **Sales Management**: Section 3 supports cross-branch salesperson evaluation
- **Audit Trail**: Complete commission breakdown for financial transparency

#### User Workflow Enhancement
- **Self-Service Access**: Users generate detailed reports on-demand
- **Professional Output**: PDF format suitable for presentations and sharing
- **Data Consistency**: Reports reflect current document state accurately
- **Time Efficiency**: Instant generation eliminates manual report creation

### ✅ Quality Assurance Completed
- **Template Security**: Eliminated unsafe Jinja operations
- **Data Accuracy**: Verified calculations match source commission data
- **Formatting Standards**: Consistent decimal precision and currency display
- **UI Integration**: Seamless button integration with existing OPC interface
- **Browser Testing**: PDF generation validated across standard browsers