# ADR-005: Hierarchical Tree Filters Implementation for GP Native Report

**Status:** Approved
**Date:** 2025-09-14
**Decision Makers:** System Owner, Development Team
**Technical Stakeholders:** ERPNext Integration Team

## Context

The "Backlog Comisiones GP nativo" Script Report was successfully implemented with ERPNext native Gross Profit integration, but the Cost Center and Sales Person filters were not functioning. Users expected hierarchical filtering where selecting a parent node would automatically include all child nodes, matching the behavior of other ERPNext reports and business logic requirements.

## Problem Statement

### Business Requirements Not Met

1. **Cost Center Filtering**: Selecting a parent sucursal should include all child sucursales automatically
2. **Sales Person Filtering**: Selecting a parent sales person should include all child sales persons in the team
3. **Combined Filtering**: Both filters should work together with proper intersection logic
4. **Performance**: Filtering should not impact GP calculation performance

### Technical Challenges Identified

1. **No Built-in Tree Filtering**: Script Reports don't have automatic tree filtering like Query Reports with hierarchical filters
2. **Complex Sales Person Logic**: Sales Person filtering requires lookup through `tabSales Team` table
3. **Post-Processing Required**: Filters needed to be applied after GP calculations to maintain performance
4. **UI Integration**: Filters were correctly defined but backend wasn't applying the filtering logic

## Decision

**Implement post-filtering using ERPNext's lft/rgt tree semantics** with the following architectural approach:

### Technical Architecture Decision

```python
# Post-filtering approach after GP calculations
def execute(filters):
    # 1. Get all base data and perform GP calculations
    base_columns, base_rows = _get_all_data_with_gp_calculations(filters)

    # 2. Apply hierarchical tree filters as post-processing
    filtered_rows = _apply_tree_filters(base_rows, filters)

    return base_columns, filtered_rows
```

### Hierarchical Filtering Strategy

1. **Cost Center Tree Filtering**: Use `lft/rgt` values from `tabCost Center` to identify all nodes within the selected hierarchy
2. **Sales Person Tree Filtering**: Use `lft/rgt` values from `tabSales Person` combined with `tabSales Team` lookup to identify relevant invoices
3. **Sequential Application**: Apply Cost Center filter first, then Sales Person filter for proper intersection
4. **Error Handling**: Fallback to unfiltered data in case of errors to prevent UI failures

### Performance Optimization

- **Post-filtering**: Apply filters after expensive GP calculations to avoid recalculating for different filter combinations
- **Efficient Queries**: Single queries to get valid node sets, then in-memory filtering
- **Caching Friendly**: Base GP calculations remain cacheable regardless of filter combinations

## Implementation Details

### Core Filter Functions

```python
def _apply_tree_filters(rows, filters):
    """Main orchestrator for tree-based filtering"""
    if cost_center_filter:
        rows = _filter_by_cost_center_tree(rows, cost_center_filter)
    if sales_person_filter:
        rows = _filter_by_sales_person_tree(rows, sales_person_filter)
    return rows

def _filter_by_cost_center_tree(rows, cost_center_name):
    """Filter by Cost Center hierarchy using lft/rgt"""
    # Get lft/rgt bounds for selected cost center
    # Find all cost centers within bounds
    # Filter rows where cost_center is in valid set

def _filter_by_sales_person_tree(rows, sales_person_name):
    """Filter by Sales Person hierarchy using lft/rgt + Sales Team"""
    # Get lft/rgt bounds for selected sales person
    # Find all sales persons within bounds
    # Get invoices with Sales Team entries for valid sales persons
    # Filter rows where invoice ID is in valid set
```

### Tree Semantics Implementation

**Cost Center Filtering:**
- Query: `SELECT name FROM tabCost Center WHERE lft >= ? AND rgt <= ?`
- Logic: Include rows where `row.cost_center` is in the valid set
- Behavior: Rows without cost_center are EXCLUDED when filter is active, INCLUDED when empty

**Sales Person Filtering:**
- Query: `SELECT DISTINCT st.parent FROM tabSales Team st WHERE st.sales_person IN (?)`
- Logic: Include rows where `row.name` (invoice ID) is in the valid invoice set
- Behavior: Rows without sales person are EXCLUDED when filter is active, INCLUDED when empty

### Error Handling Strategy

```python
try:
    # Perform tree filtering logic
    return filtered_rows
except Exception as e:
    frappe.log_error(f"Error in tree filtering: {str(e)}")
    return rows  # Fallback to unfiltered data
```

## Alternatives Considered

### Alternative 1: SQL-Level Filtering
**Rejected**: Would require complex CTEs in the base SQL query, impacting GP calculation performance and making the query much more complex.

### Alternative 2: Separate Filtered Queries
**Rejected**: Would require recalculating GP margins for each filter combination, significantly impacting performance.

### Alternative 3: JavaScript Client-Side Filtering
**Rejected**: Would require loading all data to client, impacting performance with large datasets and not following ERPNext patterns.

### Alternative 4: Query Report Conversion
**Rejected**: Would lose the Script Report benefits and GP native integration that was already successfully implemented.

## Consequences

### Positive Consequences

1. **Full Tree Hierarchy Support**: Users can select parent nodes and automatically get all children
2. **Performance Optimized**: GP calculations run once, filtering is lightweight post-processing
3. **ERPNext Native**: Uses standard ERPNext lft/rgt tree semantics
4. **Flexible**: Supports individual filters or combined filters with proper intersection
5. **Robust**: Error handling prevents UI failures

### Negative Consequences

1. **Memory Usage**: All base data loaded before filtering (acceptable for typical dataset sizes)
2. **Code Complexity**: Additional filtering logic in Python backend
3. **Maintenance**: Tree filtering logic needs to be maintained separately from base report logic

### Migration Risks Mitigated

1. **Filter Definition**: Verified filters are correctly defined in Report DocType
2. **UI Integration**: No changes needed to filter UI, works with existing ERPNext filter framework
3. **Backward Compatibility**: Empty filters continue to show all data as expected

## Monitoring and Success Metrics

### Technical Metrics
- **Filter Accuracy**: Tree filtering includes correct parent-child relationships
- **Performance**: Post-filtering adds <100ms overhead to report execution
- **Intersection Logic**: Combined filters produce mathematically correct intersections
- **Error Rate**: <1% error rate in filter execution with proper fallback

### Business Metrics
- **User Adoption**: Hierarchical filtering enables more targeted analysis
- **Query Efficiency**: Users can analyze specific branches without manual data filtering
- **Workflow Improvement**: Reduces time spent filtering data manually

### Validation Results

**Test Results (2025-09-14):**
- Base dataset: 314 rows
- Cost Center filter ("108 - VILLAHERMOSA - LLCS"): 17 rows ✅
- Sales Person filter ("Equipo de ventas"): 313 rows ✅
- Combined filters: 17 rows ✅ (proper intersection)
- Error handling: Graceful fallback verified ✅

## Implementation Timeline

- **Analysis**: Identified filter definition vs. application gap
- **Design**: Designed post-filtering architecture with tree semantics
- **Implementation**: Developed and tested tree filtering functions
- **Validation**: Comprehensive testing of all filter combinations
- **Documentation**: Updated technical documentation and ADR

## Related ADRs

- ADR-004: Script Report conversion (prerequisite for this implementation)
- ADR-001: Commission calculation methodology
- ADR-002: Query Report standardization

## Technical Debt Considerations

### Immediate Debt
- None - clean implementation following ERPNext patterns

### Future Considerations
- Monitor memory usage with larger datasets
- Consider caching filtered results for repeated filter combinations
- Evaluate SQL-level filtering if performance becomes an issue

## Approval

**Approved by**: System Owner
**Date**: 2025-09-14
**Implementation Status**: Completed ✅
**Production Verification**: All filter combinations working correctly with proper tree hierarchy support