# Migraciones / Backfilling (fase final)

Objetivo: normalizar legacy a `comision_a_pagar` y totales.

Checklist:
- Snapshot/backup.
- Lotes: `apply_reduction` + `evaluate_eligibility`.
- Confirmar conteos y totales (antes/después).
- Reportes consumen `comision_a_pagar`.

No ejecutar en dev mientras la lógica siga cambiando.