# Resolución de COGS

Orden de búsqueda:
1) Delivery Notes (docstatus=1; ignora drafts/canceled)
2) Sales Order (drop-ship)
3) Stock Ledger Entry (SLE)
4) GL Fallback (baja confianza)

Metadatos por renglón:
- `cogs_resuelto`, `cogs_source`, `delivered_via`, `cogs_refs`.