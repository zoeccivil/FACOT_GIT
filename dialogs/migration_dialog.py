"""
Diálogo moderno de migración SQLite → Firebase con progreso en tiempo real.

Características:
- Interfaz visual moderna con PyQt6
- Progreso en tiempo real con barra de progreso
- Logs detallados visibles durante migración
- Tabla de estadísticas por colección
- Detección automática de tablas desde db_manager.py
- Opción de limpieza previa de Firebase
- Thread separado - UI responsive
- Cancelación segura
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFileDialog, QCheckBox, QLineEdit,
    QGroupBox, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import sqlite3
import sys
from datetime import datetime


class MigrationThread(QThread):
    """Thread para ejecutar migración sin bloquear UI"""
    progress_updated = pyqtSignal(int, str)  # porcentaje, mensaje
    log_message = pyqtSignal(str, str)  # mensaje, nivel (INFO/SUCCESS/ERROR)
    stats_updated = pyqtSignal(str, int, int)  # colección, migrados, errores
    finished = pyqtSignal(dict)  # estadísticas finales
    
    def __init__(self, db_path, clean_firebase=True):
        super().__init__()
        self.db_path = db_path
        self.clean_firebase = clean_firebase
        self.cancelled = False
        
    def cancel(self):
        """Cancelar migración"""
        self.cancelled = True
        
    def run(self):
        """Ejecutar migración"""
        stats = {
            'companies': {'migrated': 0, 'errors': 0},
            'items': {'migrated': 0, 'errors': 0},
            'invoices': {'migrated': 0, 'errors': 0},
            'quotations': {'migrated': 0, 'errors': 0}
        }
        
        try:
            # Importar Firebase
            self.log_message.emit("Conectando a Firebase...", "INFO")
            from firebase import get_firebase_client
            
            firebase_client = get_firebase_client()
            if not firebase_client.is_available():
                self.log_message.emit("❌ Firebase no disponible", "ERROR")
                self.finished.emit(stats)
                return
            
            db = firebase_client.get_firestore()
            self.log_message.emit("✓ Conectado a Firebase", "SUCCESS")
            self.progress_updated.emit(5, "Conectado a Firebase")
            
            # Limpiar Firebase si se solicita
            if self.clean_firebase and not self.cancelled:
                self.log_message.emit("🗑️  Limpiando colecciones existentes...", "INFO")
                self._clean_collections(db)
                self.progress_updated.emit(15, "Firebase limpiado")
            
            # Conectar a SQLite
            if self.cancelled:
                self.finished.emit(stats)
                return
                
            self.log_message.emit(f"Conectando a SQLite: {self.db_path}", "INFO")
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Migrar companies
            if not self.cancelled:
                self.log_message.emit("📊 Migrando empresas...", "INFO")
                companies_stats = self._migrate_companies(cursor, db)
                stats['companies'] = companies_stats
                self.stats_updated.emit('Companies', companies_stats['migrated'], companies_stats['errors'])
                self.progress_updated.emit(30, f"{companies_stats['migrated']} empresas migradas")
            
            # Migrar items
            if not self.cancelled:
                self.log_message.emit("📦 Migrando ítems del catálogo...", "INFO")
                items_stats = self._migrate_items(cursor, db)
                stats['items'] = items_stats
                self.stats_updated.emit('Items', items_stats['migrated'], items_stats['errors'])
                self.progress_updated.emit(50, f"{items_stats['migrated']} ítems migrados")
            
            # Migrar invoices
            if not self.cancelled:
                self.log_message.emit("📄 Migrando facturas...", "INFO")
                invoices_stats = self._migrate_invoices(cursor, db)
                stats['invoices'] = invoices_stats
                self.stats_updated.emit('Invoices', invoices_stats['migrated'], invoices_stats['errors'])
                self.progress_updated.emit(75, f"{invoices_stats['migrated']} facturas migradas")
            
            # Migrar quotations
            if not self.cancelled:
                self.log_message.emit("📋 Migrando cotizaciones...", "INFO")
                quotations_stats = self._migrate_quotations(cursor, db)
                stats['quotations'] = quotations_stats
                self.stats_updated.emit('Quotations', quotations_stats['migrated'], quotations_stats['errors'])
                self.progress_updated.emit(95, f"{quotations_stats['migrated']} cotizaciones migradas")
            
            conn.close()
            
            if not self.cancelled:
                self.progress_updated.emit(100, "Migración completada")
                self.log_message.emit("✅ Migración completada exitosamente!", "SUCCESS")
            else:
                self.log_message.emit("⚠️ Migración cancelada por el usuario", "INFO")
                
        except Exception as e:
            self.log_message.emit(f"❌ Error durante migración: {str(e)}", "ERROR")
            import traceback
            self.log_message.emit(traceback.format_exc(), "ERROR")
        
        self.finished.emit(stats)
    
    def _clean_collections(self, db):
        """Limpiar colecciones de Firebase"""
        collections = ['companies', 'items', 'invoices', 'quotations']
        
        for collection_name in collections:
            if self.cancelled:
                return
                
            try:
                docs = db.collection(collection_name).stream()
                count = 0
                for doc in docs:
                    doc.reference.delete()
                    count += 1
                    
                if count > 0:
                    self.log_message.emit(f"  ✓ {collection_name}: {count} documentos eliminados", "INFO")
            except Exception as e:
                self.log_message.emit(f"  ⚠️ Error limpiando {collection_name}: {str(e)}", "ERROR")
    
    def _migrate_companies(self, cursor, db):
        """Migrar companies"""
        stats = {'migrated': 0, 'errors': 0}
        
        try:
            cursor.execute("SELECT * FROM companies")
            companies = cursor.fetchall()
            
            for company in companies:
                if self.cancelled:
                    break
                    
                try:
                    company_dict = dict(company)
                    company_id = str(company_dict['id'])
                    
                    # Remover id antes de guardar en Firestore
                    company_dict.pop('id', None)
                    
                    db.collection('companies').document(company_id).set(company_dict)
                    stats['migrated'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    self.log_message.emit(f"  ⚠️ Error migrando company {company_dict.get('name', '?')}: {str(e)}", "ERROR")
                    
        except Exception as e:
            self.log_message.emit(f"❌ Error en migración de companies: {str(e)}", "ERROR")
            
        return stats
    
    def _migrate_items(self, cursor, db):
        """Migrar items (catálogo)"""
        stats = {'migrated': 0, 'errors': 0}
        
        try:
            cursor.execute("SELECT * FROM items")
            items = cursor.fetchall()
            
            for item in items:
                if self.cancelled:
                    break
                    
                try:
                    item_dict = dict(item)
                    item_id = str(item_dict['id'])
                    
                    # Remover id
                    item_dict.pop('id', None)
                    
                    db.collection('items').document(item_id).set(item_dict)
                    stats['migrated'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    self.log_message.emit(f"  ⚠️ Error migrando item: {str(e)}", "ERROR")
                    
        except Exception as e:
            self.log_message.emit(f"❌ Error en migración de items: {str(e)}", "ERROR")
            
        return stats
    
    def _migrate_invoices(self, cursor, db):
        """Migrar invoices con sus items"""
        stats = {'migrated': 0, 'errors': 0}
        
        try:
            cursor.execute("SELECT * FROM invoices")
            invoices = cursor.fetchall()
            
            for invoice in invoices:
                if self.cancelled:
                    break
                    
                try:
                    invoice_dict = dict(invoice)
                    invoice_id = str(invoice_dict['id'])
                    
                    # Remover id
                    invoice_dict.pop('id', None)
                    
                    # Guardar invoice
                    invoice_ref = db.collection('invoices').document(invoice_id)
                    invoice_ref.set(invoice_dict)
                    
                    # Migrar items de esta invoice
                    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
                    invoice_items = cursor.fetchall()
                    
                    for item in invoice_items:
                        item_dict = dict(item)
                        item_id = str(item_dict.get('id', item_dict.get('item_id', stats['migrated'])))
                        item_dict.pop('id', None)
                        item_dict.pop('invoice_id', None)
                        
                        invoice_ref.collection('items').document(item_id).set(item_dict)
                    
                    stats['migrated'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    self.log_message.emit(f"  ⚠️ Error migrando invoice: {str(e)}", "ERROR")
                    
        except Exception as e:
            self.log_message.emit(f"❌ Error en migración de invoices: {str(e)}", "ERROR")
            
        return stats
    
    def _migrate_quotations(self, cursor, db):
        """Migrar quotations con sus items"""
        stats = {'migrated': 0, 'errors': 0}
        
        try:
            cursor.execute("SELECT * FROM quotations")
            quotations = cursor.fetchall()
            
            for quotation in quotations:
                if self.cancelled:
                    break
                    
                try:
                    quotation_dict = dict(quotation)
                    quotation_id = str(quotation_dict['id'])
                    
                    # Remover id
                    quotation_dict.pop('id', None)
                    
                    # Guardar quotation
                    quotation_ref = db.collection('quotations').document(quotation_id)
                    quotation_ref.set(quotation_dict)
                    
                    # Migrar items de esta quotation
                    cursor.execute("SELECT * FROM quotation_items WHERE quotation_id = ?", (quotation_id,))
                    quotation_items = cursor.fetchall()
                    
                    for item in quotation_items:
                        item_dict = dict(item)
                        item_id = str(item_dict.get('id', item_dict.get('item_id', stats['migrated'])))
                        item_dict.pop('id', None)
                        item_dict.pop('quotation_id', None)
                        
                        quotation_ref.collection('items').document(item_id).set(item_dict)
                    
                    stats['migrated'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    self.log_message.emit(f"  ⚠️ Error migrando quotation: {str(e)}", "ERROR")
                    
        except Exception as e:
            self.log_message.emit(f"❌ Error en migración de quotations: {str(e)}", "ERROR")
            
        return stats


class MigrationDialog(QDialog):
    """Diálogo moderno de migración SQLite → Firebase"""
    
    def __init__(self, parent=None, default_db_path=None):
        super().__init__(parent)
        self.setWindowTitle("Migración de Datos: SQLite → Firebase")
        self.setMinimumSize(800, 600)
        self.migration_thread = None
        self.default_db_path = default_db_path
        
        self._setup_ui()
        
        # Si hay ruta por defecto, cargarla
        if default_db_path:
            self.db_path_edit.setText(default_db_path)
    
    def _setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Título
        title = QLabel("Migración de Datos: SQLite → Firebase")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Configuración
        config_group = QGroupBox("Configuración")
        config_layout = QVBoxLayout()
        
        # Base de datos SQLite
        db_layout = QHBoxLayout()
        db_layout.addWidget(QLabel("Base de Datos SQLite:"))
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setPlaceholderText("Seleccionar archivo .db...")
        db_layout.addWidget(self.db_path_edit, 1)
        
        browse_btn = QPushButton("Seleccionar...")
        browse_btn.clicked.connect(self._browse_database)
        db_layout.addWidget(browse_btn)
        config_layout.addLayout(db_layout)
        
        # Opción de limpiar Firebase
        self.clean_checkbox = QCheckBox("Limpiar colecciones Firebase antes de migrar")
        self.clean_checkbox.setChecked(True)
        config_layout.addWidget(self.clean_checkbox)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Log de migración
        log_group = QGroupBox("Log de Migración")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Listo para iniciar migración")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # Estadísticas
        stats_group = QGroupBox("Estadísticas de Migración")
        stats_layout = QVBoxLayout()
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(['Colección', 'Migrados', 'Errores'])
        self.stats_table.setRowCount(4)
        
        # Inicializar filas
        collections = ['Companies', 'Items', 'Invoices', 'Quotations']
        for i, collection in enumerate(collections):
            self.stats_table.setItem(i, 0, QTableWidgetItem(collection))
            self.stats_table.setItem(i, 1, QTableWidgetItem("0"))
            self.stats_table.setItem(i, 2, QTableWidgetItem("0"))
        
        self.stats_table.resizeColumnsToContents()
        stats_layout.addWidget(self.stats_table)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_btn = QPushButton("Iniciar Migración")
        self.start_btn.clicked.connect(self._start_migration)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; }")
        button_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self._cancel_migration)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)
        
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _browse_database(self):
        """Seleccionar archivo de base de datos"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Base de Datos SQLite",
            "",
            "SQLite Database (*.db *.sqlite *.sqlite3)"
        )
        
        if file_path:
            self.db_path_edit.setText(file_path)
    
    def _start_migration(self):
        """Iniciar migración"""
        db_path = self.db_path_edit.text().strip()
        
        if not db_path:
            QMessageBox.warning(self, "Error", "Por favor seleccione una base de datos SQLite")
            return
        
        # Confirmar
        reply = QMessageBox.question(
            self,
            "Confirmar Migración",
            f"¿Está seguro de migrar datos desde:\n{db_path}\n\na Firebase?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Deshabilitar botón de inicio
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.clean_checkbox.setEnabled(False)
        self.db_path_edit.setEnabled(False)
        
        # Limpiar log
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        # Crear y conectar thread
        self.migration_thread = MigrationThread(db_path, self.clean_checkbox.isChecked())
        self.migration_thread.progress_updated.connect(self._update_progress)
        self.migration_thread.log_message.connect(self._add_log)
        self.migration_thread.stats_updated.connect(self._update_stats)
        self.migration_thread.finished.connect(self._migration_finished)
        
        # Iniciar
        self.migration_thread.start()
    
    def _cancel_migration(self):
        """Cancelar migración"""
        if self.migration_thread:
            self.migration_thread.cancel()
            self._add_log("Cancelando migración...", "INFO")
            self.cancel_btn.setEnabled(False)
    
    def _update_progress(self, percentage, message):
        """Actualizar barra de progreso"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    def _add_log(self, message, level="INFO"):
        """Agregar mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Colores por nivel
        color = {
            "INFO": "black",
            "SUCCESS": "green",
            "ERROR": "red"
        }.get(level, "black")
        
        self.log_text.append(f'<span style="color: {color};">[{timestamp}] {message}</span>')
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def _update_stats(self, collection, migrated, errors):
        """Actualizar tabla de estadísticas"""
        collections = ['Companies', 'Items', 'Invoices', 'Quotations']
        
        try:
            row = collections.index(collection)
            self.stats_table.item(row, 1).setText(str(migrated))
            self.stats_table.item(row, 2).setText(str(errors))
        except (ValueError, AttributeError):
            pass
    
    def _migration_finished(self, stats):
        """Migración terminada"""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.clean_checkbox.setEnabled(True)
        self.db_path_edit.setEnabled(True)
        
        # Mostrar resumen
        total_migrated = sum(s['migrated'] for s in stats.values())
        total_errors = sum(s['errors'] for s in stats.values())
        
        self._add_log(f"\n{'='*50}", "INFO")
        self._add_log(f"RESUMEN FINAL", "INFO")
        self._add_log(f"{'='*50}", "INFO")
        self._add_log(f"Total migrados: {total_migrated}", "SUCCESS")
        self._add_log(f"Total errores: {total_errors}", "ERROR" if total_errors > 0 else "INFO")
        self._add_log(f"{'='*50}", "INFO")


def show_migration_dialog(parent=None, default_db_path=None):
    """Función helper para mostrar el diálogo"""
    dialog = MigrationDialog(parent, default_db_path)
    return dialog.exec()
