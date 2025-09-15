# Propuesta: Mejora para Seguimiento de Tokens en AWS Bedrock

## Resumen
Esta propuesta describe cómo modificar el sistema actual de monitorización de AWS Bedrock para incluir el seguimiento de tokens consumidos por usuario, además del número de peticiones.

## Análisis del Sistema Actual

### Funcionamiento Actual
- **Captura**: CloudTrail registra eventos de llamadas a Bedrock
- **Procesamiento**: `process_bedrock_calls.py` procesa eventos y cuenta peticiones
- **Métricas**: CloudWatch almacena métricas de número de llamadas
- **Visualización**: Dashboard HTML muestra estadísticas por usuario/equipo

### Limitaciones
- Solo cuenta peticiones (no tokens)
- No accede al contenido de las respuestas de Bedrock
- Métricas basadas únicamente en eventos de CloudTrail

## Opciones para Implementar Seguimiento de Tokens

### Opción 1: Interceptación a Nivel de Aplicación (RECOMENDADA)

#### Descripción
Modificar las aplicaciones cliente para que registren información de tokens antes/después de cada llamada a Bedrock.

#### Implementación
1. **Wrapper/SDK personalizado**: Crear un wrapper que intercepte llamadas a Bedrock
2. **Logging estructurado**: Registrar tokens de entrada y salida en CloudWatch Logs
3. **Métricas personalizadas**: Crear métricas de CloudWatch para tokens consumidos

#### Ventajas
- ✅ Acceso completo a tokens de entrada y salida
- ✅ Precisión total en el conteo
- ✅ Flexibilidad para métricas adicionales
- ✅ Compatible con el sistema actual

#### Desventajas
- ❌ Requiere modificar todas las aplicaciones cliente
- ❌ Dependiente de la colaboración de los desarrolladores

### Opción 2: Análisis de Logs de CloudTrail (LIMITADA)

#### Descripción
Intentar extraer información de tokens de los eventos de CloudTrail.

#### Limitaciones
- CloudTrail **NO** incluye el contenido completo de las peticiones/respuestas
- Solo registra metadatos de las llamadas API
- **No es viable** para conteo preciso de tokens

### Opción 3: Integración con AWS Cost and Usage Reports

#### Descripción
Utilizar los informes de costos de AWS que incluyen información de tokens.

#### Ventajas
- ✅ Datos oficiales de AWS
- ✅ No requiere modificar aplicaciones

#### Desventajas
- ❌ Retraso en la disponibilidad de datos (hasta 24 horas)
- ❌ Granularidad limitada
- ❌ Complejidad en la correlación con usuarios específicos

## Propuesta de Implementación: Opción 1

### Fase 1: Wrapper SDK para Bedrock

```python
# bedrock_wrapper.py
import boto3
import json
import time
from datetime import datetime

class BedrockTokenTracker:
    def __init__(self, user_id, team_id, tool_name="Unknown"):
        self.user_id = user_id
        self.team_id = team_id
        self.tool_name = tool_name
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.logs_client = boto3.client('logs')
        
    def invoke_model(self, model_id, body, **kwargs):
        """Wrapper para invoke_model que registra tokens"""
        start_time = time.time()
        
        # Contar tokens de entrada (estimación)
        input_tokens = self._estimate_tokens(body.get('prompt', ''))
        
        # Realizar la llamada real
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            **kwargs
        )
        
        # Procesar respuesta y contar tokens de salida
        response_body = json.loads(response['body'].read())
        output_tokens = self._extract_output_tokens(response_body)
        
        # Registrar métricas
        self._log_token_usage(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            duration=time.time() - start_time
        )
        
        return response
    
    def _estimate_tokens(self, text):
        """Estimación de tokens (aproximadamente 4 caracteres por token)"""
        return len(text) // 4
    
    def _extract_output_tokens(self, response_body):
        """Extraer tokens de salida de la respuesta"""
        # Esto depende del formato de respuesta del modelo
        if 'usage' in response_body:
            return response_body['usage'].get('output_tokens', 0)
        else:
            # Estimación basada en el texto de respuesta
            completion = response_body.get('completion', '')
            return len(completion) // 4
    
    def _log_token_usage(self, model_id, input_tokens, output_tokens, total_tokens, duration):
        """Registrar uso de tokens en CloudWatch Logs"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user': self.user_id,
            'team': self.team_id,
            'tool': self.tool_name,
            'model_id': model_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'duration': duration,
            'event_type': 'token_usage'
        }
        
        try:
            self.logs_client.put_log_events(
                logGroupName='/aws/bedrock/token_usage',
                logStreamName=f'{self.user_id}_tokens',
                logEvents=[{
                    'timestamp': int(time.time() * 1000),
                    'message': json.dumps(log_entry)
                }]
            )
        except Exception as e:
            print(f"Error logging token usage: {e}")
```

### Fase 2: Modificar el Procesador de Eventos

```python
# Añadir a process_bedrock_calls.py
def process_token_usage_event(event, context):
    """Procesar eventos de uso de tokens"""
    
    # Extraer información del evento
    log_data = json.loads(event['awslogs']['data'])
    
    for log_event in log_data['logEvents']:
        message = json.loads(log_event['message'])
        
        if message.get('event_type') == 'token_usage':
            # Crear métricas de tokens
            create_token_metrics(message)

def create_token_metrics(token_data):
    """Crear métricas de CloudWatch para tokens"""
    cloudwatch = boto3.client('cloudwatch')
    
    # Métrica de tokens totales por usuario
    cloudwatch.put_metric_data(
        Namespace='TokenMetrics',
        MetricData=[
            {
                'MetricName': 'TotalTokens',
                'Dimensions': [
                    {'Name': 'User', 'Value': token_data['user']},
                    {'Name': 'Model', 'Value': token_data['model_id']}
                ],
                'Value': token_data['total_tokens'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'InputTokens',
                'Dimensions': [
                    {'Name': 'User', 'Value': token_data['user']}
                ],
                'Value': token_data['input_tokens'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'OutputTokens',
                'Dimensions': [
                    {'Name': 'User', 'Value': token_data['user']}
                ],
                'Value': token_data['output_tokens'],
                'Unit': 'Count'
            }
        ]
    )
```

### Fase 3: Actualizar el Dashboard

```javascript
// Añadir al dashboard HTML
function loadTokenMetrics() {
    // Cargar métricas de tokens desde CloudWatch
    const params = {
        MetricName: 'TotalTokens',
        Namespace: 'TokenMetrics',
        Dimensions: [
            {
                Name: 'User',
                Value: username
            }
        ],
        StartTime: startTime,
        EndTime: endTime,
        Period: 86400,
        Statistics: ['Sum']
    };
    
    cloudwatch.getMetricStatistics(params, (err, data) => {
        if (!err) {
            updateTokenCharts(data);
        }
    });
}

function updateUserUsageTable() {
    // Modificar tabla para incluir columnas de tokens
    // Añadir: "Tokens Diarios", "Tokens Mensuales", "Límite de Tokens"
}
```

## Configuración de Límites de Tokens

### Actualizar quota_config.json

```json
{
  "users": {
    "yo_leo_gas_001": {
      "monthly_limit": 3500,
      "daily_limit": 150,
      "monthly_token_limit": 1000000,
      "daily_token_limit": 50000,
      "warning_threshold": 60,
      "critical_threshold": 85,
      "team": "team_yo_leo_gas_group",
      "tools": {
        "Cline Agent": {
          "monthly_limit": 3000,
          "daily_limit": 120,
          "monthly_token_limit": 800000,
          "daily_token_limit": 40000
        }
      }
    }
  }
}
```

## Plan de Implementación

### Fase 1: Preparación (1-2 semanas)
1. Crear el wrapper SDK para Bedrock
2. Configurar nuevos log groups para tokens
3. Crear métricas de CloudWatch para tokens

### Fase 2: Integración (2-3 semanas)
1. Modificar aplicaciones cliente para usar el wrapper
2. Actualizar el procesador de eventos
3. Crear filtros de métricas para tokens

### Fase 3: Dashboard (1 semana)
1. Actualizar el dashboard para mostrar métricas de tokens
2. Añadir alertas basadas en límites de tokens
3. Crear reportes de consumo de tokens

### Fase 4: Testing y Despliegue (1 semana)
1. Pruebas exhaustivas del sistema
2. Validación de precisión en el conteo
3. Despliegue gradual

## Consideraciones Técnicas

### Precisión en el Conteo
- **Tokens de entrada**: Estimación basada en el texto del prompt
- **Tokens de salida**: Extraídos de la respuesta del modelo (si está disponible)
- **Validación**: Comparar con métricas de facturación de AWS

### Rendimiento
- El wrapper añade latencia mínima (~10-50ms)
- Logging asíncrono para minimizar impacto
- Batch processing para métricas de CloudWatch

### Costos Adicionales
- CloudWatch Logs: ~$0.50 por GB
- CloudWatch Metrics: ~$0.30 por métrica personalizada
- Estimación: $10-50/mes adicionales

## Alternativas Más Simples

### Opción Simplificada: Estimación Basada en Modelos
Si la implementación completa es demasiado compleja, se puede:

1. **Estimar tokens por petición** basándose en promedios históricos
2. **Usar métricas de facturación** de AWS (con retraso)
3. **Implementar gradualmente** empezando por un subconjunto de usuarios

### Ejemplo de Estimación Simple

```python
# Estimaciones promedio por modelo
TOKEN_ESTIMATES = {
    'claude-3-sonnet': {'avg_input': 1500, 'avg_output': 800},
    'claude-3-haiku': {'avg_input': 1000, 'avg_output': 500},
    'claude-3-opus': {'avg_input': 2000, 'avg_output': 1200}
}

def estimate_tokens_from_requests(user_requests, model_usage_distribution):
    """Estimar tokens basándose en número de peticiones"""
    total_tokens = 0
    
    for model, percentage in model_usage_distribution.items():
        model_requests = user_requests * (percentage / 100)
        if model in TOKEN_ESTIMATES:
            avg_tokens = TOKEN_ESTIMATES[model]['avg_input'] + TOKEN_ESTIMATES[model]['avg_output']
            total_tokens += model_requests * avg_tokens
    
    return total_tokens
```

## Conclusión

**Es posible implementar el seguimiento de tokens**, pero requiere:

1. **Modificaciones significativas** al sistema actual
2. **Colaboración** de los equipos de desarrollo para integrar el wrapper
3. **Inversión en tiempo** de desarrollo (4-7 semanas)
4. **Costos adicionales** de infraestructura (~$10-50/mes)

**Recomendación**: Empezar con una **implementación piloto** en un equipo pequeño para validar la viabilidad y precisión antes de desplegar a toda la organización.
