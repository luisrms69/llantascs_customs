# ADR-014: Cleanup Legacy Reports and Role-Based Permissions

**Date**: 2025-09-15
**Status**: Accepted
**Context**: Multiple confusing backlog reports + open permissions without role restrictions

## Problem

### Legacy Reports Confusion
1. **Three similar reports**: "Backlog Comisiones", "Backlog Comisiones Completo", "Backlog Comisiones GP nativo"
2. **User confusion**: Multiple options for same functionality in workspace
3. **Maintenance burden**: Three codebases for essentially same feature
4. **UI clutter**: Workspace header "Backlog" showing 3 reports

### Security Permissions Issue
1. **Open access**: All commission reports visible to all users
2. **No role restrictions**: "Accounts User" had access to commission data
3. **Data exposure**: Employees could see all commission data, not just their own
4. **Compliance risk**: No user-level filtering on personal commission reports

## Investigation

### Report Analysis
- **Backlog Comisiones GP nativo**: Uses native Gross Profit calculation (current, accurate)
- **Backlog Comisiones Completo**: Legacy SQL-based margin calculation (outdated)
- **Backlog Comisiones**: Filtered version of Completo with cost center/sales person filters

### Permission Review
- All reports had broad access across multiple roles
- "Mis Comisiones" was restricted to management roles instead of being user-filtered
- No differentiation between internal roles and general employees

## Decision

### Complete Legacy Cleanup
**Remove entirely**:
- "Backlog Comisiones Completo"
- "Backlog Comisiones"

**Keep only**:
- "Backlog Comisiones GP nativo" (most accurate, native ERPNext calculations)

### Implement Role-Based Permissions
**Internal roles** (System Manager, Llantas CS Manager, Llantas CS User):
- Full access to all commission reports
- Management and analytical capabilities

**Employee role**:
- Access only to "Mis Comisiones"
- Data filtered to show only their own commission records
- No access to other commission reports

**Removed access**:
- "Accounts User" role removed from all commission reports

## Implementation

### Database Cleanup
```python
# Removed via one_offs script
targets = ["Backlog Comisiones Completo", "Backlog Comisiones"]
- frappe.db.delete("Prepared Report", {"report_name": ["in", targets]})
- frappe.delete_doc("Report", r, force=1) for each target
```

### Fixtures Updates
- **workspace.json**: Removed legacy shortcuts, added Employee role
- **report.json**: Removed legacy report definitions, updated permissions
- **mis_comisiones_backlog.json**: Changed from manager-only to Employee + System Manager

### Permission Matrix
| Report | System Manager | Llantas CS Manager | Llantas CS User | Employee |
|--------|---------------|-------------------|-----------------|----------|
| Backlog Comisiones GP nativo | ✅ | ✅ | ✅ | ❌ |
| Pagos OPC - Por Sucursal | ✅ | ✅ | ✅ | ❌ |
| Pagos OPC - Resumen | ✅ | ✅ | ✅ | ❌ |
| Mis Comisiones Backlog | ✅ | ❌ | ❌ | ✅ (filtered) |

## Consequences

### Positive
- **Simplified UX**: Only 1 Backlog report in workspace (was 3)
- **Security compliance**: Role-based access control implemented
- **Data protection**: Employees see only their own commission data
- **Reduced maintenance**: Single backlog report codebase
- **Consistent permissions**: Standardized across all commission reports

### Operational Impact
- **Training needed**: Users must adapt to single Backlog report option
- **Access changes**: "Accounts User" roles lose commission report access
- **Employee workflow**: Direct access to personal commissions via "Mis Comisiones"

### Technical Benefits
- **Database cleanup**: Removed orphaned reports and prepared reports
- **Fixture simplification**: Reduced JSON maintenance burden
- **Clear separation**: Internal reports vs employee-accessible reports

## Verification

### Post-cleanup Validation
- ✅ Only "Backlog Comisiones GP nativo" appears in workspace Backlog header
- ✅ Legacy report URLs return 404 (properly removed from system)
- ✅ Database queries confirm zero legacy reports remaining
- ✅ Employee role can access workspace and see only "Mis Comisiones"
- ✅ Internal roles maintain full access to restricted reports

### Security Testing
- Employees cannot access management commission reports
- "Mis Comisiones" shows only user-specific data when accessed by Employee role
- System Manager retains full administrative access

## References

- Original cleanup proposal: ChatGPT controlled elimination plan
- Permission implementation: ERPNext standard role-based access patterns
- User filtering: Frappe framework user session filtering capabilities