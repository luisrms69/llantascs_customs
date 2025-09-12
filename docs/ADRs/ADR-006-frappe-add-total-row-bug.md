# ADR-006: Frappe add_total_row Bug con Queries Complejas

**Status:** Accepted  
**Date:** 2025-09-12  
**Deciders:** Sistema Llantascs Customs  

## Context

Durante la implementación de totales automáticos en reportes "Backlog Comisiones" y "Backlog Comisiones Completo", se descubrió un bug crítico en Frappe Framework relacionado con la funcionalidad `add_total_row` en Query Reports.

### Problema Identificado

1. **Fixtures vs Base de Datos**: Los fixtures JSON contienen `"add_total_row": 1` pero después de `bench migrate`, la base de datos mantiene `add_total_row: 0`

2. **Queries Complejas**: El bug se manifiesta específicamente con queries que contienen:
   - Múltiples CTEs (Common Table Expressions)  
   - Caracteres especiales (%, CONCAT)
   - Alias complejos con tipos específicos (`:Currency:120`, `:Data:110`)
   - Funciones SQL anidadas (COALESCE, ROUND, IFNULL)

3. **Queries Simples Funcionan**: Reportes con queries básicas (ej: "Reporte Cobranza por Sucural") sí mantienen `add_total_row: 1` correctamente.

### Investigación Técnica

**Reportes Afectados:**
- Backlog Comisiones: `add_total_row: 0` (debería ser 1)
- Backlog Comisiones Completo: `add_total_row: 0` (debería ser 1)

**Reportes Funcionales:**
- Reporte Cobranza por Sucural: `add_total_row: 1` ✅
- Pagos OPC - Por Sucursal: Usa `WITH ROLLUP` (alternativa no oficial)

**Errores Secundarios:**
- TypeError: not enough arguments for format string (resuelto con `'%'` → `'%%'`)

## Decision

**ABANDONAR** la implementación de totales automáticos usando `add_total_row` debido a:

1. **Bug Confirmado**: Frappe Framework v15.78.1 no sincroniza fixtures con BD para queries complejas
2. **Documentación Deficiente**: Frappe no documenta limitaciones de `add_total_row`
3. **Workarounds Problemáticos**: `WITH ROLLUP` funciona pero es hack SQL no oficial
4. **Costo vs Beneficio**: Horas invertidas vs funcionalidad básica no justifica continuación

## Consequences

### Positivas
- **Funcionalidad Core Preservada**: Los reportes funcionan sin totales
- **Conocimiento Ganado**: Documentación completa del bug para futuras referencias
- **Tiempo Ahorrado**: Evita continuar con solución inviable

### Negativas  
- **Característica Faltante**: Los totales no se mostrarán automáticamente
- **Experiencia Usuario**: Usuarios deben calcular totales manualmente
- **Expectativas**: Feature solicitado no se implementó

### Alternativas Futuras
1. **Script Report**: Migrar a Script Report con totales en Python
2. **Frappe Upgrade**: Evaluar en futuras versiones de Frappe
3. **Dashboard**: Crear dashboard con métricas calculadas separadamente

## Implementation

### Cambios Realizados
1. **Corrección Error SQL**: Cambio de `'%'` a `'%%'` en CONCAT
2. **Documentación Bug**: ADR completa con investigación técnica
3. **Fixtures Correctos**: Se mantienen `add_total_row: 1` para futuras versiones

### Cambios NO Realizados
- No modificación directa de base de datos (violación de reglas)
- No implementación con `WITH ROLLUP` 
- No workarounds manuales en JavaScript

### Evidencia Técnica

**Query Compleja (No funciona add_total_row):**
```sql
CONCAT(ROUND(COALESCE(m.avg_margin_rate, 0) * 100.0, 2), '%%') as "Margen pct CC:Data:110"
COALESCE(ROUND(si.base_net_total * IFNULL(m.avg_margin_rate,0) * ...), 0) AS "Comisión Estimada:Currency:120"
```

**Query Simple (Funciona add_total_row):**
```sql  
SELECT posting_date AS "Fecha de Pago", sum(paid_amount) AS "Total Pagado", cost_center AS "Sucursal"
```

## Notes

- **Framework**: Frappe v15.78.1, ERPNext v15.76.0
- **Tiempo Invertido**: ~4 horas de investigación técnica
- **Backup Creado**: 20250912_143751-llantascs_dev-database.sql.gz
- **Estado Final**: Reportes funcionales sin totales, fixtures correctos mantenidos