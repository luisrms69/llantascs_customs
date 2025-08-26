# Arquitectura & módulos

Componentes:
- **Comisiones Settings** (Single): toggles y políticas globales.
- **Orden de Pago Comisiones** (padre): periodo, sucursal/grupo, totales.
- **Comision LLCS** (child): renglones por factura; márgenes, COGS, comisión.

Flujos clave:
- `api.apply_reduction(opc_name)`: ingreso ajustado, márgenes, COGS (resolver).
- `api.evaluate_eligibility(opc_name)`: entrega/pago/persona; fija `comision_a_pagar`.
- `eligibility_service.py`: helpers entrega/pago/persona.
- `delivery_cogs_resolver.py`: pipeline COGS (DN → SO → SLE → GL fallback).

Hook:
- `orden_de_pago_comisiones.validate`: totales (bruto, negativos, neto pagable).