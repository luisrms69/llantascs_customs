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

## Referencias

- **Fixtures**: `/llantascs_customs/fixtures/`
- **Workspace Analysis**: `/llantascs_customs/one_offs/complete_workspace_analysis.py`
- **Documentation**: `docs/CHANGELOG.md` v2.7.1 para detalles completos de implementación