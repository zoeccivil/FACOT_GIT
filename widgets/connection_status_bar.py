"""
Barra de estado de conexión para FACOT.

Muestra el estado actual de la conexión (SQLite o Firebase)
y permite cambiar entre bases de datos.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from typing import Optional
import os


class ConnectionStatusBar(QWidget):
    """
    Widget que muestra el estado de conexión actual.
    
    Características:
    - Muestra si está conectado a SQLite o Firebase
    - Indica estado online/offline
    - Permite cambiar de base de datos SQLite
    - Permite cambiar modo de conexión
    
    Signals:
        database_changed: Emitido cuando se cambia la base de datos
        mode_changed: Emitido cuando se cambia el modo de conexión
    """
    
    database_changed = pyqtSignal(str)  # Ruta de nueva base de datos
    mode_changed = pyqtSignal(str)  # Nuevo modo (SQLITE, FIREBASE, AUTO)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = "SQLITE"  # Por defecto
        self.current_db_path = ""
        self.is_online = False
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura la interfaz del widget."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Etiqueta de estado
        self.status_label = QLabel("●")
        self.status_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # Etiqueta de modo
        self.mode_label = QLabel("SQLite")
        self.mode_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.mode_label)
        
        # Etiqueta de base de datos/estado
        self.db_label = QLabel("No conectado")
        layout.addWidget(self.db_label)
        
        # Botón de opciones
        self.options_btn = QPushButton("⚙")
        self.options_btn.setMaximumWidth(30)
        self.options_btn.setToolTip("Opciones de conexión")
        self.options_btn.clicked.connect(self._show_options_menu)
        layout.addWidget(self.options_btn)
        
        layout.addStretch()
        
        # Actualizar apariencia inicial
        self._update_appearance()
    
    def set_mode(self, mode: str, db_path: Optional[str] = None):
        """
        Establece el modo de conexión actual.
        
        Args:
            mode: "SQLITE", "FIREBASE", o "AUTO"
            db_path: Ruta a la base de datos (para SQLite)
        """
        self.current_mode = mode.upper()
        
        if db_path:
            self.current_db_path = db_path
        
        # If Firebase mode, check if it's actually available
        if self.current_mode == "FIREBASE":
            self._verify_firebase_connection()
        
        self._update_appearance()
    
    def _verify_firebase_connection(self):
        """Verifica si Firebase está realmente disponible y conectado."""
        try:
            from firebase import get_firebase_client
            client = get_firebase_client()
            
            if client.is_available():
                # Firebase is available, check if online
                # The online status will be set separately by set_online_status()
                print("[CONNECTION_STATUS] Firebase is available")
            else:
                # Firebase not available, show warning
                print("[CONNECTION_STATUS] Firebase not available despite FIREBASE mode")
        except Exception as e:
            print(f"[CONNECTION_STATUS] Error verifying Firebase: {e}")
    
    def set_online_status(self, is_online: bool):
        """
        Establece el estado online/offline.
        
        Args:
            is_online: True si hay conexión a internet
        """
        self.is_online = is_online
        self._update_appearance()
    
    def _update_appearance(self):
        """Actualiza la apariencia según el estado actual."""
        # Actualizar modo
        self.mode_label.setText(self.current_mode)
        
        # Actualizar indicador de estado
        if self.current_mode == "FIREBASE":
            if self.is_online:
                self.status_label.setText("●")
                self.status_label.setStyleSheet("color: #00C853; font-size: 14px;")  # Verde
                self.db_label.setText("Conectado a Firebase")
            else:
                self.status_label.setText("●")
                self.status_label.setStyleSheet("color: #FF6F00; font-size: 14px;")  # Naranja
                self.db_label.setText("Firebase (sin conexión)")
        
        elif self.current_mode == "SQLITE":
            self.status_label.setText("●")
            if self.is_online:
                self.status_label.setStyleSheet("color: #2196F3; font-size: 14px;")  # Azul
                self.db_label.setText(f"SQLite (Online): {self._format_db_path()}")
            else:
                self.status_label.setStyleSheet("color: #757575; font-size: 14px;")  # Gris
                self.db_label.setText(f"SQLite (Offline): {self._format_db_path()}")
        
        elif self.current_mode == "AUTO":
            if self.is_online:
                self.status_label.setText("●")
                self.status_label.setStyleSheet("color: #00C853; font-size: 14px;")  # Verde
                self.db_label.setText("AUTO → Firebase")
            else:
                self.status_label.setText("●")
                self.status_label.setStyleSheet("color: #2196F3; font-size: 14px;")  # Azul
                self.db_label.setText(f"AUTO → SQLite: {self._format_db_path()}")
    
    def _format_db_path(self) -> str:
        """Formatea la ruta de la base de datos para mostrar."""
        if not self.current_db_path:
            return "No seleccionada"
        
        # Mostrar solo el nombre del archivo
        return os.path.basename(self.current_db_path)
    
    def _show_options_menu(self):
        """Muestra el menú de opciones."""
        menu = QMenu(self)
        
        # NUEVA OPCIÓN: Configurar modo
        config_action = menu.addAction("⚙️ Configurar modo...")
        config_action.triggered.connect(self._show_mode_config_dialog)
        
        menu.addSeparator()
        
        # Opciones según el modo actual
        if self.current_mode == "SQLITE":
            # Cambiar base de datos
            change_db_action = menu.addAction("📂 Cambiar base de datos...")
            change_db_action.triggered.connect(self._change_database)
            
            # Crear nueva base de datos
            new_db_action = menu.addAction("➕ Crear nueva base de datos...")
            new_db_action.triggered.connect(self._create_new_database)
            
            menu.addSeparator()
            
            # Cambiar a Firebase (si está disponible)
            if self.is_online:
                firebase_action = menu.addAction("☁️ Cambiar a Firebase")
                firebase_action.triggered.connect(lambda: self._change_mode("FIREBASE"))
                
                auto_action = menu.addAction("🔄 Modo AUTO (Firebase/SQLite)")
                auto_action.triggered.connect(lambda: self._change_mode("AUTO"))
        
        elif self.current_mode == "FIREBASE":
            # Cambiar a SQLite
            sqlite_action = menu.addAction("💾 Cambiar a SQLite...")
            sqlite_action.triggered.connect(lambda: self._change_mode("SQLITE"))
            
            auto_action = menu.addAction("🔄 Modo AUTO (Firebase/SQLite)")
            auto_action.triggered.connect(lambda: self._change_mode("AUTO"))
        
        elif self.current_mode == "AUTO":
            # Forzar SQLite
            sqlite_action = menu.addAction("💾 Forzar SQLite...")
            sqlite_action.triggered.connect(lambda: self._change_mode("SQLITE"))
            
            # Forzar Firebase
            if self.is_online:
                firebase_action = menu.addAction("☁️ Forzar Firebase")
                firebase_action.triggered.connect(lambda: self._change_mode("FIREBASE"))
        
        # Mostrar menú en la posición del cursor
        menu.exec(QCursor.pos())
    
    def _show_mode_config_dialog(self):
        """Muestra el diálogo de configuración de modo."""
        from .connection_mode_dialog import show_connection_mode_dialog
        
        # Mostrar diálogo con modo actual
        new_mode = show_connection_mode_dialog(self.current_mode, self)
        
        if new_mode:
            # Usuario seleccionó un nuevo modo
            print(f"[CONNECTION_STATUS] Cambiando a modo: {new_mode}")
            self._change_mode(new_mode)
    
    def _change_database(self):
        """Permite al usuario cambiar la base de datos SQLite."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Base de Datos SQLite",
            os.path.dirname(self.current_db_path) if self.current_db_path else "",
            "SQLite Database (*.db);;Todos los archivos (*.*)"
        )
        
        if filename:
            self.current_db_path = filename
            self._update_appearance()
            self.database_changed.emit(filename)
    
    def _create_new_database(self):
        """Permite al usuario crear una nueva base de datos SQLite."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Crear Nueva Base de Datos SQLite",
            "",
            "SQLite Database (*.db)"
        )
        
        if filename:
            # Asegurar extensión .db
            if not filename.endswith('.db'):
                filename += '.db'
            
            self.current_db_path = filename
            self._update_appearance()
            self.database_changed.emit(filename)
    
    def _change_mode(self, new_mode: str):
        """
        Cambia el modo de conexión.
        
        Args:
            new_mode: "SQLITE", "FIREBASE", o "AUTO"
        """
        if new_mode == "SQLITE" and not self.current_db_path:
            # Si no hay base de datos seleccionada, pedir una
            self._change_database()
            if not self.current_db_path:
                return  # Usuario canceló
        
        self.current_mode = new_mode
        self._update_appearance()
        self.mode_changed.emit(new_mode)
