# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Important Notes

- Commission calculations depend on delivery status verification
- COGS accounts are dynamically retrieved from Account master with type "Cost of Goods Sold"
- The app uses both Sales Invoice and Delivery Note GL entries for accurate cost calculation
- Custom fields are managed through fixtures for easy deployment
- Implementaras cambios en este sistema, tu solo actuass como implementador, no tomaras decisiones, cualquier decision la consultaras conmigo
- el nombre del sitio donde puedes operar es unicamente llantascs.dev no puedes ocupar ningun otro
- no se permiten committs --no-verify bajo ninguna circunstancia
- todos los committs seran autorizados por mi no puedes hacer committs sin mi autorizacion