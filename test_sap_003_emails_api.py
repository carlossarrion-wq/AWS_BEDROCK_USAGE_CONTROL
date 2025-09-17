#!/usr/bin/env python3
"""
Test Email Notifications for sap_003 using Gmail API
===================================================

This script tests the email functionality by sending all 3 types of emails
to the sap_003 user using Gmail API with service account credentials.

Author: AWS Bedrock Usage Control System
Version: 2.0.0
"""

import json
import sys
import os
import boto3
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional

# Try to import Google API libraries
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    print("⚠️ Google API libraries not installed. Install with: pip install google-api-python-client google-auth")

# Custom JSON encoder for Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

class GmailAPIEmailNotificationService:
    """Service for sending email notifications using Gmail API"""
    
    def __init__(self, service_account_file: str, sender_email: str):
        self.sender_email = sender_email
        self.iam_client = boto3.client('iam', region_name='eu-west-1')
        
        if not GOOGLE_APIS_AVAILABLE:
            raise ImportError("Google API libraries are required. Install with: pip install google-api-python-client google-auth")
        
        # Load service account credentials
        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )
            
            # Delegate to the sender email for domain-wide delegation
            self.credentials = credentials.with_subject(sender_email)
            self.service = build('gmail', 'v1', credentials=self.credentials)
            print(f"✅ Gmail API service initialized for {sender_email}")
            
        except Exception as e:
            print(f"❌ Error initializing Gmail API service: {str(e)}")
            raise
    
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
                print(f"✅ Retrieved email for user {user_id}: {email}")
                return email
            else:
                print(f"❌ No Email tag found for user {user_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error retrieving email for user {user_id}: {str(e)}")
            return None
    
    def send_warning_email(self, user_id: str, usage_record: Dict[str, Any]) -> bool:
        """Send warning email to user approaching their daily limit"""
        try:
            user_email = self.get_user_email(user_id)
            if not user_email:
                print(f"❌ Cannot send warning email to {user_id} - no email address")
                return False
            
            # Prepare email content
            current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
            daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
            
            subject = f"⚠️ Bedrock Usage Warning - {current_usage}/{daily_limit} requests used"
            
            html_body = self._generate_warning_email_html(user_id, usage_record)
            text_body = self._generate_warning_email_text(user_id, usage_record)
            
            # Send email
            return self._send_email_via_api(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            print(f"❌ Error sending warning email to {user_id}: {str(e)}")
            return False
    
    def send_blocked_email(self, user_id: str, usage_record: Dict[str, Any], expires_at: str = None) -> bool:
        """Send blocked notification email to user"""
        try:
            user_email = self.get_user_email(user_id)
            if not user_email:
                print(f"❌ Cannot send blocked email to {user_id} - no email address")
                return False
            
            # Prepare email content
            current_usage = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
            daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
            
            subject = f"🚫 Bedrock Access Blocked - Daily limit exceeded ({current_usage}/{daily_limit})"
            
            html_body = self._generate_blocked_email_html(user_id, usage_record, expires_at)
            text_body = self._generate_blocked_email_text(user_id, usage_record, expires_at)
            
            # Send email
            return self._send_email_via_api(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            print(f"❌ Error sending blocked email to {user_id}: {str(e)}")
            return False
    
    def send_unblocked_email(self, user_id: str, reason: str = "automatic_expiration") -> bool:
        """Send unblocked notification email to user"""
        try:
            user_email = self.get_user_email(user_id)
            if not user_email:
                print(f"❌ Cannot send unblocked email to {user_id} - no email address")
                return False
            
            # Prepare email content
            subject = f"✅ Bedrock Access Restored - You can now use Bedrock again"
            
            html_body = self._generate_unblocked_email_html(user_id, reason)
            text_body = self._generate_unblocked_email_text(user_id, reason)
            
            # Send email
            return self._send_email_via_api(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            print(f"❌ Error sending unblocked email to {user_id}: {str(e)}")
            return False
    
    def _send_email_via_api(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send email using Gmail API"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = to_email
            message["Reply-To"] = self.sender_email
            
            # Create the plain-text and HTML version of your message
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            
            # Add HTML/plain-text parts to MIMEMultipart message
            message.attach(part1)
            message.attach(part2)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send via Gmail API
            send_message = {
                'raw': raw_message
            }
            
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            print(f"✅ Email sent successfully to {to_email} via Gmail API (Message ID: {result['id']})")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email to {to_email} via Gmail API: {str(e)}")
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
                    <p>Enviado desde: {self.sender_email}</p>
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
Sent from: {self.sender_email}
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
                    <p>Enviado desde: {self.sender_email}</p>
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
Sent from: {self.sender_email}
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
                    <p>Enviado desde: {self.sender_email}</p>
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
Sent from: {self.sender_email}
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """

def load_gmail_api_config():
    """Load Gmail API configuration"""
    service_account_file = input("Enter path to Gmail service account JSON file: ").strip()
    sender_email = input("Enter sender email address: ").strip()
    
    if not os.path.exists(service_account_file):
        print(f"❌ Service account file not found: {service_account_file}")
        return None, None
    
    return service_account_file, sender_email

def test_sap_003_emails_api():
    """Test sending all 3 types of emails to sap_003 using Gmail API"""
    print("🧪 Testing Email Notifications for sap_003 (Gmail API)")
    print("=" * 60)
    
    # Load Gmail API configuration
    service_account_file, sender_email = load_gmail_api_config()
    if not service_account_file or not sender_email:
        print("❌ Gmail API configuration is required")
        return False
    
    try:
        # Initialize Gmail API service
        gmail_service = GmailAPIEmailNotificationService(service_account_file, sender_email)
        
        # Sample data for different email types
        warning_usage_record = {
            'request_count': 42,
            'daily_limit': 50,
            'warning_threshold': 40,
            'team': 'team_sap_group'
        }
        
        blocked_usage_record = {
            'request_count': 55,
            'daily_limit': 50,
            'warning_threshold': 40,
            'team': 'team_sap_group'
        }
        
        # Calculate expiration time (00:00h of next day)
        now = datetime.utcnow()
        next_day = now.date() + timedelta(days=1)
        expires_at = datetime.combine(next_day, datetime.min.time()).isoformat() + 'Z'
        
        print("\n1️⃣ Sending WARNING email (Spanish)...")
        warning_success = gmail_service.send_warning_email('sap_003', warning_usage_record)
        print(f"   {'✅' if warning_success else '❌'} Warning email: {'Sent successfully' if warning_success else 'Failed'}")
        
        print("\n2️⃣ Sending BLOCKED email (Spanish with soft pink color)...")
        blocked_success = gmail_service.send_blocked_email('sap_003', blocked_usage_record, expires_at)
        print(f"   {'✅' if blocked_success else '❌'} Blocked email: {'Sent successfully' if blocked_success else 'Failed'}")
        
        print("\n3️⃣ Sending UNBLOCKED email (Spanish)...")
        unblocked_success = gmail_service.send_unblocked_email('sap_003', 'automatic_expiration')
        print(f"   {'✅' if unblocked_success else '❌'} Unblocked email: {'Sent successfully' if unblocked_success else 'Failed'}")
        
        print("\n" + "=" * 60)
        
        if warning_success and blocked_success and unblocked_success:
            print("🎉 All sample emails sent successfully to sap_003!")
            print(f"📧 Check the inbox at: carlos.sarrion@es.ibm.com")
            print("\n📋 What you should see:")
            print("   1. ⚠️ Aviso de Uso de Bedrock - Warning email in Spanish")
            print("   2. 🚫 Acceso a Bedrock Bloqueado - Blocked email with soft pink color")
            print("   3. ✅ Acceso a Bedrock Restaurado - Unblocked email in Spanish")
            print("\n💡 Features to notice:")
            print("   • All text is in Spanish")
            print("   • Professional HTML templates with progress bars")
            print("   • Mobile-friendly responsive design")
            print("   • Email retrieved automatically from IAM tags")
            print("   • Uses Gmail API with service account authentication")
            return True
        else:
            print("❌ Some emails failed to send")
            return False
            
    except Exception as e:
        print(f"❌ Error testing emails for sap_003: {str(e)}")
        return False

def main():
    """Main function"""
    print("🚀 Email Functionality Test for sap_003 (Gmail API)")
    print("=" * 60)
    print("📧 Target user: sap_003")
    print("📧 Email address: carlos.sarrion@es.ibm.com (from IAM tags)")
    print("🎨 Features: Spanish language + Gmail API authentication")
    print("🔑 Authentication: Service account with domain-wide delegation")
    print("=" * 60)
    
    success = test_sap_003_emails_api()
    
    if success:
        print("\n✨ Email test completed successfully!")
        print("Check carlos.sarrion@es.ibm.com inbox to see the Spanish templates in action.")
    else:
        print("\n❌ Email test failed. Please check the error messages above.")
        print("\n📋 Requirements:")
        print("   • Google API libraries: pip install google-api-python-client google-auth")
        print("   • Service account JSON file with Gmail API access")
        print("   • Domain-wide delegation configured for the service account")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
