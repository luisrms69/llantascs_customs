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