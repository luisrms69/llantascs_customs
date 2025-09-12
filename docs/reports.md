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