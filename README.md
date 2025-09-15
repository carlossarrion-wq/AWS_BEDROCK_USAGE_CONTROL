# AWS Bedrock Usage Control System

## 📋 Descripción General del Proyecto

El **AWS Bedrock Usage Control System** es una solución integral y avanzada para el control, monitoreo y gestión del uso de AWS Bedrock en organizaciones empresariales. Este sistema proporciona capacidades completas de gestión de usuarios, equipos, políticas IAM, monitoreo en tiempo real, bloqueo automático de usuarios y un dashboard web interactivo para administración.

### 🎯 Objetivos Principales

- **Control Granular de Acceso**: Gestión detallada de permisos por usuario, equipo y herramienta
- **Monitoreo en Tiempo Real**: Seguimiento continuo del uso de AWS Bedrock con alertas automáticas
- **Bloqueo Automático Inteligente**: Sistema de protección que bloquea usuarios que exceden límites diarios
- **Protección Administrativa**: Lógica avanzada que previene re-bloqueos automáticos después de desbloqueos manuales
- **Auditoría Completa**: Historial detallado de todas las operaciones para cumplimiento normativo
- **Dashboard Interactivo**: Interfaz web moderna para gestión y monitoreo

## 🏗️ Arquitectura Técnica del Sistema

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS BEDROCK USAGE CONTROL                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │   Dashboard     │    │   CLI Manager   │    │  Individual  │ │
│  │   Web (HTML)    │    │   (Python)      │    │  Blocking    │ │
│  │                 │    │                 │    │  System      │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│           │                       │                      │       │
│           └───────────────────────┼──────────────────────┘       │
│                                   │                              │
│  ┌─────────────────────────────────┼─────────────────────────────┐ │
│  │                    AWS SERVICES │                             │ │
│  │                                 │                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │ │
│  │  │     IAM     │  │ CloudWatch  │  │       Lambda            │ │ │
│  │  │   Users     │  │   Metrics   │  │  - Usage Monitor        │ │ │
│  │  │   Groups    │  │    Logs     │  │  - Policy Manager       │ │ │
│  │  │   Roles     │  │   Alarms    │  │  - Daily Reset          │ │ │
│  │  │  Policies   │  │             │  │  - Blocking History     │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │ │
│  │                                                                │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │ │
│  │  │  DynamoDB   │  │ EventBridge │  │         SNS             │ │ │
│  │  │ Daily Usage │  │   Rules     │  │    Notifications        │ │ │
│  │  │  History    │  │  Triggers   │  │      Alerts             │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos y Procesamiento

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Makes    │───▶│   CloudTrail    │───▶│   EventBridge   │
│ Bedrock Request │    │   Captures      │    │   Processes     │
│                 │    │     Event       │    │     Event       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SNS Sends     │◀───│  Usage Monitor  │◀───│   Lambda        │
│  Notification   │    │   Updates       │    │  Triggered      │
│                 │    │   DynamoDB      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Policy Manager  │
                       │   Blocks User   │
                       │  (if needed)    │
                       └─────────────────┘
```

## 📁 Estructura Detallada del Proyecto

```
AWS_BEDROCK_USAGE_CONTROL/
├── 📄 README.md                              # Este archivo - Documentación principal
├── 📄 login.html                             # Página de login del dashboard
├── 📄 bedrock_usage_dashboard_aws.html       # Dashboard web principal
├── 📄 quota_config.json                      # Configuración de límites y cuotas
├── 📄 package.json                           # Dependencias Node.js para testing
├── 📄 .gitignore                             # Archivos ignorados por Git
│
├── 🗂️ src/                                   # Código fuente principal del CLI
│   ├── 📄 bedrock_manager.py                 # Script principal CLI
│   ├── 📄 config.json                        # Configuración AWS y sistema
│   ├── 📄 provision.py                       # Script de aprovisionamiento
│   │
│   ├── 🗂️ user/                              # Módulo de gestión de usuarios
│   │   ├── 📄 __init__.py
│   │   └── 📄 user_manager.py                # Gestión completa de usuarios IAM
│   │
│   ├── 🗂️ group/                             # Módulo de gestión de grupos
│   │   ├── 📄 __init__.py
│   │   └── 📄 group_manager.py               # Gestión de grupos y equipos
│   │
│   ├── 🗂️ policy/                            # Módulo de gestión de políticas
│   │   ├── 📄 __init__.py
│   │   └── 📄 policy_manager.py              # Gestión de políticas IAM
│   │
│   ├── 🗂️ utils/                             # Utilidades comunes
│   │   ├── 📄 __init__.py
│   │   └── 📄 aws_utils.py                   # Funciones auxiliares AWS
│   │
│   └── 🗂️ dashboard/                         # Módulo del dashboard (futuro)
│
├── 🗂️ individual_blocking_system/            # Sistema de bloqueo individual
│   └── 🗂️ lambda_functions/                  # Funciones Lambda del sistema
│       ├── 📄 bedrock_usage_monitor.py       # Monitor de uso con protección admin
│       ├── 📄 bedrock_policy_manager.py      # Gestor de políticas y bloqueos
│       ├── 📄 bedrock_daily_reset.py         # Reset diario y limpieza
│       └── 📄 bedrock_blocking_history.py    # Historial de operaciones
│
├── 🗂️ scripts/                               # Scripts de automatización
│   └── 📄 pre-commit-quality-check.sh        # Verificación de calidad pre-commit
│
├── 🗂️ tests/                                 # Suite de pruebas
│   ├── 📄 README.md                          # Documentación de testing
│   ├── 📄 setup.js                           # Configuración de pruebas
│   └── 📄 dashboard.test.js                  # Pruebas del dashboard
│
├── 🗂️ docs/                                  # Documentación adicional
│   ├── 📄 git-commit-workflow.md             # Flujo de trabajo Git
│   ├── 📄 git-commit-quality-workflow.md     # Calidad en commits
│   ├── 📄 enhanced-git-commit-workflow.md    # Flujo mejorado
│   └── 📄 workflow-setup-guide.md            # Guía de configuración
│
├── 📄 deploy_complete_system.sh              # Script de despliegue completo
├── 📄 configure_dashboard_aws.sh             # Configuración del dashboard
├── 📄 launch_dashboard_integrated.sh         # Lanzamiento del dashboard
├── 📄 launch_dashboard.sh                    # Lanzamiento básico
├── 📄 process_bedrock_calls.py               # Procesador de llamadas Bedrock
├── 📄 process_bedrock_calls_poc.py           # Prueba de concepto
├── 📄 provision_bedrock_user.py              # Aprovisionamiento de usuarios
├── 📄 update_metric_filter.py                # Actualización de filtros métricos
├── 📄 fix_automatic_monitoring.py            # Corrección de monitoreo automático
│
└── 📄 Documentos de Estado y Planificación:
    ├── 📄 SOLUTION_SUMMARY_AUTOMATIC_BLOCKING.md    # Resumen de solución de bloqueo
    ├── 📄 DEPLOYMENT_GUIDE.md                       # Guía completa de despliegue
    ├── 📄 DAILY_RESET_HISTORY_ENHANCEMENT.md        # Mejoras del reset diario
    ├── 📄 dashboard_blocking_management_plan.md     # Plan de gestión del dashboard
    └── 📄 SETUP_IAM_ROLE_GUIDE.md                   # Guía de configuración IAM
```

## 🔧 Módulos y Componentes Detallados

### 1. Sistema de Gestión CLI (`src/`)

#### **bedrock_manager.py** - Interfaz Principal
- **Propósito**: Script principal que proporciona interfaz de línea de comandos
- **Funcionalidades**:
  - Aprovisionamiento completo de usuarios
  - Gestión de grupos y equipos
  - Creación y gestión de políticas IAM
  - Generación de claves API con etiquetado
  - Configuración de recursos de equipo

#### **user_manager.py** - Gestión de Usuarios
```python
class UserManager:
    def create_user(username, person_name, team_name, create_login=True)
    def delete_user(username)
    def get_user_info(username)
    def create_api_key(username, tool_name)
    def list_users_by_team(team_name)
    def save_credentials_to_file(username, tool_name, credentials)
```

#### **group_manager.py** - Gestión de Grupos
```python
class GroupManager:
    def create_group(team_name)
    def delete_group(team_name)
    def create_role_for_group(team_name)
    def create_bedrock_policy(team_name)
    def create_assume_role_policy(team_name)
    def attach_policy_to_role(team_name, policy_arn)
    def attach_policy_to_group(team_name, policy_arn)
```

#### **policy_manager.py** - Gestión de Políticas
```python
class PolicyManager:
    def create_policy(policy_name, policy_document)
    def delete_policy(policy_name)
    def create_bedrock_user_policy(username, team_name)
    def create_tool_specific_policy(username, tool_name)
    def attach_policy_to_user(policy_name, username)
    def attach_policy_to_role(policy_name, role_name)
```

### 2. Sistema de Bloqueo Individual (`individual_blocking_system/`)

#### **bedrock_usage_monitor.py** - Monitor de Uso Avanzado
- **Funcionalidades Principales**:
  - Monitoreo en tiempo real de llamadas a Bedrock API
  - Auto-aprovisionamiento inteligente de nuevos usuarios
  - Evaluación de límites diarios con lógica de protección administrativa
  - Integración con DynamoDB para seguimiento de uso
  - Notificaciones SNS automáticas

- **Lógica de Protección Administrativa**:
```python
def has_administrative_protection(user_id, usage_record):
    """
    Verifica si el usuario tiene protección administrativa
    (desbloqueado manualmente por admin hoy)
    """
    # Consulta historial de bloqueos del día
    # Busca operaciones de desbloqueo manual
    # Retorna True si encuentra protección activa
```

#### **bedrock_policy_manager.py** - Gestor de Políticas y Bloqueos
- **Operaciones Soportadas**:
  - `block`: Bloqueo de usuario con duración configurable
  - `unblock`: Desbloqueo con activación de protección administrativa
  - `check_status`: Verificación de estado actual del usuario
  - Gestión de políticas IAM dinámicas para bloqueo/desbloqueo

#### **bedrock_daily_reset.py** - Reset Diario Inteligente
- **Funcionalidades**:
  - Reset automático a las 00:00 UTC
  - Desbloqueo de usuarios bloqueados automáticamente
  - Limpieza de protecciones administrativas expiradas
  - Registro automático en historial de operaciones

#### **bedrock_blocking_history.py** - Historial de Operaciones
- **Capacidades**:
  - Registro completo de todas las operaciones de bloqueo/desbloqueo
  - Consulta de historial por usuario y fecha
  - Soporte para paginación y filtrado
  - TTL automático para gestión de datos (90 días)

### 3. Dashboard Web Interactivo

#### **Características del Dashboard**:
- **Autenticación AWS**: Login seguro con credenciales AWS
- **Múltiples Pestañas**:
  - **User Consumption**: Monitoreo detallado por usuario
  - **Team Consumption**: Análisis por equipos
  - **Consumption Details**: Vista detallada de 10 días
  - **Blocking Management**: Gestión completa de bloqueos

#### **Funcionalidades de Blocking Management**:
- **Bloqueo Manual**: Interfaz para bloquear usuarios con razones personalizadas
- **Duraciones Configurables**: 1 día, 30 días, 90 días, personalizada, indefinida
- **Estado en Tiempo Real**: Visualización del estado actual de todos los usuarios
- **Historial Paginado**: Navegación por historial de operaciones con exportación completa
- **Integración Lambda**: Comunicación directa con funciones Lambda
- **Exportación Completa**: Descarga de todos los registros de operaciones (no solo página actual)

#### **Sistema de Exportación Avanzado**:
- **Exportación Universal**: Botones de exportación CSV en todas las tablas del dashboard
- **Datos Completos**: Exporta todos los registros disponibles, no limitado por paginación
- **Formato Profesional**: Archivos CSV con nombres descriptivos y timestamps
- **Limpieza Automática**: Procesamiento inteligente de progress bars, badges y caracteres especiales
- **Iconos Personalizados**: Interfaz con iconos PNG personalizados para mejor UX

#### **Tablas con Exportación CSV**:
1. **User Usage Details** - Detalles completos de uso por usuario
2. **Team Usage Details** - Información de consumo por equipos
3. **Users in Team** - Listado de usuarios por equipo
4. **User Consumption - Last 10 Days** - Historial de consumo de 10 días
5. **Model Usage by Team** - Uso de modelos por equipo
6. **Current User Status & Manual Blocking** - Estado actual y gestión de bloqueos
7. **Recent Blocking Operations** - Historial completo de operaciones (TODOS los registros)

## 🚀 Guía de Instalación y Despliegue

### Prerrequisitos del Sistema

```bash
# Herramientas requeridas
- AWS CLI v2.x configurado
- Python 3.9+
- Node.js 16+ (para testing)
- jq (para procesamiento JSON)
- Permisos IAM administrativos

# Verificación de prerrequisitos
aws --version
python3 --version
node --version
jq --version
aws sts get-caller-identity
```

### Configuración Inicial

1. **Clonar el Repositorio**:
```bash
git clone https://github.com/carlossarrion-wq/AWS_BEDROCK_USAGE_CONTROL.git
cd AWS_BEDROCK_USAGE_CONTROL
```

2. **Configurar Variables de Entorno**:
```bash
export AWS_REGION="eu-west-1"
export AWS_ACCOUNT_ID="701055077130"
```

3. **Actualizar Configuración**:
```bash
# Editar src/config.json con tu Account ID y región
vim src/config.json

# Editar quota_config.json con límites específicos
vim quota_config.json
```

### Despliegue Completo del Sistema

#### Opción 1: Despliegue Automático (Recomendado)
```bash
# Ejecutar script de despliegue completo
chmod +x deploy_complete_system.sh
./deploy_complete_system.sh
```

#### Opción 2: Despliegue Manual Paso a Paso

**Paso 1: Infraestructura Base**
```bash
cd individual_blocking_system
chmod +x setup_infrastructure.sh
./setup_infrastructure.sh
```

**Paso 2: Funciones Lambda**
```bash
# Crear paquetes de deployment
mkdir -p temp_packages

# Desplegar cada función Lambda
aws lambda create-function \
    --function-name bedrock-usage-monitor \
    --runtime python3.9 \
    --role arn:aws:iam::$AWS_ACCOUNT_ID:role/bedrock-usage-monitor-role \
    --handler bedrock_usage_monitor.lambda_handler \
    --zip-file fileb://bedrock-usage-monitor.zip \
    --timeout 60 \
    --memory-size 256
```

**Paso 3: Configurar Triggers**
```bash
# EventBridge para monitoreo
aws events put-targets \
    --rule bedrock-individual-blocking-monitor \
    --targets "Id"="1","Arn"="arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:bedrock-usage-monitor"

# EventBridge para reset diario
aws events put-targets \
    --rule bedrock-individual-daily-reset \
    --targets "Id"="1","Arn"="arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:bedrock-daily-reset"
```

### Configuración del Dashboard

```bash
# Configurar dashboard con integración AWS
chmod +x configure_dashboard_aws.sh
./configure_dashboard_aws.sh

# Lanzar dashboard integrado
chmod +x launch_dashboard_integrated.sh
./launch_dashboard_integrated.sh
```

### ⚠️ **IMPORTANTE: Ejecutar Dashboard Correctamente**

El dashboard **DEBE** ejecutarse desde un servidor HTTP local para poder leer el archivo `quota_config.json`. **NO** abrir directamente el archivo HTML.

#### **Método Correcto:**
```bash
# En el directorio del proyecto
python3 -m http.server 8080

# Abrir en navegador:
http://localhost:8080/bedrock_usage_dashboard_aws.html
```

#### **Métodos Alternativos:**
```bash
# Opción 1: Servidor Python (recomendado)
python3 -m http.server 8080

# Opción 2: Servidor Node.js (si tienes npx)
npx http-server -p 8080

# Opción 3: Usar el script de lanzamiento
./launch_dashboard_integrated.sh
```

#### **❌ Método Incorrecto:**
```bash
# NO hacer esto - no funcionará correctamente
open bedrock_usage_dashboard_aws.html
```

**Razón**: Los navegadores modernos bloquean la carga de archivos locales por políticas de seguridad CORS. Sin servidor HTTP, el dashboard usará valores por defecto hardcodeados en lugar de leer `quota_config.json`.

## 📊 Configuración de Límites y Cuotas

### Estructura de `quota_config.json`

```json
{
  "users": {
    "darwin_001": {
      "daily_limit": 150,
      "monthly_limit": 3500,
      "warning_threshold": 60,
      "critical_threshold": 85,
      "team": "team_darwin_group",
      "tools": {
        "Cline Agent": {
          "daily_limit": 120,
          "monthly_limit": 3000
        }
      }
    }
  },
  "teams": {
    "team_darwin_group": {
      "monthly_limit": 25000,
      "warning_threshold": 60,
      "critical_threshold": 85
    }
  }
}
```

### Configuración de Equipos Soportados

- **team_darwin_group**: Equipo Darwin
- **team_sap_group**: Equipo SAP
- **team_mulesoft_group**: Equipo MuleSoft
- **team_yo_leo_gas_group**: Equipo Yo Leo Gas
- **team_lcorp_group**: Equipo LCorp

## 🔐 Gestión de Usuarios y Permisos

### 👤 Procedimiento Completo: Crear Nuevo Usuario

#### **⚠️ MÉTODO RECOMENDADO: Usar `provision_bedrock_user.py`**

El script `provision_bedrock_user.py` es la forma **correcta y completa** de crear nuevos usuarios, ya que incluye todas las configuraciones necesarias automáticamente.

#### **Ejemplo Práctico: Crear Usuario `sap_004`**

**Paso 1: Añadir Usuario a Configuración (Opcional)**
```bash
# Editar quota_config.json para añadir el nuevo usuario (opcional - se hace automáticamente)
vim quota_config.json
```

Si quieres pre-configurar el usuario, añade:
```json
{
  "users": {
    "sap_004": {
      "daily_limit": 250,
      "monthly_limit": 5000,
      "warning_threshold": 60,
      "critical_threshold": 85,
      "team": "team_sap_group"
    }
  }
}
```

**Paso 2: Crear Usuario Completo con Script de Aprovisionamiento**
```bash
# Navegar al directorio del proyecto
cd AWS_BEDROCK_USAGE_CONTROL

# Crear usuario completo con aprovisionamiento automático
python3 provision_bedrock_user.py --username sap_004 --group team_sap_group
```

**Este comando realizará automáticamente**:
- ✅ Crear usuario IAM `sap_004` con login profile
- ✅ Asignar al grupo `team_sap_group`
- ✅ Crear política específica `sap_004_BedrockPolicy` (acceso a Bedrock)
- ✅ Asignar política `CloudWatchLogsFullAccess`
- ✅ Añadir tags: `Person: Unknown`, `Team: team_sap_group`
- ✅ Configurar límites: 250 peticiones/día, 5000/mes
- ✅ Crear log streams en CloudWatch
- ✅ Configurar metric filters
- ✅ Crear métricas de prueba
- ✅ Integración completa con sistema de monitoreo

**Paso 3: Crear Clave API (Si es necesario)**
```bash
# Crear clave API usando el CLI manager
python3 src/bedrock_manager.py user create-key sap_004 "Cline Agent"
```

**Paso 4: Verificar Creación del Usuario**
```bash
# Verificar que el usuario tiene todas las políticas necesarias
aws iam list-attached-user-policies --user-name sap_004

# Verificar información completa del usuario
python3 src/bedrock_manager.py user info sap_004

# Verificar en el dashboard
open bedrock_usage_dashboard_aws.html
```

#### **Comparación de Métodos:**

| Aspecto | `provision_bedrock_user.py` ✅ | `bedrock_manager.py` ❌ |
|---------|--------------------------------|-------------------------|
| **Política de Bedrock** | ✅ Creada automáticamente | ❌ No se crea |
| **CloudWatch Logs** | ✅ Configurado automáticamente | ❌ Requiere configuración manual |
| **Límites correctos** | ✅ 250/5000 por defecto | ❌ Valores incorrectos |
| **Log Streams** | ✅ Creados automáticamente | ❌ No se crean |
| **Metric Filters** | ✅ Configurados automáticamente | ❌ No se configuran |
| **Integración completa** | ✅ Lista para usar | ❌ Requiere pasos adicionales |

### Crear Nuevo Usuario Completo (Comando Único)

```bash
# Método RECOMENDADO - Aprovisionamiento completo
python3 provision_bedrock_user.py --username nuevo_usuario --group team_sap_group

# Método ALTERNATIVO - Solo para casos específicos (requiere configuración adicional)
python3 src/bedrock_manager.py user create nuevo_usuario "Nombre Usuario" team_sap_group
python3 src/bedrock_manager.py user create-key nuevo_usuario "Cline Agent"
```

### Estructura de Recursos por Usuario

**Para cada usuario se crean**:
- Usuario IAM: `username`
- Política específica: `username_BedrockPolicy`
- Políticas por herramienta: `username_tool_name_Policy`
- Tags de identificación: `Person`, `Team`, `Tool`

**Para cada equipo se crean**:
- Grupo IAM: `team_name_group`
- Rol IAM: `team_name_BedrockRole`
- Políticas: `team_name_BedrockPolicy`, `team_name_AssumeRolePolicy`

### Permisos y Políticas IAM

#### Política Base de Usuario
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:eu-west-1:701055077130:inference-profile/eu.anthropic.claude-*",
        "arn:aws:bedrock:eu-west-1:701055077130:inference-profile/eu.amazon.nova-*"
      ]
    }
  ]
}
```

## 🛡️ Sistema de Bloqueo Automático con Protección Administrativa

### Lógica de Funcionamiento

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Usuario excede  │───▶│ Sistema bloquea │───▶│ Admin puede     │
│ límite diario   │    │ automáticamente │    │ desbloquear     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Reset diario    │◀───│ Protección      │◀───│ Usuario queda   │
│ limpia          │    │ administrativa  │    │ protegido hasta │
│ protección      │    │ activa          │    │ mañana          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tipos de Bloqueo

1. **Automático**: Por exceder límite diario
2. **Manual 1 día**: Bloqueo administrativo temporal
3. **Manual 30/90 días**: Bloqueo administrativo extendido
4. **Manual Indefinido**: Bloqueo permanente hasta desbloqueo manual
5. **Personalizado**: Con fecha/hora específica de expiración

### Estados de Usuario

- **ACTIVE**: Usuario activo normal
- **ACTIVE_ADMIN**: Usuario con protección administrativa activa
- **BLOCKED**: Usuario bloqueado (automático o manual)
- **WARNING**: Usuario cerca del límite (>60% uso diario)

## 📈 Monitoreo y Alertas

### Métricas de CloudWatch

- **UserMetrics/BedrockUsage**: Uso por usuario
- **TeamMetrics/BedrockUsage**: Uso por equipo
- **BlockingMetrics/Operations**: Operaciones de bloqueo

### Tipos de Alertas SNS

1. **Advertencia de Límite**: Usuario >60% del límite diario
2. **Bloqueo Automático**: Usuario bloqueado por exceder límite
3. **Protección Administrativa**: Usuario desbloqueado manualmente
4. **Nuevo Usuario Detectado**: Auto-aprovisionamiento activado
5. **Error del Sistema**: Fallos en funciones Lambda

### Configuración de Notificaciones

```bash
# Crear topic SNS
aws sns create-topic --name bedrock-usage-alerts

# Suscribir email
aws sns subscribe \
    --topic-arn arn:aws:sns:eu-west-1:701055077130:bedrock-usage-alerts \
    --protocol email \
    --notification-endpoint admin@company.com
```

## 🔍 Auditoría y Cumplimiento

### Historial de Operaciones

Todas las operaciones se registran en `bedrock_blocking_history` con:
- **operation_id**: ID único de la operación
- **timestamp**: Fecha y hora exacta
- **user_id**: Usuario afectado
- **operation**: BLOCK, UNBLOCK, ADMIN_PROTECTION_EXPIRED
- **reason**: Motivo de la operación
- **performed_by**: Quién realizó la operación
- **status**: SUCCESS o FAILED

### Consultas de Auditoría

```python
# Obtener historial de un usuario
lambda_client.invoke(
    FunctionName='bedrock-blocking-history',
    Payload=json.dumps({
        'action': 'get_user_history',
        'user_id': 'darwin_001'
    })
)

# Obtener operaciones recientes
lambda_client.invoke(
    FunctionName='bedrock-blocking-history',
    Payload=json.dumps({
        'action': 'get_history',
        'limit': 50
    })
)
```

## 🧪 Testing y Validación

### Suite de Pruebas Automatizadas

```bash
# Ejecutar pruebas del dashboard
cd tests
npm test

# Ejecutar test de protección administrativa
./test_admin_protection.sh
```

### Pruebas de Integración

El sistema incluye pruebas automatizadas que verifican:
- ✅ Bloqueo automático al exceder límites
- ✅ Protección administrativa funcional
- ✅ Reset diario correcto
- ✅ Historial de operaciones completo
- ✅ Notificaciones SNS
- ✅ Dashboard web responsive

### Validación Manual

```bash
# Verificar estado de usuario
aws lambda invoke \
    --function-name bedrock-policy-manager \
    --payload '{"action":"check_status","user_id":"test_user"}' \
    response.json

# Ver logs de monitoreo
aws logs tail /aws/lambda/bedrock-usage-monitor --follow
```

## 🚨 Troubleshooting y Resolución de Problemas

### Problemas Comunes

#### 1. **Funciones Lambda no se ejecutan**
```bash
# Verificar permisos EventBridge
aws events list-targets-by-rule --rule bedrock-individual-blocking-monitor

# Verificar logs de errores
aws logs filter-log-events \
    --log-group-name /aws/lambda/bedrock-usage-monitor \
    --filter-pattern ERROR
```

#### 2. **Dashboard no carga datos**
- Verificar credenciales AWS en sessionStorage
- Comprobar rol IAM `bedrock-dashboard-access-role`
- Revisar CORS en navegador
- Verificar conectividad a AWS

#### 3. **Protección administrativa no funciona**
```bash
# Verificar tabla de historial
aws dynamodb scan --table-name bedrock_blocking_history --limit 5

# Verificar flags de protección
aws dynamodb get-item \
    --table-name bedrock_user_daily_usage \
    --key '{"user_id":{"S":"user_001"},"date":{"S":"2025-01-15"}}'
```

#### 4. **Reset diario no funciona**
```bash
# Verificar regla CloudWatch Events
aws events describe-rule --name bedrock-individual-daily-reset

# Ejecutar reset manual
aws lambda invoke \
    --function-name bedrock-daily-reset \
    --payload '{"source":"manual"}' \
    response.json
```

### Logs de Debugging

```bash
# Habilitar logging detallado
aws logs put-retention-policy \
    --log-group-name /aws/lambda/bedrock-usage-monitor \
    --retention-in-days 7

# Monitorear logs en tiempo real
aws logs tail /aws/lambda/bedrock-usage-monitor --follow
aws logs tail /aws/lambda/bedrock-policy-manager --follow
aws logs tail /aws/lambda/bedrock-daily-reset --follow
```

## 📚 Documentación Adicional

### Archivos de Documentación Incluidos

- **DEPLOYMENT_GUIDE.md**: Guía completa de despliegue con protección administrativa
- **SOLUTION_SUMMARY_AUTOMATIC_BLOCKING.md**: Resumen de la solución de bloqueo automático
- **DAILY_RESET_HISTORY_ENHANCEMENT.md**: Mejoras del sistema de reset diario
- **dashboard_blocking_management_plan.md**: Plan detallado de gestión del dashboard
- **SETUP_IAM_ROLE_GUIDE.md**: Guía de configuración de roles IAM

### Flujos de Trabajo Git

El proyecto incluye flujos de trabajo Git avanzados:
- **git-commit-workflow.md**: Flujo básico de commits
- **git-commit-quality-workflow.md**: Flujo con verificación de calidad
- **enhanced-git-commit-workflow.md**: Flujo mejorado con automatización

## 🔄 Mantenimiento y Operaciones

### Tareas de Mantenimiento Regular

#### Diarias
- Revisar logs de CloudWatch por errores
- Verificar alertas SNS
- Monitorear usuarios cerca de límites

#### Semanales
- Revisar historial de bloqueos
- Analizar patrones de uso
- Verificar estado de funciones Lambda

#### Mensuales
- Actualizar límites de cuotas según necesidades
- Revisar y limpiar usuarios inactivos
- Actualizar documentación

### Comandos de Operación

```bash
# Ver estado general del sistema
aws lambda list-functions --query 'Functions[?contains(FunctionName, `bedrock`)].FunctionName'

# Verificar tablas DynamoDB
aws dynamodb list-tables --query 'TableNames[?contains(@, `bedrock`)]'

# Ver reglas EventBridge activas
aws events list-rules --query 'Rules[?contains(Name, `bedrock`)].Name'

# Estadísticas de uso
aws dynamodb scan --table-name bedrock_user_daily_usage \
    --filter-expression "#date = :today" \
    --expression-attribute-names '{"#date": "date"}' \
    --expression-attribute-values '{":today": {"S": "2025-01-15"}}'
```

## 🚀 Roadmap y Mejoras Futuras

### Funcionalidades Planificadas

#### Corto Plazo (1-3 meses)
- [ ] Dashboard móvil responsive
- [ ] Exportación de reportes en PDF
- [ ] Integración con Slack/Teams para notificaciones
- [ ] API REST para integraciones externas

#### Medio Plazo (3-6 meses)
- [ ] Machine Learning para predicción de uso
- [ ] Análisis de costos por usuario/equipo
- [ ] Integración con AWS Cost Explorer
- [ ] Sistema de aprobaciones
