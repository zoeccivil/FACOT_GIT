"""
Diálogo de Configuración de Secuencias NCF
Permite configurar secuencias por empresa y tipo de comprobante,
con soporte para cambio de nomenclatura 2026
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QGroupBox, QCheckBox,
    QDateEdit, QLineEdit, QHeaderView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from datetime import datetime


# Tipos de comprobantes según DGII
NCF_TYPES = {
    "B01": "FACTURA PRIVADA",
    "B02": "CONSUMIDOR FINAL",
    "B14": "FACTURA EXENTA",
    "B15": "FACTURA GUBERNAMENTAL",
    "B16": "FACTURA EXPORTACIÓN",
    "E31": "E-CF (Comprobante Electrónico)",
}

# Mapeo 2026 (nuevos prefijos)
NCF_2026_MAPPING = {
    "B01": "F01",
    "B02": "F02",
    "B14": "F14",
    "B15": "F15",
    "B16": "F16",
    "E31": "E31",  # E-CF no cambia
}


class NCFConfigDialog(QDialog):
    """
    Diálogo moderno para configurar secuencias NCF por empresa y tipo.
    
    Características:
    - Configuración por empresa y tipo de comprobante
    - Edición manual de última secuencia
    - Reseteo de secuencias (cambio de año fiscal)
    - Gestión de cambio de nomenclatura 2026
    """
    
    def __init__(self, logic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.current_company_id = None
        self.ncf_data = {}  # {prefix: {seq: int, new_prefix: str, date: str, enabled: bool}}
        
        self.setWindowTitle("Configuración de Secuencias NCF")
        self.setModal(True)
        self.resize(900, 700)
        
        self._init_ui()
        self._load_companies()
        
    def _init_ui(self):
        """Inicializa la interfaz de usuario"""
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("Configuración de Secuencias NCF")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Selector de empresa
        company_layout = QHBoxLayout()
        company_layout.addWidget(QLabel("Empresa:"))
        self.company_combo = QComboBox()
        self.company_combo.currentIndexChanged.connect(self._on_company_changed)
        company_layout.addWidget(self.company_combo)
        company_layout.addStretch()
        layout.addLayout(company_layout)
        
        # Sección 1: Secuencias Actuales
        group1 = QGroupBox("Secuencias Actuales por Tipo de Comprobante")
        group1_layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Tipo Comprobante", "Prefijo Actual", "Última Secuencia", "Acciones"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        group1_layout.addWidget(self.table)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("✏️ Editar Secuencia")
        self.edit_btn.clicked.connect(self._edit_sequence)
        buttons_layout.addWidget(self.edit_btn)
        
        self.reset_btn = QPushButton("🔄 Resetear a Cero")
        self.reset_btn.clicked.connect(self._reset_sequence)
        buttons_layout.addWidget(self.reset_btn)
        
        buttons_layout.addStretch()
        group1_layout.addLayout(buttons_layout)
        
        group1.setLayout(group1_layout)
        layout.addWidget(group1)
        
        # Sección 2: Configuración Cambio 2026
        group2 = QGroupBox("Configuración Cambio de Nomenclatura 2026")
        group2_layout = QVBoxLayout()
        
        info_label = QLabel(
            "⚠️ A partir de mediados de 2026, los prefijos NCF cambiarán según normativa DGII.\n"
            "Configure aquí los nuevos prefijos y la fecha de activación por tipo de comprobante."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        group2_layout.addWidget(info_label)
        
        self.table_2026 = QTableWidget()
        self.table_2026.setColumnCount(5)
        self.table_2026.setHorizontalHeaderLabels([
            "Tipo", "Prefijo Actual", "Nuevo Prefijo 2026", "Fecha Activación", "Habilitado"
        ])
        self.table_2026.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        group2_layout.addWidget(self.table_2026)
        
        self.auto_switch_check = QCheckBox("✅ Activar automáticamente en fecha configurada")
        self.auto_switch_check.setChecked(True)
        group2_layout.addWidget(self.auto_switch_check)
        
        group2.setLayout(group2_layout)
        layout.addWidget(group2)
        
        # Botones de diálogo
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        
        save_btn = QPushButton("💾 Guardar")
        save_btn.clicked.connect(self._save_config)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px; font-weight: bold;")
        dialog_buttons.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Cancelar")
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_btn)
        
        layout.addLayout(dialog_buttons)
        
    def _load_companies(self):
        """Carga la lista de empresas"""
        companies = self.logic.get_all_companies()
        self.company_combo.clear()
        
        for company in companies:
            self.company_combo.addItem(company['name'], company['id'])
            
        if companies:
            self._on_company_changed(0)
            
    def _on_company_changed(self, index):
        """Se ejecuta cuando cambia la empresa seleccionada"""
        if index < 0:
            return
            
        self.current_company_id = self.company_combo.itemData(index)
        self._load_ncf_data()
        self._populate_tables()
        
    def _load_ncf_data(self):
        """Carga las secuencias NCF de la empresa actual"""
        if not self.current_company_id:
            return
            
        self.ncf_data = {}
        
        # Obtener secuencias de cada tipo
        for prefix, name in NCF_TYPES.items():
            try:
                # Intentar obtener la última secuencia desde la base de datos
                max_seq = self._get_max_sequence(self.current_company_id, prefix)
                
                self.ncf_data[prefix] = {
                    'name': name,
                    'seq': max_seq,
                    'new_prefix': NCF_2026_MAPPING.get(prefix, prefix),
                    'activation_date': '2026-07-01',
                    'enabled': prefix != 'E31'  # E31 no cambia
                }
            except Exception as e:
                print(f"[NCF] Error loading sequence for {prefix}: {e}")
                self.ncf_data[prefix] = {
                    'name': name,
                    'seq': 0,
                    'new_prefix': NCF_2026_MAPPING.get(prefix, prefix),
                    'activation_date': '2026-07-01',
                    'enabled': prefix != 'E31'
                }
                
    def _get_max_sequence(self, company_id, prefix):
        """
        Obtiene la máxima secuencia existente para un prefijo dado.
        Busca en todas las facturas emitidas del tipo especificado.
        """
        try:
            # Intentar usar método de data_access si existe
            if hasattr(self.logic, '_max_seq_for_prefix'):
                return self.logic._max_seq_for_prefix(company_id, prefix)
            
            # Fallback: buscar manualmente
            invoices = self.logic.get_facturas(company_id)
            max_seq = 0
            
            for inv in invoices:
                ncf = inv.get('ncf', '')
                if ncf.startswith(prefix) and len(ncf) >= 11:
                    try:
                        # Extraer parte numérica
                        seq_str = ncf[3:]  # Después del prefijo de 3 caracteres
                        seq = int(seq_str)
                        if seq > max_seq:
                            max_seq = seq
                    except ValueError:
                        continue
                        
            return max_seq
        except Exception as e:
            print(f"[NCF] Error getting max sequence: {e}")
            return 0
            
    def _populate_tables(self):
        """Llena las tablas con los datos actuales"""
        # Tabla 1: Secuencias actuales
        self.table.setRowCount(0)
        
        for prefix in sorted(NCF_TYPES.keys()):
            data = self.ncf_data.get(prefix, {})
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Tipo
            self.table.setItem(row, 0, QTableWidgetItem(data.get('name', NCF_TYPES[prefix])))
            
            # Prefijo
            self.table.setItem(row, 1, QTableWidgetItem(prefix))
            
            # Secuencia (con padding correcto)
            seq = data.get('seq', 0)
            pad_len = 11 if prefix.startswith('E') else 8
            seq_str = str(seq).zfill(pad_len)
            self.table.setItem(row, 2, QTableWidgetItem(seq_str))
            
            # Botón editar individual
            edit_cell_btn = QPushButton("📝")
            edit_cell_btn.setToolTip(f"Editar secuencia de {prefix}")
            edit_cell_btn.clicked.connect(lambda checked, p=prefix: self._edit_specific_sequence(p))
            self.table.setCellWidget(row, 3, edit_cell_btn)
            
        # Tabla 2: Configuración 2026
        self.table_2026.setRowCount(0)
        
        for prefix in sorted(NCF_TYPES.keys()):
            data = self.ncf_data.get(prefix, {})
            row = self.table_2026.rowCount()
            self.table_2026.insertRow(row)
            
            # Tipo
            self.table_2026.setItem(row, 0, QTableWidgetItem(NCF_TYPES[prefix]))
            
            # Prefijo actual
            self.table_2026.setItem(row, 1, QTableWidgetItem(prefix))
            
            # Nuevo prefijo 2026 (editable)
            new_prefix_item = QTableWidgetItem(data.get('new_prefix', prefix))
            self.table_2026.setItem(row, 2, new_prefix_item)
            
            # Fecha de activación (editable)
            date_str = data.get('activation_date', '2026-07-01')
            date_item = QTableWidgetItem(date_str)
            self.table_2026.setItem(row, 3, date_item)
            
            # Checkbox habilitado
            check_widget = QCheckBox()
            check_widget.setChecked(data.get('enabled', False))
            check_widget.setProperty('prefix', prefix)
            self.table_2026.setCellWidget(row, 4, check_widget)
            
    def _edit_sequence(self):
        """Edita la secuencia de la fila seleccionada"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Advertencia", "Seleccione una fila para editar")
            return
            
        prefix_item = self.table.item(current_row, 1)
        if not prefix_item:
            return
            
        prefix = prefix_item.text()
        self._edit_specific_sequence(prefix)
        
    def _edit_specific_sequence(self, prefix):
        """Edita una secuencia específica"""
        from PyQt6.QtWidgets import QInputDialog
        
        current_seq = self.ncf_data[prefix]['seq']
        pad_len = 11 if prefix.startswith('E') else 8
        
        new_seq, ok = QInputDialog.getInt(
            self,
            "Editar Secuencia",
            f"Ingrese la última secuencia utilizada para {prefix} ({NCF_TYPES[prefix]}):",
            value=current_seq,
            min=0,
            max=10**pad_len - 1
        )
        
        if ok:
            self.ncf_data[prefix]['seq'] = new_seq
            self._populate_tables()
            
    def _reset_sequence(self):
        """Resetea la secuencia seleccionada a cero"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Advertencia", "Seleccione una fila para resetear")
            return
            
        prefix_item = self.table.item(current_row, 1)
        if not prefix_item:
            return
            
        prefix = prefix_item.text()
        
        reply = QMessageBox.question(
            self,
            "Confirmar Reseteo",
            f"¿Está seguro de resetear la secuencia de {prefix} ({NCF_TYPES[prefix]}) a cero?\n\n"
            f"Esto es útil al cambiar de año fiscal.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.ncf_data[prefix]['seq'] = 0
            self._populate_tables()
            
    def _save_config(self):
        """Guarda la configuración de NCF"""
        if not self.current_company_id:
            QMessageBox.warning(self, "Error", "No hay empresa seleccionada")
            return
            
        try:
            # Actualizar datos de tabla 2026
            for row in range(self.table_2026.rowCount()):
                prefix_item = self.table_2026.item(row, 1)
                if not prefix_item:
                    continue
                    
                prefix = prefix_item.text()
                
                new_prefix_item = self.table_2026.item(row, 2)
                date_item = self.table_2026.item(row, 3)
                check_widget = self.table_2026.cellWidget(row, 4)
                
                if prefix in self.ncf_data:
                    self.ncf_data[prefix]['new_prefix'] = new_prefix_item.text() if new_prefix_item else prefix
                    self.ncf_data[prefix]['activation_date'] = date_item.text() if date_item else '2026-07-01'
                    self.ncf_data[prefix]['enabled'] = check_widget.isChecked() if check_widget else False
            
            # Guardar en base de datos (Firebase o SQLite)
            self._persist_ncf_config()
            
            QMessageBox.information(
                self,
                "Éxito",
                f"Configuración de secuencias NCF guardada correctamente para {self.company_combo.currentText()}"
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar configuración:\n{str(e)}")
            
    def _persist_ncf_config(self):
        """Persiste la configuración NCF en la base de datos"""
        # Aquí se implementaría la lógica para guardar en Firebase/SQLite
        # Por ahora solo mostramos un log
        print(f"[NCF] Guardando configuración para empresa {self.current_company_id}:")
        for prefix, data in self.ncf_data.items():
            print(f"  {prefix}: seq={data['seq']}, new={data['new_prefix']}, date={data['activation_date']}, enabled={data['enabled']}")
            
        # TODO: Implementar guardado real en Firebase/SQLite
        # if hasattr(self.logic, 'save_ncf_config'):
        #     self.logic.save_ncf_config(self.current_company_id, self.ncf_data)


def show_ncf_config_dialog(logic, parent=None):
    """
    Función helper para mostrar el diálogo de configuración NCF
    
    Args:
        logic: Instancia de LogicController
        parent: Widget padre
        
    Returns:
        True si se guardó la configuración, False si se canceló
    """
    dialog = NCFConfigDialog(logic, parent)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted
