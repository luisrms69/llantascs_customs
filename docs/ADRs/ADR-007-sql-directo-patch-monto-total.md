# ADR-007: Usar SQL directo con UPDATE+JOIN para patches de agregación

**Fecha**: 2025-09-15
**Estado**: Aceptado
**Decisor**: Usuario + ChatGPT Solution

## Contexto

Los patches que recalculan campos agregados (ej: monto_total desde suma de tabla hija) fallaban sistemáticamente usando el patrón estándar de Frappe:
1. `frappe.get_all()` con filtros para encontrar registros candidatos
2. `frappe.db.sql()` para agregar valores de tabla hija
3. `frappe.db.set_value()` individual para actualizar cada registro

### Problema Específico
Patch para corregir `monto_total` en OPCs (Orden de Pago Comisiones):
- **Síntoma**: 88 OPCs con `monto_total=0` pero `SUM(total_comision) > 0`
- **Falla**: `get_all` con filtros `[monto_total, "in", [0, 0.0, None]]` no encontraba registros con `monto_total=0.0` (float)
- **Resultado**: Patch se ejecutaba pero no actualizaba registros, causando inconsistencia de datos crítica

## Decisión

**Adoptar SQL directo con UPDATE+JOIN para patches de recálculo agregado**, abandonando el patrón get_all + set_value individual.

### Patrón Nuevo (Funcional):
```python
def execute():
    query = f"""
        UPDATE `tab{PARENT_DT}` p
        JOIN (
          SELECT parent,
                 COALESCE(SUM(`{CHILD_COMM_FIELD}`), 0) AS child_sum
          FROM `tab{CHILD_DT}`
          GROUP BY parent
        ) s ON s.parent = p.name
        SET p.`{PARENT_TOTAL_FIELD}` = s.child_sum
        WHERE p.docstatus = 1
          AND (p.`{PARENT_TOTAL_FIELD}` IS NULL OR ABS(p.`{PARENT_TOTAL_FIELD}`) < 0.0000001)
          AND s.child_sum > 0
    """
    frappe.db.sql(query)
    frappe.db.commit()
```

### Patrón Anterior (Problemático):
```python
def execute():
    # FALLA: filtro no encuentra 0.0 (float)
    parents = frappe.get_all(PARENT_DT, filters=[
        [PARENT_TOTAL_FIELD, "in", [0, None]]  # ❌ Missing 0.0
    ])
    # Resto del código nunca se ejecuta
```

## Consecuencias

### ✅ Positivas
- **100% Efectivo**: UPDATE con JOIN procesa todos los casos de una vez
- **Sin filtros problemáticos**: No depende de `get_all()` con comparaciones float
- **Atómico**: Operación única transaccional
- **Más rápido**: Una query vs N updates individuales
- **Más seguro**: WHERE con múltiples condiciones protege datos válidos

### ⚠️ Negativas
- **Menos "Frappe-esque"**: No usa APIs de alto nivel del framework
- **SQL directo**: Requiere conocimiento específico de SQL
- **Menos portable**: Dependiente de sintaxis MySQL/MariaDB

### 🔧 Mitigaciones
- **Validación robusta**: WHERE con múltiples condiciones de seguridad
- **Logging detallado**: frappe.logger() para audit trail
- **Testing manual**: Verificación de casos edge antes de deploy

## Alternativas Consideradas

1. **Corregir filtros get_all()**: Agregar `0.0` a lista `[0, 0.0, None]`
   - **Rechazado**: Siguió fallando, problema más profundo en el enfoque

2. **Usar frappe.db.get_all()** en lugar de frappe.get_all()
   - **Rechazado**: Mismo problema de filtrado

3. **Enfoque híbrido**: get_all sin filtros + filtro manual en Python
   - **Rechazado**: Ineficiente y complejo

## Implementación

**Patch funcional**: `patches/post/fix_opc_monto_total_corrected.py`
**Resultado**: 80/88 OPCs corregidas (8 casos edge válidos como están)
**Deploy status**: ✅ Listo para otros sitios

## Notas Adicionales

Esta decisión es **específica para patches de recálculo agregado**. Para operaciones CRUD normales, seguir usando las APIs estándar de Frappe.

**Aplicar este patrón cuando**:
- Recálculo de campos agregados desde tablas hijas
- Patches masivos de correción de datos
- Casos donde get_all con filtros complejos falla consistentemente

**NO aplicar cuando**:
- Operaciones CRUD de un solo registro
- Logic de negocio normal en DocTypes
- APIs públicas o client-facing functions