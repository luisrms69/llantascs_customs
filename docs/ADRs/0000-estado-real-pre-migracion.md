# ADR-0000: Estado Real de la App Pre-Migración

- **Fecha:** 2026-04-30
- **Estado:** Informativo (auditoría de estado)
- **Versión auditada:** 2.7.21
- **Rama:** feat/dot-numeros-serie-sales-invoice-item

---

## Contexto

Este documento registra el estado real de la aplicación `llantascs_customs` antes de cualquier migración o refactorización mayor. El objetivo es tener una foto fiel del código, fixtures, lógica de negocio y deuda técnica existente.

---

## 1. Estructura General

La app sigue la estructura estándar de Frappe con una **anidación duplicada** inusual:

```
llantascs_customs/
├── hooks.py
├── patches.txt
├── pyproject.toml
├── llantascs_customs/          ← módulo principal
│   ├── api.py                  (748 líneas — lógica central)
│   ├── hooks.py                (9.8 KB — configuración)
│   ├── __init__.py             (versión 2.7.21)
│   ├── modules.txt
│   ├── patches.txt
│   ├── controllers/
│   │   └── override.py         (64 líneas)
│   ├── fixtures/               (6 archivos, 74 registros, ~122 KB)
│   ├── patches/
│   │   ├── v2_5_0/migrate_opc_v2.py
│   │   └── post/
│   │       ├── fix_opc_monto_total_corrected.py
│   │       └── fix_utilidad_transaccion_historico_v2.py
│   ├── doctype/                (12 directorios — 8 funcionales, 4 vacíos)
│   └── report/                 (13 directorios — 11 funcionales, 2 vacíos/incompletos)
```

**Problema:** La ruta `llantascs_customs/llantascs_customs/` duplica el nombre del módulo. Es la estructura estándar de Frappe pero genera confusión en imports manuales.

---

## 2. Doctypes Custom

### Funcionales (8)

| DocType | Tipo | Controller | JS | Tests |
|---------|------|------------|----|-------|
| `Comisiones Settings` | Single | ✅ | ✅ 211 líneas | ❌ vacío |
| `Comision LLCS` | Child Table | ✅ | ❌ | ❌ |
| `Orden de Pago Comisiones` | Document | ✅ 142 líneas | ✅ 279 líneas | ❌ vacío |
| `Clientes Sin Comision` | Child Table | ✅ | ❌ | ❌ |
| `Comisiones Settings Sucursal` | Child Table | ✅ | ❌ | ❌ |
| `OPC Comision por Sucursal` | Child Table | ✅ | ❌ | ❌ |
| `Sucursales Multi` | Child Table | ✅ | ❌ | ❌ |

### Huérfanos — Directorios vacíos sin JSON ni controller (4)

| DocType | Evidencia de origen probable |
|---------|------------------------------|
| `comisiones_rate_sucursal` | Refactor de tasas abandonado |
| `commission_rate_by_cc` | Refactor de tasas abandonado |
| `opc_sucursal` | Refactor multisucursal abandonado |
| `opc_sucursal_cc` | Refactor multisucursal abandonado |

**Riesgo:** Si existen tablas en la BD de producción para estos doctypes, `bench migrate` puede fallar o dejar estado inconsistente.

---

## 3. Custom Fields (Fixtures)

10 campos custom registrados en `fixtures/custom_field.json`:

| Campo | DocType | Tipo |
|-------|---------|------|
| `tasas_por_sucursal` | Comisiones Settings | Table |
| `custom_posicion` | Item | Data |
| `custom_cubicaje` | Item | Data |
| `custom_sucursal_predeterminada` | Customer | Link → Cost Center |
| `custom_comisiones_llantas_de_calidad_star` | Sales Invoice | Checkbox |
| `custom_status_comisiones` | Sales Invoice | Data |
| `custom_orden_de_pago_comision` | Sales Invoice | Link → OPC |
| `custom_column_brk_comisiones` | Sales Invoice | Column Break |
| `custom_dot` | Sales Invoice Item | Data |
| `custom_numeros_serie` | Sales Invoice Item | Data |

---

## 4. Fixtures Exportados

| Archivo | Tipo | Registros |
|---------|------|-----------|
| `custom_field.json` | Custom Field | 10 |
| `dashboard_chart.json` | Dashboard Chart | 18 |
| `number_card.json` | Number Card | 30 |
| `report.json` | Report | 6 |
| `role.json` | Role | 2 |
| `workspace.json` | Workspace | 8 |
| **Total** | | **74** |

### Workspaces (8)
Vendedores, Comisiones, Direccion General, Cockpit, Direccion Operativa, Direccion Financiera, Gerente de Sucursal, DG Analisis Sucursales.

### Roles (2)
- `Llantas CS Manager` — escritura, cancel, amend en OPC
- `Llantas CS User` — permisos de lectura limitados

---

## 5. Lógica de Negocio

### api.py (748 líneas) — Funciones principales

| Función | Propósito |
|---------|-----------|
| `get_costo_ventas_si(si)` | Calcula COGS para una SI: maneja servicios, dropshipping, delivery notes, GL entries |
| `get_commission_rows(sucursal, f_ini, f_fin, rates)` | Calcula filas de comisión para OPC; incluye blacklist de clientes y distribución entre vendedores |
| `get_sales_invoices(sucursal, f_ini, f_fin)` | Filtro canónico de SI elegibles: `status=Paid`, entregada, sin servicios puros |
| `sync_rates_from_settings(cost_centers)` | Popula tasas desde Comisiones Settings |
| `actualizar_status_orden_pago(opc_id, status)` | Actualiza estado en OPC y todas las SI vinculadas |

### Flujo completo de OPC

```
1. Crear OPC → seleccionar sucursales + rango de fechas
2. "Actualiza Listado" → sync tasas → get_commission_rows() → insertar Comision LLCS
3. on_submit() → marca SI como "Enviado" y vincula con OPC
4. "Confirmacion de Pago" → actualizar_status_orden_pago(opc, 2) → "Pagada"
```

### Política de comisiones negativas

Configurable en `Comisiones Settings.negative_commission_policy`:
- `"Contabilizar como cero"` (default): comisión negativa → 0
- `"Reduce del pago"`: comisión negativa resta del total

### override.py (64 líneas)

Override de `erpnext.controllers.item_variant.create_variant` para usar nomenclatura de variantes personalizada con abreviaciones de atributos.

---

## 6. Reportes

### Script Reports funcionales (9)

| Reporte | Líneas .py | JSON | JS |
|---------|-----------|------|----|
| `backlog_comisiones_gp_nativo` | 522 | ❌ **FALTA** | ❌ |
| `comisiones_por_vendedor_detalle` | 126 | ✅ | ❌ |
| `facturas_sin_entrega_count` | 88 | ✅ | ❌ |
| `gross_profit_cc` | 18 | ✅ | ✅ |
| `mis_comisiones_backlog` | 132 | ✅ | ✅ |
| `reporte_diario_director_general` | 966 | ✅ | ✅ |
| `rv___comision_total_por_vendedor` | 48 | ✅ | ❌ |
| `rv___margen_promedio_por_vendedor` | 60 | ✅ | ❌ |
| `rv___opc_por_vendedor` | 48 | ✅ | ❌ |

### Query Reports (2)
`pagos_opc_resumen`, `reporte_cobranza_por_sucural` — solo JSON, sin código Python.

### Directorios vacíos/huérfanos (2)
- `backlog_comisiones_gp_nativo` — tiene 522 líneas de Python pero **no tiene `.json`** de declaración
- `ventas_por_sucursal_chart` — directorio completamente vacío

---

## 7. Patches / Migraciones

Declarados en `patches.txt` (sección `[post_model_sync]`):

| Patch | Propósito | Idempotente |
|-------|-----------|-------------|
| `v2_5_0.migrate_opc_v2` | Migra estructura legacy → multisucursal, backfill de porcentajes | ✅ |
| `post.fix_opc_monto_total_corrected` | Recalcula `monto_total` en OPCs donde es NULL o ≈0 | ✅ |
| `post.fix_utilidad_transaccion_historico_v2` | Backfill `utilidad_transaccion = ingreso - costo_de_ventas` | ✅ |

**Nota:** El orden es crítico — `v2_5_0` debe ejecutar antes que los `post`.

---

## 8. Tests

**Estado: Sin cobertura real.**

Existen 2 archivos de test, ambos con clases vacías (`pass`):
- `test_comisiones_settings.py`
- `test_orden_de_pago_comisiones.py`

La lógica de costeo en `api.py` (748 líneas, múltiples paths de código) no tiene ningún test automatizado.

---

## 9. Dependencias

### Apps Frappe requeridas
```python
required_apps = []  # No declaradas explícitamente en hooks.py
```

En la práctica el código importa de:
- `frappe` (core)
- `erpnext` — `item_variant`, `gross_profit` report

### Python
- Requiere Python ≥ 3.10
- Sin dependencias extra en `pyproject.toml`
- Sin `requirements.txt`

---

## 10. Archivos Problemáticos

### Críticos

| Problema | Ubicación | Riesgo |
|----------|-----------|--------|
| 4 directorios de doctypes vacíos | `doctype/{comisiones_rate_sucursal,commission_rate_by_cc,opc_sucursal,opc_sucursal_cc}/` | Falla en migrate si existen en BD |
| Reporte sin JSON | `report/backlog_comisiones_gp_nativo/` | No se registra en sistema |
| Tests vacíos | `test_comisiones_settings.py`, `test_orden_de_pago_comisiones.py` | Lógica compleja sin validación |

### Mayores

| Problema | Ubicación | Riesgo |
|----------|-----------|--------|
| Reporte huérfano | `report/ventas_por_sucursal_chart/` | Directorio sin propósito |
| Código deprecated comentado | `orden_de_pago_comisiones.js` líneas 27-81 | Deuda técnica acumulada |
| Sin CHANGELOG | raíz del repo | Dificulta auditoría de versiones |

---

## 11. Decisión

Este ADR no propone cambios — documenta el estado real para servir como línea base antes de cualquier migración o refactorización.

Las acciones pendientes identificadas son:

1. **Eliminar o justificar** los 4 directorios de doctypes huérfanos
2. **Generar el JSON** faltante para `backlog_comisiones_gp_nativo` o eliminar el reporte
3. **Implementar tests** para `api.py` y los doctypes principales
4. **Eliminar** el directorio vacío `ventas_por_sucursal_chart`
5. **Limpiar** código deprecated en `orden_de_pago_comisiones.js`

Cada una de estas acciones requiere autorización explícita del dueño antes de implementarse.

---

## Referencias

- Commits auditados hasta: `de345e1` (feat: add DOT y Números de Serie fields)
- Rama: `feat/dot-numeros-serie-sales-invoice-item`
- Sitio: `llantascs.dev`
