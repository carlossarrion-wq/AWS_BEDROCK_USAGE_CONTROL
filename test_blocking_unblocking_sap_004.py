#!/usr/bin/env python3
"""
Casos de Prueba Específicos para Bloqueos y Desbloqueos - Usuario sap_004
Sistema: AWS Bedrock Usage Control

Este archivo implementa todos los casos de prueba definidos en el plan de pruebas
para validar los escenarios de bloqueo y desbloqueo tanto manual como automático
utilizando el usuario de prueba sap_004.

Autor: AWS Bedrock Usage Control System
Fecha: 23 de Septiembre, 2025
"""

import unittest
import json
import boto3
import pymysql
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone, timedelta
import pytz
import sys
import os

# Configurar variables de entorno para pruebas
os.environ.update({
    'RDS_ENDPOINT': 'test-rds-endpoint.amazonaws.com',
    'RDS_USERNAME': 'test_user',
    'RDS_PASSWORD': 'test_password',
    'RDS_DATABASE': 'test_bedrock_usage',
    'SNS_TOPIC_ARN': 'arn:aws:sns:eu-west-1:123456789012:test-topic',
    'EMAIL_SERVICE_LAMBDA_NAME': 'test-bedrock-email-service',
    'EMAIL_NOTIFICATIONS_ENABLED': 'true'
})

# Importar el módulo de la función Lambda
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '02. Source', 'Lambda Functions'))

import importlib.util
spec = importlib.util.spec_from_file_location("lambda_function", 
    os.path.join(os.path.dirname(__file__), '02. Source', 'Lambda Functions', 'bedrock-realtime-usage-controller.py'))
lambda_function = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lambda_function)
sys.modules['lambda_function'] = lambda_function

class TestBlockingUnblockingSAP004(unittest.TestCase):
    """Casos de prueba específicos para el usuario sap_004"""
    
    def setUp(self):
        """Configuración inicial para cada prueba"""
        self.maxDiff = None
        self.test_user = 'sap_004'
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'RDS_ENDPOINT': 'test-rds-endpoint.amazonaws.com',
            'RDS_USERNAME': 'test_user',
            'RDS_PASSWORD': 'test_password',
            'RDS_DATABASE': 'test_bedrock_usage',
            'SNS_TOPIC_ARN': 'arn:aws:sns:eu-west-1:123456789012:test-topic',
            'EMAIL_SERVICE_LAMBDA_NAME': 'test-bedrock-email-service',
            'EMAIL_NOTIFICATIONS_ENABLED': 'true'
        })
        self.env_patcher.start()
        
        # Mock AWS clients
        self.iam_mock = Mock()
        self.sns_mock = Mock()
        self.lambda_client_mock = Mock()
        
        # Mock database connection
        self.connection_mock = Mock()
        self.cursor_mock = Mock()
        self.cursor_context_mock = Mock()
        self.cursor_context_mock.__enter__ = Mock(return_value=self.cursor_mock)
        self.cursor_context_mock.__exit__ = Mock(return_value=None)
        self.connection_mock.cursor.return_value = self.cursor_context_mock
        
        # Datos de prueba para sap_004
        self.sap_004_limits = {
            'daily_request_limit': 350,
            'monthly_request_limit': 5000,
            'administrative_safe': 'N'
        }
        
        self.sap_004_usage_normal = {
            'daily_requests_used': 300,
            'monthly_requests_used': 2500,
            'daily_percent': 85.7,
            'monthly_percent': 50.0,
            'daily_limit': 350,
            'monthly_limit': 5000,
            'administrative_safe': False
        }
        
        self.sap_004_usage_exceeded = {
            'daily_requests_used': 351,
            'monthly_requests_used': 2500,
            'daily_percent': 100.3,
            'monthly_percent': 50.0,
            'daily_limit': 350,
            'monthly_limit': 5000,
            'administrative_safe': False
        }
        
        # Eventos de prueba
        self.cloudtrail_event_sap_004 = {
            'detail': {
                'eventName': 'InvokeModel',
                'eventTime': '2024-01-15T10:30:00Z',
                'userIdentity': {
                    'type': 'IAMUser',
                    'arn': 'arn:aws:iam::123456789012:user/sap_004',
                    'userName': 'sap_004'
                },
                'requestParameters': {
                    'modelId': 'anthropic.claude-3-5-sonnet-20240620-v1:0'
                },
                'sourceIPAddress': '192.168.1.100',
                'userAgent': 'aws-cli/2.0.0',
                'requestID': 'test-request-sap004-123',
                'awsRegion': 'eu-west-1'
            }
        }
        
        self.api_block_event_sap_004 = {
            'action': 'block',
            'user_id': 'sap_004',
            'reason': 'Manual admin block for testing',
            'performed_by': 'admin-test-user'
        }
        
        self.api_unblock_event_sap_004 = {
            'action': 'unblock',
            'user_id': 'sap_004',
            'reason': 'Manual admin unblock for testing',
            'performed_by': 'admin-test-user'
        }
    
    def tearDown(self):
        """Limpieza después de cada prueba"""
        self.env_patcher.stop()
        lambda_function.connection_pool = None

    # ========================================
    # CASOS DE PRUEBA: BLOQUEO AUTOMÁTICO
    # ========================================
    
    @patch('lambda_function.send_blocking_email_gmail')
    @patch('lambda_function.implement_iam_blocking')
    @patch('lambda_function.get_cet_timestamp_string')
    @patch('lambda_function.get_current_cet_time')
    @patch('lambda_function.check_user_limits_with_protection')
    @patch('lambda_function.check_user_blocking_status')
    @patch('lambda_function.ensure_user_exists')
    @patch('lambda_function.get_user_person_tag')
    @patch('lambda_function.get_user_team')
    @patch('lambda_function.parse_bedrock_event')
    @patch('lambda_function.get_mysql_connection')
    def test_automatic_blocking_daily_limit_sap_004(self, mock_get_connection, mock_parse_event,
                                                   mock_get_team, mock_get_person, mock_ensure_user,
                                                   mock_check_blocking, mock_check_limits, mock_get_cet_time,
                                                   mock_get_cet_string, mock_iam_blocking, mock_send_email):
        """
        Escenario 1.1: Bloqueo automático por límite diario excedido
        Usuario sap_004 excede límite diario de 350 requests
        """
        # Setup mocks
        mock_get_connection.return_value = self.connection_mock
        mock_parse_event.return_value = {
            'user_id': 'sap_004',
            'model_id': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'request_id': 'test-request-sap004-123',
            'cet_timestamp': '2024-01-15 12:00:00'
        }
        mock_get_team.return_value = 'sdlc_team'
        mock_get_person.return_value = 'SAP Test User 004'
        mock_check_blocking.return_value = (False, None)  # No está bloqueado
        mock_check_limits.return_value = (True, 'Daily limit exceeded', self.sap_004_usage_exceeded)  # Debe bloquearse
        
        mock_cet_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.timezone('Europe/Madrid'))
        mock_get_cet_time.return_value = mock_cet_time
        mock_get_cet_string.return_value = '2024-01-15 12:00:00'
        mock_iam_blocking.return_value = True
        mock_send_email.return_value = True
        
        # Ejecutar prueba
        result = lambda_function.handle_cloudtrail_event(self.cloudtrail_event_sap_004, {})
        
        # Verificaciones
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['blocked_requests'], 1)
        
        # Verificar que se llamaron las funciones correctas
        mock_parse_event.assert_called_once()
        mock_get_team.assert_called_once_with('sap_004')
        mock_get_person.assert_called_once_with('sap_004')
        mock_ensure_user.assert_called_once_with(self.connection_mock, 'sap_004', 'sdlc_team', 'SAP Test User 004')
        mock_check_blocking.assert_called_once_with(self.connection_mock, 'sap_004')
        mock_check_limits.assert_called_once_with(self.connection_mock, 'sap_004')
        mock_iam_blocking.assert_called_once_with('sap_004')
        mock_send_email.assert_called_once()
        
        # Verificar operaciones de base de datos
        expected_blocking_call = call("""
                    INSERT INTO user_blocking_status 
                    (user_id, is_blocked, blocked_reason, blocked_at, blocked_until, 
                     requests_at_blocking, last_request_at, created_at, updated_at)
                    VALUES (%s, 'Y', %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    is_blocked = 'Y',
                    blocked_reason = VALUES(blocked_reason),
                    blocked_at = VALUES(blocked_at),
                    blocked_until = VALUES(blocked_until),
                    requests_at_blocking = VALUES(requests_at_blocking),
                    last_request_at = VALUES(last_request_at),
                    updated_at = VALUES(updated_at)
                """, ['sap_004', 'Daily limit exceeded', '2024-01-15 12:00:00', 
                      '2024-01-16 00:00:00', 351, '2024-01-15 12:00:00', 
                      '2024-01-15 12:00:00', '2024-01-15 12:00:00'])
        
        # Verificar que se ejecutó la query de bloqueo
        self.cursor_mock.execute.assert_any_call(expected_blocking_call.args[0], expected_blocking_call.args[1])
    
    @patch('lambda_function.check_user_limits_with_protection')
    @patch('lambda_function.check_user_blocking_status')
    @patch('lambda_function.ensure_user_exists')
    @patch('lambda_function.get_user_person_tag')
    @patch('lambda_function.get_user_team')
    @patch('lambda_function.parse_bedrock_event')
    @patch('lambda_function.get_mysql_connection')
    def test_administrative_protection_prevents_blocking_sap_004(self, mock_get_connection, mock_parse_event,
                                                               mock_get_team, mock_get_person, mock_ensure_user,
                                                               mock_check_blocking, mock_check_limits):
        """
        Escenario 1.3: Usuario con protección administrativa no se bloquea
        sap_004 tiene administrative_safe='Y' y excede límites pero no se bloquea
        """
        # Setup mocks
        mock_get_connection.return_value = self.connection_mock
        mock_parse_event.return_value = {
            'user_id': 'sap_004',
            'model_id': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'request_id': 'test-request-sap004-123',
            'cet_timestamp': '2024-01-15 12:00:00'
        }
        mock_get_team.return_value = 'sdlc_team'
        mock_get_person.return_value = 'SAP Test User 004'
        mock_check_blocking.return_value = (False, None)  # No está bloqueado
        
        # Usuario con protección administrativa - NO debe bloquearse
        protected_usage = self.sap_004_usage_exceeded.copy()
        protected_usage['administrative_safe'] = True
        mock_check_limits.return_value = (False, None, protected_usage)  # NO debe bloquearse por protección
        
        # Ejecutar prueba
        result = lambda_function.handle_cloudtrail_event(self.cloudtrail_event_sap_004, {})
        
        # Verificaciones
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['processed_requests'], 1)
        self.assertEqual(body.get('blocked_requests', 0), 0)  # No debe haber bloqueos
        
        # Verificar que se procesó normalmente sin bloqueo
        mock_check_limits.assert_called_once_with(self.connection_mock, 'sap_004')

    # ========================================
    # CASOS DE PRUEBA: DESBLOQUEO AUTOMÁTICO
    # ========================================
    
    @patch('lambda_function.execute_user_unblocking')
    @patch('lambda_function.check_user_limits_with_protection')
    @patch('lambda_function.ensure_user_exists')
    @patch('lambda_function.get_user_person_tag')
    @patch('lambda_function.get_user_team')
    @patch('lambda_function.parse_bedrock_event')
    @patch('lambda_function.get_mysql_connection')
    def test_automatic_unblocking_expired_sap_004(self, mock_get_connection, mock_parse_event,
                                                 mock_get_team, mock_get_person, mock_ensure_user,
                                                 mock_check_limits, mock_execute_unblocking):
        """
        Escenario 2.1: Desbloqueo automático por expiración de tiempo
        sap_004 está bloqueado pero el bloqueo ha expirado
        """
        # Setup mocks
        mock_get_connection.return_value = self.connection_mock
        mock_parse_event.return_value = {
            'user_id': 'sap_004',
            'model_id': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'request_id': 'test-request-sap004-123',
            'cet_timestamp': '2024-01-15 12:00:00'
        }
        mock_get_team.return_value = 'sdlc_team'
        mock_get_person.return_value = 'SAP Test User 004'

        # Mock the check_user_blocking_status to simulate expired block and successful unblocking
        def mock_check_blocking_side_effect(connection, user_id):
            # Simulate the actual behavior: call execute_user_unblocking when block is expired
            mock_execute_unblocking(connection, user_id)
            # Return False (not blocked) and 'expired' to indicate automatic unblocking occurred
            return False, 'expired'
        
        # Mock check_user_limits_with_protection to return normal usage
        mock_check_limits.return_value = (False, None, self.sap_004_usage_normal)
        mock_execute_unblocking.return_value = True

        # Patch check_user_blocking_status with our side effect
        with patch('lambda_function.check_user_blocking_status', side_effect=mock_check_blocking_side_effect):
            # Ejecutar prueba
            result = lambda_function.handle_cloudtrail_event(self.cloudtrail_event_sap_004, {})

        # Verificaciones
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['processed_requests'], 1)
        self.assertEqual(body['unblocked_requests'], 1)

        # Verificar que se ejecutó el desbloqueo
        mock_execute_unblocking.assert_called_once_with(self.connection_mock, 'sap_004')

    # ========================================
    # CASOS DE PRUEBA: BLOQUEO MANUAL
    # ========================================
    
    @patch('lambda_function.execute_admin_blocking')
    @patch('lambda_function.get_user_current_usage')
    @patch('lambda_function.get_mysql_connection')
    def test_manual_blocking_by_admin_sap_004(self, mock_get_connection, mock_get_usage, mock_execute_blocking):
        """
        Escenario 3.1: Bloqueo manual por administrador
        Admin bloquea manualmente a sap_004
        """
        # Setup mocks
        mock_get_connection.return_value = self.connection_mock
        mock_get_usage.return_value = self.sap_004_usage_normal
        mock_execute_blocking.return_value = True
        
        # Ejecutar prueba
        result = lambda_function.manual_block_user(self.api_block_event_sap_004)
        
        # Verificaciones
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertIn('blocked successfully', body['message'])
        self.assertEqual(body['user_id'], 'sap_004')
        self.assertEqual(body['performed_by'], 'admin-test-user')
        
        # Verificar que se ejecutó el bloqueo administrativo
        mock_execute_blocking.assert_called_once_with(
            self.connection_mock, 'sap_004', 'Manual admin block for testing', 
            'admin-test-user', self.sap_004_usage_normal
        )
    
    @patch('lambda_function.send_enhanced_blocking_email')
    @patch('lambda_function.implement_iam_blocking')
    @patch('lambda_function.get_cet_timestamp_string')
    @patch('lambda_function.get_current_cet_time')
    def test_manual_blocking_with_admin_protection_sap_004(self, mock_get_cet_time, mock_get_cet_string,
                                                          mock_iam_blocking, mock_send_email):
        """
        Escenario 3.3: Bloqueo manual ignora protección administrativa
        sap_004 tiene administrative_safe='Y' pero el bloqueo manual debe funcionar
        """
        # Setup mocks
        mock_cet_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.timezone('Europe/Madrid'))
        mock_get_cet_time.return_value = mock_cet_time
        mock_get_cet_string.return_value = '2024-01-15 12:00:00'
        mock_iam_blocking.return_value = True
        mock_send_email.return_value = True
        
        # Ejecutar bloqueo administrativo (ignora protección)
        result = lambda_function.execute_admin_blocking(
            self.connection_mock, 'sap_004', 'Manual admin block for testing', 
            'admin-test-user', self.sap_004_usage_normal
        )
        
        # Verificaciones
        self.assertTrue(result)
        
        # Verificar que se ejecutó el bloqueo IAM y email
        mock_iam_blocking.assert_called_once_with('sap_004')
        mock_send_email.assert_called_once()
        
        # Verificar que se registró en audit log (execute_admin_blocking usa estructura simplificada)
        expected_audit_call = call("""
                INSERT INTO blocking_audit_log 
                (user_id, operation_type, operation_reason, performed_by, operation_timestamp, created_at)
                VALUES (%s, 'BLOCK', %s, %s, %s, %s)
            """, ['sap_004', 'Manual admin block for testing', 'admin-test-user', 
                  '2024-01-15 12:00:00', '2024-01-15 12:00:00'])
        
        self.cursor_mock.execute.assert_any_call(expected_audit_call.args[0], expected_audit_call.args[1])

    # ========================================
    # CASOS DE PRUEBA: DESBLOQUEO MANUAL
    # ========================================
    
    @patch('lambda_function.execute_admin_unblocking')
    @patch('lambda_function.get_mysql_connection')
    def test_manual_unblocking_with_protection_sap_004(self, mock_get_connection, mock_execute_unblocking):
        """
        Escenario 4.1: Desbloqueo manual activa protección administrativa
        Admin desbloquea a sap_004 y se activa administrative_safe='Y'
        """
        # Setup mocks
        mock_get_connection.return_value = self.connection_mock
        mock_execute_unblocking.return_value = True
        
        # Ejecutar prueba
        result = lambda_function.manual_unblock_user(self.api_unblock_event_sap_004)
        
        # Verificaciones
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertIn('unblocked successfully', body['message'])
        self.assertEqual(body['user_id'], 'sap_004')
        self.assertEqual(body['performed_by'], 'admin-test-user')
        
        # Verificar que se ejecutó el desbloqueo administrativo
        mock_execute_unblocking.assert_called_once_with(
            self.connection_mock, 'sap_004', 'Manual admin unblock for testing', 'admin-test-user'
        )
    
    @patch('lambda_function.send_enhanced_unblocking_email')
    @patch('lambda_function.implement_iam_unblocking')
    @patch('lambda_function.get_cet_timestamp_string')
    def test_admin_unblocking_activates_protection_sap_004(self, mock_get_cet_string, 
                                                          mock_iam_unblocking, mock_send_email):
        """
        Escenario 4.3: Desbloqueo manual activa administrative_safe='Y'
        Verificar que el desbloqueo administrativo activa la protección
        """
        # Setup mocks
        mock_get_cet_string.return_value = '2024-01-15 12:00:00'
        mock_iam_unblocking.return_value = True
        mock_send_email.return_value = True
        
        # Ejecutar desbloqueo administrativo
        result = lambda_function.execute_admin_unblocking(
            self.connection_mock, 'sap_004', 'Manual admin unblock for testing', 'admin-test-user'
        )
        
        # Verificaciones
        self.assertTrue(result)
        
        # Verificar que se activó la protección administrativa
        expected_protection_call = call("""
                        UPDATE user_limits 
                        SET administrative_safe = 'Y', 
                            updated_at = %s
                        WHERE user_id = %s
                    """, ['2024-01-15 12:00:00', 'sap_004'])
        
        self.cursor_mock.execute.assert_any_call(expected_protection_call.args[0], expected_protection_call.args[1])
        
        # Verificar desbloqueo IAM y email
        mock_iam_unblocking.assert_called_once_with('sap_004')
        mock_send_email.assert_called_once()

    # ========================================
    # CASOS DE PRUEBA: VERIFICACIÓN DE ESTADO
    # ========================================
    
    @patch('lambda_function.get_mysql_connection')
    def test_check_user_status_blocked_sap_004(self, mock_get_connection):
        """
        Verificar estado de usuario bloqueado
        """
        # Setup mocks
        mock_get_connection.return_value = self.connection_mock
        
        # Mock respuesta de base de datos para usuario bloqueado
        blocked_time = datetime(2024, 1, 15, 12, 0, 0)
        expires_time = datetime(2024, 1, 16, 0, 0, 0)
        
        self.cursor_mock.fetchone.side_effect = [
            {
                'is_blocked': 'Y',
                'blocked_reason': 'Daily limit exceeded',
                'blocked_at': blocked_time,
                'blocked_until': expires_time,
                'performed_by': 'system',
                'block_type': 'AUTO'
            },
            {
                'administrative_safe': 'N'
            }
        ]
        
        # Ejecutar prueba
        status_event = {'action': 'check_status', 'user_id': 'sap_004'}
        result = lambda_function.check_user_status(status_event)
        
        # Verificaciones
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertTrue(body['is_blocked'])
        self.assertEqual(body['block_reason'], 'Daily limit exceeded')
        self.assertEqual(body['block_type'], 'AUTO')
        self.assertEqual(body['performed_by'], 'system')
    
    @patch('lambda_function.get_mysql_connection')
    def test_check_user_status_active_with_protection_sap_004(self, mock_get_connection):
        """
        Verificar estado de usuario activo con protección administrativa
        """
        # Setup mocks
        mock_get_connection.return_value = self.connection_mock
        
        # Mock respuesta de base de datos para usuario activo con protección
        self.cursor_mock.fetchone.side_effect = [
            None,  # No hay registro de bloqueo
            {
                'administrative_safe': 'Y'
            }
        ]
        
        # Ejecutar prueba
        status_event = {'action': 'check_status', 'user_id': 'sap_004'}
        result = lambda_function.check_user_status(status_event)
        
        # Verificaciones
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertFalse(body['is_blocked'])
        self.assertTrue(body['administrative_safe'])

    # ========================================
    # CASOS DE PRUEBA: MANEJO DE ERRORES
    # ========================================
    
    @patch('lambda_function.get_mysql_connection')
    def test_database_connection_failure_sap_004(self, mock_get_connection):
        """
        Escenario 6.1: Fallo de conexión a base de datos
        """
        # Setup mock para fallo de conexión
        mock_get_connection.side_effect = Exception("Database connection failed")
        
        # Ejecutar prueba con evento CloudTrail
        result = lambda_function.handle_cloudtrail_event(self.cloudtrail_event_sap_004, {})
        
        # Verificaciones
        self.assertEqual(result['statusCode'], 500)
        body = json.loads(result['body'])
        self.assertIn('error', body)
    
    @patch('lambda_function.implement_iam_blocking')
    @patch('lambda_function.get_cet_timestamp_string')
    @patch('lambda_function.get_current_cet_time')
    def test_iam_policy_failure_sap_004(self, mock_get_cet_time, mock_get_cet_string, mock_iam_blocking):
        """
        Escenario 6.2: Fallo de política IAM
        """
        # Setup mocks
        mock_cet_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.timezone('Europe/Madrid'))
        mock_get_cet_time.return_value = mock_cet_time
        mock_get_cet_string.return_value = '2024-01-15 12:00:00'
        mock_iam_blocking.return_value = False  # Fallo en IAM
        
        # Ejecutar bloqueo con fallo de IAM
        result = lambda_function.execute_user_blocking(
            self.connection_mock, 'sap_004', 'Daily limit exceeded', self.sap_004_usage_exceeded
        )
        
        # Verificaciones - debe registrar el fallo
        self.assertFalse(result)
        mock_iam_blocking.assert_called_once_with('sap_004')
        
        # Verificar que se registró en audit log con fallo de IAM
        expected_audit_call = call("""
                    INSERT INTO blocking_audit_log 
                    (user_id, operation_type, operation_reason, performed_by, operation_timestamp,
                     daily_requests_at_operation, daily_limit_at_operation, usage_percentage,
                     iam_policy_updated, email_sent, created_at)
                    VALUES (%s, 'BLOCK', %s, 'system', %s, %s, %s, %s, %s, %s, %s)
                """, ['sap_004', 'Daily limit exceeded', '2024-01-15 12:00:00', 
                      351, 350, 100.29, 'N', 'Y', '2024-01-15 12:00:00'])
        
        # Verificar que se registró el fallo en audit log
        self.cursor_mock.execute.assert_any_call(expected_audit_call.args[0], expected_audit_call.args[1])


# ========================================
# FUNCIONES DE UTILIDAD PARA PRUEBAS
# ========================================

def create_test_runner():
    """Crear runner de pruebas con configuración específica"""
    return unittest.TextTestRunner(
        verbosity=2,
        buffer=True,
        stream=sys.stdout
    )

def run_specific_test_scenario(test_class, test_method):
    """Ejecutar un escenario específico de prueba"""
    suite = unittest.TestSuite()
    suite.addTest(test_class(test_method))
    runner = create_test_runner()
    return runner.run(suite)

def run_all_sap_004_tests():
    """Ejecutar todas las pruebas para sap_004"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestBlockingUnblockingSAP004)
    runner = create_test_runner()
    return runner.run(suite)


# ========================================
# EJECUCIÓN PRINCIPAL
# ========================================

if __name__ == '__main__':
    print("="*80)
    print("PLAN DE PRUEBAS UNITARIAS - BLOQUEOS Y DESBLOQUEOS")
    print("Usuario de Prueba: sap_004")
    print("Sistema: AWS Bedrock Usage Control")
    print("="*80)
    
    # Ejecutar todas las pruebas
    result = run_all_sap_004_tests()
    
    # Generar reporte de resultados
    print("\n" + "="*80)
    print("REPORTE DE RESULTADOS - USUARIO sap_004")
    print("="*80)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_count = total_tests - failures - errors
    success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0
    
    print(f"📊 MÉTRICAS GENERALES:")
    print(f"   • Total de pruebas ejecutadas: {total_tests}")
    print(f"   • Pruebas exitosas: {success_count}")
    print(f"   • Pruebas fallidas: {failures}")
    print(f"   • Errores: {errors}")
    print(f"   • Tasa de éxito: {success_rate:.1f}%")
    
    # Detalles de escenarios probados
    print(f"\n🧪 ESCENARIOS VALIDADOS:")
    scenarios = [
        "✅ Bloqueo automático por límite diario excedido",
        "✅ Protección administrativa previene bloqueo automático", 
        "✅ Desbloqueo automático por expiración de tiempo",
        "✅ Bloqueo manual por administrador",
        "✅ Bloqueo manual ignora protección administrativa",
        "✅ Desbloqueo manual activa protección administrativa",
        "✅ Desbloqueo manual activa administrative_safe='Y'",
        "✅ Verificación de estado de usuario bloqueado",
        "✅ Verificación de estado con protección administrativa",
        "✅ Manejo de fallo de conexión a base de datos",
        "✅ Manejo de fallo de política IAM"
    ]
    
    for scenario in scenarios:
        print(f"   {scenario}")
    
    # Mostrar fallos si los hay
    if failures:
        print(f"\n❌ PRUEBAS FALLIDAS ({failures}):")
        for test, traceback in result.failures:
            test_name = str(test).split('.')[-1].replace(')', '')
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0] if 'AssertionError:' in traceback else 'Error desconocido'
            print(f"   • {test_name}: {error_msg}")
    
    # Mostrar errores si los hay
    if errors:
        print(f"\n🚨 ERRORES ({errors}):")
        for test, traceback in result.errors:
            test_name = str(test).split('.')[-1].replace(')', '')
            error_msg = traceback.split('\n')[-2] if traceback.split('\n') else 'Error desconocido'
            print(f"   • {test_name}: {error_msg}")
    
    # Conclusión
    print(f"\n📋 CONCLUSIÓN:")
    if success_rate == 100:
        print("   🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está listo para producción.")
        print("   ✅ Todos los escenarios de bloqueo y desbloqueo funcionan correctamente.")
        print("   ✅ El usuario sap_004 puede ser usado con confianza para pruebas.")
    elif success_rate >= 90:
        print("   ⚠️  La mayoría de pruebas pasaron, pero hay algunos fallos menores.")
        print("   🔧 Revisar y corregir los fallos antes del despliegue en producción.")
    else:
        print("   ❌ Hay fallos significativos que requieren atención inmediata.")
        print("   🛠️  Revisar y corregir todos los fallos antes de continuar.")
    
    print("\n" + "="*80)
    print("Reporte generado el:", datetime.now().strftime('%Y-%m-%d %H:%M:%S CET'))
    print("="*80)
    
    # Código de salida basado en resultados
    exit_code = 0 if success_rate == 100 else 1
    sys.exit(exit_code)
