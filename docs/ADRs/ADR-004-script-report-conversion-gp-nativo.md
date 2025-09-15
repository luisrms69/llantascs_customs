# ADR-004: Query Report to Script Report Conversion for GP Nativo Implementation

**Status:** Approved
**Date:** 2025-09-14
**Decision Makers:** System Owner, Development Team
**Technical Stakeholders:** ERPNext Integration Team

## Context

The "Backlog Comisiones GP nativo" report was initially implemented as a Query Report skeleton in Phase 1, designed to eventually integrate with ERPNext's native Gross Profit methodology. However, ERPNext's native Gross Profit functionality is only accessible through Python API calls, not through SQL queries, necessitating a conversion to Script Report architecture.

## Problem Statement

### Technical Limitations Identified

1. **ERPNext GP API Access**: Native Gross Profit calculations require Python function calls to `erpnext.accounts.report.gross_profit.gross_profit.execute()`
2. **Query Report Constraints**: Query Reports are limited to SQL-only operations, cannot invoke Python APIs during execution
3. **Data Integration Requirements**: Need to merge base commission data with dynamically calculated GP margins from ERPNext native algorithms
4. **Caching Issues**: Initial implementation suffered from prepared report caching serving stale/empty data

### Business Requirements

- Maintain all existing columns from "Backlog Comisiones Completo"
- Add new column "Margen Sucursal 6m (GP nativo)" using ERPNext official algorithms
- Preserve existing filter functionality (from_date, to_date, cost_center, sales_person)
- Ensure no performance degradation from Query Report baseline
- Maintain workspace integration as first item in "Backlog" section

## Decision

**Convert "Backlog Comisiones GP nativo" from Query Report to Script Report** with the following architectural changes:

### Technical Architecture Decision

```python
# FROM: Query Report (SQL-only)
{
  "report_type": "Query Report",
  "query": "SELECT 'En desarrollo - Fase 1 completada' as \"Estado:Data:300\"",
  "report_script": null
}

# TO: Script Report (Python backend)
{
  "report_type": "Script Report",
  "query": null,
  "report_script": "llantascs_customs.llantascs_customs.report.backlog_comisiones_gp_nativo.backlog_comisiones_gp_nativo"
}
```

### Backend Implementation Strategy

1. **Data Source Integration**: Invoke existing "Backlog Comisiones Completo" Query Report for base data
2. **GP Native Integration**: Call ERPNext standard `gross_profit.execute()` with 6-month lookback
3. **Margin Calculation**: Compute weighted average GP margins by cost center tree hierarchy
4. **Data Merging**: Combine base commission data with calculated GP margins
5. **Response Format**: Return `(columns, data)` tuple compatible with ERPNext Script Report framework

### Caching Strategy Decision

```python
# Critical Configuration
{
  "prepared_report": 0  # Disable caching for fresh data queries
}
```

**Rationale**: Prepared report caching proved problematic during implementation, serving stale/empty data when fixture vs database values were misaligned. Fresh queries ensure data consistency.

## Implementation Details

### Core Function Signature

```python
def execute(filters=None):
    """
    Main Script Report execution function

    Args:
        filters (dict, optional): Report filters from UI

    Returns:
        tuple: (columns, data) for ERPNext framework
    """
```

### ERPNext Integration Pattern

```python
from erpnext.accounts.report.gross_profit.gross_profit import execute as gp_execute

# Invoke native ERPNext report
gp_filters = {
    "company": "Llantas de Calidad Star, S.A. de C.V.",
    "from_date": six_months_ago,
    "to_date": filters.get("to_date")
}
gp_columns, gp_data = gp_execute(gp_filters)
```

### Data Structure Decisions

**Column Mapping Strategy:**
- Exact SQL key mapping required: `"Factura:Link/Sales Invoice:160"` vs `"Factura"`
- All base columns inherited from "Backlog Comisiones Completo"
- New column: `"Margen Sucursal 6m (GP nativo):Percent:130"`

**Filter Compatibility:**
- Maintain identical filter structure as Query Report
- All filters optional (no mandatory constraints)
- Direct pass-through to base report for consistency

## Alternatives Considered

### Alternative 1: Custom DocType with Background Jobs
**Rejected**: Overhead of creating new DocType, managing scheduled jobs, and maintaining cache tables deemed excessive for reporting requirement.

### Alternative 2: Pure SQL with GL Entry Analysis
**Rejected**: Would replicate ERPNext GP logic in custom SQL, creating maintenance burden and divergence from official algorithms.

### Alternative 3: Hybrid Query Report with Custom Fields
**Rejected**: Query Reports cannot invoke Python APIs during execution, fundamental technical limitation.

### Alternative 4: JavaScript Client-Side Calculations
**Rejected**: Performance concerns with large datasets and complexity of replicating GP algorithms in JavaScript.

## Consequences

### Positive Consequences

1. **Native ERPNext Integration**: Leverages official GP algorithms, ensuring compatibility with ERPNext updates
2. **Maintainability**: No custom GP logic to maintain, follows ERPNext standard patterns
3. **Flexibility**: Python backend allows future enhancements and complex calculations
4. **Performance**: Direct API calls more efficient than recreating GP logic
5. **Consistency**: Margins calculated using same methodology as other ERPNext reports

### Negative Consequences

1. **Complexity**: Script Reports more complex than Query Reports, require Python maintenance
2. **Dependencies**: Tight coupling with ERPNext GP report API, affected by core changes
3. **Development Overhead**: Backend Python code vs pure SQL approach
4. **Testing Burden**: Must test both data integration and GP calculation accuracy

### Migration Risks Mitigated

1. **Fixture Synchronization**: Implemented verification of prepared_report fixture → database sync
2. **Cache Invalidation**: Established clear cache purging procedures for prepared reports
3. **SQL Key Mapping**: Documented exact key mapping requirements for data display
4. **Filter Compatibility**: Preserved all existing filter functionality

## Monitoring and Success Metrics

### Technical Metrics
- **Data Accuracy**: GP margins within ±1% of native ERPNext GP report
- **Performance**: Report execution time <10 seconds for typical dataset (500-1000 rows)
- **Cache Efficiency**: 0 stale cache issues with prepared_report=0 configuration
- **Filter Functionality**: All 4 filters (from_date, to_date, cost_center, sales_person) working correctly

### Business Metrics
- **User Adoption**: Positioned as first item in workspace "Backlog" section
- **Comparative Analysis**: Enable comparison between GL methodology vs GP native
- **Commission Planning**: Support enhanced commission calculation validation

## Implementation Timeline

- **Phase 1 (Completed)**: Query Report skeleton with workspace integration
- **Phase 2 (Completed)**: Script Report conversion with GP integration
- **Phase 3 (Future)**: Performance optimization and advanced GP features

## Related ADRs

- ADR-001: Commission calculation methodology (GL-based approach)
- ADR-002: Query Report standardization for commission backlog
- ADR-003: Workspace organization and user experience

## Technical Debt Considerations

### Immediate Debt
- None - clean implementation with proper ERPNext integration patterns

### Future Debt Prevention
- Regular testing of ERPNext GP API compatibility
- Monitoring for ERPNext core changes affecting GP report structure
- Documentation maintenance for backend Python logic

## Approval

**Approved by**: System Owner
**Date**: 2025-09-14
**Implementation Status**: Completed ✅
**Production Verification**: 707 rows displaying correctly with all 13 columns functional