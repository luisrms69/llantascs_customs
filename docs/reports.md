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
2. **Cliente** (Link/Customer:220) - Cliente de la factura  
3. **Fecha** (Date:100) - Fecha de la factura
4. **Sucursal(es)** (Data:240) - Concatenación de sucursales de items
5. **Importe Factura** (Currency:120) - Total de la factura
6. **Cobro OK** (Check:90) - Indicador si está totalmente pagada
7. **Vendedores OK** (Check:90) - Indicador si tiene vendedores válidos
8. **Vendedores (en subárbol)** (Data:260) - Lista de vendedores del subárbol seleccionado

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

## Pagos OPC - Resumen

**Tipo:** Query Report  
**Descripción:** Resumen de Órdenes de Pago de Comisiones con estadísticas por período.

## Pagos OPC - Por Sucursal  

**Tipo:** Query Report  
**Descripción:** Análisis de pagos de comisiones agrupados por sucursal/centro de costo.