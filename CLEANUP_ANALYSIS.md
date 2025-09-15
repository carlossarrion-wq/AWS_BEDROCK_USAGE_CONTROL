# Análisis de Limpieza del Proyecto AWS Bedrock Usage Control

## Funcionalidad Principal Identificada

### Core del Sistema (MANTENER)
1. **Sistema de gestión principal**: `src/bedrock_manager.py` - CLI principal
2. **Módulos core**: `src/user/`, `src/group/`, `src/policy/`, `src/utils/` - Funcionalidad principal
3. **Dashboard**: `bedrock_usage_dashboard.html` - Dashboard principal
4. **Configuración**: `src/config.json`, `quota_config.json` - Configuración del sistema
5. **Scripts de despliegue**: `launch_dashboard.sh` - Script principal de lanzamiento
6. **Documentación principal**: `README.md` - Documentación principal del proyecto

### Sistema de Monitoreo (MANTENER)
1. **Procesamiento de logs**: `process_bedrock_calls.py` - Procesamiento de CloudTrail
2. **Gestión de usuarios**: `provision_bedrock_user.py` - Provisioning de usuarios
3. **Configuración de métricas**: `update_metric_filter.py` - Actualización de filtros

## Archivos Obsoletos/Auxiliares Identificados (ELIMINAR)

### 1. Archivos Duplicados/Obsoletos
- `bedrock_usage_dashboard_original.html` - Versión original del dashboard (obsoleta)
- `bedrock_usage_dashboard_aws.html` - Versión duplicada del dashboard
- `enhanced_provision_bedrock_user.py` - Versión mejorada que puede reemplazar la original
- `bedrock_daily_reset.py` - Duplicado con `individual_blocking_system/lambda_functions/bedrock_daily_reset.py`
- `bedrock_blocking_history.py` - Funcionalidad específica que puede estar obsoleta

### 2. Scripts de Configuración/Despliegue Auxiliares
- `setup.sh` - Script de setup básico (puede estar obsoleto)
- `cleanup.sh` - Script de limpieza genérico
- `implementation_steps.sh` - Pasos de implementación (documentación temporal)
- `bedrock_usage_control_extended.sh` - Script extendido que puede estar obsoleto
- `deploy_session_token_fix.sh` - Fix específico temporal
- `update_metric_filter.sh` - Versión shell del script Python

### 3. Archivos de Documentación Temporal/Auxiliar
- `solution_summary.md` - Resumen de solución específica
- `solution_summary_session_token_fix.md` - Fix específico temporal
- `testing_plan.md` - Plan de testing temporal
- `testing_results.md` - Resultados de testing temporal
- `user_creation_guide.md` - Guía específica que puede estar en README
- `bedrock_usage_requirements.md` - Requisitos que pueden estar en README

### 4. Archivos de Fix/Parches Temporales
- `api_key_metrics_fix.py` - Fix específico temporal
- `fix_automatic_monitoring.py` - Fix específico temporal

### 5. Directorio Individual Blocking System
- `individual_blocking_system/` - Sistema duplicado/experimental con estructura anidada incorrecta
  - Contiene solo `temp_packages/` vacío y estructura anidada confusa
  - Los archivos lambda están referenciados en tabs pero no existen físicamente

### 6. Archivos de Node.js/Testing
- `package.json`, `package-lock.json` - Dependencias de testing que pueden no ser necesarias
- `node_modules/` - Dependencias de Node.js (muy pesado, se puede regenerar)
- `tests/` - Tests que pueden estar obsoletos

### 7. Archivos de Configuración Git/Workflow
- `.clinerules/` - Reglas específicas de Cline que pueden no ser necesarias para el proyecto
- `docs/` - Documentación de workflows que puede estar obsoleta

## Archivos a Mantener Pero Revisar

### Scripts que Necesitan Revisión
- `configure_dashboard_aws.sh` - Revisar si es necesario
- `launch_dashboard_integrated.sh` - Revisar si duplica funcionalidad
- `deploy_complete_system.sh` - Revisar si está actualizado
- `test_admin_protection.sh` - Revisar si es necesario

### Documentación que Necesita Revisión
- `SETUP_IAM_ROLE_GUIDE.md` - Puede integrarse en README
- `DEPLOYMENT_GUIDE.md` - Puede integrarse en README
- Archivos en tabs abiertos que pueden no existir físicamente

## Recomendaciones de Limpieza

### Fase 1: Eliminación Segura
1. Eliminar `node_modules/` (se puede regenerar)
2. Eliminar archivos duplicados obvios
3. Eliminar directorio `individual_blocking_system/` problemático
4. Eliminar archivos de fix temporales

### Fase 2: Consolidación
1. Consolidar documentación en README.md
2. Mantener solo una versión de cada script
3. Revisar y actualizar scripts de despliegue

### Fase 3: Optimización
1. Revisar si las dependencias de Node.js son necesarias
2. Consolidar configuración
3. Limpiar archivos de log y temporales
