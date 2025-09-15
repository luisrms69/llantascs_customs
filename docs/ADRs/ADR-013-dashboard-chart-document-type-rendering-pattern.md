# ADR-013: Dashboard Chart Document Type Rendering Pattern

**Date**: 2025-09-15
**Status**: Accepted
**Context**: Dashboard chart showing data on hover but missing visual bars/lines

## Problem

Dashboard chart "Comisiones Pagadas por Mes" configured as Document Type chart was displaying data values on hover but not rendering visual elements (bars/lines). Users could see numeric values when hovering over chart area but no visual representation was shown.

## Investigation

### Root Cause Analysis
1. **Missing `type` field**: Chart configuration lacked the `type: "Bar"` field required for visual rendering
2. **Incomplete filters**: Missing standard `docstatus=1` filter in `filters_json`
3. **Non-standard configuration**: Chart didn't follow ERPNext's Document Type chart patterns

### ERPNext Standard Pattern Discovery
Analysis of working ERPNext charts (`/erpnext/setup/setup_wizard/data/dashboard_charts.py`) revealed consistent pattern:

```json
{
  "chart_type": "Sum",
  "document_type": "[DocType]",
  "based_on": "[date_field]",
  "value_based_on": "[amount_field]",
  "timeseries": 1,
  "time_interval": "Monthly",
  "timespan": "Last Year",
  "type": "Bar",                                          // CRITICAL: Missing in our chart
  "filters_json": "[[\"[DocType]\",\"docstatus\",\"=\",1]]", // CRITICAL: Missing in our chart
  "color": "#7b933d"                                      // RECOMMENDED: For consistency
}
```

## Decision

Implement complete ERPNext Document Type chart pattern with all required fields:

### Required Fields Added
- **`type: "Bar"`**: Essential for visual rendering engine
- **`filters_json: [["Orden de Pago Comisiones","docstatus","=","1",false]]`**: Standard docstatus filter
- **`color: "#7b933d"`**: Visual consistency with ERPNext standards

### Configuration Improvements
- **`chart_name`**: "comisiones_pagadas_por_mes" → "Comisiones Pagadas por Mes" (UX)
- **`timespan`**: "This Year" → "Last Year" (historical data access)
- **Removed**: Empty `source` field (not needed for Document Type charts)

## Implementation

### Files Modified
- `llantascs_customs/fixtures/dashboard_chart.json`
  - Applied complete ERPNext Document Type pattern
  - Fixed missing visualization fields
  - Improved UX elements

### Deployment Method
- Used standard `bench migrate` to apply fixture changes
- No custom patches required for configuration changes

## Consequences

### Positive
- **Complete visualization**: Chart now renders bars for all months with data
- **Standard compliance**: Follows ERPNext patterns exactly
- **Future-proof**: Configuration compatible with ERPNext upgrades
- **Improved UX**: Clean labels without underscores
- **Consistent filtering**: Only shows submitted (docstatus=1) records

### Pattern for Future Charts
This ADR establishes the pattern for all future Document Type dashboard charts:

1. **Always include `type` field**: Required for visual rendering
2. **Always filter `docstatus=1`**: Standard practice for Document Type charts
3. **Use `timespan: "Last Year"`**: Better historical data access than "This Year"
4. **Include `color` field**: Visual consistency
5. **Clean `chart_name`**: User-friendly display names

### Risk Mitigation
- Zero risk: Changes are fixture-based configuration updates
- Backwards compatible: Existing data unaffected
- Standard patterns: Reduces maintenance burden

## References

- ERPNext standard charts: `/erpnext/setup/setup_wizard/data/dashboard_charts.py`
- Working examples: "Outgoing Bills (Sales Invoice)", "Delivery Trends"
- ERPNext documentation: Dashboard Chart configuration patterns