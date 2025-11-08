"""
Diálogo para seleccionar el modo de conexión preferido.

Permite al usuario elegir entre SQLite, Firebase o AUTO,
y guardar su preferencia para futuras sesiones.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
    QLabel, QPushButton, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt
from typing import Optional


class ConnectionModeDialog(QDialog):
    """
    Diálogo para seleccionar el modo de obtención de datos.
    
    Permite elegir entre:
    - SQLite (base de datos local)
    - Firebase (nube)
    - AUTO (automático según disponibilidad)
    """
    
    def __init__(self, current_mode: str = "AUTO", parent=None):
        super().__init__(parent)
        self.selected_mode = current_mode.upper()
        self.remember_choice = False
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        self.setWindowTitle("Configurar Modo de Conexión")
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel("Seleccione cómo desea obtener sus datos:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Grupo de opciones
        options_group = QGroupBox("Modo de Conexión")
        options_layout = QVBoxLayout()
        
        # Opción: SQLite
        self.sqlite_radio = QRadioButton("SQLite (Base de datos local)")
        self.sqlite_radio.setStyleSheet("font-weight: bold; font-size: 12px;")
        options_layout.addWidget(self.sqlite_radio)
        
        sqlite_desc = QLabel(
            "  ✓ Funciona sin conexión a internet\n"
            "  ✓ Control total de sus datos\n"
            "  ✗ Solo un usuario a la vez\n"
            "  ✗ Acceso solo desde esta computadora"
        )
        sqlite_desc.setStyleSheet("color: #666; margin-left: 20px; margin-bottom: 10px;")
        options_layout.addWidget(sqlite_desc)
        
        # Opción: Firebase
        self.firebase_radio = QRadioButton("Firebase (Nube)")
        self.firebase_radio.setStyleSheet("font-weight: bold; font-size: 12px;")
        options_layout.addWidget(self.firebase_radio)
        
        firebase_desc = QLabel(
            "  ✓ Acceso desde cualquier lugar\n"
            "  ✓ Multi-usuario (varios usuarios simultáneos)\n"
            "  ✓ Backup automático por Google\n"
            "  ✗ Requiere conexión a internet"
        )
        firebase_desc.setStyleSheet("color: #666; margin-left: 20px; margin-bottom: 10px;")
        options_layout.addWidget(firebase_desc)
        
        # Opción: AUTO (recomendado)
        self.auto_radio = QRadioButton("AUTO - Automático (Recomendado)")
        self.auto_radio.setStyleSheet("font-weight: bold; font-size: 12px; color: #2196F3;")
        options_layout.addWidget(self.auto_radio)
        
        auto_desc = QLabel(
            "  ✓ Usa Firebase cuando hay internet\n"
            "  ✓ Usa SQLite cuando no hay conexión\n"
            "  ✓ Lo mejor de ambos mundos\n"
            "  ✓ Cambio automático según disponibilidad"
        )
        auto_desc.setStyleSheet("color: #2196F3; margin-left: 20px; margin-bottom: 10px;")
        options_layout.addWidget(auto_desc)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Checkbox: Recordar preferencia
        self.remember_checkbox = QCheckBox("Recordar mi preferencia (guardar en configuración)")
        self.remember_checkbox.setChecked(True)  # Por defecto marcado
        self.remember_checkbox.setStyleSheet("margin-top: 10px; font-size: 11px;")
        layout.addWidget(self.remember_checkbox)
        
        # Nota informativa
        info_label = QLabel(
            "💡 Puede cambiar el modo en cualquier momento desde el botón ⚙ "
            "en la barra de estado."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: #666; font-size: 10px; margin-top: 10px; "
            "padding: 8px; background-color: #F5F5F5; border-radius: 4px;"
        )
        layout.addWidget(info_label)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Aceptar")
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet(
            "background-color: #2196F3; color: white; "
            "padding: 6px 20px; font-weight: bold;"
        )
        ok_btn.clicked.connect(self._on_accept)
        buttons_layout.addWidget(ok_btn)
        
        layout.addLayout(buttons_layout)
        
        # Conectar señales
        self.sqlite_radio.toggled.connect(lambda: self._on_mode_selected("SQLITE"))
        self.firebase_radio.toggled.connect(lambda: self._on_mode_selected("FIREBASE"))
        self.auto_radio.toggled.connect(lambda: self._on_mode_selected("AUTO"))
        
        # Seleccionar modo actual
        self._set_current_mode(self.selected_mode)
    
    def _set_current_mode(self, mode: str):
        """Establece el modo seleccionado actualmente."""
        mode = mode.upper()
        if mode == "SQLITE":
            self.sqlite_radio.setChecked(True)
        elif mode == "FIREBASE":
            self.firebase_radio.setChecked(True)
        else:  # AUTO
            self.auto_radio.setChecked(True)
    
    def _on_mode_selected(self, mode: str):
        """Callback cuando se selecciona un modo."""
        if self.sender().isChecked():
            self.selected_mode = mode
    
    def _on_accept(self):
        """Callback cuando se acepta el diálogo."""
        self.remember_choice = self.remember_checkbox.isChecked()
        self.accept()
    
    def get_selected_mode(self) -> str:
        """
        Obtiene el modo seleccionado.
        
        Returns:
            str: "SQLITE", "FIREBASE", o "AUTO"
        """
        return self.selected_mode
    
    def should_remember(self) -> bool:
        """
        Indica si se debe recordar la preferencia.
        
        Returns:
            bool: True si se debe guardar en configuración
        """
        return self.remember_choice


def show_connection_mode_dialog(current_mode: str = "AUTO", parent=None) -> Optional[str]:
    """
    Muestra el diálogo de selección de modo y retorna el modo seleccionado.
    
    Args:
        current_mode: Modo actual ("SQLITE", "FIREBASE", "AUTO")
        parent: Widget padre
        
    Returns:
        Modo seleccionado si se aceptó, None si se canceló
    """
    dialog = ConnectionModeDialog(current_mode, parent)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        mode = dialog.get_selected_mode()
        
        # Guardar en configuración si se marcó "recordar"
        if dialog.should_remember():
            try:
                from config_facot import set_connection_mode
                set_connection_mode(mode)
                print(f"[CONFIG] Modo de conexión guardado: {mode}")
            except Exception as e:
                print(f"[CONFIG] Error guardando preferencia: {e}")
        
        return mode
    
    return None
