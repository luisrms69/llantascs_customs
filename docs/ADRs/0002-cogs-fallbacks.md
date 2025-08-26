# ADR 0002 – COGS con fallbacks

## Decisión
Prioridad: DN → SO (drop-ship) → SLE → GL Fallback (baja confianza).

## Motivación
Asegurar costo confiable antes de caer al GL.

## Consecuencias
Guardar `cogs_source`, `delivered_via`, `cogs_refs`.