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

### Next Phase
Upcoming "Actualizar Comisiones" button will handle:
- Commission rate synchronization from Comisiones Settings
- Commission table generation with COGS calculation using `get_costo_ventas_si`
- Complete commission calculation workflow