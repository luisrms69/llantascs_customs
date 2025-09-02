# ADR-003: Sistema de Exclusión de Clientes con Fechas de Vigencia

**Status**: Aceptado  
**Date**: 2025-09-02  
**Author**: Claude Code  
**Version**: v2.3.0  

## Context

El sistema de comisiones necesitaba la capacidad de excluir clientes específicos de los cálculos de comisión. El caso inmediato era "AUTOTRANSPORTES DE ORIENTE ESTRELLA AZUL" que no debería generar comisiones, pero pueden existir otros casos similares en el futuro.

### Requerimientos Identificados
1. **Exclusión Flexible**: No todos los clientes se excluyen permanentemente
2. **Control Temporal**: Algunos clientes pueden ser excluidos solo por períodos específicos
3. **Performance**: El filtrado debe ser eficiente y no impactar el rendimiento
4. **Mantenimiento**: La configuración debe ser fácil de gestionar sin cambios de código
5. **Auditoría**: Debe ser claro por qué y cuándo se excluye un cliente

## Decision

Implementar un **Sistema de Exclusión de Clientes con Fechas de Vigencia** que permita configurar períodos de exclusión flexibles a través de la interfaz de Comisiones Settings.

### Arquitectura Elegida

#### 1. Child DocType: "Clientes Sin Comision"
```json
Fields:
- customer (Link to Customer, Required): Cliente a excluir
- start_date (Date, Optional): Inicio del período de exclusión
- end_date (Date, Optional): Fin del período de exclusión  
- motivo (Small Text, Optional): Razón de la exclusión
```

#### 2. Integration con Comisiones Settings
- Nueva tabla `clientes_sin_comision` en el Single DocType
- Nueva sección "Clientes sin comisión" en la interfaz
- Configuración centralizada con otros parámetros de comisión

#### 3. Filtrado Temprano en API
- Función `_build_blacklist_with_dates()`: construye mapa de exclusiones
- Función `_is_blacklisted()`: evalúa si cliente está excluido en fecha específica
- Integración en `get_commission_rows()`: filtrado antes del cálculo de COGS

### Lógica de Fechas de Vigencia

#### Escenarios Soportados
1. **Exclusión Permanente**: Sin fechas → siempre excluido
2. **Exclusión con Inicio**: Solo start_date → excluido desde fecha en adelante
3. **Exclusión con Fin**: Solo end_date → excluido hasta fecha inclusive
4. **Exclusión Acotada**: Ambas fechas → excluido en rango específico
5. **Múltiples Períodos**: Mismo cliente con varias entradas para diferentes rangos

#### Algoritmo de Evaluación
```python
def _is_blacklisted(customer, posting_date, blacklist_map):
    for (start, end) in blacklist_map.get(customer, []):
        if start and end:
            if start <= posting_date <= end: return True
        elif start and not end:
            if posting_date >= start: return True
        elif end and not start:
            if posting_date <= end: return True
        else:  # sin fechas
            return True
    return False
```

## Alternatives Considered

### Alternative 1: Customer Master Flag
**Approach**: Agregar campo boolean `exclude_from_commissions` al Customer DocType
**Pros**: Más simple, directamente en Customer
**Cons**: 
- No permite control temporal
- Requiere modificar DocType core de ERPNext
- No permite múltiples períodos
- Sin centralización con otros parámetros de comisión

### Alternative 2: Hard-coded Exclusions
**Approach**: Lista estática de clientes en código Python
**Pros**: Máximo performance, simple implementación
**Cons**:
- Requiere cambios de código para cada exclusión
- Sin control temporal
- Sin interfaz de usuario
- Difícil mantenimiento

### Alternative 3: Separate DocType for Exclusions
**Approach**: DocType independiente "Client Exclusions"
**Pros**: Mayor flexibilidad, reporting independiente
**Cons**:
- Configuración dispersa
- Más complejo de mantener
- No integrado con settings centrales

## Consequences

### Positive
- **Flexibilidad Temporal**: Soporte completo para rangos de fechas
- **Performance Optimizado**: Filtrado temprano antes del cálculo costoso de COGS
- **Configuración Centralizada**: Todo en Comisiones Settings
- **Múltiples Períodos**: Mismo cliente puede tener varias exclusiones
- **No Breaking Changes**: No afecta funcionalidad existente
- **Business Agility**: Cambios dinámicos sin necesidad de deployments

### Negative
- **Complejidad Adicional**: Más campos y lógica para gestionar
- **No Retroactivo**: Documentos OPC existentes no se actualizan automáticamente
- **Potential for Misconfiguration**: Fechas incorrectas pueden causar exclusiones no intencionadas

### Mitigation Strategies
- **Documentación Clara**: Guías detalladas en docs/settings.md
- **Validation Logic**: Verificaciones en la interfaz para prevenir errores
- **Audit Trail**: Motivo requerido para documentar razones de exclusión

## Implementation Details

### Database Schema
- Table: `tabClientes Sin Comision` (child table)
- Fields: customer (varchar), start_date (date), end_date (date), motivo (text)
- Parent Link: Via `clientes_sin_comision` field in `tabComisiones Settings`

### Performance Considerations
- **Blacklist Caching**: Mapa construido una vez por llamada a `get_commission_rows()`
- **Early Exit**: Filtrado ocurre antes del procesamiento pesado de COGS
- **Memory Efficiency**: Solo clientes con exclusiones cargados en memoria

### Future Extensions
- **Customer Groups**: Extensión futura para excluir grupos completos
- **Branch-Specific**: Exclusiones por sucursal específica
- **Percentage Adjustments**: Reducción parcial en lugar de exclusión completa

## Subsequent Changes

### v2.3.1 - Sales Team Filtering
**Issue**: QC Caso 3 revealed that Sales Invoices without Sales Team were generating empty commission rows  
**Solution**: Added early filtering in `get_commission_rows()` to exclude SI without Sales Team  
**Impact**: Cleaner OPC reports, only invoices with assigned salespeople generate commissions  
**Implementation**: Simple query to Sales Team table with set intersection filtering  

## Related Documentation
- `docs/settings.md`: Documentación detallada de configuración
- `docs/CHANGELOG.md`: Historial de implementación
- `llantascs_customs/api.py`: Implementación técnica