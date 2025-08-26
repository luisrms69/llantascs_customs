# llantascs_customs

Extensiones de comisiones para ERPNext/Frappe (cliente único).  
Este repo contiene la app, lógica de cálculo, validaciones y reportes.

- Documentación: ver [`docs/index.md`](docs/index.md)
- Ambiente: Frappe/ERPNext (ver `Procfile`, `requirements.txt`)
- Convenciones de commit: Conventional Commits

## Levantar en desarrollo (rápido)
```bash
bench start
bench --site <site> migrate
bench --site <site> run-tests --app llantascs_customs
```

## Puntos de entrada

* `llantascs_customs/llantascs_customs/api.py` – `apply_reduction`, `evaluate_eligibility`
* `doctype/orden_de_pago_comisiones/` – DocType padre (hooks, JS)
* `doctype/comisiones_settings/` – configuración global
* `eligibility_service.py`, `delivery_cogs_resolver.py` – lógica de negocio