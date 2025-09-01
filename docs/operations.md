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

### Commission Rate Synchronization
The "Actualizar Comisiones" button (Part 1) handles:
- **Confirmation Dialog**: Warns about data loss before proceeding
- **Table Cleanup**: Clears both `comisiones_por_sucursal` and `comisiones_incluidas`
- **Rate Sync**: Pulls global default from Comisiones Settings
- **Rebuild**: Creates 1:1 mapping between selected branches and rates
- **Total Reset**: Sets `monto_total = 0` for clean state

### Button Behavior
- **Visibility**: Only in Draft documents that are saved (`frm.doc.name && docstatus === 0`)
- **Validation**: Requires at least one branch selected in `sucursales_multi`
- **Clear+Rebuild**: Ensures perfect synchronization, no orphaned data
- **User Control**: Confirmation required, cancellation supported

### Next Phase
Upcoming "Actualizar Comisiones" button Part 2 will handle:
- Sales Invoice filtering by date range and selected branches
- Commission table generation with COGS calculation using `get_costo_ventas_si`
- Complete commission calculation workflow with totals