# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Non-Negotiables (Límites duros)
- Operar **solo** sobre el sitio `llantascs.dev`.
- Nunca usar `--no-verify` en commits.
- Ningún commit o PR se considera válido sin autorización del dueño.
- No crear/modificar DocTypes, fixtures o campos salvo instrucción explícita.
- No inventar lógica nueva: implementar **únicamente** lo que la tarea indica.
- No mover este archivo (`CLAUDE.md`) a `docs/`; siempre vive en la raíz.

## Stop Conditions (detener y preguntar)
Claude debe detenerse y pedir confirmación si:
- Aparece la necesidad de cambiar fixtures o Doctypes sin orden expresa.
- Un cambio afecta filtros, totales o reportes sin que lo haya solicitado el dueño.
- Los resultados de filtrado (ej. número de facturas) cambian en órdenes de magnitud.
- Se detecta que la lógica de preview escribe en la base de datos.

## Project Overview

This is a Frappe/ERPNext custom app called "Llantascs Customs" for customizations specific to Llantas CS (a tire company). It provides commission management functionality, item variant creation customizations, and sales reporting features.

## Architecture

### App Structure
- **Main app directory**: `llantascs_customs/`
- **Core module**: `llantascs_customs/llantascs_customs/`
- **Custom doctypes**: Located in `llantascs_customs/llantascs_customs/doctype/`
- **API functions**: Located in `llantascs_customs/llantascs_customs/api.py`
- **Controllers/Overrides**: Located in `llantascs_customs/controllers/override.py`

### Key Components

#### Commission Management System
- **Comisiones Settings**: Configuration doctype for commission rates
- **Comision LLCS**: Individual commission records
- **Orden de Pago Comisiones**: Commission payment orders
- Commission calculation based on COGS (Cost of Goods Sold) and delivery status
- Status tracking: "Sin Enviar", "Enviado", "Pagada"

#### Item Variant Customization
- Custom item variant creation logic in `controllers/override.py`
- Overrides ERPNext's standard variant creation to use custom naming conventions
- Handles attribute-based variants with abbreviations

#### Sales Invoice Extensions  
- Custom fields for commission tracking
- Integration with delivery status validation
- COGS calculation from both Sales Invoice and Delivery Note GL entries

## Development Commands

This is a standard Frappe app. Common development tasks should use Frappe's bench commands:

```bash
# Install/update app in site
bench install-app llantascs_customs

# Run tests
bench run-tests --app llantascs_customs

# Migrate after schema changes
bench migrate

# Build assets if JavaScript/CSS changes
bench build

# Clear cache during development
bench clear-cache
```


### Git & PR Policy (refuerzo)
- Prohibido usar `--no-verify`.
- Cada commit/PR debe estar autorizado por el dueño.
- Todos los cambios deben venir acompañados de pruebas automáticas relacionadas.
- Si el PR implica documentación, Claude solo debe modificar **los archivos y secciones indicados explícitamente** por el dueño.


## Testing

Test files are located alongside their respective doctype files:
- `test_comisiones_settings.py`
- `test_orden_de_pago_comisiones.py`

## Configuration

### Hooks Configuration
- Custom JavaScript for Sales Invoice: `core_doctype.js`
- Method overrides defined in `hooks.py`
- Custom field fixtures managed via `fixtures` configuration

### Key Override
- `erpnext.controllers.item_variant.create_variant` → `custom_create_variant`

## Common Bench Command Errors and Corrections

### Site-specific Commands
- ❌ **WRONG**: `bench clear-cache` (applies to default site only)
- ✅ **CORRECT**: `bench --site llantascs.dev clear-cache`

- ❌ **WRONG**: `bench migrate`
- ✅ **CORRECT**: `bench --site llantascs.dev migrate`

- ❌ **WRONG**: `bench execute function`
- ✅ **CORRECT**: `bench --site llantascs.dev execute function`

- ❌ **WRONG**: `bench --site llantascs.dev restart` 
- ✅ **CORRECT**: `bench restart` (no --site flag for restart command)

### Module Import Paths for bench execute
- ❌ **WRONG**: `llantascs_customs.llantascs_customs.module.function`
- ✅ **CORRECT**: `llantascs_customs.module.function` (single app name)

### Console and Execute Commands
- `bench console` exits immediately - use `bench execute` instead
- For temporary functions, use `one_offs` directory structure:
  ```
  apps/llantascs_customs/llantascs_customs/one_offs/
  ├── __init__.py
  └── script_name.py
  ```
- Execute with: `bench --site llantascs.dev execute llantascs_customs.one_offs.script_name.function`

## Cuándo debes actualizar `docs/`
Actualiza la documentación en **cualquier PR** que haga alguno de estos cambios:
- Campos nuevos o eliminados en DocTypes (JSON).
- Cambios en lógica de negocio: `apply_reduction`, `evaluate_eligibility`, resolvers, hooks.
- Nuevos toggles o defaults en **Comisiones Settings**.
- Cambios en reportes (campos, SQL, columnas, KPIs).
- Migraciones/patches que afecten datos de producción o interpretación de reportes.
- Cambios en totales de Orden o políticas (márgenes negativos, elegibilidad).

## Qué debes actualizar
- `docs/settings.md`: nuevos campos, defaults y efectos.
- `docs/commission-policy.md`: si cambia la política o su efecto en totales.
- `docs/cogs-resolution.md`: si cambia el orden o metadatos del resolver.
- `docs/eligibility.md`: si cambia alguna regla de gate (entrega/pago/persona/tolerancia).
- `docs/reports.md`: si cambia qué se suma o cómo se presentan totales/KPIs.
- `docs/operations.md`: si cambia el runbook (deploy/rollback).
- `docs/migrations.md` y `docs/playbooks/*`: si se agregan pasos de backfill.
- `docs/ADRs/*`: agrega una ADR por cada decisión de arquitectura relevante.

## Estándar mínimo por PR
- Incluir actualización de **al menos un archivo** en `docs/`.
- Si el cambio es sustantivo, incluir **nueva ADR** en `docs/ADRs/`.
- Actualizar `docs/CHANGELOG.md` con un bullet conciso.

## Cómo validar
- Revisa ortografía rápida.
- Verifica rutas/archivos citados existen.
- Si el cambio afecta tests, agrega/actualiza sección en `docs/testing.md`.

## Anti-reglas
- No merges a main sin tocar docs si cambiaste lógica o schema.
- No dejes referencias a campos antiguos sin nota de transición.
- No introduzcas siglas nuevas sin definir en `docs/glossary.md`.


## Important Notes

- Commission calculations depend on delivery status verification
- COGS accounts are dynamically retrieved from Account master with type "Cost of Goods Sold"
- The app uses both Sales Invoice and Delivery Note GL entries for accurate cost calculation
- Custom fields are managed through fixtures for easy deployment
- Implementaras cambios en este sistema, tu solo actuass como implementador, no tomaras decisiones, cualquier decision la consultaras conmigo
- el nombre del sitio donde puedes operar es unicamente llantascs.dev no puedes ocupar ningun otro
- no se permiten committs --no-verify bajo ninguna circunstancia
- todos los committs seran autorizados por mi no puedes hacer committs sin mi autorizacion
- claude code solo puede implementar codigo que se le entregue, cualquier codigo que quiera generar debe ser aprobado por el usuario