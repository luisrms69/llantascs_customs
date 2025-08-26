# ADR 0001 – Política de márgenes negativos

## Decisión
Modos: CERO / NEGATIVO_COMPENSA / REQUIERE_APROBACION.  
Se almacenan `margen_ajustado_raw`, origen del negativo y totales (bruto/negativos/neto).

## Motivación
Evitar pagar en negativo por diferimiento y dar trazabilidad.

## Consecuencias
Nuevos campos en child y totales en padre. Tests dedicados.