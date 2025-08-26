# Política de márgenes negativos

Distinción:
- **Original negativo** (antes de diferimiento).
- **Negativo por ajuste** (ingreso ajustado < costo).

Modos:
- **CERO**: margen ≤ 0 → comisión = 0.
- **NEGATIVO_COMPENSA**: comisión negativa compensa; opcional "solo si original negativo".
- **REQUIERE_APROBACION**: bandera y comisión 0.

Totales en Orden:
- `total_comision_bruta` (≥0), `total_compensaciones_negativas` (≤0),
- `monto_total` (neto; cap a 0 salvo `permitir_total_orden_negativo=1`).