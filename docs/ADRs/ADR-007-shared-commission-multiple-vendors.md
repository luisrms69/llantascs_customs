# ADR-007: Implementación de Múltiples Vendedores en Comisiones Compartidas

**Status:** Accepted  
**Date:** 2025-09-12  
**Deciders:** Sistema Llantascs Customs  

## Context

Los reportes "Backlog Comisiones" y "Backlog Comisiones Completo" solo mostraban el primer vendedor del Sales Team (`st.idx = 1`) cuando había comisiones compartidas entre múltiples vendedores. Esto generaba pérdida de información crítica para el análisis de comisiones y transparencia en equipos de ventas.

### Problema Identificado

1. **Información incompleta**: Solo se veía un vendedor aunque la factura tuviera múltiples sales persons
2. **Pérdida de contexto**: Imposible identificar todos los involucrados en comisiones compartidas  
3. **JOIN problemático**: El `LEFT JOIN` duplicaba filas cuando había múltiples vendedores
4. **Inconsistencia**: Diferentes reportes trataban la información de vendedores de forma diferente

### Propuesta ChatGPT

**Objetivo**: Mostrar todos los vendedores cuando la comisión se comparte sin romper funcionalidad existente ni duplicar código.

**Estrategia**: Reemplazar columna de vendedor con sub-query que concatena nombres del Sales Team por factura, evitando duplicación de filas.

## Decision

**IMPLEMENTAR** el cambio de columna vendedor usando sub-query con GROUP_CONCAT en ambos reportes.

### Razones para la Decisión

1. **Información completa**: Todos los vendedores visibles en una sola columna
2. **Sin duplicación**: Una fila por factura, múltiples vendedores concatenados
3. **Performance mejorada**: Sub-query más eficiente que JOIN con duplicación
4. **Compatibilidad total**: No afecta CTEs, filtros, ni exclusiones existentes
5. **Consistencia**: Ambos reportes con comportamiento idéntico

### Implementación Técnica

**Columna reemplazada:**
```sql
-- ANTES (problemático):
coalesce(st.sales_person, '') as "Vendedor:Data:150"
-- Con JOIN: left join `tabSales Team` st on st.parent = si.name and st.idx = 1

-- DESPUÉS (solución):
COALESCE((
  SELECT GROUP_CONCAT(DISTINCT st.sales_person ORDER BY st.sales_person SEPARATOR ', ')
  FROM `tabSales Team` st
  WHERE st.parent = si.name
), '') AS "Vendedores:Data:220"
-- Sin JOIN problemático
```

**Cambios aplicados:**
1. **Ambos reportes actualizados**: "Backlog Comisiones" y "Backlog Comisiones Completo"
2. **JOIN eliminado**: Removido `left join tabSales Team` que causaba duplicación
3. **Nombre actualizado**: "Vendedor" (singular) → "Vendedores" (plural)  
4. **Ancho expandido**: 150px → 220px para acomodar múltiples nombres
5. **Ordenamiento**: Vendedores alfabéticamente ordenados con `ORDER BY`

## Consequences

### Positivas
- **Transparencia completa**: Visibilidad total de vendedores en comisiones compartidas
- **Performance optimizada**: Eliminación de JOINs innecesarios que duplicaban filas  
- **Información preservada**: Cero pérdida de datos de vendedores
- **Compatibilidad total**: CTEs, filtros jerárquicos y exclusiones intactos
- **Experiencia mejorada**: Información más rica para análisis de comisiones

### Negativas  
- **Ancho de columna**: Nombres múltiples requieren más espacio horizontal
- **Parsing manual**: Si necesitas vendedores individuales, requiere split por coma
- **Cambio de esquema**: Aplicaciones que dependían del formato anterior requieren actualización

### Alternativas Descartadas

1. **Múltiples filas por factura**: Rechazado por duplicar información financiera
2. **Columnas separadas por vendedor**: Rechazado por complejidad y limitaciones de cantidad
3. **JOIN optimizado**: Rechazado por continuar con problema de duplicación
4. **Reporte separado**: Rechazado por duplicación de lógica y mantenimiento

## Implementation

### Archivos Modificados
- `llantascs_customs/fixtures/report.json`: Ambos reportes actualizados

### Comandos Ejecutados
```bash
bench --site llantascs.dev migrate
bench --site llantascs.dev clear-cache  
bench --site llantascs.dev clear-website-cache
bench restart
```

### Verificación
- ✅ Migración exitosa sin errores
- ✅ Reportes muestran múltiples vendedores separados por coma
- ✅ Sin duplicación de filas por factura
- ✅ Filtros jerárquicos funcionando
- ✅ CTEs de márgenes intactos

## Notes

- **Framework**: Frappe v15.78.1, ERPNext v15.76.0
- **Tiempo de implementación**: ~1 hora (incluye migración y verificación)
- **Commit**: `c5c77fa - feat: Show all salespeople in shared commission reports`
- **Compatibilidad**: Cambio compatible con lógica existente, solo mejora información mostrada
- **Mantenimiento**: Solución estable, no requiere cambios adicionales en futuro