# CLAUDE.md — llantascs_customs

> **Reglas de operación Claude Code** (commits, PRs, base de datos, flujo de trabajo, prohibiciones git):
> Ver `/home/erpnext/Developer/frappe-infrastructure/.claude/CLAUDE.md`

---

## Estado del proyecto

- **Migración v15 → v16:** En curso
- **Bench activo:** `/home/erpnext/frappe-bench-v16`
- **Branch protegida:** `develop` (nunca commitear directamente)
- **Versión:** 2.7.21
- **En producción:** Sí — llantascs.dev (cliente LlantasCS, bench v15)

---

## Sites de desarrollo y prueba

| Site | Bench | Propósito | Notas |
|---|---|---|---|
| `llantascs-v16.dev` | frappe-bench-v16 | Desarrollo activo v16 | Features, migrate, export-fixtures |
| `test-llantascs.localhost` | frappe-bench-v16 | Tests unitarios | Solo para `bench run-tests` — nunca modificar manualmente |
| `llantascs.dev` | frappe-bench | Producción / referencia v15 | No usar para desarrollo nuevo |

**Reglas de uso:**
- `bench migrate` → siempre con `--site`. Nunca sin site en bench compartido.
- `bench run-tests` → siempre `test-llantascs.localhost` — nunca en el site de desarrollo.
- `bench export-fixtures` → `llantascs-v16.dev`

**Apps en test-llantascs.localhost:** frappe, erpnext, llantascs_customs

## Entorno
Ver contexto global en `frappe-infrastructure/.claude/CLAUDE.md`.

**Comandos frecuentes (bench v16):**
```bash
bench --site llantascs-v16.dev migrate
bench --site llantascs-v16.dev export-fixtures --app llantascs_customs
bench --site llantascs-v16.dev run-tests --app llantascs_customs
bench build --app llantascs_customs
```
**NUNCA:** `bench migrate` sin `--site` — afecta todos los sites del bench compartido

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

**Integración con facturación (PR #25):** dentro de `get_commission_rows`, el UUID fiscal de Sales Invoice se obtiene mediante `get_invoice_uuid(si_doc.name)`, importado de `facturacion_mexico.facturacion_fiscal.utils`. En esta lógica fueron eliminadas las lecturas del campo legacy `custom_folio_fiscal`. No afirmar que el campo dejó de usarse en toda la app salvo que una búsqueda exhaustiva confirme que no existen otras referencias.

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
`controllers/override.py` — override de `erpnext.controllers.item_variant.create_variant` para nomenclatura de variantes con abreviaciones de atributos. Desde PR #24, `custom_create_variant` omite atributos sin valor (`if value is not None`) para evitar `ValidationError` al crear variantes con atributos parciales.

### Evento customer en Sales Invoice (core_doctype.js)
Al seleccionar cliente: si el cliente tiene `custom_sucursal_predeterminada` **y** la SI no tiene `cost_center`, se asigna la sucursal. Si el cliente no tiene sucursal, **no se toca** el `cost_center`. Un `cost_center` ya definido siempre se respeta (PR #26).

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
- `backlog_comisiones_gp_nativo` (522 líneas) — Script Report **activo**. Su definición está en `fixtures/report.json` (no como `.json` local junto al `.py`). Referenciado desde workspace y sidebar de Comisiones.

---

## Patches

3 patches en `patches.txt` sección `[post_model_sync]`. Todos idempotentes. Orden crítico:
1. `v2_5_0.migrate_opc_v2` — migración estructura legacy → multisucursal
2. `post.fix_opc_monto_total_corrected`
3. `post.fix_utilidad_transaccion_historico_v2`

---

## Problemas conocidos

1. **4 directorios de DocTypes vacíos** — `comisiones_rate_sucursal`, `commission_rate_by_cc`, `opc_sucursal`, `opc_sucursal_cc`. Si existen tablas en BD de producción, `bench migrate` puede fallar. No eliminar sin verificar primero.

2. **`backlog_comisiones_gp_nativo`** — Script Report **activo**, no huérfano. Su declaración vive en `fixtures/report.json` con `report_script` apuntando al módulo Python y 3 roles asignados (System Manager, Llantas CS Manager, Llantas CS User). Está en la whitelist de export de `hooks.py` y referenciado en `fixtures/workspace.json` y `workspace_sidebar/comisiones.json`. **Sus archivos Python NO deben eliminarse aisladamente** — borrarlos sin retirar el fixture y las referencias dejaría el reporte registrado en BD apuntando a un módulo inexistente (ImportError al abrirlo).

3. **Sin tests reales** — 748 líneas de lógica en `api.py` sin ningún test automatizado. Los 2 archivos de test existentes tienen clases vacías.

4. **Código deprecated** en `orden_de_pago_comisiones.js` líneas 27-81.

5. **Directorio vacío** `report/ventas_por_sucursal_chart/`.

6. **PRs #24, #25 y #26 sin pruebas automatizadas** — ninguna añadió tests. La cobertura pendiente es especialmente relevante para la integración `get_invoice_uuid`, el evento `customer` de Sales Invoice y el override de creación de variantes.

---

## Dependencias

- **Apps presentes en el bench:** erpnext, facturacion_mx, facturacion_mexico, dfp_external_storage, hrms, wiki.
- **Dependencia entre apps:** `api.py` importa directamente `get_invoice_uuid` desde `facturacion_mexico.facturacion_fiscal.utils`. Por lo tanto, las funciones que cargan ese módulo requieren que `facturacion_mexico` esté instalado y disponible.
- **Dependencias Python externas adicionales:** ninguna identificada.
- `hooks.py` no declara actualmente `required_apps`. Evaluar por separado si `facturacion_mexico` debe declararse formalmente; no modificarlo como parte de esta actualización documental.

---

## Tests

```bash
bench --site test-llantascs.localhost run-tests --app llantascs_customs
```

**NUNCA** correr tests en `llantascs-v16.dev` — usar siempre `test-llantascs.localhost`.

**Sin cobertura real.** Los 2 archivos de test existentes están vacíos. La lógica compleja de api.py no tiene tests.

---

## Auditoría pre-migración

Ver `docs/adr/0000-estado-real-pre-migracion.md` — estado completo documentado el 2026-04-30.

---

## REGLAS GIT — LLANTASCS CUSTOMS

### Antes de cada commit

- Correr linters en archivos modificados:
  ```bash
  ruff format <archivos .py modificados>
  npx prettier@2.7.1 --write <archivos .js modificados>
  ```

### Antes de cada PR

- [ ] Linters pasados (ver arriba)
- [ ] Fixtures exportados si hubo cambios de Custom Fields, Roles, Workspaces, Dashboard Charts
- [ ] Patch creado si hay cambios de esquema — **requiere autorización explícita del usuario**
- [ ] `bench --site llantascs-v16.dev migrate` limpio
- [ ] Ver checklist global en `frappe-infrastructure/CONTRIBUTING.md`

### PROHIBICIÓN ABSOLUTA — NUNCA TRABAJAR EN DEVELOP

**`develop` es la rama protegida de llantascs_customs. Es el equivalente a `main` en otros proyectos del ecosistema.**

- **Nunca implementar cambios estando en `develop`.**
- **Nunca crear commits estando en `develop`.**
- **Nunca preparar commits estando en `develop`.**
- Todo cambio debe iniciar en una rama feature creada desde `develop` limpio.
- Antes de tocar cualquier archivo, confirmar rama: `git branch --show-current`
- Si la rama es `develop`, **detenerse inmediatamente** y crear rama feature.
- Si ya hay cambios en `develop`, **detenerse** y pedir autorización para rescatarlos a rama.
- `/ship commit` y `/ship commit-push` deben rechazar si la rama es `develop`.
- `/ship pr` debe exigir rama distinta de `develop`.

### Reglas específicas del proyecto

- PRs siempre a `develop` — es la rama default/protegida de este repo
- La rama `develop` es el equivalente a `main` (uniformizar nombre en el futuro)
- Site de desarrollo v16: `llantascs-v16.dev`
- Site de desarrollo v15 (producción activa): `llantascs.dev`
