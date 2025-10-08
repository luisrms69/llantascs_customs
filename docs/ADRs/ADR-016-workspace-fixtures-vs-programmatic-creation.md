# ADR-016: Workspace Creation Using Fixtures vs Programmatic Approach

**Status**: Accepted
**Date**: 2025-10-07
**Deciders**: Development Team
**Context**: Cockpit Phase 1 - Executive Dashboards Implementation

---

## Context and Problem Statement

During the implementation of Cockpit Phase 1 (Executive Dashboards for Dirección General), we faced a fundamental architectural decision: how to create and distribute Workspace configurations in Frappe/ERPNext.

**Initial Approach**: ChatGPT v3 proposal suggested programmatic creation using Python code with CLI commands, similar to Django management commands.

**Problem Discovered**: After implementing 570 lines of Python code (commit ed817e0), we discovered that existing workspace "Comisiones" was created using fixtures JSON, not Python code. This raised the question: what is the correct Frappe pattern?

## Decision Drivers

1. **Frappe Framework Standards**: Follow framework's intended patterns
2. **Portability**: Must work across development, staging, and production sites
3. **Maintainability**: Easy to version control and review changes
4. **Migration Safety**: Survive `bench migrate` operations without manual intervention
5. **Team Knowledge**: Align with existing implementation patterns in codebase

## Options Considered

### Option 1: Programmatic Creation (Python Code)

**Implementation**:
```python
# llantascs_customs/cockpit/builders.py
def create_workspace_direccion_general():
    workspace = frappe.get_doc({
        "doctype": "Workspace",
        "name": "Direccion General",
        "title": "Dirección General",
        # ... 200+ lines of configuration
    })
    workspace.insert()
```

**Execution**: `bench --site SITENAME execute llantascs_customs.cockpit.install.install_all`

**Pros**:
- ✅ Familiar to developers from Django/Rails backgrounds
- ✅ Can include complex logic and validation
- ✅ Easy to add conditional behavior per environment

**Cons**:
- ❌ Not idempotent (requires manual checks for existing docs)
- ❌ Requires manual execution on every site
- ❌ Not integrated with `bench migrate` workflow
- ❌ Difficult to version control (procedural code vs declarative JSON)
- ❌ **CRITICAL**: Not the Frappe standard pattern

### Option 2: Fixtures JSON (Declarative Configuration)

**Implementation**:
```json
// llantascs_customs/fixtures/workspace.json
[
  {
    "doctype": "Workspace",
    "name": "Direccion General",
    "title": "Dirección General",
    "number_cards": [...],
    "charts": [...],
    "shortcuts": [...]
  }
]
```

**Execution**: Automatic during `bench migrate`

**Pros**:
- ✅ **Frappe standard pattern** (confirmed by existing "Comisiones" workspace)
- ✅ Automatic installation via `bench migrate`
- ✅ Declarative and easy to review in version control
- ✅ Idempotent (migrate handles updates automatically)
- ✅ Works across all sites without manual intervention
- ✅ Integrated with Frappe's fixture export/import system

**Cons**:
- ❌ Limited to static configuration (no complex logic)
- ❌ Requires understanding of child table structure (parent/parentfield/parenttype)
- ❌ JSON escaping can be complex for nested content

## Decision Outcome

**Chosen Option: Option 2 - Fixtures JSON**

### Rationale

1. **Framework Alignment**: Frappe documentation and existing codebase confirm fixtures as the standard pattern for distributing DocType configurations.

2. **Evidence from Codebase**: Workspace "Comisiones" (existing in this app) uses fixtures JSON, not Python code.

3. **Migrate Integration**: `bench migrate` automatically installs/updates fixtures, making deployment trivial.

4. **Version Control**: JSON fixtures are declarative and easy to diff/review in pull requests.

5. **Portability**: Works identically across dev/staging/prod without manual intervention.

### Implementation Changes

**Removed** (commit 6f8f0ff):
- `llantascs_customs/cockpit/__init__.py`
- `llantascs_customs/cockpit/builders.py` (200 lines)
- `llantascs_customs/cockpit/constants.py` (250 lines)
- `llantascs_customs/cockpit/bundles.py` (20 lines)
- `llantascs_customs/cockpit/install.py` (60 lines)
- `llantascs_customs/commands.py` (40 lines)

**Total**: 570 lines of Python code deleted

**Created**:
- `llantascs_customs/fixtures/number_card.json` (4 cards)
- Updated `llantascs_customs/fixtures/dashboard_chart.json` (+2 charts)
- Updated `llantascs_customs/fixtures/workspace.json` (+2 workspaces)
- Updated `llantascs_customs/hooks.py` (fixture filters)

**Total**: ~400 lines of declarative JSON

### Consequences

**Positive**:
- ✅ Automatic deployment via standard `bench migrate`
- ✅ Idempotent (can re-run migrate safely)
- ✅ Easy to review changes in version control
- ✅ Follows Frappe best practices
- ✅ Works across all environments without manual steps

**Negative**:
- ⚠️ Requires understanding of Frappe fixture structure
- ⚠️ JSON escaping for nested content can be tricky
- ⚠️ Limited to declarative configuration (no runtime logic)

**Neutral**:
- 📝 Need to document fixture patterns for team
- 📝 Export fixtures from UI when testing new configurations

## Technical Details

### Fixture Structure

**Number Cards**:
```json
{
  "doctype": "Number Card",
  "name": "Ventas del Mes",
  "type": "Document Type",
  "document_type": "Sales Invoice",
  "function": "Sum",
  "aggregate_function_based_on": "base_net_total",
  "filters_json": "[[...]]",
  "is_public": 1
}
```

**Dashboard Charts**:
```json
{
  "doctype": "Dashboard Chart",
  "name": "chart_dg_sales_by_branch_12m",
  "chart_type": "Report",
  "report_name": "Sales Analytics",
  "filters_json": "{...}",
  "is_public": 1
}
```

**Workspace**:
```json
{
  "doctype": "Workspace",
  "name": "Direccion General",
  "parent_page": "Cockpit",
  "number_cards": [
    {
      "number_card_name": "Ventas del Mes",
      "parent": "Direccion General",
      "parentfield": "number_cards",
      "parenttype": "Workspace"
    }
  ],
  "content": "[{...}]"
}
```

### Hooks Configuration

```python
# hooks.py
fixtures = [
    {"doctype": "Workspace", "filters": [["name", "in", ["Cockpit", "Direccion General"]]]},
    {"doctype": "Dashboard Chart", "filters": [["name", "in", ["chart_dg_sales_by_branch_12m", ...]]]},
    {"doctype": "Number Card", "filters": [["name", "in", ["Ventas del Mes", ...]]]}
]
```

### Deployment Workflow

1. **Development**: Create/modify fixtures JSON
2. **Version Control**: Commit fixtures to git
3. **Staging/Production**: `git pull && bench migrate`
4. **Result**: Workspaces, charts, and cards automatically installed/updated

## Lessons Learned

1. **Always Check Existing Patterns First**: Before implementing, search codebase for similar functionality.

2. **Fixtures are the Standard**: For DocType configurations (Workspace, Dashboard Chart, Number Card, Report, etc.), use fixtures JSON.

3. **When to Use Python**:
   - Business logic (commission calculation, COGS resolution)
   - Data migrations (one-off backfills)
   - API endpoints
   - Custom validations

4. **When to Use Fixtures**:
   - Workspace configurations
   - Dashboard Charts and Number Cards
   - Custom Fields
   - Reports (structure, not data)
   - Roles and permissions
   - Any DocType configuration that needs to be distributed

5. **Export from UI**: Frappe provides export functionality for most DocTypes - use it to generate fixture templates.

## Related Decisions

- Number Cards type "Document Type" vs "Report" (Frappe v15 limitation)
- Spanish names as primary key for UI display
- Workspace parent-child hierarchy for Cockpit structure

## References

- **Frappe Documentation**: [Fixtures](https://frappeframework.com/docs/user/en/basics/doctypes/fixtures)
- **Commit History**:
  - ed817e0: Initial Python implementation (removed)
  - 6f8f0ff: Refactor to fixtures
  - This commit: Final fixture-based implementation
- **Related ADRs**: ADR-012 (Dashboard Charts), ADR-013 (Document Type rendering)

## Notes

This decision was made after implementing the wrong approach, which provided valuable learning. The 570 lines of Python code served as a "spike" to understand the problem domain before discovering the correct pattern.

**Key Takeaway**: In Frappe/ERPNext, declarative fixtures are preferred over procedural code for distributing configurations.
