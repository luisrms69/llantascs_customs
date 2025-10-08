# PLAN DE DEPLOYMENT: Migración 9 OPC Históricas

**Fecha creación:** 2025-10-07
**Versión:** v2.8.0
**Branch:** fix/migrate-opc-historicas → develop
**PR:** https://github.com/luisrms69/llantascs_customs/pull/15

---

## 📋 RESUMEN EJECUTIVO

**Problema:**
- 9 OPC en draft sin campo requerido `sucursales_multi`
- OPC fueron pagadas pero no validadas antes de migración
- Intentar validarlas directamente recalcula comisiones e incluye facturas nuevas incorrectas

**Solución:**
- Restaurar datos originales desde backup vía SQL bypass
- Validar sin ejecutar hooks de recalculo
- 6 etapas con verificación completa

**Tiempo estimado:**
- Staging: ~15 minutos
- Producción: ~15 minutos

---

## 🎯 PRE-REQUISITOS

### 1. Verificar Branch Merged
```bash
# Verificar que PR #15 está merged a develop
git log --oneline develop | grep "resolver COGS"
```

### 2. Backup Crítico
```bash
# OBLIGATORIO antes de iniciar
bench --site SITENAME backup --with-files
```

### 3. Archivos Necesarios
Todos están en el repo después del merge:
- ✅ `one_offs/opc_backup.json` (backup autorizado)
- ✅ `one_offs/validar_backup.py`
- ✅ `one_offs/restaurar_opc_completo.py`
- ✅ `one_offs/marcar_sales_invoices.py`
- ✅ `one_offs/validar_opc_final.py`
- ✅ `one_offs/verificacion_final_completa.py`

---

## 🔄 PROCESO PARA STAGING

### Paso 1: Actualizar Código
```bash
cd /path/to/frappe-bench/apps/llantascs_customs

# Pull latest code
git checkout develop
git pull upstream develop

# Verificar que tienes el commit correcto
git log --oneline -1
# Debe mostrar: e45adc2 fix: resolver COGS con link inverso DN...
```

### Paso 2: Aplicar Migración
```bash
cd /path/to/frappe-bench

# Migrate (actualiza DocType + aplica resolver nuevo)
bench --site STAGING_SITE migrate

# Clear cache
bench --site STAGING_SITE clear-cache
```

### Paso 3: Verificar OPC Pendientes
```bash
bench --site STAGING_SITE execute frappe.db.sql --kwargs '{"query": "SELECT name, docstatus, monto_total FROM `tabOrden de Pago Comisiones` WHERE docstatus = 0 AND name LIKE \"COMISIONES-2025-09-30-%\" ORDER BY name", "as_dict": 1}'
```

**Si retorna 9 OPC → CONTINUAR**
**Si retorna 0 OPC → SKIP al Paso 9 (verificación resolver)**

### Paso 4: ETAPA 0 - Validar Backup
```bash
cd apps/llantascs_customs

bench --site STAGING_SITE execute llantascs_customs.one_offs.validar_backup.run
```

**Verificar salida:**
```
✅ BACKUP VÁLIDO
Total OPC: 9
Total comisiones: 147
Monto total: $72,885.97
```

**⚠️ Si hay errores → DETENER y reportar**

### Paso 5: ETAPA 1 - Dry Run Restauración
```bash
bench --site STAGING_SITE execute llantascs_customs.one_offs.restaurar_opc_completo.run --kwargs '{"dry_run": 1}'
```

**Verificar salida:**
```
🔍 DRY RUN MODE
9/9 OPC procesadas exitosamente
```

### Paso 6: ETAPA 2 - Restauración REAL
```bash
bench --site STAGING_SITE execute llantascs_customs.one_offs.restaurar_opc_completo.run --kwargs '{"dry_run": 0}'
```

**Verificar salida:**
```
⚡ EJECUCIÓN REAL
9/9 OPC restauradas exitosamente
Total comisiones restauradas: 147
Total monto restaurado: $72,885.97
```

**⚠️ Si hay errores → ROLLBACK con backup**

### Paso 7: ETAPA 3 - Dry Run Marcar Sales Invoices
```bash
bench --site STAGING_SITE execute llantascs_customs.one_offs.marcar_sales_invoices.run --kwargs '{"dry_run": 1}'
```

**Verificar salida:**
```
🔍 DRY RUN MODE
147 SI originales a marcar
0 SI adicionales a limpiar
```

### Paso 8: ETAPA 4 - Marcar Sales Invoices REAL
```bash
bench --site STAGING_SITE execute llantascs_customs.one_offs.marcar_sales_invoices.run --kwargs '{"dry_run": 0}'
```

**Verificar salida:**
```
⚡ EJECUCIÓN REAL
147 SI marcadas como "Enviado"
```

### Paso 9: ETAPA 5 - Validar OPC (SQL bypass)
```bash
bench --site STAGING_SITE execute llantascs_customs.one_offs.validar_opc_final.run
```

**Verificar salida:**
```
9/9 OPC validadas exitosamente (docstatus → 1)
```

### Paso 10: ETAPA 6 - Verificación Final Completa
```bash
bench --site STAGING_SITE execute llantascs_customs.one_offs.verificacion_final_completa.run
```

**Verificar salida:**
```
✅ ÉXITO TOTAL
9 OPC validadas
147 comisiones correctas
$72,885.97 total verificado
147/147 SI correctamente marcadas
```

**Archivo generado:** `one_offs/reporte_final_9opc.txt`

### Paso 11: Verificar Resolver COGS (CRÍTICO)
```bash
bench --site STAGING_SITE execute llantascs_customs.one_offs.verificar_costos_vs_gl.run
```

**Verificar salida:**
```
Total facturas verificadas: 25
Resolver coincide con GL: 25 ✅
Facturas corregidas (costo 0 → costo > 0): 17
```

**Archivo generado:** `one_offs/verificacion_costos_vs_gl.json`

### Paso 12: Smoke Test Manual
1. Abrir ERPNext UI en Staging
2. Ir a "Orden de Pago Comisiones"
3. Abrir una de las 9 OPC migradas (ej: COMISIONES-2025-09-30-08308)
4. Verificar:
   - ✅ Estado: Submitted (docstatus=1)
   - ✅ Tiene sucursales en tabla "Sucursales Multi"
   - ✅ Comisiones correctas (coinciden con backup)
   - ✅ Campos Currency muestran solo 2 decimales
5. Abrir una SI de las 147 migradas
6. Verificar:
   - ✅ Campo "Status Comisiones" = "Enviado"
   - ✅ Campo "Orden de Pago Comision" vinculado a OPC

### Paso 13: Crear OPC Nueva (Test Resolver COGS)
1. Crear nueva OPC
2. Incluir facturas que tengan DN
3. Verificar que COGS > 0 (no debe haber costo $0 en facturas con productos)

---

## 🔄 PROCESO PARA PRODUCCIÓN

**REPETIR EXACTAMENTE LOS MISMOS PASOS QUE STAGING**

Solo cambiar:
- `STAGING_SITE` → `PRODUCTION_SITE`

**DIFERENCIAS IMPORTANTES:**

### Timing de Ejecución
- **Staging:** Cualquier momento
- **Producción:** Horario no laboral (evitar uso concurrente)

### Backup Adicional
```bash
# Backup ANTES de iniciar
bench --site PRODUCTION_SITE backup --with-files

# Verificar backup creado
ls -lh sites/PRODUCTION_SITE/private/backups/ | tail -3
```

### Comunicación
- Notificar a usuarios que habrá mantenimiento
- Estimar downtime: ~15 minutos
- Tener plan de rollback listo

---

## 🚨 ROLLBACK (si algo falla)

### Opción 1: Rollback Rápido (SQL)
```bash
# Solo si falla ANTES de validar (Paso 9)
bench --site SITENAME execute frappe.db.sql --kwargs '{"query": "UPDATE `tabOrden de Pago Comisiones` SET docstatus=0 WHERE name LIKE \"COMISIONES-2025-09-30-%\""}'

bench --site SITENAME execute frappe.db.sql --kwargs '{"query": "UPDATE `tabSales Invoice` SET custom_status_comisiones=\"Sin Enviar\", custom_orden_de_pago_comision=NULL WHERE name IN (SELECT sales_invoice_id FROM `tabComision LLCS` WHERE parent LIKE \"COMISIONES-2025-09-30-%\")"}'
```

### Opción 2: Rollback Completo (Restore Backup)
```bash
# Si falla después de validar o hay inconsistencias
bench --site SITENAME restore PATH_TO_BACKUP.sql.gz
```

### Opción 3: Rollback Código
```bash
cd apps/llantascs_customs
git checkout COMMIT_ANTERIOR
bench --site SITENAME migrate
bench --site SITENAME clear-cache
```

---

## ✅ VALIDACIÓN POST-DEPLOYMENT

### Checklist Staging
- [ ] 9 OPC validadas (docstatus=1)
- [ ] 147 comisiones correctas
- [ ] 147 SI marcadas "Enviado"
- [ ] Resolver COGS: 25/25 match GL
- [ ] Campos Currency: 2 decimales
- [ ] Nueva OPC: COGS correcto
- [ ] Reportes funcionan correctamente

### Checklist Producción
- [ ] Mismo checklist que Staging
- [ ] Usuarios confirmaron acceso normal
- [ ] Sin errores en logs
- [ ] Performance normal

### Verificar Logs
```bash
# Ver últimos logs
tail -100 sites/SITENAME/logs/frappe.log

# Buscar errores
grep -i error sites/SITENAME/logs/frappe.log | tail -20
```

---

## 📊 DATOS DE REFERENCIA

### 9 OPC a Migrar
| OPC | Comisiones | Monto |
|-----|-----------|-------|
| COMISIONES-2025-09-30-08308 | 19 | $3,904.97 |
| COMISIONES-2025-09-30-08309 | 21 | $3,651.63 |
| COMISIONES-2025-09-30-08310 | 33 | $26,261.72 |
| COMISIONES-2025-09-30-08311 | 6 | $7,008.53 |
| COMISIONES-2025-09-30-08312 | 8 | $3,152.56 |
| COMISIONES-2025-09-30-08313 | 13 | $3,500.98 |
| COMISIONES-2025-09-30-08314 | 15 | $11,049.06 |
| COMISIONES-2025-09-30-08315 | 5 | $10,086.86 |
| COMISIONES-2025-09-30-08316 | 27 | $4,269.67 |
| **TOTAL** | **147** | **$72,885.97** |

### 17 Facturas Corregidas (Resolver COGS)
Total COGS corregido: $1,030,396.29

---

## 🆘 TROUBLESHOOTING

### Error: "OPC ya tiene sucursales"
**Causa:** OPC ya fue migrada
**Solución:** Skip esa OPC, es normal

### Error: "Backup no válido"
**Causa:** Archivo `opc_backup.json` corrupto o faltante
**Solución:** Verificar que el archivo existe y tiene contenido válido

### Error: "No se encontraron cuentas COGS"
**Causa:** Cuentas COGS deshabilitadas o eliminadas
**Solución:** Verificar en Chart of Accounts que existan cuentas con tipo "Cost of Goods Sold"

### Resolver COGS sigue dando $0
**Causa:** Facturas sin DN asociado
**Solución:** Verificar que las facturas SÍ tengan DN. Si no tienen, es correcto que costo=0

### Campos Currency muestran muchos decimales
**Causa:** Cache no limpiado después de migrate
**Solución:** `bench --site SITENAME clear-cache` y recargar página

---

## 📞 CONTACTO Y SOPORTE

**En caso de problemas:**
1. DETENER el proceso inmediatamente
2. NO continuar con siguientes etapas
3. Documentar el error exacto (screenshot + logs)
4. Ejecutar rollback si es necesario
5. Contactar equipo técnico

**Logs importantes:**
- `sites/SITENAME/logs/frappe.log`
- `one_offs/reporte_final_9opc.txt`
- `one_offs/verificacion_costos_vs_gl.json`

---

## 📝 NOTAS FINALES

- **NO saltar etapas:** El proceso es secuencial e incremental
- **Verificar cada etapa:** No continuar si hay errores
- **Backup es obligatorio:** Antes de cualquier cambio en producción
- **Dry run primero:** Siempre probar en modo lectura antes de escritura
- **Staging first:** Nunca ir directo a producción sin validar en staging

**Una vez completado exitosamente en Staging y Producción, el sistema quedará con:**
- ✅ 9 OPC históricas validadas y pagables
- ✅ Resolver COGS funcionando correctamente para todos los casos
- ✅ Campos con precisión correcta (2 decimales)
- ✅ Sistema listo para operación normal

---

**Fin del documento**
