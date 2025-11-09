"""
Diálogo para enviar facturas/cotizaciones por email.

Este diálogo permite:
- Ingresar email del destinatario
- Ver vista previa del email
- Adjuntar PDF de la factura/cotización
- Enviar usando EmailService (SMTP/SendGrid)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QCheckBox, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import os
from typing import Dict, Any, Optional
from utils.mail_utils import EmailService, EmailConfig


class EmailSenderThread(QThread):
    """Thread para enviar email sin bloquear la UI."""
    
    finished = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(self, email_service: EmailService, to_email: str, 
                 subject: str, body: str, attachments: list):
        super().__init__()
        self.email_service = email_service
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.attachments = attachments
    
    def run(self):
        """Ejecuta el envío del email."""
        try:
            success, message = self.email_service.send_invoice_email(
                invoice_payload={},  # Opcional: agregar datos de factura
                to_email=self.to_email,
                subject=self.subject,
                body_html=self.body,
                attachments=self.attachments
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"Error al enviar email: {str(e)}")


class EmailDialog(QDialog):
    """
    Diálogo para enviar facturas/cotizaciones por email.
    
    Uso:
        dialog = EmailDialog(
            parent=self,
            invoice_data={'invoice_number': 'B0100000123', ...},
            pdf_path='/path/to/invoice.pdf',
            db_path='facturas_cotizaciones.db'
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            print("Email enviado exitosamente")
    """
    
    def __init__(self, parent=None, invoice_data: Optional[Dict[str, Any]] = None,
                 pdf_path: Optional[str] = None, db_path: str = "facturas_cotizaciones.db"):
        super().__init__(parent)
        self.invoice_data = invoice_data or {}
        self.pdf_path = pdf_path
        self.db_path = db_path
        self.email_service = None
        
        self.setWindowTitle("Enviar Factura por Email")
        self.setMinimumSize(600, 500)
        
        self._init_ui()
        self._init_email_service()
        self._populate_defaults()
    
    def _init_ui(self):
        """Inicializa la interfaz de usuario."""
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel("📧 Enviar Factura por Email")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Email destinatario
        email_layout = QHBoxLayout()
        email_label = QLabel("Para:")
        email_label.setMinimumWidth(80)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("correo@ejemplo.com")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)
        
        # Asunto
        subject_layout = QHBoxLayout()
        subject_label = QLabel("Asunto:")
        subject_label.setMinimumWidth(80)
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Factura #...")
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.subject_input)
        layout.addLayout(subject_layout)
        
        # Checkbox para adjuntar PDF
        self.attach_pdf_checkbox = QCheckBox("Adjuntar PDF de la factura")
        self.attach_pdf_checkbox.setChecked(True)
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            self.attach_pdf_checkbox.setEnabled(False)
            self.attach_pdf_checkbox.setToolTip("No hay PDF disponible")
        layout.addWidget(self.attach_pdf_checkbox)
        
        # Vista previa del cuerpo del email
        body_label = QLabel("Mensaje:")
        layout.addWidget(body_label)
        
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("Escriba el mensaje del email aquí...")
        layout.addWidget(self.body_edit)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.test_connection_btn = QPushButton("🔌 Probar Conexión")
        self.test_connection_btn.clicked.connect(self._test_connection)
        button_layout.addWidget(self.test_connection_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.send_btn = QPushButton("✉️ Enviar")
        self.send_btn.setDefault(True)
        self.send_btn.clicked.connect(self._send_email)
        button_layout.addWidget(self.send_btn)
        
        layout.addLayout(button_layout)
        
        # Estado de configuración
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)
    
    def _init_email_service(self):
        """Inicializa el servicio de email."""
        try:
            config = EmailConfig.from_env()
            self.email_service = EmailService(config, self.db_path)
            
            # Verificar configuración
            if config.smtp_host and config.smtp_user:
                self.status_label.setText(
                    f"✅ Configurado: {config.smtp_user} → {config.smtp_host}:{config.smtp_port}"
                )
                self.status_label.setStyleSheet("color: green; font-size: 10px;")
            else:
                self.status_label.setText(
                    "⚠️ Email no configurado. Configure las variables de entorno SMTP_*"
                )
                self.status_label.setStyleSheet("color: orange; font-size: 10px;")
                self.send_btn.setEnabled(False)
                self.test_connection_btn.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-size: 10px;")
            self.send_btn.setEnabled(False)
            self.test_connection_btn.setEnabled(False)
    
    def _populate_defaults(self):
        """Rellena valores por defecto basados en invoice_data."""
        if not self.invoice_data:
            return
        
        # Email del cliente si existe
        client_email = self.invoice_data.get('client_email', '')
        if client_email:
            self.email_input.setText(client_email)
        
        # Asunto basado en número de factura
        invoice_number = self.invoice_data.get('invoice_number', 'SIN_NUMERO')
        invoice_type = self.invoice_data.get('invoice_type', 'factura')
        doc_type = 'Factura' if invoice_type == 'emitida' else 'Cotización'
        self.subject_input.setText(f"{doc_type} #{invoice_number}")
        
        # Cuerpo del email
        client_name = self.invoice_data.get('client_name', 'Cliente')
        total = self.invoice_data.get('total_amount', 0.0)
        currency = self.invoice_data.get('currency', 'RD$')
        
        body_template = f"""
<html>
<body>
<p>Estimado/a {client_name},</p>

<p>Adjunto encontrará la {doc_type.lower()} <strong>#{invoice_number}</strong> 
por un monto de <strong>{currency} {total:,.2f}</strong>.</p>

<p>Si tiene alguna pregunta, no dude en contactarnos.</p>

<p>Saludos cordiales,</p>
<p><em>Su empresa</em></p>
</body>
</html>
        """.strip()
        
        self.body_edit.setHtml(body_template)
    
    def _test_connection(self):
        """Prueba la conexión SMTP."""
        if not self.email_service:
            QMessageBox.warning(self, "Error", "Servicio de email no inicializado")
            return
        
        # Mostrar diálogo de progreso
        progress = QProgressDialog("Probando conexión SMTP...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Probando Conexión")
        progress.show()
        
        try:
            success, message = self.email_service.test_connection()
            progress.close()
            
            if success:
                QMessageBox.information(self, "Conexión Exitosa", 
                                      f"✅ {message}")
            else:
                QMessageBox.warning(self, "Error de Conexión", 
                                  f"❌ {message}")
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", 
                               f"Error al probar conexión: {str(e)}")
    
    def _send_email(self):
        """Envía el email."""
        # Validar campos
        to_email = self.email_input.text().strip()
        if not to_email:
            QMessageBox.warning(self, "Campo Requerido", 
                              "Debe ingresar un email de destinatario")
            self.email_input.setFocus()
            return
        
        # Validar formato básico de email
        if '@' not in to_email or '.' not in to_email:
            QMessageBox.warning(self, "Email Inválido", 
                              "El email no parece tener un formato válido")
            self.email_input.setFocus()
            return
        
        subject = self.subject_input.text().strip()
        if not subject:
            QMessageBox.warning(self, "Campo Requerido", 
                              "Debe ingresar un asunto")
            self.subject_input.setFocus()
            return
        
        body = self.body_edit.toHtml()
        
        # Preparar adjuntos
        attachments = []
        if self.attach_pdf_checkbox.isChecked() and self.pdf_path:
            if os.path.exists(self.pdf_path):
                attachments.append(self.pdf_path)
            else:
                reply = QMessageBox.question(
                    self, "PDF No Encontrado",
                    f"El archivo PDF no existe:\n{self.pdf_path}\n\n"
                    "¿Desea enviar el email sin adjunto?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
        
        # Confirmar envío
        confirm_msg = f"¿Enviar email a {to_email}?"
        if attachments:
            confirm_msg += f"\n\nAdjunto: {os.path.basename(attachments[0])}"
        
        reply = QMessageBox.question(
            self, "Confirmar Envío",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Enviar en thread separado
        self._send_email_async(to_email, subject, body, attachments)
    
    def _send_email_async(self, to_email: str, subject: str, body: str, attachments: list):
        """Envía el email de forma asíncrona."""
        # Deshabilitar botones
        self.send_btn.setEnabled(False)
        self.test_connection_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        
        # Mostrar progreso
        self.progress = QProgressDialog("Enviando email...", None, 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setWindowTitle("Enviando")
        self.progress.show()
        
        # Crear y ejecutar thread
        self.sender_thread = EmailSenderThread(
            self.email_service, to_email, subject, body, attachments
        )
        self.sender_thread.finished.connect(self._on_email_sent)
        self.sender_thread.start()
    
    def _on_email_sent(self, success: bool, message: str):
        """Callback cuando el email se ha enviado."""
        self.progress.close()
        
        # Rehabilitar botones
        self.send_btn.setEnabled(True)
        self.test_connection_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Email Enviado", 
                                  f"✅ {message}")
            self.accept()  # Cerrar el diálogo
        else:
            QMessageBox.critical(self, "Error al Enviar", 
                               f"❌ {message}")


# Para testing del diálogo
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Datos de prueba
    test_invoice = {
        'invoice_number': 'B0100000123',
        'invoice_type': 'emitida',
        'client_name': 'Juan Pérez',
        'client_email': 'juan@ejemplo.com',
        'total_amount': 15000.00,
        'currency': 'RD$'
    }
    
    dialog = EmailDialog(
        invoice_data=test_invoice,
        pdf_path='/tmp/test_invoice.pdf'
    )
    dialog.exec()
    
    sys.exit(0)
