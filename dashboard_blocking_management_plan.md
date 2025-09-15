# Plan de Desarrollo: Nueva Pestaña de Gestión de Bloqueos en el Dashboard

## 📋 RESUMEN EJECUTIVO

Este documento describe el plan completo para añadir una nueva funcionalidad de gestión de bloqueos de usuarios al dashboard existente de AWS Bedrock Usage Control.

### 🎯 OBJETIVO
Crear una nueva pestaña "**User Blocking Management**" que permita:
1. **Gestionar bloqueos** de usuarios (bloquear/desbloquear manualmente)
2. **Ver historial** de operaciones de bloqueo/desbloqueo
3. **Monitorear estado** actual de usuarios bloqueados
4. **Integración completa** con el sistema de bloqueo desplegado

## 📊 ANÁLISIS DEL DASHBOARD ACTUAL

### Estructura Existente
- ✅ **3 pestañas actuales**: User Consumption, Team Consumption, Consumption Details
- ✅ **Sistema de tabs** ya implementado con JavaScript
- ✅ **Integración AWS** con CloudWatch y IAM
- ✅ **Estilos Naturgy** consistentes
- ✅ **Tablas dinámicas** y gráficos Chart.js

### Puntos de Integración Identificados
- ✅ **AWS SDK** ya configurado para llamadas a Lambda
- ✅ **Sistema de usuarios** ya cargado desde IAM
- ✅ **Manejo de errores** y notificaciones implementado
- ✅ **Credenciales** gestionadas via sessionStorage

## 🏗️ PLAN DE DESARROLLO DETALLADO

### FASE 1: Estructura Base de la Nueva Pestaña

#### HTML Structure
```html
<!-- Nueva pestaña: User Blocking Management -->
<div id="blocking-management-tab" class="tab-content">
    <div class="section-header">
        <h2>User Blocking Management</h2>
        <button class="refresh-button" onclick="loadBlockingData()">
            <span class="refresh-icon">&#x21bb;</span>
            Refresh
        </button>
    </div>
    
    <!-- Sección 1: Estado Actual de Usuarios -->
    <div class="card">
        <h2>Current User Status & Manual Blocking</h2>
        <div class="admin-controls">
            <div class="blocking-controls">
                <h3>Manual Block User</h3>
                <div class="block-form">
                    <select id="user-select" class="form-control">
                        <option value="">Select User to Block...</option>
                    </select>
                    <select id="block-duration" class="form-control">
                        <option value="1day">1 Day</option>
                        <option value="indefinite">Indefinite</option>
                    </select>
                    <input type="text" id="block-reason" class="form-control" placeholder="Reason for blocking...">
                    <button onclick="performManualBlock()" class="btn btn-danger">
                        🚫 Block User
                    </button>
                </div>
            </div>
        </div>
        
        <table id="user-blocking-status-table">
            <thead>
                <tr>
                    <th>User</th>
                    <th>Person</th>
                    <th>Team</th>
                    <th>Status</th>
                    <th>Daily Usage</th>
                    <th>Daily Limit</th>
                    <th>Block Type</th>
                    <th>Blocked Since</th>
                    <th>Expires</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <tr><td colspan="10">Loading...</td></tr>
            </tbody>
        </table>
    </div>
    
    <!-- Sección 2: Historial de Operaciones -->
    <div class="card">
        <h2>Recent Blocking Operations</h2>
        <table id="blocking-operations-table">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Operation</th>
                    <th>Reason</th>
                    <th>Performed By</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr><td colspan="6">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</div>
```

#### Tab Button Addition
```html
<!-- Añadir a los botones de pestañas existentes -->
<button class="tab-button" onclick="showTab('blocking-management-tab')">Blocking Management</button>
```

### FASE 2: Funciones JavaScript de Integración

#### Funciones Principales
```javascript
// Nuevas funciones para gestión de bloqueos
async function loadBlockingData() {
    try {
        // Mostrar indicadores de carga
        showLoadingIndicators();
        
        // Cargar estado actual de usuarios desde DynamoDB
        await loadUserBlockingStatus();
        
        // Cargar historial de operaciones
        await loadBlockingOperationsHistory();
        
        console.log('Blocking data loaded successfully');
    } catch (error) {
        console.error('Error loading blocking data:', error);
        showBlockingError('Failed to load blocking management data');
    }
}

async function loadUserBlockingStatus() {
    const tableBody = document.querySelector('#user-blocking-status-table tbody');
    tableBody.innerHTML = '<tr><td colspan="8">Loading user status...</td></tr>';
    
    try {
        // Para cada usuario, verificar su estado de bloqueo
        const userStatusPromises = allUsers.map(async (userId) => {
            const status = await checkUserBlockStatus(userId);
            return { userId, ...status };
        });
        
        const userStatuses = await Promise.all(userStatusPromises);
        
        // Actualizar tabla con estados
        updateUserStatusTable(userStatuses);
        
    } catch (error) {
        console.error('Error loading user blocking status:', error);
        tableBody.innerHTML = '<tr><td colspan="8">Error loading user status</td></tr>';
    }
}

async function loadBlockingOperationsHistory() {
    const tableBody = document.querySelector('#blocking-operations-table tbody');
    tableBody.innerHTML = '<tr><td colspan="6">Loading operations history...</td></tr>';
    
    try {
        // Llamar a nueva Lambda function para obtener historial
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-blocking-history',
            Payload: JSON.stringify({
                action: 'get_history',
                limit: 50 // Últimas 50 operaciones
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        if (response.statusCode === 200) {
            const operations = JSON.parse(response.body).operations;
            updateOperationsHistoryTable(operations);
        } else {
            throw new Error('Failed to fetch operations history');
        }
        
    } catch (error) {
        console.error('Error loading operations history:', error);
        tableBody.innerHTML = '<tr><td colspan="6">Error loading operations history</td></tr>';
    }
}

// Gestión de bloqueos manuales
async function performBlockingAction(userId, action, reason) {
    try {
        // Mostrar confirmación para acciones críticas
        if (!confirm(`Are you sure you want to ${action} user ${userId}?\nReason: ${reason}`)) {
            return;
        }
        
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify({
                action: action, // 'block' or 'unblock'
                user_id: userId,
                reason: reason,
                performed_by: 'dashboard_admin'
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        // Log operation in history
        await logBlockingOperation(userId, action, reason, response.statusCode === 200 ? 'SUCCESS' : 'FAILED');
        
        // Mostrar resultado
        if (response.statusCode === 200) {
            showSuccessMessage(`User ${userId} ${action}ed successfully`);
        } else {
            showErrorMessage(`Failed to ${action} user ${userId}: ${response.body}`);
        }
        
        // Refresh data
        await loadBlockingData();
        
        return response;
    } catch (error) {
        console.error('Error performing blocking action:', error);
        showErrorMessage(`Error performing ${action} operation: ${error.message}`);
        throw error;
    }
}

async function blockUser(userId, reason = 'manual_override') {
    return await performBlockingAction(userId, 'block', reason);
}

async function unblockUser(userId, reason = 'manual_override') {
    return await performBlockingAction(userId, 'unblock', reason);
}

async function checkUserBlockStatus(userId) {
    try {
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify({
                action: 'check_status',
                user_id: userId
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        if (response.statusCode === 200) {
            return JSON.parse(response.body);
        } else {
            throw new Error('Failed to check user status');
        }
    } catch (error) {
        console.error(`Error checking status for user ${userId}:`, error);
        return { user_id: userId, is_blocked: false, error: true };
    }
}

// Funciones auxiliares
function updateUserStatusTable(userStatuses) {
    const tableBody = document.querySelector('#user-blocking-status-table tbody');
    tableBody.innerHTML = '';
    
    // Poblar dropdown de usuarios para bloqueo manual
    populateUserSelect(userStatuses);
    
    userStatuses.forEach(status => {
        const personTag = getUserPersonTag(status.userId) || "Unknown";
        const userTeam = getUserTeam(status.userId);
        const dailyUsage = userMetrics[status.userId]?.daily?.[8] || 0;
        const dailyLimit = getUserDailyLimit(status.userId);
        
        const isBlocked = status.is_blocked;
        const blockType = status.block_type || 'N/A';
        const blockedSince = status.blocked_at ? new Date(status.blocked_at).toLocaleString() : 'N/A';
        const expiresAt = status.expires_at ? new Date(status.expires_at).toLocaleString() : 
                         (status.block_type === 'indefinite' ? 'Never' : 'N/A');
        
        const row = `
            <tr class="${isBlocked ? 'blocked-user' : ''}">
                <td>${status.userId}</td>
                <td>${personTag}</td>
                <td>${userTeam}</td>
                <td>
                    <span class="status-badge ${isBlocked ? 'blocked' : 'active'}">
                        ${isBlocked ? '🚫 BLOCKED' : '✅ ACTIVE'}
                    </span>
                </td>
                <td>${dailyUsage}</td>
                <td>${dailyLimit}</td>
                <td>
                    <span class="block-type-badge ${blockType.toLowerCase()}">
                        ${blockType === 'manual_1day' ? '⏰ 1 Day' : 
                          blockType === 'manual_indefinite' ? '∞ Indefinite' : 
                          blockType === 'automatic' ? '🤖 Auto' : blockType}
                    </span>
                </td>
                <td>${blockedSince}</td>
                <td>${expiresAt}</td>
                <td class="actions-cell">
                    <button class="action-btn block-btn" onclick="showBlockModal('${status.userId}')" 
                            ${isBlocked ? 'disabled' : ''}>
                        🚫 Block
                    </button>
                    <button class="action-btn unblock-btn" onclick="unblockUser('${status.userId}', 'manual_unblock')" 
                            ${!isBlocked ? 'disabled' : ''}>
                        ✅ Unblock
                    </button>
                    <button class="action-btn status-btn" onclick="refreshUserStatus('${status.userId}')">
                        📊 Refresh
                    </button>
                </td>
            </tr>
        `;
        
        tableBody.innerHTML += row;
    });
}

// Poblar dropdown de usuarios para bloqueo manual
function populateUserSelect(userStatuses) {
    const userSelect = document.getElementById('user-select');
    userSelect.innerHTML = '<option value="">Select User to Block...</option>';
    
    // Solo mostrar usuarios activos (no bloqueados)
    const activeUsers = userStatuses.filter(status => !status.is_blocked);
    
    activeUsers.forEach(status => {
        const personTag = getUserPersonTag(status.userId) || "Unknown";
        const option = document.createElement('option');
        option.value = status.userId;
        option.textContent = `${status.userId} (${personTag})`;
        userSelect.appendChild(option);
    });
}

// Función para bloqueo manual desde el formulario
async function performManualBlock() {
    const userSelect = document.getElementById('user-select');
    const durationSelect = document.getElementById('block-duration');
    const reasonInput = document.getElementById('block-reason');
    
    const userId = userSelect.value;
    const duration = durationSelect.value;
    const reason = reasonInput.value.trim();
    
    // Validaciones
    if (!userId) {
        showErrorMessage('Please select a user to block');
        return;
    }
    
    if (!reason) {
        showErrorMessage('Please provide a reason for blocking');
        return;
    }
    
    try {
        // Confirmar acción
        const confirmMessage = `Block user ${userId} for ${duration === '1day' ? '1 day' : 'indefinitely'}?\nReason: ${reason}`;
        if (!confirm(confirmMessage)) {
            return;
        }
        
        // Llamar a Lambda con información de duración
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify({
                action: 'block',
                user_id: userId,
                reason: reason,
                block_type: duration === '1day' ? 'manual_1day' : 'manual_indefinite',
                duration: duration,
                performed_by: 'dashboard_admin'
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        if (response.statusCode === 200) {
            showSuccessMessage(`User ${userId} blocked successfully for ${duration === '1day' ? '1 day' : 'indefinitely'}`);
            
            // Limpiar formulario
            userSelect.value = '';
            reasonInput.value = '';
            durationSelect.value = '1day';
            
            // Recargar datos
            await loadBlockingData();
        } else {
            showErrorMessage(`Failed to block user ${userId}: ${response.body}`);
        }
        
        // Log operation
        await logBlockingOperation(userId, 'BLOCK', reason, response.statusCode === 200 ? 'SUCCESS' : 'FAILED');
        
    } catch (error) {
        console.error('Error performing manual block:', error);
        showErrorMessage(`Error blocking user: ${error.message}`);
    }
}

// Modal para bloqueo individual (alternativa al formulario principal)
function showBlockModal(userId) {
    const reason = prompt(`Enter reason for blocking user ${userId}:`);
    if (!reason) return;
    
    const duration = confirm(`Block indefinitely? Click OK for indefinite, Cancel for 1 day.`) ? 'indefinite' : '1day';
    
    performBlockingActionWithDuration(userId, 'block', reason, duration);
}

// Versión extendida de performBlockingAction con duración
async function performBlockingActionWithDuration(userId, action, reason, duration = null) {
    try {
        const confirmMessage = action === 'block' && duration ? 
            `Block user ${userId} for ${duration === '1day' ? '1 day' : 'indefinitely'}?\nReason: ${reason}` :
            `Are you sure you want to ${action} user ${userId}?\nReason: ${reason}`;
            
        if (!confirm(confirmMessage)) {
            return;
        }
        
        const lambda = new AWS.Lambda();
        const payload = {
            action: action,
            user_id: userId,
            reason: reason,
            performed_by: 'dashboard_admin'
        };
        
        // Añadir información de duración para bloqueos
        if (action === 'block' && duration) {
            payload.block_type = duration === '1day' ? 'manual_1day' : 'manual_indefinite';
            payload.duration = duration;
        }
        
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify(payload)
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        // Log operation
        await logBlockingOperation(userId, action.toUpperCase(), reason, response.statusCode === 200 ? 'SUCCESS' : 'FAILED');
        
        // Mostrar resultado
        if (response.statusCode === 200) {
            const durationText = duration ? ` for ${duration === '1day' ? '1 day' : 'indefinitely'}` : '';
            showSuccessMessage(`User ${userId} ${action}ed successfully${durationText}`);
        } else {
            showErrorMessage(`Failed to ${action} user ${userId}: ${response.body}`);
        }
        
        // Refresh data
        await loadBlockingData();
        
        return response;
    } catch (error) {
        console.error('Error performing blocking action:', error);
        showErrorMessage(`Error performing ${action} operation: ${error.message}`);
        throw error;
    }
}

function updateOperationsHistoryTable(operations) {
    const tableBody = document.querySelector('#blocking-operations-table tbody');
    tableBody.innerHTML = '';
    
    operations.forEach(operation => {
        const timestamp = new Date(operation.timestamp).toLocaleString();
        const statusClass = operation.status === 'SUCCESS' ? 'success' : 'failed';
        
        const row = `
            <tr>
                <td>${timestamp}</td>
                <td>${operation.user_id}</td>
                <td>
                    <span class="operation-badge ${operation.operation.toLowerCase()}">
                        ${operation.operation === 'BLOCK' ? '🚫' : '✅'} ${operation.operation}
                    </span>
                </td>
                <td>${operation.reason}</td>
                <td>${operation.performed_by}</td>
                <td>
                    <span class="status-badge ${statusClass}">
                        ${operation.status}
                    </span>
                </td>
            </tr>
        `;
        
        tableBody.innerHTML += row;
    });
}

async function logBlockingOperation(userId, operation, reason, status) {
    try {
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-blocking-history',
            Payload: JSON.stringify({
                action: 'log_operation',
                operation: {
                    user_id: userId,
                    operation: operation.toUpperCase(),
                    reason: reason,
                    performed_by: 'dashboard_admin',
                    status: status,
                    timestamp: new Date().toISOString()
                }
            })
        };
        
        await lambda.invoke(params).promise();
    } catch (error) {
        console.error('Error logging blocking operation:', error);
    }
}

// Funciones de utilidad
function showLoadingIndicators() {
    document.querySelector('#user-blocking-status-table tbody').innerHTML = 
        '<tr><td colspan="8">Loading user status...</td></tr>';
    document.querySelector('#blocking-operations-table tbody').innerHTML = 
        '<tr><td colspan="6">Loading operations history...</td></tr>';
}

function showSuccessMessage(message) {
    // Implementar notificación de éxito
    console.log('SUCCESS:', message);
    // Aquí se podría añadir un toast o modal de éxito
}

function showErrorMessage(message) {
    // Implementar notificación de error
    console.error('ERROR:', message);
    // Aquí se podría añadir un toast o modal de error
}

function showBlockingError(message) {
    const statusTable = document.querySelector('#user-blocking-status-table tbody');
    const historyTable = document.querySelector('#blocking-operations-table tbody');
    
    statusTable.innerHTML = `<tr><td colspan="8" class="error-message">${message}</td></tr>`;
    historyTable.innerHTML = `<tr><td colspan="6" class="error-message">${message}</td></tr>`;
}

function getUserTeam(userId) {
    for (const team in usersByTeam) {
        if (usersByTeam[team].includes(userId)) {
            return team;
        }
    }
    return "Unknown";
}

function getUserDailyLimit(userId) {
    return quotaConfig?.users?.[userId]?.daily_limit || 150;
}

async function refreshUserStatus(userId) {
    try {
        const status = await checkUserBlockStatus(userId);
        // Actualizar solo la fila de este usuario
        await loadUserBlockingStatus();
        showSuccessMessage(`Status refreshed for user ${userId}`);
    } catch (error) {
        showErrorMessage(`Failed to refresh status for user ${userId}`);
    }
}
```

### FASE 3: Backend - Nueva Lambda Function

#### Nueva función: bedrock-blocking-history
```python
#!/usr/bin/env python3
"""
AWS Bedrock Individual Blocking System - Blocking History Lambda
===============================================================

This Lambda function manages the history of blocking operations:
1. Logging blocking/unblocking operations
2. Retrieving operation history
3. Providing audit trail for compliance

Author: AWS Bedrock Usage Control System
Version: 1.0.0
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List
import uuid
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')

# Configuration
REGION = os.environ.get('AWS_REGION', 'eu-west-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '701055077130')
HISTORY_TABLE_NAME = os.environ.get('HISTORY_TABLE', 'bedrock_blocking_operations')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for blocking history management
    
    Args:
        event: Event containing action and parameters
        context: Lambda context object
        
    Returns:
        Dict with status code and results
    """
    try:
        logger.info(f"Processing blocking history event: {json.dumps(event, default=str)}")
        
        action = event.get('action')
        
        if action == 'get_history':
            return get_blocking_history(event.get('limit', 50))
        elif action == 'log_operation':
            return log_blocking_operation(event.get('operation', {}))
        elif action == 'get_user_history':
            return get_user_blocking_history(event.get('user_id'))
        else:
            logger.error(f"Invalid action: {action}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid action: {action}'})
            }
            
    except Exception as e:
        logger.error(f"Error processing blocking history event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_blocking_history(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent blocking operations history
    
    Args:
        limit: Maximum number of operations to return
        
    Returns:
        Dict with operations list
    """
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Scan table and sort by timestamp (most recent first)
        response = table.scan(
            Limit=limit
        )
        
        operations = response.get('Items', [])
        
        # Sort by timestamp descending
        operations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Take only the requested limit
        operations = operations[:limit]
        
        logger.info(f"Retrieved {len(operations)} blocking operations")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'operations': operations,
                'count': len(operations)
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting blocking history: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def log_blocking_operation(operation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log a blocking operation to the history table
    
    Args:
        operation: Operation details to log
        
    Returns:
        Dict with operation result
    """
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        
        # Prepare operation record
        operation_record = {
            'operation_id': operation_id,
            'timestamp': operation.get('timestamp', datetime.utcnow().isoformat()),
            'user_id': operation.get('user_id'),
            'operation': operation.get('operation'),  # 'BLOCK' or 'UNBLOCK'
            'reason': operation.get('reason'),
            'performed_by': operation.get('performed_by'),
            'status': operation.get('status'),  # 'SUCCESS' or 'FAILED'
            'details': operation.get('details', ''),
            'ttl': int((datetime.utcnow().timestamp() + 86400 * 90))  # 90 days TTL
        }
        
        # Store operation
        table.put_item(Item=operation_record)
        
        logger.info(f"Logged blocking operation: {operation_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Operation logged successfully',
                'operation_id': operation_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error logging blocking operation: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_user_blocking_history(user_id: str) -> Dict[str, Any]:
    """
    Get blocking history for a specific user
    
    Args:
        user_id: User ID to get history for
        
    Returns:
        Dict with user's blocking history
    """
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Query operations for specific user
        response = table.scan(
            FilterExpression='user_id = :user_id',
            ExpressionAttributeValues={
                ':user_id': user_id
            }
        )
        
        operations = response.get('Items', [])
        
        # Sort by timestamp descending
        operations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        logger.info(f"Retrieved {len(operations)} operations for user {user_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'user_id': user_id,
                'operations': operations,
                'count': len(operations)
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting user blocking history: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For testing purposes
if __name__ == "__main__":
    # Test events
    test_log_event = {
        "action": "log_operation",
        "operation": {
            "user_id": "test_user_001",
            "operation": "BLOCK",
            "reason": "daily_limit_exceeded",
            "performed_by": "system",
            "status": "SUCCESS",
            "details": "User exceeded daily limit of 50 requests"
        }
    }
    
    test_get_history_event = {
        "action": "get_history",
        "limit": 10
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "bedrock-blocking-history"
            self.memory_limit_in_mb = 256
    
    # Test the handlers
    print("Testing log operation:")
    result = lambda_handler(test_log_event, MockContext())
    print(json.dumps(result, indent=2))
    
    print("\nTesting get history:")
    result = lambda_handler(test_get_history_event, MockContext())
    print(json.dumps(result, indent=2))
```

### FASE 4: Extensión de DynamoDB

#### Nueva tabla: bedrock_blocking_operations
```python
# Definición de la nueva tabla DynamoDB
{
    "TableName": "bedrock_blocking_operations",
    "KeySchema": [
        {
            "AttributeName": "operation_id",
            "KeyType": "HASH"
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "operation_id",
            "AttributeType": "S"
        }
    ],
    "BillingMode": "PAY_PER_REQUEST",
    "TimeToLiveSpecification": {
        "AttributeName": "ttl",
        "Enabled": True
    }
}

# Estructura de registro
{
    "operation_id": "uuid-string",
    "timestamp": "2025-01-15T14:30:00Z",
    "user_id": "darwin_001",
    "operation": "BLOCK|UNBLOCK",
    "reason": "daily_limit_exceeded|manual_override|daily_reset|admin_manual_block",
    "block_type": "automatic|manual_1day|manual_indefinite",
    "duration": "1day|indefinite",
    "expires_at": "2025-01-16T14:30:00Z",  # Para bloqueos temporales
    "performed_by": "system|dashboard_admin|admin_user",
    "status": "SUCCESS|FAILED",
    "details": "Additional information about the operation",
    "ttl": 1737849600  # 90 days from creation
}

# Extensión de la tabla bedrock_user_daily_usage para incluir información de bloqueo
{
    "user_id": "darwin_001",
    "date": "2025-01-15",
    "requests": 45,
    "status": "active|blocked",
    "is_blocked": true,
    "block_type": "manual_1day|manual_indefinite|automatic",
    "blocked_at": "2025-01-15T14:30:00Z",
    "expires_at": "2025-01-16T14:30:00Z",  # null para bloqueos indefinidos
    "blocked_by": "dashboard_admin",
    "block_reason": "Inappropriate usage detected",
    "ttl": 1737849600
}
```

### FASE 5: Estilos CSS Adicionales

```css
/* Estilos para la nueva pestaña de gestión de bloqueos */

/* Controles de administración */
.admin-controls {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}

.blocking-controls h3 {
    color: #1e4a72;
    margin-bottom: 15px;
    font-size: 16px;
}

.block-form {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.form-control {
    padding: 8px 12px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 14px;
    min-width: 150px;
}

.form-control:focus {
    outline: none;
    border-color: #1e4a72;
    box-shadow: 0 0 0 2px rgba(30, 74, 114, 0.25);
}

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: bold;
    transition: all 0.3s ease;
}

.btn-danger {
    background-color: #f56565;
    color: white;
}

.btn-danger:hover {
    background-color: #e53e3e;
}

/* Badges de tipo de bloqueo */
.block-type-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
}

.block-type-badge.manual_1day {
    background-color: #fff3cd;
    color: #856404;
    border: 1px solid #ffeaa7;
}

.block-type-badge.manual_indefinite {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.block-type-badge.automatic {
    background-color: #d1ecf1;
    color: #0c5460;
    border: 1px solid #bee5eb;
}

.block-type-badge.n\/a {
    background-color: #e2e3e5;
    color: #6c757d;
    border: 1px solid #d6d8db;
}

/* Botones de acción */
.action-btn {
    padding: 4px 8px;
    margin: 2px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: bold;
    transition: all 0.3s ease;
}

.block-btn {
    background-color: #f56565;
    color: white;
}

.block-btn:hover:not(:disabled) {
    background-color: #e53e3e;
}

.unblock-btn {
    background-color: #27ae60;
    color: white;
}

.unblock-btn:hover:not(:disabled) {
    background-color: #2ecc71;
}

.status-btn {
    background-color: #3498db;
    color: white;
}

.status-btn:hover:not(:disabled) {
    background-color: #2980b9;
}

.action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Badges de estado */
.status-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
}

.status-badge.active {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.status-badge.blocked {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.status-badge.success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.status-badge.failed {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

/* Badges de operación */
.operation-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
}

.operation-badge.block {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.operation-badge.unblock {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

/* Filas de usuarios bloqueados */
.blocked-user {
    background-color: #fff5f5;
    border-left: 4px solid #f56565;
}

.blocked-user:hover {
    background-color: #fed7d7;
}

/* Celda de acciones */
.actions-cell {
    white-space: nowrap;
    text-align: center;
}

/* Mensajes de error */
.error-message {
    color: #721c24;
    background-color: #f8d7da;
    padding: 10px;
    text-align: center;
    font-style: italic;
}

/* Indicadores de carga */
.loading-indicator {
    text-align: center;
    color: #6c757d;
    font-style: italic;
    padding: 20px;
}

/* Responsive design para botones de acción */
@media (max-width: 768px) {
    .action-btn {
        display: block;
        width: 100%;
        margin: 2px 0;
    }
    
    .actions-cell {
        min-width: 120px;
    }
}

/* Animaciones */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.tab-content.active {
    animation: fadeIn 0.3s ease-in;
}

/* Tooltips para botones deshabilitados */
.action-btn:disabled {
    position: relative;
}

.action-btn:disabled:hover::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background-color: #333;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    white-space: nowrap;
    z-index: 1000;
}
```

## 📅 CRONOGRAMA DE IMPLEMENTACIÓN

### Semana 1: Preparación y Estructura
- **Día 1-2**: Crear estructura HTML de nueva pestaña
- **Día 3-4**: Implementar navegación entre tabs
- **Día 5**: Añadir estilos CSS y responsive design

### Semana 2: Funcionalidad Backend
- **Día 1-2**: Crear nueva Lambda function `bedrock-blocking-history`
- **Día 3-4**: Crear tabla DynamoDB `bedrock_blocking_operations`
- **Día 5**: Testing de integración backend

### Semana 3: Funcionalidad Frontend
- **Día 1-2**: Implementar funciones JavaScript de bloqueo
- **Día 3-4**: Crear interfaz de gestión de usuarios
- **Día 5**: Implementar historial de operaciones

### Semana 4: Testing y Refinamiento
- **Día 1-2**: Testing completo de funcionalidades
- **Día 3-4**: Refinamiento de UI/UX
- **Día 5**: Documentación y despliegue

## 🎯 FUNCIONALIDADES ESPECÍFICAS

### 1. Gestión de Bloqueos
- ✅ **Bloqueo manual** de usuarios con razón personalizable
- ✅ **Bloqueo temporal** (1 día) o **indefinido** por administrador
- ✅ **Desbloqueo manual** con confirmación
- ✅ **Verificación de estado** en tiempo real
- ✅ **Prevención de acciones duplicadas**
- ✅ **Listado completo** de usuarios con estado de consumo y bloqueo

### 2. Historial de Operaciones
- ✅ **Log completo** de todas las operaciones
- ✅ **Filtrado** por usuario, fecha, tipo de operación
- ✅ **Búsqueda** en tiempo real
- ✅ **Exportación** de datos (opcional)

### 3. Monitoreo en Tiempo Real
- ✅ **Estado actual** de todos los usuarios
- ✅ **Indicadores visuales** de usuarios bloqueados
- ✅ **Alertas** para usuarios cerca del límite
- ✅ **Refresh automático** cada 30 segundos

## 🔒 CONSIDERACIONES DE SEGURIDAD

### 1. Autenticación y Autorización
- ✅ **Verificación** de credenciales AWS
- ✅ **Permisos IAM** específicos para gestión de bloqueos
- ✅ **Audit trail** completo de todas las acciones
- ✅ **Confirmaciones** para acciones críticas

### 2. Validaciones
- ✅ **Validación** de usuarios existentes
- ✅ **Prevención** de auto-bloqueo
- ✅ **Límites** de operaciones por minuto
- ✅ **Rollback** automático en caso de error

### 3. Permisos IAM Requeridos

#### Para el Dashboard (usuario administrador)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:eu-west-1:701055077130:function:bedrock-policy-manager",
        "arn:aws:lambda:eu-west-1:701055077130:function
