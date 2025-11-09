"""
Utilidades para envío de emails.
Soporta SMTP con TLS y SendGrid API.
"""
import os
import smtplib
import sqlite3
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class EmailConfig:
    """Configuración de email desde variables de entorno."""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Retorna configuración de email desde variables de entorno.
        
        Variables de entorno:
        - SMTP_HOST: Host del servidor SMTP (default: smtp.gmail.com)
        - SMTP_PORT: Puerto SMTP (default: 587)
        - SMTP_USER: Usuario/email para autenticación
        - SMTP_PASSWORD: Contraseña del email
        - SMTP_USE_TLS: Usar TLS (default: true)
        - SENDGRID_API_KEY: API key de SendGrid (opcional)
        """
        return {
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            'sendgrid_api_key': os.getenv('SENDGRID_API_KEY', ''),
            'from_email': os.getenv('SMTP_FROM_EMAIL') or os.getenv('SMTP_USER', '')
        }


class EmailService:
    """Servicio para envío de emails."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None):
        """
        Inicializa el servicio de email.
        
        Args:
            config: Configuración de email. Si es None, usa EmailConfig.get_config()
            db_path: Ruta a la base de datos para logging
        """
        self.config = config or EmailConfig.get_config()
        self.db_path = db_path
        
        if self.db_path:
            self._ensure_email_logs_table()
    
    def _ensure_email_logs_table(self):
        """Crea la tabla email_logs si no existe."""
        if not self.db_path:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER,
                    to_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_logs_invoice 
                ON email_logs(invoice_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at 
                ON email_logs(sent_at DESC)
            """)
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Prueba la conexión SMTP.
        
        Returns:
            Tuple de (success: bool, message: str)
        """
        try:
            if not self.config.get('smtp_user') or not self.config.get('smtp_password'):
                return False, "Credenciales SMTP no configuradas"
            
            server = smtplib.SMTP(
                self.config['smtp_host'],
                self.config['smtp_port'],
                timeout=10
            )
            
            if self.config.get('use_tls', True):
                server.starttls()
            
            server.login(
                self.config['smtp_user'],
                self.config['smtp_password']
            )
            server.quit()
            
            return True, "Conexión SMTP exitosa"
            
        except smtplib.SMTPAuthenticationError:
            return False, "Error de autenticación SMTP. Verifica usuario y contraseña."
        except smtplib.SMTPException as e:
            return False, f"Error SMTP: {str(e)}"
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"
    
    def send_invoice_email(
        self,
        invoice_payload: Dict[str, Any],
        to_email: str,
        subject: str,
        body_html: str,
        attachments: List[str] = None,
        invoice_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Envía un email con factura.
        
        Args:
            invoice_payload: Datos de la factura
            to_email: Email del destinatario
            subject: Asunto del email
            body_html: Cuerpo del email en HTML
            attachments: Lista de rutas de archivos a adjuntar
            invoice_id: ID de la factura para logging
        
        Returns:
            Tuple de (success: bool, message: str)
        """
        try:
            # Validar configuración
            if not self.config.get('smtp_user') or not self.config.get('smtp_password'):
                error_msg = "Credenciales SMTP no configuradas"
                self._log_email(invoice_id, to_email, subject, 'failed', error_msg)
                return False, error_msg
            
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config.get('from_email', self.config['smtp_user'])
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Agregar cuerpo HTML
            html_part = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Agregar texto plano como fallback
            text_body = self._html_to_text(body_html, invoice_payload)
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Agregar adjuntos
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            part = MIMEApplication(f.read())
                            filename = os.path.basename(attachment_path)
                            part.add_header(
                                'Content-Disposition',
                                'attachment',
                                filename=filename
                            )
                            msg.attach(part)
            
            # Enviar email
            server = smtplib.SMTP(
                self.config['smtp_host'],
                self.config['smtp_port'],
                timeout=30
            )
            
            if self.config.get('use_tls', True):
                server.starttls()
            
            server.login(
                self.config['smtp_user'],
                self.config['smtp_password']
            )
            
            server.send_message(msg)
            server.quit()
            
            # Log exitoso
            self._log_email(invoice_id, to_email, subject, 'sent', None)
            
            return True, "Email enviado exitosamente"
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Error de autenticación: {str(e)}"
            self._log_email(invoice_id, to_email, subject, 'failed', error_msg)
            return False, error_msg
            
        except smtplib.SMTPException as e:
            error_msg = f"Error SMTP: {str(e)}"
            self._log_email(invoice_id, to_email, subject, 'failed', error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Error al enviar email: {str(e)}"
            self._log_email(invoice_id, to_email, subject, 'failed', error_msg)
            return False, error_msg
    
    def _html_to_text(self, html: str, invoice_payload: Dict[str, Any]) -> str:
        """
        Convierte HTML a texto plano simple para fallback.
        """
        # Texto básico de la factura
        text_parts = ["FACTURA"]
        text_parts.append("=" * 50)
        
        if 'invoice_number' in invoice_payload:
            text_parts.append(f"Número: {invoice_payload['invoice_number']}")
        
        if 'invoice_date' in invoice_payload:
            text_parts.append(f"Fecha: {invoice_payload['invoice_date']}")
        
        if 'third_party_name' in invoice_payload:
            text_parts.append(f"Cliente: {invoice_payload['third_party_name']}")
        
        if 'total_amount' in invoice_payload:
            text_parts.append(f"Total: {invoice_payload.get('currency', 'RD$')} {invoice_payload['total_amount']:,.2f}")
        
        text_parts.append("=" * 50)
        text_parts.append("")
        text_parts.append("Este email contiene su factura adjunta.")
        
        return "\n".join(text_parts)
    
    def _log_email(
        self,
        invoice_id: Optional[int],
        to_email: str,
        subject: str,
        status: str,
        error_message: Optional[str]
    ):
        """Registra el envío de email en la base de datos."""
        if not self.db_path:
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO email_logs 
                    (invoice_id, to_email, subject, sent_at, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    to_email,
                    subject,
                    datetime.now().isoformat(),
                    status,
                    error_message
                ))
        except Exception as e:
            # No fallar el envío si falla el logging
            print(f"Error al registrar email log: {e}")
    
    def get_email_logs(
        self,
        invoice_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de emails enviados.
        
        Args:
            invoice_id: Filtrar por factura específica
            limit: Número máximo de registros
        
        Returns:
            Lista de registros de email
        """
        if not self.db_path:
            return []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if invoice_id is not None:
                    cursor = conn.execute("""
                        SELECT * FROM email_logs
                        WHERE invoice_id = ?
                        ORDER BY sent_at DESC
                        LIMIT ?
                    """, (invoice_id, limit))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM email_logs
                        ORDER BY sent_at DESC
                        LIMIT ?
                    """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"Error al obtener email logs: {e}")
            return []


def send_invoice_email(
    invoice_payload: Dict[str, Any],
    to_email: str,
    subject: str,
    body_html: str,
    attachments: List[str] = None,
    db_path: Optional[str] = None,
    invoice_id: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Función helper para enviar email de factura.
    
    Args:
        invoice_payload: Datos de la factura
        to_email: Email del destinatario
        subject: Asunto del email
        body_html: Cuerpo del email en HTML
        attachments: Lista de rutas de archivos a adjuntar
        db_path: Ruta a la base de datos para logging
        invoice_id: ID de la factura
    
    Returns:
        Tuple de (success: bool, message: str)
    """
    service = EmailService(db_path=db_path)
    return service.send_invoice_email(
        invoice_payload,
        to_email,
        subject,
        body_html,
        attachments,
        invoice_id
    )
