# CONTINUITY.md — llantascs_customs

**Fecha:** 2026-06-13
**Rama activa:** `fix/folio-fiscal-bridge-get-invoice-uuid`
**Tarea actual:** PR #XX abierto — sustituye campo legacy custom_folio_fiscal por get_invoice_uuid()

---

## Recuperación rápida

Estoy trabajando en:
PR abierto en `llantascs_customs` hacia `develop` para eliminar dependencia del campo
legacy `custom_folio_fiscal` (de `facturacion_mx`) usando la función puente oficial
`get_invoice_uuid()` de `facturacion_mexico`.

Plan que estoy siguiendo:
Migración `facturacion_mx` → `facturacion_mexico`. Este PR es el Paso 1 de la
migración de `llantascs_customs`.

Objetivo inmediato:
Merge del PR. Luego: inventario de custom fields legacy de `facturacion_mx` en la BD
del sitio LlantasCS (comparar campos existentes vs lo que provee `facturacion_mexico`).

Criterio de avance:
PR mergeado + inventario de campos legacy generado.

---

## Estado actual

### Ya cerrado
- ✅ Auditoría de referencias fiscales en `llantascs_customs` — solo `custom_folio_fiscal`
- ✅ Reemplazo de `custom_folio_fiscal` por `get_invoice_uuid()` en `api.py`
- ✅ Fix F823 ruff — import json duplicado dentro de función
- ✅ Commit `826c18b` — solo `api.py`
- ✅ Push a upstream

### En progreso
- PR abierto hacia `develop`

### Pendiente inmediato
1. Merge del PR
2. Inventario de custom fields legacy de `facturacion_mx` en BD de LlantasCS
3. Mapeo campos legacy vs campos de `facturacion_mexico`
4. Decisión campo por campo + one-off SQL donde aplique

### No repetir
- `custom_folio_fiscal` ya NO existe como campo activo — no usar
- No hacer `frappe.db.get_value()` directo sobre `Factura Fiscal Mexico` desde `llantascs_customs`
- El JS `orden_de_pago_comisiones.js:34` está comentado como LEGACY DEPRECATED — no tocar
- `develop` es la rama protegida de `llantascs_customs`

---

## Decisiones vigentes

- Usar `get_invoice_uuid()` de `facturacion_mexico.facturacion_fiscal.utils`
- No agregar campo snapshot de UUID en Sales Invoice (ADR 0014 de `facturacion_mexico`)
- PRs de `llantascs_customs` van a `develop`, no a `main`

---

## Riesgos / cuidados

- SIs legacy sin `fm_factura_fiscal_mx` retornan `""` — comportamiento correcto
- El inventario de campos legacy DEBE compararse contra lo que `facturacion_mexico`
  provee en la BD del sitio LlantasCS (no solo en fixtures)
