#!/usr/bin/env python3
"""
AWS Bedrock Individual Blocking System - Usage Monitor Lambda
=============================================================

This Lambda function monitors Bedrock API calls via CloudTrail events and:
1. Updates daily usage counters in DynamoDB
2. Auto-provisions new users with intelligent configuration
3. Evaluates daily limits and triggers blocking when exceeded
4. Sends notifications for warnings and blocks

Author: AWS Bedrock Usage Control System
Version: 1.0.0
"""

import json
import boto3
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional
import os

# Custom JSON encoder for Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')
sns = boto3.client('sns')
cloudwatch = boto3.client('cloudwatch')

# Configuration
REGION = os.environ.get('AWS_REGION', 'eu-west-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '701055077130')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'bedrock_user_daily_usage')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', f'arn:aws:sns:{REGION}:{ACCOUNT_ID}:bedrock-usage-alerts')
POLICY_MANAGER_FUNCTION = os.environ.get('POLICY_MANAGER_FUNCTION', 'bedrock-policy-manager')

# Email configuration from environment variables
EMAIL_SERVICE_TYPE = os.environ.get('EMAIL_SERVICE_TYPE', 'gmail_smtp')
EMAIL_NOTIFICATIONS_ENABLED = os.environ.get('EMAIL_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
GMAIL_USER = os.environ.get('GMAIL_USER', '')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', '')

# Load configuration from file or environment
DEFAULT_CONFIG = {
    "daily_limits": {
        "default_user_limit": 250,
        "default_warning_threshold": 150,
        "reset_time_utc": "00:00:00",
        "grace_period_minutes": 5
    },
    "blocking_system": {
        "enabled": True,
        "dry_run_mode": False,
        "notification_channels": ["sns", "email"],
        "auto_unblock": True,
        "emergency_override_users": ["admin_user"]
    },
    "auto_provisioning": {
        "enabled": True,
        "default_team_daily_limit": 50,
        "team_limit_division_factor": 10,
        "notification_on_new_user": True
    }
}

class GmailEmailNotificationService:
    """Service for sending email notifications using Gmail SMTP"""
    
    def __init__(self, gmail_user: str, gmail_password: str):
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
        self.iam_client = iam
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
    
    def get_user_email(self, user_id: str) -> Optional[str]:
        """
        Retrieve user email from IAM tags
        
        Args:
            user_id: The user ID to get email for
            
        Returns:
            User email address or None if not found
        """
        try:
            response = self.iam_client.list_user_tags(UserName=user_id)
            user_tags = {tag['Key']: tag['Value'] for tag in response['Tags']}
            
            email = user_tags.get('Email')
            if email:
                logger.info(f"Retrieved email for user {user_id}: {email}")
                return email
            else:
                logger.warning(f"No Email tag found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving email for user {user_id}: {str(e)}")
            return None
    
    def send_warning_email(self, user_id: str, usage_record: Dict[str, Any]) -> bool:
        """
        Send warning email to user approaching their daily limit
        
        Args:
            user_id: The user ID
            usage_record: Current usage record from DynamoDB
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            user_email = self.get_user_email(user_id)
            if not user_email:
                logger.warning(f"Cannot send warning email to {user_id} - no email address")
                return False
            
            # Prepare email content
            current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
            daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
            
            subject = f"⚠️ Bedrock Usage Warning - {current_usage}/{daily_limit} requests used"
            
            html_body = self._generate_warning_email_html(user_id, usage_record)
            text_body = self._generate_warning_email_text(user_id, usage_record)
            
            # Send email
            return self._send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error(f"Error sending warning email to {user_id}: {str(e)}")
            return False
    
    def send_blocked_email(self, user_id: str, usage_record: Dict[str, Any], expires_at: str = None) -> bool:
        """
        Send blocked notification email to user
        
        Args:
            user_id: The user ID
            usage_record: Current usage record from DynamoDB
            expires_at: When the block expires
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            user_email = self.get_user_email(user_id)
            if not user_email:
                logger.warning(f"Cannot send blocked email to {user_id} - no email address")
                return False
            
            # Prepare email content
            current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
            daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
            
            subject = f"🚫 Bedrock Access Blocked - Daily limit exceeded ({current_usage}/{daily_limit})"
            
            html_body = self._generate_blocked_email_html(user_id, usage_record, expires_at)
            text_body = self._generate_blocked_email_text(user_id, usage_record, expires_at)
            
            # Send email
            return self._send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error(f"Error sending blocked email to {user_id}: {str(e)}")
            return False
    
    def send_unblocked_email(self, user_id: str, reason: str = "automatic_expiration") -> bool:
        """
        Send unblocked notification email to user
        
        Args:
            user_id: The user ID
            reason: Reason for unblocking
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            user_email = self.get_user_email(user_id)
            if not user_email:
                logger.warning(f"Cannot send unblocked email to {user_id} - no email address")
                return False
            
            # Prepare email content
            subject = f"✅ Bedrock Access Restored - You can now use Bedrock again"
            
            html_body = self._generate_unblocked_email_html(user_id, reason)
            text_body = self._generate_unblocked_email_text(user_id, reason)
            
            # Send email
            return self._send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error(f"Error sending unblocked email to {user_id}: {str(e)}")
            return False
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Send email using Gmail SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.gmail_user
            message["To"] = to_email
            message["Reply-To"] = self.gmail_user
            
            # Create the plain-text and HTML version of your message
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            
            # Add HTML/plain-text parts to MIMEMultipart message
            message.attach(part1)
            message.attach(part2)
            
            # Create secure connection with server and send email
            context = ssl.create_default_context()
            # For development/testing, we may need to be less strict about certificates
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.gmail_user, self.gmail_password)
                text = message.as_string()
                server.sendmail(self.gmail_user, to_email, text)
            
            logger.info(f"Email sent successfully to {to_email} via Gmail SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email} via Gmail SMTP: {str(e)}")
            return False
    
    def _generate_warning_email_html(self, user_id: str, usage_record: Dict[str, Any]) -> str:
        """Generate HTML content for warning email in Spanish"""
        current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
        daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
        warning_threshold = int(usage_record['warning_threshold']) if isinstance(usage_record['warning_threshold'], Decimal) else usage_record['warning_threshold']
        team = usage_record.get('team', 'desconocido')
        percentage = int((current_usage / daily_limit) * 100) if daily_limit > 0 else 0
        remaining = daily_limit - current_usage
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Aviso de Uso de Bedrock</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #F4B860; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .usage-bar {{ background-color: #EFE6D5; height: 20px; border-radius: 10px; margin: 10px 0; }}
                .usage-fill {{ background-color: #F4B860; height: 100%; border-radius: 10px; transition: width 0.3s ease; }}
                .stats {{ display: flex; justify-content: space-between; margin: 20px 0; }}
                .stat {{ text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #F4B860; }}
                .stat-label {{ font-size: 12px; color: #666; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Aviso de Uso de Bedrock</h1>
                    <p>Te estás acercando a tu límite diario</p>
                </div>
                <div class="content">
                    <p>Hola <strong>{user_id}</strong>,</p>
                    
                    <p>Este es un aviso de que te estás acercando a tu límite diario de uso de AWS Bedrock.</p>
                    
                    <div class="usage-bar">
                        <div class="usage-fill" style="width: {percentage}%;"></div>
                    </div>
                    
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-value">{current_usage}</div>
                            <div class="stat-label">Solicitudes Usadas</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{remaining}</div>
                            <div class="stat-label">Restantes</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{daily_limit}</div>
                            <div class="stat-label">Límite Diario</div>
                        </div>
                    </div>
                    
                    <p><strong>Estado Actual:</strong></p>
                    <ul>
                        <li>Uso: {current_usage} de {daily_limit} solicitudes ({percentage}%)</li>
                        <li>Equipo: {team}</li>
                        <li>Umbral de aviso: {warning_threshold} solicitudes</li>
                        <li>Solicitudes restantes: {remaining}</li>
                    </ul>
                    
                    <p><strong>¿Qué sucede después?</strong></p>
                    <p>Si excedes tu límite diario de {daily_limit} solicitudes, tu acceso a AWS Bedrock será bloqueado temporalmente. El bloqueo expirará automáticamente y tu acceso será restaurado a las 00h de mañana.</p>
                    
                    <p>Por favor, regula el uso de este servicio para evitar interrupciones en tu trabajo.</p>
                </div>
                <div class="footer">
                    <p>Esta es una notificación automática del Sistema de Control de Uso de AWS Bedrock.</p>
                    <p>Enviado desde: {self.gmail_user}</p>
                    <p>Fecha y hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_warning_email_text(self, user_id: str, usage_record: Dict[str, Any]) -> str:
        """Generate plain text content for warning email"""
        current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
        daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
        warning_threshold = int(usage_record['warning_threshold']) if isinstance(usage_record['warning_threshold'], Decimal) else usage_record['warning_threshold']
        team = usage_record.get('team', 'unknown')
        percentage = int((current_usage / daily_limit) * 100) if daily_limit > 0 else 0
        remaining = daily_limit - current_usage
        
        return f"""
BEDROCK USAGE WARNING

Hello {user_id},

This is a friendly reminder that you're approaching your daily AWS Bedrock usage limit.

CURRENT STATUS:
- Usage: {current_usage} out of {daily_limit} requests ({percentage}%)
- Team: {team}
- Warning threshold: {warning_threshold} requests
- Remaining requests: {remaining}

WHAT HAPPENS NEXT:
If you exceed your daily limit of {daily_limit} requests, your access to AWS Bedrock will be temporarily blocked for 24 hours. The block will automatically expire, and your access will be restored.

Please monitor your usage carefully to avoid interruption to your work.

---
This is an automated notification from the AWS Bedrock Usage Control System.
Sent from: {self.gmail_user}
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """
    
    def _generate_blocked_email_html(self, user_id: str, usage_record: Dict[str, Any], expires_at: str = None) -> str:
        """Generate HTML content for blocked email in Spanish with soft pink color"""
        current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
        daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
        team = usage_record.get('team', 'desconocido')
        
        # Format expiration time in Spanish - show as 00:00h CET regardless of UTC time
        expiration_text = "00:00h de mañana"
        if expires_at and expires_at != 'Indefinite':
            try:
                from datetime import timezone, timedelta
                exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                # Since the system sets expiration to 00:00h UTC of next day,
                # we show it as 00:00h CET (which is the intended user experience)
                expiration_text = exp_time.strftime('%Y-%m-%d a las 00:00:00 CET')
            except:
                expiration_text = "00:00h de mañana"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Acceso a Bedrock Bloqueado</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #EC7266; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .alert-box {{ background-color: #ffebee; border-left: 4px solid #EC7266; padding: 15px; margin: 20px 0; }}
                .stats {{ display: flex; justify-content: space-between; margin: 20px 0; }}
                .stat {{ text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #EC7266; }}
                .stat-label {{ font-size: 12px; color: #666; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Acceso a Bedrock Bloqueado</h1>
                    <p>Límite diario excedido</p>
                </div>
                <div class="content">
                    <p>Hola <strong>{user_id}</strong>,</p>
                    
                    <div class="alert-box">
                        <strong>Tu acceso a AWS Bedrock ha sido bloqueado temporalmente.</strong><br>
                        Has excedido tu límite diario de uso y no puedes realizar solicitudes adicionales hasta que expire dicho bloqueo.
                    </div>
                    
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-value">{current_usage}</div>
                            <div class="stat-label">Solicitudes Usadas</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{daily_limit}</div>
                            <div class="stat-label">Límite Diario</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">0</div>
                            <div class="stat-label">Restantes</div>
                        </div>
                    </div>
                    
                    <p><strong>Detalles del Bloqueo:</strong></p>
                    <ul>
                        <li>Razón: Límite diario excedido ({current_usage}/{daily_limit} solicitudes)</li>
                        <li>Equipo: {team}</li>
                        <li>El bloqueo expira: {expiration_text}</li>
                        <li>Duración del bloqueo: 24 horas</li>
                    </ul>
                    
                    <p><strong>¿Qué sucede después?</strong></p>
                    <p>Tu acceso será restaurado automáticamente cuando expire el bloqueo. No necesitas realizar ninguna acción adicional.</p>
                    
                    <p><strong>¿Necesitas acceso inmediato?</strong></p>
                    <p>Si tienes una necesidad urgente de negocio, por favor contacta a tu administrador de AWS quien podrá restaurar tu acceso manualmente.</p>
                </div>
                <div class="footer">
                    <p>Esta es una notificación automática del Sistema de Control de Uso de AWS Bedrock.</p>
                    <p>Enviado desde: {self.gmail_user}</p>
                    <p>Fecha y hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_blocked_email_text(self, user_id: str, usage_record: Dict[str, Any], expires_at: str = None) -> str:
        """Generate plain text content for blocked email"""
        current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
        daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
        team = usage_record.get('team', 'unknown')
        
        # Format expiration time
        expiration_text = "24 hours from now"
        if expires_at and expires_at != 'Indefinite':
            try:
                exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                expiration_text = exp_time.strftime('%Y-%m-%d at %H:%M:%S UTC')
            except:
                expiration_text = "24 hours from now"
        
        return f"""
BEDROCK ACCESS BLOCKED

Hello {user_id},

Your AWS Bedrock access has been temporarily blocked.
You have exceeded your daily usage limit and cannot make additional requests until the block expires.

BLOCK DETAILS:
- Reason: Daily limit exceeded ({current_usage}/{daily_limit} requests)
- Team: {team}
- Block expires: {expiration_text}
- Block duration: 24 hours

WHAT HAPPENS NEXT:
Your access will be automatically restored when the block expires. You don't need to take any action - just wait for the 24-hour period to pass.

NEED IMMEDIATE ACCESS:
If you have an urgent business need, please contact your system administrator who can manually restore your access.

---
This is an automated notification from the AWS Bedrock Usage Control System.
Sent from: {self.gmail_user}
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """
    
    def _generate_unblocked_email_html(self, user_id: str, reason: str) -> str:
        """Generate HTML content for unblocked email in Spanish"""
        reason_text = {
            'automatic_expiration': 'Tu período de bloqueo de 24 horas ha expirado',
            'manual_unblock': 'Un administrador ha restaurado tu acceso manualmente',
            'daily_reset': 'El reinicio diario ha restaurado tu acceso'
        }.get(reason, 'Tu acceso ha sido restaurado')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Acceso a Bedrock Restaurado</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #9CD286; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .success-box {{ background-color: #E8F5E8; border-left: 4px solid #9CD286; padding: 15px; margin: 20px 0; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Acceso a Bedrock Restaurado</h1>
                    <p>Ya puedes usar Bedrock nuevamente</p>
                </div>
                <div class="content">
                    <p>Hola <strong>{user_id}</strong>,</p>
                    
                    <div class="success-box">
                        <strong>¡Buenas noticias!</strong> Tu acceso a AWS Bedrock ha sido restaurado.<br>
                        {reason_text}.
                    </div>
                    
                    <p><strong>Esto significa que:</strong></p>
                    <ul>
                        <li>Ya puedes realizar llamadas a la API de AWS Bedrock nuevamente</li>
                        <li>Tu contador de uso diario ha sido reiniciado</li>
                        <li>Se aplican los límites de uso normales</li>
                    </ul>
                    
                    <p><strong>De aquí en adelante:</strong></p>
                    <p>Por favor, regula el uso de este servicio para evitar futuros bloqueos. Recibirás un aviso cuando te acerques a tu límite diario.</p>
                    
                    <p>¡Gracias por tu colaboración!</p>
                </div>
                <div class="footer">
                    <p>Esta es una notificación automática del Sistema de Control de Uso de AWS Bedrock.</p>
                    <p>Enviado desde: {self.gmail_user}</p>
                    <p>Fecha y hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_unblocked_email_text(self, user_id: str, reason: str) -> str:
        """Generate plain text content for unblocked email"""
        reason_text = {
            'automatic_expiration': 'Your 24-hour block period has expired',
            'manual_unblock': 'An administrator has manually restored your access',
            'daily_reset': 'Daily reset has restored your access'
        }.get(reason, 'Your access has been restored')
        
        return f"""
BEDROCK ACCESS RESTORED

Hello {user_id},

Good news! Your AWS Bedrock access has been restored.
{reason_text}.

WHAT THIS MEANS:
- You can now make AWS Bedrock API calls again
- Your daily usage counter has been reset
- Normal usage limits apply

MOVING FORWARD:
Please monitor your usage to avoid future blocks. You'll receive a warning when you approach your daily limit.

Thank you for your patience!

---
This is an automated notification from the AWS Bedrock Usage Control System.
Sent from: {self.gmail_user}
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """

# Initialize email service if enabled
email_service = None
if EMAIL_NOTIFICATIONS_ENABLED and EMAIL_SERVICE_TYPE == 'gmail_smtp' and GMAIL_USER and GMAIL_PASSWORD:
    email_service = GmailEmailNotificationService(GMAIL_USER, GMAIL_PASSWORD)
    logger.info("Gmail email service initialized")
elif EMAIL_NOTIFICATIONS_ENABLED:
    logger.warning("Email notifications enabled but Gmail credentials not provided")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for processing Bedrock API events
    
    Args:
        event: CloudWatch Events event containing CloudTrail data
        context: Lambda context object
        
    Returns:
        Dict with status code and processing results
    """
    try:
        logger.info(f"Processing event: {json.dumps(event, default=str)}")
        
        # Parse CloudTrail event
        if 'detail' not in event:
            logger.error("Invalid event format - missing 'detail' field")
            return {'statusCode': 400, 'body': 'Invalid event format'}
        
        detail = event['detail']
        
        # Extract user information
        user_info = extract_user_info(detail)
        if not user_info:
            logger.warning("Could not extract user information from event")
            return {'statusCode': 200, 'body': 'No user info found'}
        
        logger.info(f"Processing request for user: {user_info['user_id']}")
        
        # Update usage counter with auto-provisioning
        usage_record = update_daily_usage(user_info)
        
        # Publish metrics to CloudWatch for real-time dashboard updates
        publish_cloudwatch_metrics(user_info['user_id'], usage_record)
        
        # Evaluate limits and take action
        action_taken = evaluate_limits_and_act(user_info['user_id'], usage_record)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'user_id': user_info['user_id'],
                'current_usage': int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count'],
                'daily_limit': int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit'],
                'status': usage_record['status'],
                'action_taken': action_taken
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}, cls=DecimalEncoder)
        }

def extract_user_info(detail: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Extract user information from CloudTrail event detail
    
    Args:
        detail: CloudTrail event detail section
        
    Returns:
        Dict with user_id and other relevant info, or None if extraction fails
    """
    try:
        user_identity = detail.get('userIdentity', {})
        
        # Handle different user identity types
        if user_identity.get('type') == 'IAMUser':
            user_id = user_identity.get('userName')
            user_arn = user_identity.get('arn')
        elif user_identity.get('type') == 'AssumedRole':
            # Extract user from assumed role ARN
            arn = user_identity.get('arn', '')
            if '/user/' in arn:
                user_id = arn.split('/user/')[-1].split('/')[0]
            else:
                user_id = user_identity.get('userName')
            user_arn = arn
        else:
            logger.warning(f"Unsupported user identity type: {user_identity.get('type')}")
            return None
        
        if not user_id:
            logger.warning("Could not determine user_id from event")
            return None
        
        return {
            'user_id': user_id,
            'user_arn': user_arn,
            'event_time': detail.get('eventTime'),
            'source_ip': detail.get('sourceIPAddress'),
            'user_agent': detail.get('userAgent', '')
        }
        
    except Exception as e:
        logger.error(f"Error extracting user info: {str(e)}")
        return None

def update_daily_usage(user_info: Dict[str, str]) -> Dict[str, Any]:
    """
    Update daily usage counter in DynamoDB with auto-provisioning
    
    Args:
        user_info: Dictionary containing user information
        
    Returns:
        Updated usage record from DynamoDB
    """
    table = dynamodb.Table(TABLE_NAME)
    user_id = user_info['user_id']
    today = date.today().isoformat()
    
    try:
        # Get user configuration with auto-discovery
        user_config = get_user_config_with_autodiscovery(user_id)
        
        # Calculate TTL (7 days from now)
        ttl_timestamp = int((datetime.utcnow().timestamp() + 86400 * 7))
        
        # Update item with auto-provisioning
        # ALWAYS update team field to ensure consistency with current IAM tags
        response = table.update_item(
            Key={'user_id': user_id, 'date': today},
            UpdateExpression='''
                ADD request_count :inc 
                SET #status = if_not_exists(#status, :active),
                    daily_limit = if_not_exists(daily_limit, :limit),
                    warning_threshold = if_not_exists(warning_threshold, :warning),
                    last_request_time = :now,
                    team = :team,
                    #ttl = if_not_exists(#ttl, :ttl),
                    first_seen = if_not_exists(first_seen, :first_seen)
            ''',
            ExpressionAttributeNames={
                '#status': 'status',
                '#ttl': 'ttl'
            },
            ExpressionAttributeValues={
                ':inc': 1,
                ':active': 'ACTIVE',
                ':limit': user_config['daily_limit'],
                ':warning': user_config['warning_threshold'],
                ':now': datetime.utcnow().isoformat(),
                ':team': user_config['team'],
                ':ttl': ttl_timestamp,
                ':first_seen': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        usage_record = response['Attributes']
        
        # Check if this is a new user (first time seen today)
        if usage_record.get('request_count', 0) == 1:
            log_new_user_discovery(user_id, user_config, user_info)
        
        logger.info(f"Updated usage for {user_id}: {usage_record['request_count']}/{usage_record['daily_limit']}")
        return usage_record
        
    except Exception as e:
        logger.error(f"Error updating daily usage for {user_id}: {str(e)}")
        raise

def get_user_config_with_autodiscovery(user_id: str) -> Dict[str, Any]:
    """
    Get user configuration with automatic discovery from IAM tags and quota_config.json
    Priority: quota_config.json explicit config > IAM tag-based team config > defaults
    
    Args:
        user_id: The user ID to get configuration for
        
    Returns:
        Dictionary with user configuration (daily_limit, warning_threshold, team)
    """
    try:
        # Try to load quota_config.json from the parent directory
        quota_config = load_quota_config()
        
        # ALWAYS get IAM tags first for consistent team assignment
        iam_team_name = 'unknown'
        try:
            user_tags_response = iam.list_user_tags(UserName=user_id)
            user_tags = {tag['Key']: tag['Value'] for tag in user_tags_response['Tags']}
            iam_team_name = user_tags.get('Team', 'unknown')
            logger.info(f"Retrieved IAM team for {user_id}: {iam_team_name}")
        except Exception as e:
            logger.warning(f"Could not retrieve IAM tags for user {user_id}: {str(e)}")
        
        # Check if user exists in current quota_config.json
        if user_id in quota_config.get('users', {}):
            user_config = quota_config['users'][user_id]
            
            # Use explicit config but OVERRIDE team with IAM tag for consistency
            # This ensures team assignment is always based on current IAM tags
            config_team = user_config.get('team', 'unknown')
            final_team = iam_team_name if iam_team_name != 'unknown' else config_team
            
            logger.info(f"User {user_id} found in quota_config with team '{config_team}', using IAM team '{final_team}' for consistency")
            
            # Use default values (250 daily, 150 warning) even if user exists in quota_config
            return {
                'daily_limit': 250,  # Always use default 250
                'warning_threshold': 150,  # Always use default 150 (60% of 250)
                'team': final_team
            }
        
        # Auto-discover user information from IAM if not in quota_config
        try:
            # Check if team exists in quota_config.json teams section
            team_config = quota_config.get('teams', {}).get(iam_team_name, {})
            
            # Always use default limits (250 daily, 150 warning) regardless of team config
            config = DEFAULT_CONFIG
            user_daily_limit = config['daily_limits']['default_user_limit']  # 250
            user_warning_threshold = config['daily_limits']['default_warning_threshold']  # 150
            
            if team_config:
                logger.info(f"Auto-configured user {user_id} with defaults (ignoring team '{iam_team_name}' monthly limit): daily_limit={user_daily_limit}, warning={user_warning_threshold}")
            else:
                logger.info(f"Auto-configured user {user_id} with defaults (team '{iam_team_name}' not found in config): daily_limit={user_daily_limit}, warning={user_warning_threshold}")
            
            return {
                'daily_limit': user_daily_limit,
                'warning_threshold': user_warning_threshold,
                'team': iam_team_name
            }
            
        except Exception as e:
            logger.warning(f"Could not auto-discover config for user {user_id}: {str(e)}")
            # Fallback to defaults
            config = DEFAULT_CONFIG
            return {
                'daily_limit': config['daily_limits']['default_user_limit'],
                'warning_threshold': config['daily_limits']['default_warning_threshold'],
                'team': iam_team_name  # Use IAM team even in fallback
            }
            
    except Exception as e:
        logger.error(f"Error getting user config for {user_id}: {str(e)}")
        # Final fallback
        return {
            'daily_limit': 50,
            'warning_threshold': 40,
            'team': 'unknown'
        }

def load_quota_config() -> Dict[str, Any]:
    """
    Load quota configuration from quota_config.json
    
    Returns:
        Dictionary with quota configuration
    """
    try:
        # Load quota_config.json from the root of the Lambda package
        import os
        
        # Try multiple possible locations for the config file
        possible_paths = [
            'quota_config.json',  # Root of Lambda package
            '../../quota_config.json',  # Relative path from lambda_functions directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quota_config.json'),  # Same directory as Lambda function
        ]
        
        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        if not config_path:
            logger.warning("quota_config.json not found in any expected location, using empty config")
            return {'users': {}, 'teams': {}}
        
        logger.info(f"Loading quota config from {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        logger.info(f"Successfully loaded quota config with {len(config.get('users', {}))} users and {len(config.get('teams', {}))} teams")
        return config
        
    except FileNotFoundError:
        logger.warning("quota_config.json not found, using empty config")
        return {'users': {}, 'teams': {}}
    except Exception as e:
        logger.error(f"Error loading quota_config.json: {str(e)}")
        return {'users': {}, 'teams': {}}

def log_new_user_discovery(user_id: str, user_config: Dict[str, Any], user_info: Dict[str, str]) -> None:
    """
    Log discovery of new user and send notification
    
    Args:
        user_id: The user ID that was discovered
        user_config: The configuration assigned to the user
        user_info: Additional user information from the event
    """
    logger.info(f"Auto-discovered new user: {user_id} with config: {user_config}")
    
    # Send notification about new user discovery
    try:
        config = DEFAULT_CONFIG
        if config['auto_provisioning']['notification_on_new_user']:
            message = {
                'event_type': 'new_user_discovered',
                'user_id': user_id,
                'team': user_config['team'],
                'daily_limit': user_config['daily_limit'],
                'warning_threshold': user_config['warning_threshold'],
                'discovered_at': datetime.utcnow().isoformat(),
                'user_arn': user_info.get('user_arn', ''),
                'source_ip': user_info.get('source_ip', ''),
                'user_agent': user_info.get('user_agent', '')
            }
            
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"New Bedrock User Discovered: {user_id}",
                Message=json.dumps(message, indent=2)
            )
            
            logger.info(f"Sent new user notification for {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to send new user notification: {str(e)}")

def evaluate_limits_and_act(user_id: str, usage_record: Dict[str, Any]) -> str:
    """
    Evaluate usage limits and take appropriate action (warn or block)
    
    Args:
        user_id: The user ID to evaluate
        usage_record: Current usage record from DynamoDB
        
    Returns:
        String describing the action taken
    """
    try:
        current_count = usage_record['request_count']
        daily_limit = usage_record['daily_limit']
        warning_threshold = usage_record['warning_threshold']
        current_status = usage_record['status']
        
        config = DEFAULT_CONFIG
        
        # Check if blocking is enabled
        if not config['blocking_system']['enabled']:
            logger.info(f"Blocking system disabled - no action taken for {user_id}")
            return "blocking_disabled"
        
        # Check for emergency override users
        if user_id in config['blocking_system']['emergency_override_users']:
            logger.info(f"Emergency override user {user_id} - no limits applied")
            return "emergency_override"
        
        # NEW: Check if user is blocked but block has expired
        if current_status == 'BLOCKED':
            if check_and_handle_expired_block(user_id, usage_record):
                logger.info(f"User {user_id} block has expired - automatically unblocked")
                # Update the status in our local record for further processing
                usage_record['status'] = 'ACTIVE'
                current_status = 'ACTIVE'
        
        # Check if daily limit exceeded
        if current_count >= daily_limit:
            if current_status != 'BLOCKED':
                # NEW: Check if user has administrative protection (manually unblocked today)
                if has_administrative_protection(user_id, usage_record):
                    logger.info(f"User {user_id} has administrative protection - automatic blocking disabled until tomorrow")
                    send_notification(user_id, 'ADMIN_PROTECTED', usage_record)
                    return "admin_protected"
                
                if config['blocking_system']['dry_run_mode']:
                    logger.info(f"DRY RUN: Would block user {user_id} (usage: {current_count}/{daily_limit})")
                    send_notification(user_id, 'DRY_RUN_BLOCK', usage_record)
                    return "dry_run_block"
                else:
                    logger.warning(f"Blocking user {user_id} - daily limit exceeded ({current_count}/{daily_limit})")
                    block_user(user_id, usage_record)
                    return "blocked"
            else:
                logger.info(f"User {user_id} already blocked")
                return "already_blocked"
        
        # Check warning threshold
        elif current_count >= warning_threshold:
            if current_status != 'WARNING' and current_status != 'BLOCKED':
                logger.info(f"Warning threshold reached for {user_id} ({current_count}/{daily_limit})")
                warn_user(user_id, usage_record)
                return "warning_sent"
        
        # Normal operation
        return "normal"
        
    except Exception as e:
        logger.error(f"Error evaluating limits for {user_id}: {str(e)}")
        return "error"

def block_user(user_id: str, usage_record: Dict[str, Any]) -> None:
    """
    Block user by updating status and invoking policy manager
    
    Args:
        user_id: The user ID to block
        usage_record: Current usage record
    """
    try:
        # Update status in DynamoDB
        update_user_status(user_id, 'BLOCKED')
        
        # Invoke policy manager to modify IAM policy
        lambda_client.invoke(
            FunctionName=POLICY_MANAGER_FUNCTION,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps({
                'action': 'block',
                'user_id': user_id,
                'reason': 'daily_limit_exceeded',
                'usage_record': usage_record
            }, cls=DecimalEncoder)
        )
        
        # Send notification
        send_notification(user_id, 'BLOCKED', usage_record)
        
        logger.info(f"Successfully initiated blocking for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error blocking user {user_id}: {str(e)}")
        raise

def warn_user(user_id: str, usage_record: Dict[str, Any]) -> None:
    """
    Warn user by updating status and sending notification
    
    Args:
        user_id: The user ID to warn
        usage_record: Current usage record
    """
    try:
        # Update status in DynamoDB
        update_user_status(user_id, 'WARNING')
        
        # Send notification
        send_notification(user_id, 'WARNING', usage_record)
        
        logger.info(f"Successfully sent warning to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error warning user {user_id}: {str(e)}")

def update_user_status(user_id: str, status: str) -> None:
    """
    Update user status in DynamoDB
    
    Args:
        user_id: The user ID to update
        status: New status (ACTIVE, WARNING, BLOCKED)
    """
    try:
        table = dynamodb.Table(TABLE_NAME)
        today = date.today().isoformat()
        
        update_expression = 'SET #status = :status, last_status_change = :now'
        expression_values = {
            ':status': status,
            ':now': datetime.utcnow().isoformat()
        }
        
        # Add blocked_at timestamp if blocking
        if status == 'BLOCKED':
            update_expression += ', blocked_at = :blocked_at'
            expression_values[':blocked_at'] = datetime.utcnow().isoformat()
        
        table.update_item(
            Key={'user_id': user_id, 'date': today},
            UpdateExpression=update_expression,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expression_values
        )
        
        logger.info(f"Updated status for {user_id} to {status}")
        
    except Exception as e:
        logger.error(f"Error updating status for {user_id}: {str(e)}")
        raise

def has_administrative_protection(user_id: str, usage_record: Dict[str, Any]) -> bool:
    """
    Check if user has administrative protection (manually unblocked by admin today)
    
    Args:
        user_id: The user ID to check
        usage_record: Current usage record from DynamoDB
        
    Returns:
        True if user has administrative protection, False otherwise
    """
    try:
        # Check if user has been manually unblocked today by checking the blocking history
        history_table = dynamodb.Table('bedrock_blocking_history')
        today = date.today().isoformat()
        
        # Query blocking history for today's operations on this user
        response = history_table.query(
            IndexName='user-date-index',  # Assuming we have a GSI on user_id and date
            KeyConditionExpression='user_id = :user_id AND begins_with(#date, :today)',
            ExpressionAttributeNames={
                '#date': 'date'
            },
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':today': today
            },
            ScanIndexForward=False  # Most recent first
        )
        
        operations = response.get('Items', [])
        
        # Look for manual unblock operations today
        for operation in operations:
            if (operation.get('operation') == 'unblock' and 
                operation.get('performed_by') != 'system' and
                operation.get('performed_by') != 'daily_reset'):
                
                logger.info(f"Found administrative unblock for {user_id} by {operation.get('performed_by')} at {operation.get('timestamp')}")
                return True
        
        # Also check if there's an admin_protection flag in the usage record
        if usage_record.get('admin_protection') == True:
            logger.info(f"User {user_id} has admin_protection flag set")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking administrative protection for {user_id}: {str(e)}")
        # In case of error, err on the side of caution and allow blocking
        return False

def check_and_handle_expired_block(user_id: str, usage_record: Dict[str, Any]) -> bool:
    """
    Check if user's block has expired and automatically unblock if so
    
    Args:
        user_id: The user ID to check
        usage_record: Current usage record from DynamoDB
        
    Returns:
        True if user was unblocked due to expiration, False otherwise
    """
    try:
        expires_at = usage_record.get('expires_at')
        
        # If no expiration date or set to 'Indefinite', don't auto-unblock
        if not expires_at or expires_at == 'Indefinite':
            logger.debug(f"User {user_id} has no expiration date or indefinite block")
            return False
        
        # Parse expiration date
        from datetime import datetime
        try:
            # Handle different datetime formats
            if expires_at.endswith('Z'):
                expiration_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            else:
                expiration_time = datetime.fromisoformat(expires_at)
        except ValueError as e:
            logger.error(f"Invalid expiration date format for user {user_id}: {expires_at} - {str(e)}")
            return False
        
        # Check if block has expired
        current_time = datetime.utcnow().replace(tzinfo=expiration_time.tzinfo) if expiration_time.tzinfo else datetime.utcnow()
        
        if current_time >= expiration_time:
            logger.info(f"Block for user {user_id} has expired (expired at: {expires_at}, current: {current_time.isoformat()})")
            
            # Automatically unblock the user
            try:
                response = lambda_client.invoke(
                    FunctionName=POLICY_MANAGER_FUNCTION,
                    InvocationType='RequestResponse',  # Synchronous call for immediate result
                    Payload=json.dumps({
                        'action': 'unblock',
                        'user_id': user_id,
                        'reason': 'automatic_expiration',
                        'performed_by': 'system'
                    })
                )
                
                # Parse response
                response_payload = json.loads(response['Payload'].read())
                
                if response_payload.get('statusCode') == 200:
                    logger.info(f"Successfully auto-unblocked expired user {user_id}")
                    
                    # Send notification about automatic unblock
                    send_notification(user_id, 'AUTO_UNBLOCKED', usage_record)
                    
                    return True
                else:
                    logger.error(f"Failed to auto-unblock expired user {user_id}: {response_payload.get('body', 'Unknown error')}")
                    return False
                    
            except Exception as unblock_error:
                logger.error(f"Error auto-unblocking expired user {user_id}: {str(unblock_error)}")
                return False
        else:
            logger.debug(f"Block for user {user_id} has not yet expired (expires at: {expires_at}, current: {current_time.isoformat()})")
            return False
            
    except Exception as e:
        logger.error(f"Error checking block expiration for user {user_id}: {str(e)}")
        return False

def publish_cloudwatch_metrics(user_id: str, usage_record: Dict[str, Any]) -> None:
    """
    Publish real-time metrics to CloudWatch for dashboard consumption
    
    Args:
        user_id: The user ID
        usage_record: Current usage record from DynamoDB
    """
    try:
        current_count = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
        team = usage_record.get('team', 'unknown')
        
        # Get current timestamp
        timestamp = datetime.utcnow()
        
        # Prepare metric data for individual user
        metric_data = [
            {
                'MetricName': 'BedrockUsage',
                'Dimensions': [
                    {
                        'Name': 'User',
                        'Value': user_id
                    }
                ],
                'Value': 1,  # Each call represents 1 request
                'Unit': 'Count',
                'Timestamp': timestamp
            }
        ]
        
        # Add team-level metric if team is known
        if team != 'unknown':
            metric_data.append({
                'MetricName': 'BedrockUsage',
                'Dimensions': [
                    {
                        'Name': 'Team',
                        'Value': team
                    }
                ],
                'Value': 1,  # Each call represents 1 request
                'Unit': 'Count',
                'Timestamp': timestamp
            })
            
            # Add combined user+team metric for detailed analysis
            metric_data.append({
                'MetricName': 'BedrockUsage',
                'Dimensions': [
                    {
                        'Name': 'User',
                        'Value': user_id
                    },
                    {
                        'Name': 'Team',
                        'Value': team
                    }
                ],
                'Value': 1,  # Each call represents 1 request
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Publish metrics to CloudWatch
        cloudwatch.put_metric_data(
            Namespace='UserMetrics',
            MetricData=metric_data
        )
        
        logger.info(f"Published CloudWatch metrics for {user_id} (team: {team}, current usage: {current_count})")
        
    except Exception as e:
        logger.error(f"Error publishing CloudWatch metrics for {user_id}: {str(e)}")
        # Don't raise the exception - metrics publishing failure shouldn't break the main flow

def send_notification(user_id: str, notification_type: str, usage_record: Dict[str, Any]) -> None:
    """
    Send notification via SNS and Email
    
    Args:
        user_id: The user ID
        notification_type: Type of notification (WARNING, BLOCKED, ADMIN_PROTECTED, etc.)
        usage_record: Current usage record
    """
    try:
        config = DEFAULT_CONFIG
        notification_channels = config['blocking_system']['notification_channels']
        
        # Send SNS notification if enabled
        if 'sns' in notification_channels:
            try:
                # Prepare notification message
                message = {
                    'event_type': notification_type.lower(),
                    'user_id': user_id,
                    'team': usage_record.get('team', 'unknown'),
                    'current_usage': usage_record['request_count'],
                    'daily_limit': usage_record['daily_limit'],
                    'warning_threshold': usage_record['warning_threshold'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'date': usage_record.get('date', date.today().isoformat())
                }
                
                # Customize subject based on notification type
                subjects = {
                    'WARNING': f"Bedrock Usage Warning: {user_id}",
                    'BLOCKED': f"Bedrock User Blocked: {user_id}",
                    'DRY_RUN_BLOCK': f"Bedrock Dry Run Block: {user_id}",
                    'ADMIN_PROTECTED': f"Bedrock User Protected by Admin: {user_id}",
                    'AUTO_UNBLOCKED': f"Bedrock User Auto-Unblocked: {user_id}"
                }
                
                subject = subjects.get(notification_type, f"Bedrock Notification: {user_id}")
                
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject=subject,
                    Message=json.dumps(message, indent=2)
                )
                
                logger.info(f"Sent {notification_type} SNS notification for {user_id}")
                
            except Exception as e:
                logger.error(f"Error sending SNS notification for {user_id}: {str(e)}")
        
        # Send email notification if enabled and email service is available
        if 'email' in notification_channels and email_service:
            try:
                email_sent = False
                
                if notification_type == 'WARNING':
                    email_sent = email_service.send_warning_email(user_id, usage_record)
                elif notification_type == 'BLOCKED':
                    expires_at = usage_record.get('expires_at')
                    email_sent = email_service.send_blocked_email(user_id, usage_record, expires_at)
                elif notification_type == 'AUTO_UNBLOCKED':
                    email_sent = email_service.send_unblocked_email(user_id, 'automatic_expiration')
                else:
                    logger.info(f"No email template for notification type: {notification_type}")
                
                if email_sent:
                    logger.info(f"Sent {notification_type} email notification for {user_id}")
                else:
                    logger.warning(f"Failed to send {notification_type} email notification for {user_id}")
                    
            except Exception as e:
                logger.error(f"Error sending email notification for {user_id}: {str(e)}")
        elif 'email' in notification_channels and not email_service:
            logger.warning(f"Email notifications requested but email service not available for {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending notifications for {user_id}: {str(e)}")

# For testing purposes
if __name__ == "__main__":
    # Test event structure
    test_event = {
        "detail": {
            "eventTime": "2025-01-15T14:30:00Z",
            "eventSource": "bedrock.amazonaws.com",
            "eventName": "InvokeModel",
            "userIdentity": {
                "type": "IAMUser",
                "userName": "test_user_001",
                "arn": "arn:aws:iam::701055077130:user/test_user_001"
            },
            "sourceIPAddress": "192.168.1.100",
            "userAgent": "aws-cli/2.0.0"
        }
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "bedrock-usage-monitor"
            self.memory_limit_in_mb = 256
            self.invoked_function_arn = "arn:aws:lambda:eu-west-1:701055077130:function:bedrock-usage-monitor"
    
    # Test the handler
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
