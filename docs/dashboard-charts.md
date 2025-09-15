# Dashboard Charts Implementation Guide

## Resumen

Este documento describe la implementación correcta de Dashboard Charts en ERPNext v15, incluyendo la solución al problema crítico de charts que desaparecían después de migrate operations.

## Problema Resuelto

### Root Cause Identificado
- **Problema**: Dashboard Charts funcionaban desde UI pero desaparecían sistemáticamente al ejecutar `bench migrate`
- **Causa Root**: `migrate` sobrescribe workspaces completamente usando fixtures, eliminando configuración manual
- **Solución**: Fixtures completos que incluyen TODAS las referencias necesarias

## Arquitectura de Dashboard Charts

### Componentes Requeridos

#### 1. Dashboard Chart DocType
**Ubicación**: `fixtures/dashboard_chart.json`

**Campos Obligatorios**:
- `chart_name`: Nombre interno del chart (diferente de `name`)
- `filters_json`: JSON de filtros (mínimo `"{}"`)
- `is_public`: 1 (requerido para visibilidad)
- `x_field`: Campo X del script report (NO `x_axis`)
- `chart_type`: "Report" para charts basados en Script Reports
- `type`: Tipo de gráfico ("Bar", "Line", etc.)

**Child Tables Requeridas**:
- `y_axis`: Configuración de ejes Y con estructura parent/parentfield/parenttype

### 2. Document Type Charts (Nuevo)

**Implementación**: Charts basados directamente en DocTypes (sin Script Report intermedio)

**Configuración Correcta**:
```json
{
  "chart_type": "Sum",
  "source": "",
  "document_type": "Orden de Pago Comisiones",
  "based_on": "hasta_fecha",
  "value_based_on": "monto_total",
  "timeseries": 1,
  "time_interval": "Monthly"
}
```

**Campos Críticos**:
- `chart_type`: "Sum" (NO "Bar" para Document Type)
- `source`: "" (vacío, NO "Document Type")
- `based_on`: Campo de fecha para agrupación temporal
- `value_based_on`: Campo numérico para agregación
- `timeseries`: 1 para habilitar series temporales
- `roles`: Roles con acceso al chart, incluyendo `idx` para ordering

#### 2. Workspace Integration
**Ubicación**: `fixtures/workspace.json`

**Elementos Críticos**:
- `charts` child table: Lista de charts del workspace
- `content` JSON: Referencias a charts en layout

**CRÍTICO**: Ambas referencias deben usar el mismo `chart_name`

## Implementación Paso a Paso

### Paso 1: Crear Dashboard Chart Fixture

```json
{
  "doctype": "Dashboard Chart",
  "name": "CH - OPC por Vendedor",
  "chart_name": "CH - OPC por Vendedor", 
  "title": "OPC por Vendedor",
  "chart_type": "Report",
  "type": "Bar",
  "report_name": "RV - OPC por Vendedor",
  "is_public": 1,
  "x_field": "sales_person",
  "filters_json": "{}",
  "y_axis": [
    {
      "y_field": "opc_count",
      "label": "OPC", 
      "parent": "CH - OPC por Vendedor",
      "parentfield": "y_axis",
      "parenttype": "Dashboard Chart"
    }
  ],
  "roles": [
    {
      "role": "System Manager",
      "parent": "CH - OPC por Vendedor",
      "parentfield": "roles", 
      "parenttype": "Dashboard Chart",
      "idx": 1
    },
    {
      "role": "Llantas CS User",
      "parent": "CH - OPC por Vendedor", 
      "parentfield": "roles",
      "parenttype": "Dashboard Chart",
      "idx": 2
    },
    {
      "role": "Llantas CS Manager",
      "parent": "CH - OPC por Vendedor",
      "parentfield": "roles",
      "parenttype": "Dashboard Chart", 
      "idx": 3
    }
  ]
}
```

### Paso 2: Actualizar Workspace Fixture

**CRÍTICO**: Agregar sección `charts` al workspace:

```json
{
  "doctype": "Workspace",
  "name": "Vendedores",
  "charts": [
    {
      "chart_name": "CH - OPC por Vendedor",
      "label": "CH - OPC por Vendedor"
    }
  ],
  "content": "[{\"id\":\"chart-1\",\"type\":\"chart\",\"data\":{\"chart_name\":\"CH - OPC por Vendedor\",\"col\":12}}]"
}
```

### Paso 3: Deploy y Validación

```bash
# Deploy fixtures
bench --site llantascs.dev migrate

# Validar que chart persiste después de migrate
# (ejecutar script de análisis completo)
```

## Errores Comunes y Soluciones

### Error 1: Charts Desaparecen Después de Migrate
**Causa**: Falta sección `charts` en workspace fixture
**Solución**: Agregar child table `charts` con todas las referencias

### Error 2: Chart No Visible en UI
**Causa**: Roles faltantes o incorrectos
**Solución**: Incluir roles completos con estructura parent/parentfield/parenttype/idx

### Error 3: Campo No Encontrado
**Causa**: Usar `x_axis` en lugar de `x_field`
**Solución**: Usar `x_field` para campo X del script report

### Error 4: Chart Vacío
**Causa**: `filters_json` null o malformado
**Solución**: Usar mínimo `"{}"` para filters_json

## Script de Validación

Para verificar el estado completo del workspace después de cambios:

```python
# Ubicación: llantascs_customs/llantascs_customs/one_offs/complete_workspace_analysis.py
bench --site llantascs.dev execute llantascs_customs.llantascs_customs.one_offs.complete_workspace_analysis.run
```

Este script analiza:
- Todos los 28 campos del workspace
- Child tables (charts, shortcuts, roles, etc.)
- Content JSON parseado
- Metadata del DocType

## Consideraciones de Performance

### Child Tables Structure
- Usar estructura parent/parentfield/parenttype para todas las child tables
- Incluir `idx` en roles para ordering correcto
- Mantener consistencia en naming entre chart_name y referencias

### Migrate-Proof Implementation
- NUNCA agregar charts manualmente desde UI para producción
- SIEMPRE usar fixtures completos
- VERIFICAR que sección `charts` existe en workspace fixture antes de deploy

## Próximos Charts

Para agregar charts adicionales:

1. **Crear nuevo Dashboard Chart** siguiendo el template exact
2. **Agregar a workspace fixture** en sección `charts`  
3. **Actualizar content JSON** con nueva referencia
4. **Incluir roles apropiados** para cada chart
5. **Validar con migrate** que chart persiste

## v2.7.4 Update - Modificación Reporte OPC por Vendedor 

### Cambio de Conteo: OPCs → Facturas Únicas por Vendedor

**PROBLEMA ABORDADO**: RV - OPC por Vendedor contaba número de OPCs, se necesitaba contar facturas con comisión

#### Modificaciones Implementadas

**1. Script Report Changes (`rv___opc_por_vendedor.py`):**
```sql
-- ANTES:
COUNT(DISTINCT c.parent) AS opc_count

-- DESPUÉS: 
COUNT(DISTINCT c.sales_invoice_id) AS invoice_count
```

**2. Dashboard Chart Update (`dashboard_chart.json`):**
```json
{
  "y_axis": [{
    "y_field": "invoice_count",  // era "opc_count"
    "label": "Facturas"          // era "OPC"
  }]
}
```

**3. Column Definition:**
```python
{"label": _("# Facturas"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 120}
```

#### Lógica de Filtrado Mejorada

**Joins con Validación de Estado:**
```sql
INNER JOIN `tabOrden de Pago Comisiones` opc 
  ON opc.name = c.parent AND opc.docstatus = 1
LEFT JOIN `tabSales Invoice` si 
  ON si.name = c.sales_invoice_id AND si.docstatus = 1
WHERE c.sales_invoice_id IS NOT NULL
```

**Resultado**: Solo considera OPCs confirmadas y facturas sometidas, contando facturas únicas por vendedor.

#### Datos de Validación
- **22 vendedores** con datos válidos
- **724 facturas** máximo (Jose Luis Messner)
- **Protección DISTINCT** contra duplicados

## v2.7.15 Update - Comisiones Mensuales Chart

### Document Type Chart Implementation

**PROBLEMA ABORDADO**: Necesidad de visualizar comisiones pagadas por mes en workspace Comisiones

#### Chart Implementado: `comisiones_pagadas_por_mes`

**Configuración Final (Funcional)**:
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

#### Lessons Learned - ERPNext Document Type Charts

**PATRONES CORRECTOS** (basados en charts funcionales como "Outgoing Bills"):
- ✅ `chart_type: "Sum"` (NO "Bar")
- ✅ `source: ""` (vacío, NO "Document Type")
- ✅ `based_on`: Campo de fecha (ej: "hasta_fecha", "posting_date")
- ✅ `value_based_on`: Campo numérico para agregación
- ✅ `timeseries: 1` para series temporales

**ERRORES COMUNES EVITAR**:
- ❌ `chart_type: "Bar"` con `source: "Document Type"`
- ❌ `based_on`: Campo numérico (causa TypeError en comparaciones de fecha)
- ❌ `data_source` vs `source` (field name confusion)
- ❌ `time_series` vs `timeseries` (field name confusion)

#### Integración Workspace

**Cambios en `workspace.json`**:
1. **Comisiones**: Agregado header "Comisiones Mensuales" + chart
2. **Vendedores**: Removido header "Indicadores (rango de fechas)"

**Charts Array Requerido**:
```json
"charts": [{
  "chart_name": "comisiones_pagadas_por_mes",
  "label": "comisiones_pagadas_por_mes",
  "parent": "Comisiones",
  "parentfield": "charts",
  "parenttype": "Workspace"
}]
```

---

## v2.7.3 Update - Filtros de Dashboard Charts Funcionales

### Implementación Completa de Filtros de Fecha

**PROBLEMA RESUELTO**: Dashboard Charts no mostraban controles de filtro en UI

#### Solución Implementada

**1. Report DocType Configuration:**
Agregados filtros a los 3 Script Reports JSON:

```json
"filters": [
  { "fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "mandatory": 0, "default": null },
  { "fieldname": "to_date",   "label": "To Date",   "fieldtype": "Date", "mandatory": 0, "default": null }
]
```

**2. Dashboard Chart Configuration:**
```json
{
  "use_report_chart": 1,
  "filters_json": "{\"from_date\":\"\",\"to_date\":\"\"}"
}
```

#### Archivos Modificados
- `llantascs_customs/report/rv___opc_por_vendedor/rv___opc_por_vendedor.json`
- `llantascs_customs/report/rv___comision_total_por_vendedor/rv___comision_total_por_vendedor.json`
- `llantascs_customs/report/rv___margen_promedio_por_vendedor/rv___margen_promedio_por_vendedor.json`
- `fixtures/dashboard_chart.json` (ya tenía `use_report_chart: 1`)

#### Flujo de Funcionamiento
1. **UI**: Modal "Set Filters" muestra campos From Date y To Date
2. **Storage**: Filtros se guardan en Dashboard Chart
3. **Execution**: Script Reports reciben filtros y filtran datos correctamente

#### Resultado Final
✅ **Controles de fecha completamente funcionales en los 3 Dashboard Charts**

---

## v2.7.2 Update - Filtros y Precisión

### Filtros Interactivos Implementados

**Todos los Dashboard Charts ahora incluyen:**
```json
"filters_json": "{\"from_date\": \"\", \"to_date\": \"\", \"sales_person\": \"\", \"cost_center\": \"\"}"
```

**Scripts Reports con Filtros Robustos:**
- Lógica condicional: `(%(param)s IS NULL OR field = %(param)s)`
- Parámetros opcionales sin errores KeyError
- FROM_DATE default: "2025-01-01" si no se especifica
- TO_DATE, SALES_PERSON, COST_CENTER: completamente opcionales

### Mejoras de Precisión Decimal

**Comisión Total (2 decimales):**
```python
# SQL:
ROUND(SUM(c.total_comision), 2) AS commission_total

# Column:
{"fieldtype": "Currency", "precision": 2}
```

**Margen Promedio (1 decimal):**
```python
# SQL con división segura:
ROUND(
    CASE WHEN COALESCE(SUM(c.ingreso), 0) = 0 THEN 0
         ELSE (SUM(c.utilidad_transaccion) / SUM(c.ingreso)) * 100.0
    END, 1) AS avg_margin

# Column:
{"fieldtype": "Percent", "precision": 1}
```

### Cambio OPC → Facturas

**Chart "OPC por Vendedor" ahora muestra facturas únicas:**
```python
# SQL:
COUNT(DISTINCT c.sales_invoice_id) AS invoice_count
WHERE c.sales_invoice_id IS NOT NULL

# Y-field actualizado:
"y_field": "invoice_count"  # Era: opc_count
"label": "Facturas"        # Era: OPC
```

## Troubleshooting

### Debug Migration Issues
Si un chart desaparece después de migrate:

1. Verificar que existe en `fixtures/dashboard_chart.json`
2. Confirmar sección `charts` en workspace fixture
3. Validar consistencia de `chart_name` en ambas ubicaciones
4. Ejecutar script de análisis completo para state comparison

### Permission Issues
Si chart no es visible para usuarios:

1. Verificar roles en Dashboard Chart fixture
2. Confirmar estructura parent/parentfield/parenttype
3. Incluir `idx` en roles para ordering
4. Validar que usuario tiene rol asignado

### Filtros No Funcionan
Si filtros no aparecen en UI:

1. Verificar `filters_json` en Dashboard Chart fixture
2. Confirmar sintaxis JSON correcta con escaping
3. Ejecutar migrate para aplicar cambios
4. Clear cache: `bench --site SITENAME clear-cache`

### Field Names Incorrectos
Si gráficos muestran ceros después de v2.7.2:

1. Verificar field names en scripts: `invoice_count`, `commission_total`, `avg_margin`
2. Confirmar y_field en Dashboard Chart fixture coincide
3. Verificar SQL alias en script reports
4. Validar que scripts retornan data con field names correctos

## Referencias

- **Fixtures**: `/llantascs_customs/fixtures/`
- **Workspace Analysis**: `/llantascs_customs/one_offs/complete_workspace_analysis.py`
- **Documentation**: `docs/CHANGELOG.md` v2.7.2 para detalles completos de mejoras