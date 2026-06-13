# CONTINUITY.md — llantascs_customs

**Fecha:** 2026-06-12
**Rama activa:** `fix/folio-fiscal-bridge-get-invoice-uuid`
**Tarea actual:** Migración de dependencia fiscal — sustituir lectura de campo legacy `custom_folio_fiscal` por función puente `get_invoice_uuid()` de `facturacion_mexico`

---

## Recuperación rápida

Estoy trabajando en:
Primera etapa de la migración de `llantascs_customs` para usar `facturacion_mexico`
en lugar de `facturacion_mx`. La única dependencia fiscal encontrada era el campo
`custom_folio_fiscal` en Sales Invoice. Se resolvió usando `get_invoice_uuid()`.

Plan que estoy siguiendo:
Migración `facturacion_mx` → `facturacion_mexico` en el sitio LlantasCS. Paso actual:
ajuste de dependencia en `llantascs_customs/api.py`.

Objetivo inmediato:
PR de este cambio a `develop`. Luego: inventario completo de custom fields legacy
de `facturacion_mx` en toda la app (no solo Customer/SI).

Criterio de avance:
PR mergeado + inventario de campos legacy generado.

---

## Estado actual

### Ya cerrado
- ✅ Auditoría de referencias fiscales en `llantascs_customs` — solo `custom_folio_fiscal`
- ✅ Reemplazo de `custom_folio_fiscal` por `get_invoice_uuid()` en `api.py`
- ✅ Fix F823 ruff — import json duplicado dentro de función

### En progreso
- Commit + PR de `fix/folio-fiscal-bridge-get-invoice-uuid` → `develop`

### Pendiente inmediato
1. Push de la rama y PR a `develop`
2. Inventario completo custom fields legacy de `facturacion_mx` en TODA la app
3. Mapeo de campos legacy vs campos actuales de `facturacion_mexico`
4. Decisión campo por campo (migrar / ignorar / mantener temporal)
5. One-off SQL para copiar datos donde aplique

### No repetir
- `custom_folio_fiscal` ya NO existe como campo activo — no es un Custom Field de `facturacion_mexico`
- El JS `orden_de_pago_comisiones.js:34` está comentado como LEGACY DEPRECATED — no tocarlo
- `get_invoice_uuid()` es la función canónica según ADR 0014 de `facturacion_mexico`

---

## Decisiones vigentes

- No agregar campo snapshot de UUID a Sales Invoice — ADR 0014 de `facturacion_mexico` lo prohíbe
- `llantascs_customs` NO debe hacer `frappe.db.get_value()` directo sobre `Factura Fiscal Mexico`
  — usar la función puente de `facturacion_mexico.facturacion_fiscal.utils`
- `develop` es la rama protegida de `llantascs_customs` (equivalente a `main`)

---

## Archivos relevantes ahora

### Leer primero
- `facturacion_mexico/docs/adr/0014-diagnostico-conectividad-si-ffm.md`
- `facturacion_mexico/facturacion_fiscal/utils.py`

### Probablemente editar
- `llantascs_customs/llantascs_customs/api.py` (ya editado en este PR)

### No tocar
- `orden_de_pago_comisiones.js` — código deprecated, no modificar
- `facturacion_mexico/hooks.py` — sin cambios para este PR

---

## Riesgos / cuidados

- El inventario de campos legacy DEBE hacerse sobre el bench v15 (donde `facturacion_mx`
  está instalado) O consultando los fixtures de `facturacion_mx` directamente
- Algunos campos pueden tener datos históricos importantes — no borrar sin one-off de migración
