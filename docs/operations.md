# Operaciones (Runbook)

## Deploy
```bash
bench --site <site> migrate
bench --site <site> clear-cache
bench --site <site> restart
```

## Post-deploy

* Revisar `Comisiones Settings`.
* Probar Orden (dos botones).
* Validar totales con positivo+negativo.

## Rollback

* Revertir commit.
* Si hubo patch de datos: restaurar snapshot.