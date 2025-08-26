# Workflows

## Flujo estándar
1. Crear **Orden de Pago** (periodo, sucursal/grupo).
2. **Aplicar Reducción** → márgenes (y COGS si falta).
3. **Evaluar Elegibilidad** → entrega/pago/persona; fija `comision_a_pagar`.
4. **Guardar/Submit** → totales (bruto, negativos, neto).

## Entregado
- Servicios: entregados por definición (si `validar_entrega_total=1`).
- Stock: requiere `delivered_qty >= qty` (o `update_stock=1` en SI).

## Pagado
- `status="Paid"` **y** `outstanding_amount=0` (o dentro de `tolerancia_pago_monetaria`).