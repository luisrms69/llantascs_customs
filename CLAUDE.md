# CLAUDE.md — llantascs_customs

## Estado de migración
- **Migrada a v16:** No
- **Versión origen:** v15 (Frappe 15.97, ERPNext 15.95)
- **En producción:** Sí — llantascs.dev (cliente LlantasCS)
- **Branch activo:** feat/dot-numeros-serie-sales-invoice-item
- **Sitio de desarrollo:** llantascs.dev
- **Versión:** 2.7.21

## Entorno
Ver contexto global en `frappe-infrastructure/.claude/CLAUDE.md`.

**Bench:** /home/erpnext/frappe-bench  
**Comandos siempre con --site:**
```bash
bench --site llantascs.dev migrate
bench --site llantascs.dev export-fixtures --app llantascs_customs
bench --site llantascs.dev run-tests --app llantascs_customs
bench build --app llantascs_customs
```
**NUNCA:** `bench migrate` sin --site (afecta otros sitios del bench compartido)

---

## Qué hace esta app

App de customización para cliente LlantasCS. Implementa el sistema de comisiones de vendedores sobre ERPNext: cálculo de comisiones por sucursal, generación de Órdenes de Pago de Comisiones (OPC), reportes de dirección general, y workspaces personalizados por rol.

---

## DocTypes principales

| DocType | Tipo | Qué hace |
|---|---|---|
| `Comisiones Settings` | Single | Configuración global de comisiones — tasas por sucursal, política de negativos |
| `Orden de Pago Comisiones` | Document — Submittable | OPC: agrupa comisiones de vendedores por período y sucursal |
| `Comision LLCS` | Child Table | Fila de comisión individual dentro de una OPC |
| `Clientes Sin Comision` | Child Table | Blacklist de clientes excluidos del cálculo |
| `Comisiones Settings Sucursal` | Child Table | Tasas de comisión por sucursal |
| `OPC Comision por Sucursal` | Child Table | Detalle de comisión por sucursal en OPC |
| `Sucursales Multi` | Child Table | Selección de múltiples sucursales |

### DocTypes huérfanos (4 directorios vacíos — no tocar sin verificar BD)
`comisiones_rate_sucursal`, `commission_rate_by_cc`, `opc_sucursal`, `opc_sucursal_cc`

---

## Lógica crítica

### Flujo completo de OPC
```
1. Crear OPC → seleccionar sucursales + rango de fechas
2. "Actualiza Listado" → sync tasas → get_commission_rows() → insertar Comision LLCS
3. on_submit() → marca SI como "Enviado" y vincula con OPC
4. "Confirmacion de Pago" → actualizar_status_orden_pago() → "Pagada"
```

### api.py (748 líneas) — funciones clave
- `get_costo_ventas_si(si)` — calcula COGS: servicios, dropshipping, delivery notes, GL entries
- `get_commission_rows(sucursal, f_ini, f_fin, rates)` — calcula comisiones con blacklist y distribución por vendedor
- `get_sales_invoices(sucursal, f_ini, f_fin)` — filtro canónico: `status=Paid`, entregada, sin servicios puros
- `actualizar_status_orden_pago(opc_id, status)` — actualiza OPC y todas las SI vinculadas

### Política de comisiones negativas
Configurable en `Comisiones Settings.negative_commission_policy`:
- `"Contabilizar como cero"` (default)
- `"Reduce del pago"`

### Custom Fields sobre ERPNext
- `Sales Invoice`: custom_comisiones_llantas_de_calidad_star, custom_status_comisiones, custom_orden_de_pago_comision
- `Sales Invoice Item`: custom_dot, custom_numeros_serie
- `Item`: custom_posicion, custom_cubicaje
- `Customer`: custom_sucursal_predeterminada

### Override de ERPNext
`controllers/override.py` — override de `erpnext.controllers.item_variant.create_variant` para nomenclatura de variantes con abreviaciones de atributos.

---

## Fixtures

6 archivos, 74 registros totales:
- `custom_field.json` — 10 custom fields
- `dashboard_chart.json` — 18 charts
- `number_card.json` — 30 cards
- `report.json` — 6 reportes
- `role.json` — 2 roles (Llantas CS Manager, Llantas CS User)
- `workspace.json` — 8 workspaces (Vendedores, Comisiones, Direccion General, Cockpit, etc.)

---

## Reportes

9 Script Reports funcionales. El más crítico:
- `reporte_diario_director_general` (966 líneas) — reporte principal de dirección
- `backlog_comisiones_gp_nativo` (522 líneas) — **falta el .json de declaración, no se registra en sistema**

---

## Patches

3 patches en `patches.txt` sección `[post_model_sync]`. Todos idempotentes. Orden crítico:
1. `v2_5_0.migrate_opc_v2` — migración estructura legacy → multisucursal
2. `post.fix_opc_monto_total_corrected`
3. `post.fix_utilidad_transaccion_historico_v2`

---

## Problemas conocidos

1. **4 directorios de DocTypes vacíos** — `comisiones_rate_sucursal`, `commission_rate_by_cc`, `opc_sucursal`, `opc_sucursal_cc`. Si existen tablas en BD de producción, `bench migrate` puede fallar. No eliminar sin verificar primero.

2. **`backlog_comisiones_gp_nativo`** — tiene 522 líneas de Python pero **falta el `.json`**. No está registrado en el sistema.

3. **Sin tests reales** — 748 líneas de lógica en `api.py` sin ningún test automatizado. Los 2 archivos de test existentes tienen clases vacías.

4. **Código deprecated** en `orden_de_pago_comisiones.js` líneas 27-81.

5. **Directorio vacío** `report/ventas_por_sucursal_chart/`.

---

## Dependencias

**Apps en el mismo bench:** erpnext, facturacion_mx, dfp_external_storage, hrms, wiki  
**Dependencias externas:** Ninguna  
**Sin `required_apps` declarado** en hooks.py (depende implícitamente de erpnext)

---

## Tests

```bash
bench --site llantascs.dev run-tests --app llantascs_customs
```

**Sin cobertura real.** Los 2 archivos de test existentes están vacíos. La lógica compleja de api.py no tiene tests.

---

## Antes de cada PR

- [ ] Fixtures exportados si hubo cambios de Custom Fields, Roles, Workspaces, Dashboard Charts
- [ ] Patch creado si hay cambios de esquema con datos
- [ ] `bench --site llantascs.dev migrate` limpio
- [ ] Verificar que los 4 DocTypes huérfanos no causan problemas
- [ ] Ver checklist global en `frappe-infrastructure/CONTRIBUTING.md`

---

## Auditoría pre-migración

Ver `docs/adr/0000-estado-real-pre-migracion.md` — estado completo documentado el 2026-04-30.
