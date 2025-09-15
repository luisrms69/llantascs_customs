# Reports Documentation

## Query Reports

### Backlog Comisiones

**Tipo:** Query Report  
**Ubicación:** `/app/query-report/Backlog Comisiones`  
**Módulo:** Llantascs Customs  

#### Descripción

Reporte principal para identificar facturas pendientes de inclusión en Órdenes de Pago de Comisiones. Utiliza semántica de árbol jerárquico (lft/rgt) para filtrado por Cost Center y Sales Person.

#### Filtros

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `from_date` | Date | Sí | "2025-01-01" | Fecha inicio del rango de búsqueda |
| `to_date` | Date | Sí | "Today" | Fecha fin del rango de búsqueda |
| `cost_center` | Link | Sí | "Llantas de Calidad Star - LLCS" | Centro de costo (sucursal) raíz o hija |
| `sales_person` | Link | Sí | "Equipo de ventas" | Vendedor raíz o hijo |

#### Lógica de Filtrado

**Filtrado Jerárquico:**
- **Cost Centers**: Usa tabla `tabCost Center` con lógica `lft BETWEEN sel.lft AND sel.rgt`
- **Sales Persons**: Usa tabla `tabSales Person` con lógica `lft BETWEEN sel.lft AND sel.rgt`
- **Semántica "All"**: Nodos raíz incluyen todos sus descendientes automáticamente

**Exclusiones Automáticas:**
1. **Clientes sin comisión**: Excluye clientes listados en `tabClientes Sin Comision` con vigencia por fechas
2. **OPCs ya procesadas**: Excluye facturas ya incluidas en OPCs con `docstatus = 1`
3. **Facturas sin validar**: Solo `si.docstatus = 1`

#### Columnas del Reporte

1. **Factura** (Link/Sales Invoice:160) - Enlace a la factura
2. **Fecha** (Date:95) - Fecha de la factura
3. **Cliente** (Link/Customer:220) - Cliente de la factura
4. **Sucursal** (Link/Cost Center:200) - Centro de costo de la factura
5. **Venta (OPC def)** (Currency:120) - Base net total redondeado a 2 decimales
6. **Margen pct CC** (Percent:110) - Porcentaje de margen por CC (metodología GL, 90 días)
7. **Rate Comisión** (Percent:110) - Tasa de comisión aplicable
8. **Comisión Estimada** (Currency:120) - Comisión calculada con IFNULL optimizado
9. **Vendedores** (Data:220) - Todos los vendedores concatenados con coma cuando hay comisión compartida
10. **Pago OK** (Check:80) - Check binario: 1=factura totalmente pagada, 0=pendiente
11. **Entrega OK** (Check:80) - Check binario: 1=servicios o entregado, 0=pendiente
12. **Comisiones OK** (Check:90) - Check binario: 1=incluida en OPC aprobada, 0=pendiente

#### Arquitectura Técnica

**Tipo:** Query Report puro (sin JavaScript ni Python embebido)  
**SQL:** Query directa con JOINs optimizados  
**Performance:** Filtrado temprano por índices de fecha y jerarquía  

**Verificaciones de Integridad:**
- `report_script = NULL`
- `javascript = NULL` 
- `json = NULL`
- Sin Custom Reports que generen duplicación

#### Historial de Implementación

**v2.7.15 (2025-09-14):**
- **CONVERSIÓN A SCRIPT REPORT**: Migración completa del reporte "Backlog Comisiones GP nativo" de Query Report a Script Report
- **Integración ERPNext nativa**: Implementación de Python backend que invoca ERPNext standard Gross Profit report
- **Nueva columna GP nativo**: "Margen Sucursal 6m (GP nativo)" calculada mediante promedio 6 meses por cost center tree
- **Resolución caching crítico**: Solucionado issue de prepared_report causando 707 filas vacías en UI
- **Metodología 4-plano**: Debugging sistemático identificó discrepancia fixture vs BD en prepared_report
- **Performance optimizada**: Sin cache de prepared reports, consultas frescas directas
- **Mapeo SQL corregido**: Fix crítico en key mapping ("Factura:Link/Sales Invoice:160" vs "Factura")
- **Arquitectura robusta**: Script Report con execute() function, filtros dinámicos, integración workspace

**v2.7.14 (2025-09-13):**
- **Nuevo reporte GP nativo**: Implementación Fase 1 de "Backlog Comisiones (GP nativo)"
- **Metodología revolucionaria**: Skeleton Query Report preparado para usar ERPNext native Gross Profit en Fase 2
- **Workspace integration**: Posicionado como primer item en workspace Comisiones > sección Backlog
- **Filtros sin defaults**: cost_center y sales_person sin valores por defecto para máxima flexibilidad
- **Arquitectura limpia**: Query Report puro sin lógica Python embebida, listo para GP nativo
- **Fix estético**: Shortcuts de Backlog organizados en filas separadas (col:1) evitando amontonamiento

**v2.7.13 (2025-09-13):**
- **LIMPIEZA COMPLETA**: Eliminación total del proyecto fallido GP Margen por Sucursal
- **Sistema restaurado**: Regreso completo al último punto funcional (commit c5c77fae486a86)
- **Cleanup filesystem**: Eliminados DocType, tasks.py, install.py, gp_cache/ y todos los archivos relacionados
- **Cleanup BD**: Dropeada tabla, eliminados metadata DocType, DocField, DocPerm y Scheduled Job Type
- **Fixtures restaurados**: report.json restaurado a metodología GL original con 4 CTEs funcionales
- **Hooks limpiados**: Eliminadas referencias a after_migrate y scheduler_events del proyecto fallido
- **Verificación exitosa**: Ambos reportes funcionando correctamente con metodología GL sin residuos GP

**v2.7.12 (2025-09-13):**
- **FRACASO TOTAL**: Proyecto de migración a reporte nativo ERPNext abandonado por problemas técnicos irresolubles
- **ImportError persistente**: DocType "GP Margen por Sucursal" no se puede instanciar vía ORM después de múltiples propuestas técnicas
- **Márgenes en cero**: Tabla cache vacía resulta en márgenes cero en reportes, problema no resuelto
- **Metodología GL mantenida**: Se mantiene metodología GL-based existente como única alternativa funcional
- **Diagnóstico técnico**: DocType recién creado (2025-09-12) no se registró correctamente en sistema de controladores Frappe
- **Decisión de abandono**: Después de 3 propuestas técnicas implementadas completamente sin éxito, proyecto declarado fracaso total

**v2.7.11 (2025-09-12):**
- **Comisiones compartidas**: Implementación de columna "Vendedores" con concatenación multiple
- **Sub-query optimizado**: Reemplazo de JOIN problemático por sub-query con GROUP_CONCAT
- **Elimina duplicación**: Una sola fila por factura, múltiples vendedores separados por coma
- **Ancho ajustado**: Columna Vendedores expandida de 150 a 220 píxeles
- **Compatibilidad**: Mantiene filtros jerárquicos y todas las exclusiones existentes

**v2.7.8 (2025-09-08):**
- Implementación propuesta ChatGPT: metodología GL-based para márgenes
- Conversión de columnas status a formato Check binario (1/0)
- Corrección formato porcentaje siguiendo patrón ERPNext (x100.0 + ROUND)
- Optimización IFNULL en cálculos de comisión
- Precisión decimal limitada a 2 en campo Venta
- **Metodología GL**: 4 CTEs nuevos (gl_90d, sales_cc, cogs_cc, cc_margin)
- **Lógica binaria**: outstanding_amount=0, servicios/DN delivery, OPC existente

**v2.7.7 (2025-09-08):**
- Corrección de 4 errores críticos identificados en segunda revisión
- Restauración de 12 columnas completas (vs 8 anteriores)
- Corrección del campo default rate: `default_commission_rate` → `porcentaje_sobre_utilidad`
- Fix del error de cálculo de comisiones (factor 100x corregido)
- Adición del LEFT JOIN con Sales Team para información de vendedores

**v2.7.6 (2025-09-07):** 
- Implementación inicial como Query Report puro
- Resolución KeyError mediante defaults obligatorios
- Limpieza quirúrgica completa eliminando Script Reports conflictivos
- Verificación completa según metodología ChatGPT (verificaciones E.1-E.4 ✅)

#### Casos de Uso

1. **Preparación OPC**: Identificar facturas pendientes para nueva OPC
2. **Auditoría de cobranza**: Verificar estado de cobro por sucursal/vendedor  
3. **Seguimiento de vendedores**: Analizar cartera por equipo de ventas
4. **Control de sucursales**: Monitoreo por centro de costo específico

#### Notas de Mantenimiento

- **Fixtures Only**: Configuración vía `fixtures/report.json` únicamente
- **No Manual Creation**: No crear reportes manualmente en UI  
- **Migrate Safe**: Configuración garantizada vía `bench migrate`
- **Tree Dependency**: Requiere estructura lft/rgt válida en Cost Center y Sales Person

---

## Backlog Comisiones Completo

**Tipo:** Query Report  
**Ubicación:** `/app/query-report/Backlog Comisiones Completo`  
**Módulo:** Llantascs Customs  

#### Descripción

Versión sin filtros obligatorios del reporte Backlog Comisiones. Eliminó las limitaciones de lógica de negocio que requerían seleccionar Cost Center y Sales Person, manteniendo las columnas visibles en resultados.

#### Filtros

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `from_date` | Date | No | "2025-01-01" | Fecha inicio del rango de búsqueda |
| `to_date` | Date | No | "Today" | Fecha fin del rango de búsqueda |

#### Diferencias vs Backlog Comisiones

**ELIMINADO:**
- Filtros obligatorios `cost_center` y `sales_person`
- CTEs jerárquicos `cc_root` y `sp_root` 
- Condiciones de filtrado por jerarquía lft/rgt
- Dependencias a `%(cost_center)s` y `%(sales_person)s`

**CONSERVADO:**
- Todas las columnas incluyendo Sucursal y Vendedor
- Exclusiones de clientes sin comisión
- Exclusiones de OPCs ya procesadas
- Metodología GL para márgenes (CTEs: gl_90d, sales_cc, cogs_cc, cc_margin)
- Cálculo de comisión estimada
- Checks binarios de estado (Pago OK, Entrega OK, Comisiones OK)

#### Columnas del Reporte

1. **Factura** (Link/Sales Invoice:160) - Enlace a la factura
2. **Fecha** (Date:95) - Fecha de la factura
3. **Cliente** (Link/Customer:220) - Cliente de la factura
4. **Sucursal** (Link/Cost Center:150) - Centro de costo de la factura
5. **Vendedores** (Data:220) - Todos los vendedores concatenados con coma cuando hay comisión compartida
6. **Venta (OPC def)** (Currency:120) - Base net total redondeado a 2 decimales
7. **Margen pct CC** (Percent:110) - Porcentaje de margen por CC (metodología GL, 90 días)
8. **Rate Comisión** (Percent:110) - Tasa de comisión aplicable
9. **Comisión Estimada** (Currency:120) - Comisión calculada con IFNULL optimizado
10. **Pago OK** (Check:80) - Check binario: 1=factura totalmente pagada, 0=pendiente
11. **Entrega OK** (Check:80) - Check binario: 1=servicios o entregado, 0=pendiente
12. **Comisiones OK** (Check:90) - Check binario: 1=incluida en OPC aprobada, 0=pendiente

#### Casos de Uso

1. **Vista general sin filtros**: Análisis amplio sin restricciones de sucursal/vendedor
2. **Exploración inicial**: Identificar patrones antes de filtros específicos  
3. **Auditorías completas**: Revisión total del backlog sin limitaciones
4. **Preparación masiva OPC**: Identificar facturas pendientes globalmente

#### Arquitectura Técnica

**SQL Base Simplificado:**
```sql
base_si as (
  select si.*
  from `tabSales Invoice` si
  where si.docstatus = 1
    and si.posting_date between %(from_date)s and %(to_date)s
    -- Sin condiciones jerárquicas de CC o SP
    -- Mantiene exclusiones de clientes y OPCs
)
```

**Columnas Mantenidas:**
```sql
si.cost_center as "Sucursal:Link/Cost Center:150"
(select group_concat(distinct st.sales_person...) as "Vendedor:Data:150"
```

#### Historial de Implementación

**v2.7.11 (2025-09-12):**
- **Comisiones compartidas**: Implementación de columna "Vendedores" con concatenación multiple
- **Sub-query optimizado**: Vendedores concatenados con GROUP_CONCAT sin JOINs problemáticos
- **Ancho ajustado**: Columna expandida de 150 a 220 píxeles para múltiples nombres
- **Consistencia**: Sincronizado con cambios del reporte "Backlog Comisiones" normal

**v2.7.9 (2025-09-11):**
- Implementación inicial del reporte sin filtros obligatorios
- Eliminación de CTEs jerárquicos cc_root y sp_root
- Remoción de condiciones lft/rgt en base_si
- Conservación de columnas Sucursal y Vendedor como output
- Descontaminación de fixtures con whitelist en hooks.py
- Configuración en workspace como primer acceso en sección Backlog

**Investigación de Totales (2025-09-12):**
- **PROBLEMA IDENTIFICADO**: Sistema `add_total_row` de Frappe no funciona con queries complejas
- **Fixtures vs BD**: Los fixtures contienen `add_total_row: 1` pero la BD mantiene `0` después de migrate
- **Caracteres problemáticos**: Corrección de `'%'` → `'%%'` solucionó error SQL pero no totales
- **Comparación técnica**: Reportes que funcionan (ej: "Reporte Cobranza por Sucural") usan queries simples
- **Alternativas evaluadas**: `WITH ROLLUP` funciona pero es "hack" SQL no oficial de Frappe
- **CONCLUSIÓN**: Bug confirmado de Frappe - `add_total_row` no sincroniza con fixtures en queries complejas

---

## Pagos OPC - Resumen

**Tipo:** Query Report  
**Descripción:** Resumen de Órdenes de Pago de Comisiones con estadísticas por período.

## Pagos OPC - Por Sucursal

**Tipo:** Query Report
**Descripción:** Análisis de pagos de comisiones agrupados por sucursal/centro de costo.

---

## Script Reports

### Backlog Comisiones GP nativo

**Tipo:** Script Report
**Ubicación:** `/app/query-report/Backlog Comisiones GP nativo`
**Módulo:** Llantascs Customs
**Python Module:** `llantascs_customs.llantascs_customs.report.backlog_comisiones_gp_nativo.backlog_comisiones_gp_nativo`

#### Descripción

Script Report avanzado que combina todas las columnas de "Backlog Comisiones Completo" con una nueva columna calculada "Margen Sucursal 6m (GP nativo)" que utiliza la metodología nativa de ERPNext Gross Profit report para calcular márgenes promedio de 6 meses por cost center tree.

#### Arquitectura Técnica

**Tipo:** Script Report con Python backend
**Función Principal:** `execute(filters=None)`
**Integración:** ERPNext standard Gross Profit report
**Caching:** `prepared_report = 0` (sin cache, consultas frescas)

**Backend Flow:**
1. **Data Source**: Invoke "Backlog Comisiones Completo" para obtener datos base
2. **GP Integration**: Llama a `erpnext.accounts.report.gross_profit.gross_profit.execute()`
3. **Margin Calculation**: Calcula promedio 6 meses por cost center usando tree hierarchy
4. **Data Merge**: Combina datos base con márgenes GP nativos
5. **Response**: Retorna `(columns, data)` para ERPNext framework

#### Filtros

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `from_date` | Date | No | None | Fecha inicio del rango de búsqueda |
| `to_date` | Date | No | None | Fecha fin del rango de búsqueda |
| `cost_center` | Link | No | None | Centro de costo (sucursal) raíz o hija |
| `sales_person` | Link | No | None | Vendedor raíz o hijo |

**Características de Filtros:**
- **Sin defaults**: Máxima flexibilidad, usuario define rangos
- **Filtros opcionales**: Todos los filtros son opcionales (no mandatory)
- **Filtros jerárquicos**: Implementados con lft/rgt tree semantics
- **Post-filtrado**: Se aplica después de cálculos GP, no afecta performance

#### Filtrado Jerárquico Avanzado

**Filtrado por Cost Center (Sucursal):**
- **Lógica**: Si se selecciona un nodo, incluye automáticamente todos sus nodos hijos
- **Implementación**: Usa `lft/rgt` tree de `tabCost Center` para determinar jerarquía
- **Comportamiento**: Filas sin sucursal quedan FUERA cuando hay filtro, INCLUIDAS cuando está vacío
- **Ejemplo**: Seleccionar "LLCS (Matriz)" incluye "VILLAHERMOSA", "QUERETARO", etc.

**Filtrado por Sales Person (Vendedor):**
- **Lógica**: Si se selecciona un nodo, incluye facturas de todos sus vendedores hijos
- **Implementación**: Usa `lft/rgt` tree de `tabSales Person` + `tabSales Team` lookup
- **Comportamiento**: Facturas sin vendedor quedan FUERA cuando hay filtro, INCLUIDAS cuando está vacío
- **Ejemplo**: Seleccionar "Equipo de ventas" incluye todos los vendedores individuales

**Filtros Combinados:**
- **Intersección**: Cuando ambos filtros están presentes, se aplican secuencialmente
- **Orden**: Primero Cost Center, luego Sales Person
- **Resultado**: Solo facturas que cumplan AMBOS criterios jerárquicos

**Casos de Uso Filtrado:**
- **Vista por sucursal**: cost_center = "VILLAHERMOSA" → solo facturas de esa sucursal
- **Vista por equipo**: sales_person = "Equipo de ventas" → facturas de todo el equipo
- **Vista específica**: Ambos filtros → intersección precisa
- **Vista global**: Sin filtros → incluye facturas sin asignaciones

#### Columnas del Reporte

**Columnas Base (heredadas de "Backlog Comisiones Completo"):**
1. **Factura** (Link/Sales Invoice:160) - Enlace a la factura
2. **Fecha** (Date:95) - Fecha de la factura
3. **Cliente** (Link/Customer:220) - Cliente de la factura
4. **Sucursal** (Link/Cost Center:200) - Centro de costo de la factura
5. **Vendedores** (Data:220) - Todos los vendedores concatenados
6. **Venta (OPC def)** (Currency:120) - Base net total redondeado
7. **Margen pct CC** (Percent:110) - Porcentaje de margen (metodología GL)
8. **Rate Comisión** (Percent:110) - Tasa de comisión aplicable
9. **Comisión Estimada** (Currency:120) - Comisión calculada
10. **Pago OK** (Check:80) - Estado de pago
11. **Entrega OK** (Check:80) - Estado de entrega
12. **Comisiones OK** (Check:90) - Estado de comisión

**Nueva Columna (GP nativo):**
13. **Margen Sucursal 6m (GP nativo)** (Percent:130) - Promedio 6 meses calculado con ERPNext native Gross Profit

#### Metodología GP Nativo

**Integración ERPNext:**
```python
from erpnext.accounts.report.gross_profit.gross_profit import execute as gp_execute

# Invocar reporte nativo
gp_columns, gp_data = gp_execute(gp_filters)
```

**Cálculo de Márgenes:**
1. **Período**: 6 meses retrospectivos desde `to_date`
2. **Granularidad**: Por cost center individual
3. **Agregación**: Promedio ponderado por net amount
4. **Tree Hierarchy**: Incluye cost centers hijos automáticamente
5. **Fallback**: 0.0% cuando no hay datos GP

**Ventajas vs Metodología GL:**
- **Nativo ERPNext**: Usa algoritmos oficiales de gross profit
- **Actualización automática**: Sigue cambios en ERPNext core
- **Compatibilidad**: Consistente con otros reportes ERPNext
- **Precision**: Mayor precisión en cálculos complejos

#### Resolución de Issues Técnicos

**Issue Crítico Resuelto (2025-09-14):**
- **Problema**: 707 filas devueltas por backend pero UI mostraba filas vacías
- **Causa Raíz**: `prepared_report = 1` en BD vs `prepared_report = 0` en fixture + cache obsoleto
- **Metodología**: Debugging sistemático 4-plano identificó discrepancia caching
- **Solución**: Migrate + cache purge sincronizó fixture → BD correctamente
- **Fix SQL Mapping**: Corrección mapeo keys ("Factura:Link/Sales Invoice:160")

**Debugging 4-Plano Aplicado:**
1. **Plano 0**: Sanity checks ✅
2. **Plano 1**: Backend verification ✅ (datos reales retornados)
3. **Plano 2**: Filter types verification ✅ (string/dict ambos funcionan)
4. **Plano 3**: Prepared report identification ✅ (fixture vs BD sync)
5. **Plano 4**: No requerido (problema resuelto en Plano 3)

#### Casos de Uso

1. **Análisis comparativo**: Comparar márgenes GL vs GP nativo por sucursal
2. **Validación metodológica**: Verificar consistencia entre enfoques de cálculo
3. **Commission planning**: Planificación de comisiones con márgenes ERPNext oficiales
4. **Auditoría avanzada**: Análisis profundo con metodología nativa ERPNext

#### Workspace Integration

**Ubicación:** Workspace "Comisiones" > Sección "Backlog" > Primer ítem
**Shortcut:** "Backlog Comisiones GP nativo"
**Prioridad:** Posicionado antes de "Backlog Comisiones Completo"

#### Historial de Implementación

**v2.7.16 (2025-09-14):**
- **FILTROS JERÁRQUICOS FUNCIONALES**: Implementación completa de filtrado por Cost Center y Sales Person
- **Post-filtrado por árbol**: Usa lft/rgt tree semantics para incluir nodos hijos automáticamente
- **Filtros combinados**: Intersección correcta cuando ambos filtros están presentes
- **Performance optimizada**: Post-filtrado después de cálculos GP, no afecta performance base
- **Validación completa**: 314→17 filas (sucursal), 314→313 filas (vendedor), intersección funcional
- **Columnas simplificadas**: Solo metodología GP nativa visible, eliminadas columnas GL anteriores
- **Orden optimizado**: Nuevas columnas GP en posiciones de las anteriores para UX consistente

**v2.7.15 (2025-09-14):**
- **Implementación inicial**: Conversión completa Query Report → Script Report
- **Python backend**: Función execute() con integración ERPNext Gross Profit
- **Resolución caching**: Debugging 4-plano y corrección prepared_report sync
- **Mapeo SQL fix**: Corrección crítica key mapping para display correcto
- **Testing completo**: Verificación 707 filas datos reales en UI