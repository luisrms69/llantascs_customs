# ADR-012: Document Type Charts Using ERPNext Native Patterns

**Status**: ✅ Accepted
**Date**: 2025-09-15
**Context**: Implementation of monthly commissions chart in workspace

## Context

Need to display monthly commission data in Comisiones workspace. Initial attempts using ChatGPT's "Document Type" configuration patterns failed with `TypeError: '<=' not supported between instances of 'NoneType' and 'datetime.date'`.

## Problem

Dashboard Charts for Document Types were failing due to:
1. Incorrect field naming (`data_source` vs `source`, `time_series` vs `timeseries`)
2. Wrong chart type configuration (`chart_type: "Bar"` with `source: "Document Type"`)
3. Improper field assignment (`based_on` using numeric field instead of date field)

## Research & Discovery

Investigation of existing functional ERPNext charts revealed correct patterns:

### Working Examples Analyzed:
- "Outgoing Bills (Sales Invoice)"
- "Incoming Bills (Purchase Invoice)"
- "Ventas Diarias"
- "Won Opportunities"

### Pattern Identified:
```json
{
  "chart_type": "Sum",      // NOT "Bar"
  "source": "",             // Empty, NOT "Document Type"
  "document_type": "DocType Name",
  "based_on": "date_field", // Date field for grouping
  "value_based_on": "numeric_field", // Numeric field for aggregation
  "timeseries": 1,          // Boolean, NOT text field
  "time_interval": "Monthly"
}
```

## Decision

**ADOPTED**: Use ERPNext native Document Type chart patterns exactly as implemented in core ERPNext charts.

### Implementation:
```json
{
  "chart_type": "Sum",
  "source": "",
  "document_type": "Orden de Pago Comisiones",
  "based_on": "hasta_fecha",
  "value_based_on": "monto_total",
  "timeseries": 1,
  "time_interval": "Monthly",
  "timespan": "This Year"
}
```

## Consequences

### ✅ Positive:
- **Functional**: Chart works without errors
- **Maintainable**: Follows ERPNext core patterns, less likely to break in updates
- **Reproducible**: Same patterns work across different ERPNext instances
- **Documented**: Clear guidance for future Document Type charts

### ⚠️ Considerations:
- **Data Quality**: Chart shows correct structure but some `monto_total` values are zero (pre-migration data issue, to be addressed via separate patch)
- **Field Dependency**: Relies on `hasta_fecha` being populated in all OPC documents

## Lessons for Future Document Type Charts

### ✅ DO:
- Use `chart_type: "Sum"` for Document Type aggregations
- Leave `source` empty (`""`)
- Use date field in `based_on` for time series
- Use numeric field in `value_based_on` for aggregation
- Set `timeseries: 1` (boolean) for time-based charts

### ❌ DON'T:
- Mix `chart_type: "Bar"` with Document Type source
- Put field names in wrong configuration keys
- Use ChatGPT patterns without validating against working ERPNext examples
- Assume field names without checking DocType meta

## Implementation Files

- **Chart Definition**: `fixtures/dashboard_chart.json`
- **Workspace Integration**: `fixtures/workspace.json`
- **Fixture Config**: `hooks.py`
- **Documentation**: `docs/dashboard-charts.md`