# 🚀 AWS Bedrock Individual Blocking System - Deployment Guide

## 📋 **Guía Completa de Despliegue con Protección Administrativa**

Esta guía te ayudará a desplegar el sistema completo de control de uso de AWS Bedrock con la nueva funcionalidad de **protección administrativa**.

---

## 🎯 **Características del Sistema**

### **✅ Funcionalidades Principales**
- **Bloqueo Automático**: Usuarios bloqueados al superar límites diarios
- **🛡️ Protección Administrativa**: Manual unblocks previenen re-bloqueo hasta el día siguiente
- **🔄 Reseteo Diario**: Limpieza automática de protecciones a las 00:00 UTC
- **📊 Historial Completo**: Auditoría de todas las operaciones de bloqueo
- **📧 Notificaciones**: Alertas automáticas por SNS
- **🎛️ Dashboard Web**: Interfaz para gestión manual

### **🆕 Nueva Lógica de Protección Administrativa**
```
Usuario supera límite → Bloqueo automático → Admin desbloquea → Protección activa → No re-bloqueo hasta mañana
```

---

## 🔧 **Prerrequisitos**

### **1. Herramientas Necesarias**
```bash
# AWS CLI
aws --version

# jq (para testing)
jq --version

# Permisos AWS
aws sts get-caller-identity
```

### **2. Permisos IAM Requeridos**
Tu usuario AWS necesita permisos para:
- **Lambda**: Crear/actualizar funciones y configurar roles
- **DynamoDB**: Crear tablas y configurar TTL
- **IAM**: Crear roles y políticas (CRÍTICO)
- **CloudWatch**: Crear reglas de eventos y métricas
- **SNS**: Crear topics (opcional)

### **3. Configuración de Cuenta**
- **Región**: `eu-west-1`
- **Account ID**: `701055077130`
- **CloudTrail**: Habilitado para eventos de Bedrock

### **4. ⚠️ CRÍTICO: Verificación de Roles IAM**
**ANTES de cualquier despliegue, verificar que existen los roles IAM necesarios:**

```bash
# Verificar rol principal de Lambda
aws iam get-role --role-name bedrock-usage-monitor-role

# Verificar política del rol
aws iam get-role-policy --role-name bedrock-usage-monitor-role --policy-name BedrockUsageMonitorPolicy
```

**Si los roles no existen, crearlos PRIMERO antes del despliegue.**

---

## 🔐 **PASO CRÍTICO: Creación de Roles IAM**

### **⚠️ IMPORTANTE: Ejecutar ANTES del despliegue de Lambda**

**Crear el rol principal `bedrock-usage-monitor-role` con TODOS los permisos necesarios:**

```bash
# 1. Crear el rol IAM
aws iam create-role \
  --role-name bedrock-usage-monitor-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# 2. Crear la política completa con TODOS los permisos necesarios
aws iam put-role-policy \
  --role-name bedrock-usage-monitor-role \
  --policy-name BedrockUsageMonitorPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:eu-west-1:701055077130:*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem"
        ],
        "Resource": "arn:aws:dynamodb:eu-west-1:701055077130:table/bedrock_user_daily_usage"
      },
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:Query"
        ],
        "Resource": "arn:aws:dynamodb:eu-west-1:701055077130:table/bedrock_blocking_history/index/user-date-index"
      },
      {
        "Effect": "Allow",
        "Action": [
          "lambda:InvokeFunction"
        ],
        "Resource": "arn:aws:lambda:eu-west-1:701055077130:function:bedrock-policy-manager"
      },
      {
        "Effect": "Allow",
        "Action": [
          "sns:Publish"
        ],
        "Resource": "arn:aws:sns:eu-west-1:701055077130:bedrock-usage-alerts"
      },
      {
        "Effect": "Allow",
        "Action": [
          "iam:ListUserTags",
          "iam:GetUser"
        ],
        "Resource": "arn:aws:iam::701055077130:user/*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "cloudwatch:PutMetricData"
        ],
        "Resource": "*"
      }
    ]
  }'

# 3. Verificar que el rol se creó correctamente
aws iam get-role --role-name bedrock-usage-monitor-role
aws iam get-role-policy --role-name bedrock-usage-monitor-role --policy-name BedrockUsageMonitorPolicy
```

### **✅ Verificación de Permisos Críticos**

**Verificar que el rol tiene TODOS los permisos necesarios:**

```bash
# Verificar permisos de CloudWatch (CRÍTICO para métricas)
aws iam get-role-policy --role-name bedrock-usage-monitor-role --policy-name BedrockUsageMonitorPolicy | grep -A 5 "cloudwatch:PutMetricData"

# Verificar permisos de DynamoDB
aws iam get-role-policy --role-name bedrock-usage-monitor-role --policy-name BedrockUsageMonitorPolicy | grep -A 5 "dynamodb"

# Verificar permisos de IAM para tags de usuarios
aws iam get-role-policy --role-name bedrock-usage-monitor-role --policy-name BedrockUsageMonitorPolicy | grep -A 5 "iam:ListUserTags"
```

### **🔧 Asignación Automática del Rol a Lambda**

**Al desplegar la función Lambda, el rol se asigna automáticamente:**

```bash
# El comando de despliegue incluye la asignación del rol
aws lambda update-function-code \
  --function-name bedrock-usage-monitor \
  --zip-file fileb://bedrock-usage-monitor-fixed-cloudwatch.zip \
  --region eu-west-1

# Verificar que el rol está asignado correctamente
aws lambda get-function --function-name bedrock-usage-monitor --region eu-west-1 --query 'Configuration.Role'
```

**Resultado esperado:**
```
"arn:aws:iam::701055077130:role/bedrock-usage-monitor-role"
```

---

## 🚀 **Proceso de Despliegue**

### **Paso 1: Preparación**
```bash
# Clonar o descargar el proyecto
cd /path/to/AWS_BEDROCK_USAGE_CONTROL

# Verificar estructura
ls -la individual_blocking_system/lambda_functions/
```

### **Paso 2: Despliegue Completo**
```bash
# Ejecutar script de despliegue completo
./deploy_complete_system.sh
```

**El script realizará automáticamente:**
1. ✅ **Infraestructura**: DynamoDB, IAM roles, CloudWatch Events
2. ✅ **Tabla de Historial**: Nueva tabla para auditoría
3. ✅ **Permisos Actualizados**: IAM roles con nuevos permisos
4. ✅ **4 Funciones Lambda**: Con lógica de protección administrativa
5. ✅ **Triggers**: Configuración de eventos automáticos
6. ✅ **Verificación**: Comprobación de estado del sistema

### **Paso 3: Verificación del Despliegue**
```bash
# Verificar funciones Lambda
aws lambda list-functions --query 'Functions[?contains(FunctionName, `bedrock`)].FunctionName'

# Verificar tablas DynamoDB
aws dynamodb list-tables --query 'TableNames[?contains(@, `bedrock`)]'

# Verificar reglas de CloudWatch Events
aws events list-rules --query 'Rules[?contains(Name, `bedrock`)].Name'
```

### **Paso 4: Verificación Crítica Post-Despliegue**

**⚠️ VERIFICAR INMEDIATAMENTE DESPUÉS DEL DESPLIEGUE:**

```bash
# 1. Verificar que el rol está asignado correctamente a Lambda
aws lambda get-function --function-name bedrock-usage-monitor --region eu-west-1 --query 'Configuration.Role'

# 2. Verificar permisos de CloudWatch (CRÍTICO)
aws iam get-role-policy --role-name bedrock-usage-monitor-role --policy-name BedrockUsageMonitorPolicy | grep "cloudwatch:PutMetricData"

# 3. Test rápido de CloudWatch metrics
aws lambda invoke \
  --function-name bedrock-usage-monitor \
  --payload '{
    "detail": {
      "eventTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "eventSource": "bedrock.amazonaws.com",
      "eventName": "InvokeModel",
      "userIdentity": {
        "type": "IAMUser",
        "userName": "test_user_deployment",
        "arn": "arn:aws:iam::701055077130:user/test_user_deployment"
      }
    }
  }' \
  response.json

# 4. Verificar logs para confirmar éxito
aws logs filter-log-events \
  --log-group-name /aws/lambda/bedrock-usage-monitor \
  --start-time $(date -d '5 minutes ago' +%s)000 \
  --filter-pattern "✅ Published CloudWatch metrics"
```

**Resultados esperados:**
- ✅ Rol asignado: `"arn:aws:iam::701055077130:role/bedrock-usage-monitor-role"`
- ✅ Permisos CloudWatch: `"cloudwatch:PutMetricData"`
- ✅ Lambda ejecuta sin errores
- ✅ Logs muestran: `"✅ Published CloudWatch metrics for test_user_deployment"`

### **Paso 5: Prueba del Sistema**
```bash
# Ejecutar test de protección administrativa
./test_admin_protection.sh
```

---

## 🧪 **Testing y Validación**

### **Test Automático de Protección Administrativa**
El script `test_admin_protection.sh` realiza:

1. **🔨 Crea usuario de prueba** y simula 60 requests
2. **🚫 Verifica bloqueo automático** al superar límites
3. **🛡️ Simula desbloqueo manual** por administrador
4. **✅ Verifica protección** - no re-bloqueo con más requests
5. **📊 Revisa historial** de operaciones
6. **🔄 Simula reset diario** y limpieza de protección
7. **🧹 Limpia recursos** de prueba

### **Resultados Esperados**
```
✅ Test Results Summary:
   1. ✅ User automatic blocking: Working
   2. ✅ Admin manual unblock: Working  
   3. ✅ Administrative protection: Prevents re-blocking
   4. ✅ Blocking history: Tracking operations
   5. ✅ Daily reset: Clears protection
   6. ✅ Post-reset blocking: Can block again
```

---

## 🎛️ **Configuración del Dashboard**

### **Paso 1: Configurar Dashboard**
```bash
# Configurar dashboard con integración AWS
./configure_dashboard_aws.sh
```

### **Paso 2: Lanzar Dashboard**
```bash
# Lanzar dashboard integrado
./launch_dashboard_integrated.sh
```

### **Paso 3: Acceder al Dashboard**
1. Abrir navegador en `http://localhost:8000`
2. Usar credenciales AWS configuradas
3. Navegar a **"Blocking Management"** para gestión manual

---

## ⚙️ **Configuración de Límites**

### **Archivo de Configuración: `quota_config.json`**
```json
{
  "users": {
    "mulesoft_001": {
      "daily_limit": 250,
      "monthly_limit": 5000,
      "warning_threshold": 60,
      "critical_threshold": 85,
      "team": "team_mulesoft_group"
    }
  },
  "teams": {
    "team_mulesoft_group": {
      "monthly_limit": 25000,
      "warning_threshold": 60,
      "critical_threshold": 85
    }
  }
}
```

### **Modificar Límites**
1. Editar `quota_config.json`
2. Los cambios se aplican automáticamente en nuevos usuarios
3. Para usuarios existentes, usar el dashboard para ajustes manuales

---

## 🔍 **Monitoreo y Operación**

### **CloudWatch Logs**
```bash
# Ver logs de las funciones Lambda
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/bedrock"

# Ver logs específicos
aws logs tail /aws/lambda/bedrock-usage-monitor --follow
```

### **Métricas Importantes**
- **Usuarios Bloqueados**: Número de usuarios actualmente bloqueados
- **Protecciones Activas**: Usuarios con protección administrativa
- **Operaciones Diarias**: Bloqueos/desbloqueos por día
- **Errores de Sistema**: Fallos en funciones Lambda

### **Notificaciones SNS**
- **Bloqueos Automáticos**: Notificación cuando usuario supera límite
- **Protección Administrativa**: Alerta cuando admin desbloquea usuario
- **Errores del Sistema**: Fallos en reseteo diario o funciones

---

## 🛡️ **Gestión de Protección Administrativa**

### **Cómo Funciona**
1. **Usuario supera límite** → Sistema bloquea automáticamente
2. **Usuario solicita ayuda** → Contacta administrador
3. **Admin desbloquea** desde dashboard → Se activa protección
4. **Usuario protegido** → No puede ser bloqueado automáticamente hasta mañana
5. **Reset diario** → Protección se limpia a las 00:00 UTC

### **Usar el Dashboard para Gestión Manual**
1. **Ir a "Blocking Management"**
2. **Seleccionar usuario** de la lista
3. **Elegir duración** del bloqueo/desbloqueo
4. **Proporcionar razón** para la operación
5. **Confirmar acción** - se registra en historial

### **Verificar Estado de Protección**
```bash
# Via AWS CLI
aws lambda invoke \
  --function-name bedrock-policy-manager \
  --payload '{"action":"check_status","user_id":"mulesoft_001"}' \
  response.json && cat response.json
```

---

## 🔧 **Troubleshooting**

### **Problemas Comunes**

#### **1. Funciones Lambda no se ejecutan**
```bash
# Verificar permisos de EventBridge
aws events list-targets-by-rule --rule bedrock-individual-blocking-monitor

# Verificar logs de errores
aws logs filter-log-events --log-group-name /aws/lambda/bedrock-usage-monitor --filter-pattern ERROR
```

#### **2. Dashboard no carga datos**
- Verificar credenciales AWS en `sessionStorage`
- Comprobar rol IAM `bedrock-dashboard-access-role`
- Revisar CORS en navegador

#### **3. Protección administrativa no funciona**
```bash
# Verificar tabla de historial
aws dynamodb scan --table-name bedrock_blocking_history --limit 5

# Verificar flags de protección en DynamoDB
aws dynamodb get-item \
  --table-name bedrock_user_daily_usage \
  --key '{"user_id":{"S":"mulesoft_001"},"date":{"S":"2025-01-15"}}'
```

#### **4. Reset diario no funciona**
```bash
# Verificar regla de CloudWatch Events
aws events describe-rule --name bedrock-individual-daily-reset

# Ejecutar reset manual
aws lambda invoke \
  --function-name bedrock-daily-reset \
  --payload '{"source":"manual"}' \
  response.json
```

### **Logs de Debugging**
```bash
# Habilitar logging detallado
export AWS_CLI_FILE_ENCODING=UTF-8
aws logs put-retention-policy --log-group-name /aws/lambda/bedrock-usage-monitor --retention-in-days 7
```

---

## 📊 **Estructura del Sistema Desplegado**

### **Funciones Lambda**
```
bedrock-usage-monitor     → Monitorea uso y aplica bloqueos
bedrock-policy-manager    → Gestiona políticas IAM (bloqueo/desbloqueo)
bedrock-daily-reset       → Reset diario y limpieza de protecciones
bedrock-blocking-history  → Gestiona historial de operaciones
```

### **Tablas DynamoDB**
```
bedrock_user_daily_usage  → Contadores diarios y estado de usuarios
bedrock_blocking_history  → Historial completo de operaciones
```

### **CloudWatch Events**
```
bedrock-individual-blocking-monitor → Trigger para monitoreo de uso
bedrock-individual-daily-reset     → Trigger para reset diario (00:00 UTC)
```

### **IAM Roles**
```
bedrock-usage-monitor-role     → Permisos para monitoreo y DynamoDB
bedrock-policy-manager-role    → Permisos para gestión de políticas IAM
bedrock-daily-reset-role       → Permisos para reset y limpieza
bedrock-blocking-history-role  → Permisos para gestión de historial
```

---

## 🎯 **Próximos Pasos**

### **1. Configuración Inicial**
- [ ] Ejecutar `./deploy_complete_system.sh`
- [ ] Ejecutar `./test_admin_protection.sh`
- [ ] Configurar dashboard con `./configure_dashboard_aws.sh`
- [ ] Lanzar dashboard con `./launch_dashboard_integrated.sh`

### **2. Configuración de Producción**
- [ ] Ajustar límites en `quota_config.json`
- [ ] Configurar notificaciones SNS
- [ ] Entrenar administradores en uso del dashboard
- [ ] Establecer procedimientos de monitoreo

### **3. Monitoreo Continuo**
- [ ] Configurar alertas de CloudWatch
- [ ] Revisar logs regularmente
- [ ] Monitorear historial de bloqueos
- [ ] Ajustar límites según uso real

---

## 📞 **Soporte**

### **Documentación Adicional**
- `individual_usage_blocking_system.md` - Documentación técnica detallada
- `dashboard_blocking_management_plan.md` - Plan de gestión del dashboard
- `token_tracking_enhancement.md` - Mejoras de seguimiento

### **Archivos de Configuración**
- `quota_config.json` - Límites de usuarios y equipos
- `blocking_system_config.json` - Configuración del sistema (auto-generado)

### **Scripts de Utilidad**
- `deploy_complete_system.sh` - Despliegue completo
- `test_admin_protection.sh` - Test de protección administrativa
- `configure_dashboard_aws.sh` - Configuración del dashboard
- `launch_dashboard_integrated.sh` - Lanzamiento del dashboard

---

## ✅ **Checklist de Despliegue**

### **Pre-Despliegue**
- [ ] AWS CLI configurado y funcionando
- [ ] Permisos IAM suficientes
- [ ] CloudTrail habilitado para Bedrock
- [ ] Región configurada (`eu-west-1`)

### **Despliegue**
- [ ] `./deploy_complete_system.sh` ejecutado exitosamente
- [ ] Todas las funciones Lambda activas
- [ ] Tablas DynamoDB creadas
- [ ] CloudWatch Events configurados

### **Post-Despliegue**
- [ ] `./test_admin_protection.sh` pasado exitosamente
- [ ] Dashboard configurado y accesible
- [ ] Notificaciones SNS funcionando
- [ ] Límites de usuarios configurados

### **Producción**
- [ ] Administradores entrenados
- [ ] Procedimientos de monitoreo establecidos
- [ ] Alertas configuradas
- [ ] Documentación actualizada

---

**🎉 ¡El sistema está listo para producción con protección administrativa completa!**

*Última actualización: 15/09/2025*
