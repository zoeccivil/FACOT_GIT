"""
Tests para mail_utils.py
"""
import os
import tempfile
import sqlite3
from unittest.mock import Mock, patch, MagicMock
import pytest
from utils.mail_utils import EmailService, EmailConfig, send_invoice_email


class TestEmailConfig:
    """Tests para EmailConfig."""
    
    def test_get_config_defaults(self):
        """Test de configuración por defecto."""
        # Limpiar variables de entorno
        env_vars = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 
                    'SMTP_USE_TLS', 'SENDGRID_API_KEY']
        old_values = {}
        for var in env_vars:
            old_values[var] = os.environ.pop(var, None)
        
        try:
            config = EmailConfig.get_config()
            
            assert config['smtp_host'] == 'smtp.gmail.com'
            assert config['smtp_port'] == 587
            assert config['use_tls'] is True
            assert config['smtp_user'] == ''
            assert config['smtp_password'] == ''
        finally:
            # Restaurar variables
            for var, value in old_values.items():
                if value is not None:
                    os.environ[var] = value
    
    def test_get_config_custom(self):
        """Test de configuración personalizada."""
        os.environ['SMTP_HOST'] = 'smtp.test.com'
        os.environ['SMTP_PORT'] = '465'
        os.environ['SMTP_USER'] = 'test@test.com'
        os.environ['SMTP_PASSWORD'] = 'testpass'
        os.environ['SMTP_USE_TLS'] = 'false'
        
        try:
            config = EmailConfig.get_config()
            
            assert config['smtp_host'] == 'smtp.test.com'
            assert config['smtp_port'] == 465
            assert config['smtp_user'] == 'test@test.com'
            assert config['smtp_password'] == 'testpass'
            assert config['use_tls'] is False
        finally:
            # Limpiar
            for var in ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_USE_TLS']:
                os.environ.pop(var, None)


class TestEmailService:
    """Tests para EmailService."""
    
    def test_initialization(self, temp_db):
        """Test de inicialización del servicio."""
        config = {
            'smtp_host': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': 'test@test.com',
            'smtp_password': 'testpass',
            'use_tls': True
        }
        
        service = EmailService(config, temp_db)
        assert service.config == config
        assert service.db_path == temp_db
    
    def test_email_logs_table_created(self, temp_db):
        """Test de creación de tabla email_logs."""
        service = EmailService(db_path=temp_db)
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='email_logs'
            """)
            tables = cursor.fetchall()
            assert len(tables) == 1
    
    @patch('utils.mail_utils.smtplib.SMTP')
    def test_test_connection_success(self, mock_smtp):
        """Test de prueba de conexión exitosa."""
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        config = {
            'smtp_host': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': 'test@test.com',
            'smtp_password': 'testpass',
            'use_tls': True
        }
        
        service = EmailService(config)
        success, message = service.test_connection()
        
        assert success is True
        assert "exitosa" in message.lower()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
        mock_server.quit.assert_called_once()
    
    @patch('utils.mail_utils.smtplib.SMTP')
    def test_test_connection_auth_failure(self, mock_smtp):
        """Test de fallo de autenticación."""
        import smtplib
        
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Invalid credentials')
        mock_smtp.return_value = mock_server
        
        config = {
            'smtp_host': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': 'test@test.com',
            'smtp_password': 'wrongpass',
            'use_tls': True
        }
        
        service = EmailService(config)
        success, message = service.test_connection()
        
        assert success is False
        assert "autenticación" in message.lower()
    
    def test_test_connection_no_credentials(self):
        """Test de conexión sin credenciales."""
        config = {
            'smtp_host': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': '',
            'smtp_password': '',
            'use_tls': True
        }
        
        service = EmailService(config)
        success, message = service.test_connection()
        
        assert success is False
        assert "credenciales" in message.lower()
    
    @patch('utils.mail_utils.smtplib.SMTP')
    def test_send_invoice_email_success(self, mock_smtp, temp_db):
        """Test de envío exitoso de email."""
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        config = {
            'smtp_host': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': 'test@test.com',
            'smtp_password': 'testpass',
            'use_tls': True,
            'from_email': 'test@test.com'
        }
        
        service = EmailService(config, temp_db)
        
        invoice_payload = {
            'invoice_number': 'B0100000001',
            'invoice_date': '2025-01-15',
            'third_party_name': 'Cliente Test',
            'total_amount': 11800.00,
            'currency': 'RD$'
        }
        
        success, message = service.send_invoice_email(
            invoice_payload,
            'cliente@test.com',
            'Factura B0100000001',
            '<h1>Factura</h1><p>Gracias por su compra</p>',
            invoice_id=1
        )
        
        assert success is True
        assert "exitosamente" in message.lower()
        mock_server.send_message.assert_called_once()
        
        # Verificar que se registró el log
        logs = service.get_email_logs(invoice_id=1)
        assert len(logs) == 1
        assert logs[0]['status'] == 'sent'
        assert logs[0]['to_email'] == 'cliente@test.com'
    
    @patch('utils.mail_utils.smtplib.SMTP')
    def test_send_invoice_email_with_attachment(self, mock_smtp, temp_db):
        """Test de envío con archivo adjunto."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        config = {
            'smtp_host': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': 'test@test.com',
            'smtp_password': 'testpass',
            'use_tls': True,
            'from_email': 'test@test.com'
        }
        
        service = EmailService(config, temp_db)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write('Test PDF content')
            temp_file = f.name
        
        try:
            invoice_payload = {
                'invoice_number': 'B0100000001',
                'invoice_date': '2025-01-15',
                'third_party_name': 'Cliente Test',
                'total_amount': 11800.00
            }
            
            success, message = service.send_invoice_email(
                invoice_payload,
                'cliente@test.com',
                'Factura con PDF',
                '<h1>Factura Adjunta</h1>',
                attachments=[temp_file],
                invoice_id=2
            )
            
            assert success is True
            mock_server.send_message.assert_called_once()
            
        finally:
            os.unlink(temp_file)
    
    @patch('utils.mail_utils.smtplib.SMTP')
    def test_send_invoice_email_smtp_failure(self, mock_smtp, temp_db):
        """Test de fallo en envío SMTP."""
        import smtplib
        
        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPException("Connection error")
        mock_smtp.return_value = mock_server
        
        config = {
            'smtp_host': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': 'test@test.com',
            'smtp_password': 'testpass',
            'use_tls': True,
            'from_email': 'test@test.com'
        }
        
        service = EmailService(config, temp_db)
        
        invoice_payload = {
            'invoice_number': 'B0100000001',
            'total_amount': 11800.00
        }
        
        success, message = service.send_invoice_email(
            invoice_payload,
            'cliente@test.com',
            'Test',
            '<h1>Test</h1>',
            invoice_id=3
        )
        
        assert success is False
        assert "error" in message.lower()
        
        # Verificar log de fallo
        logs = service.get_email_logs(invoice_id=3)
        assert len(logs) == 1
        assert logs[0]['status'] == 'failed'
    
    def test_get_email_logs(self, temp_db):
        """Test de obtención de logs."""
        service = EmailService(db_path=temp_db)
        
        # Insertar logs manualmente
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                INSERT INTO email_logs 
                (invoice_id, to_email, subject, sent_at, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (1, 'test1@test.com', 'Test 1', '2025-01-15T10:00:00', 'sent', None))
            
            conn.execute("""
                INSERT INTO email_logs 
                (invoice_id, to_email, subject, sent_at, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (1, 'test2@test.com', 'Test 2', '2025-01-15T11:00:00', 'sent', None))
        
        # Obtener logs de factura 1
        logs = service.get_email_logs(invoice_id=1)
        assert len(logs) == 2
        
        # Obtener todos los logs
        all_logs = service.get_email_logs()
        assert len(all_logs) == 2
    
    def test_html_to_text(self):
        """Test de conversión de HTML a texto."""
        service = EmailService()
        
        invoice_payload = {
            'invoice_number': 'B0100000001',
            'invoice_date': '2025-01-15',
            'third_party_name': 'Cliente Test',
            'total_amount': 11800.00,
            'currency': 'RD$'
        }
        
        text = service._html_to_text('<h1>HTML</h1>', invoice_payload)
        
        assert 'FACTURA' in text
        assert 'B0100000001' in text
        assert '2025-01-15' in text
        assert 'Cliente Test' in text
        assert '11,800.00' in text


class TestHelperFunction:
    """Tests para la función helper send_invoice_email."""
    
    @patch('utils.mail_utils.EmailService')
    def test_send_invoice_email_helper(self, mock_email_service):
        """Test de la función helper."""
        mock_instance = MagicMock()
        mock_instance.send_invoice_email.return_value = (True, "Success")
        mock_email_service.return_value = mock_instance
        
        invoice_payload = {'invoice_number': 'B01'}
        
        success, message = send_invoice_email(
            invoice_payload,
            'test@test.com',
            'Test Subject',
            '<h1>Test</h1>'
        )
        
        assert success is True
        assert message == "Success"
        mock_instance.send_invoice_email.assert_called_once()
