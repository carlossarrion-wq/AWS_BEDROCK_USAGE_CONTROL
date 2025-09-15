# Guía para Crear el Rol IAM del Dashboard

## 🎯 Problema Identificado

El dashboard está fallando con el error "Failed to connect to AWS" porque necesita un rol IAM específico para acceder a los servicios de AWS de forma segura.

## 🔧 Solución: Crear Rol IAM

### Paso 1: Ejecutar el Script de Creación

```bash
./create_dashboard_iam_role.sh
```

### Paso 2: Verificar la Creación

El script creará:
- **Rol IAM**: `bedrock-dashboard-access-role`
- **Política**: `BedrockDashboardAccessPolicy`
- **Archivo de configuración**: `dashboard_iam_config.json`

### Paso 3: Probar el Dashboard

```bash
./launch_dashboard_integrated.sh
```

## 📋 Qué Hace el Script

### 🔐 Permisos Otorgados

1. **CloudWatch**: Leer métricas y alarmas
2. **IAM**: Leer usuarios, grupos y tags
3. **Lambda**: Invocar funciones de gestión de bloqueos
4. **DynamoDB**: Leer datos de seguimiento de uso
5. **Bedrock**: Leer modelos y métricas de uso
6. **CloudWatch Logs**: Leer logs de Lambda y Bedrock

### 🛡️ Seguridad

- **External ID**: `bedrock-dashboard-access` (requerido para asumir el rol)
- **Principio de menor privilegio**: Solo permisos de lectura (excepto Lambda invoke)
- **Restricción de cuenta**: Solo usuarios de la misma cuenta AWS pueden asumir el rol

## 🚀 Flujo Completo

1. **Crear rol IAM**:
   ```bash
   ./create_dashboard_iam_role.sh
   ```

2. **Lanzar dashboard**:
   ```bash
   ./launch_dashboard_integrated.sh
   ```

3. **Acceder al dashboard**:
   - Ir a: http://localhost:8080
   - Introducir credenciales AWS
   - El dashboard ahora debería conectarse correctamente

## 📊 Resultado Esperado

Después de crear el rol:
- ✅ El dashboard se conectará a AWS
- ✅ Mostrará usuarios reales desde IAM
- ✅ Mostrará métricas reales desde CloudWatch
- ✅ El indicador de conexión mostrará "🟢 Connected to AWS"

## 🔍 Verificación

El script incluye una prueba automática de asunción del rol. Si falla:
1. Esperar 2-3 minutos (propagación de IAM)
2. Probar el dashboard manualmente
3. Revisar los logs en la consola del navegador

## 📝 Archivos Creados

- `create_dashboard_iam_role.sh` - Script de creación del rol
- `dashboard_iam_config.json` - Configuración generada
- Rol IAM en AWS Console

---

**¡Ejecuta el script y el dashboard debería funcionar perfectamente!**
