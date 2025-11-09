"""
Diálogo de Configuración de Secuencias NCF
Permite configurar secuencias por empresa y tipo de comprobante,
con soporte para cambio de nomenclatura 2026
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QGroupBox, QCheckBox,
    QHeaderView, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Tipos de comprobantes según DGII (prefijo → nombre)
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
    Configura secuencias NCF por empresa y tipo, persistiendo en ncf_sequences.
    """

    def __init__(self, logic_or_parent=None, parent=None):
        """
        Soporta:
        - NCFConfigDialog(logic, parent)
        - NCFConfigDialog(parent) => extrae logic de parent.hybrid_logic/logic/data_access
        """
        logic = None
        real_parent = parent

        if real_parent is None and isinstance(logic_or_parent, QWidget) and not hasattr(logic_or_parent, "get_all_companies"):
            real_parent = logic_or_parent
            if hasattr(real_parent, "hybrid_logic"):
                logic = getattr(real_parent, "hybrid_logic")
            elif hasattr(real_parent, "logic"):
                logic = getattr(real_parent, "logic")
            elif hasattr(real_parent, "data_access"):
                logic = getattr(real_parent, "data_access")
        else:
            logic = logic_or_parent

        super().__init__(real_parent)
        self.logic = logic
        self.current_company_id = None
        self.ncf_data = {}  # {prefix: {name, seq, new_prefix, activation_date, enabled}}

        if not self.logic:
            raise RuntimeError("NCFConfigDialog: No se pudo resolver el backend de datos (logic).")

        self.setWindowTitle("Configuración de Secuencias NCF")
        self.setModal(True)
        self.resize(900, 700)

        self._init_ui()
        self._load_companies()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Configuración de Secuencias NCF")
        title_font = QFont(); title_font.setPointSize(14); title_font.setBold(True)
        title.setFont(title_font); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        company_layout = QHBoxLayout()
        company_layout.addWidget(QLabel("Empresa:"))
        self.company_combo = QComboBox()
        self.company_combo.currentIndexChanged.connect(self._on_company_changed)
        company_layout.addWidget(self.company_combo)
        company_layout.addStretch()
        layout.addLayout(company_layout)

        # Grupo 1: Secuencias actuales
        group1 = QGroupBox("Secuencias Actuales por Tipo de Comprobante")
        group1_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tipo Comprobante", "Prefijo Actual", "Última Secuencia", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        group1_layout.addWidget(self.table)

        buttons_layout = QHBoxLayout()
        self.edit_btn = QPushButton("✏️ Editar Secuencia"); self.edit_btn.clicked.connect(self._edit_sequence)
        buttons_layout.addWidget(self.edit_btn)
        self.reset_btn = QPushButton("🔄 Resetear a Cero"); self.reset_btn.clicked.connect(self._reset_sequence)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addStretch()
        group1_layout.addLayout(buttons_layout)

        group1.setLayout(group1_layout)
        layout.addWidget(group1)

        # Grupo 2: Cambio 2026 (placeholder visual)
        group2 = QGroupBox("Configuración Cambio de Nomenclatura 2026")
        group2_layout = QVBoxLayout()
        info_label = QLabel(
            "⚠️ A partir de 2026 podrían cambiar prefijos según normativa DGII.\n"
            "Este módulo permite preconfigurar nuevos prefijos y fecha de activación."
        )
        info_label.setWordWrap(True)
        group2_layout.addWidget(info_label)

        self.table_2026 = QTableWidget()
        self.table_2026.setColumnCount(5)
        self.table_2026.setHorizontalHeaderLabels(["Tipo", "Prefijo Actual", "Nuevo Prefijo 2026", "Fecha Activación", "Habilitado"])
        self.table_2026.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        group2_layout.addWidget(self.table_2026)

        self.auto_switch_check = QCheckBox("✅ Activar automáticamente en fecha configurada")
        self.auto_switch_check.setChecked(True)
        group2_layout.addWidget(self.auto_switch_check)

        group2.setLayout(group2_layout)
        layout.addWidget(group2)

        # Botones inferiores
        dialog_buttons = QHBoxLayout(); dialog_buttons.addStretch()
        save_btn = QPushButton("💾 Guardar"); save_btn.clicked.connect(self._save_config)
        dialog_buttons.addWidget(save_btn)
        cancel_btn = QPushButton("❌ Cancelar"); cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_btn)
        layout.addLayout(dialog_buttons)

    def _load_companies(self):
        companies = []
        for m in ("get_all_companies", "list_companies", "get_companies"):
            if hasattr(self.logic, m):
                try:
                    companies = getattr(self.logic, m)() or []
                    break
                except Exception as e:
                    print(f"[NCF] Error llamando {m}: {e}")
        if not companies:
            print("[NCF] No se encontraron empresas.")

        self.company_combo.clear()
        for c in companies:
            cid = c.get('id') or c.get('company_id') or c.get('pk')
            name = c.get('name') or c.get('nombre') or str(cid)
            if cid is not None:
                self.company_combo.addItem(str(name), int(cid))

        if self.company_combo.count() > 0:
            self._on_company_changed(0)

    def _on_company_changed(self, index):
        if index < 0:
            return
        self.current_company_id = self.company_combo.itemData(index)
        self._load_ncf_data()
        self._populate_tables()

    def _load_ncf_data(self):
        """
        Carga desde ncf_sequences si está disponible; si no, siembra con máximo histórico.
        """
        if not self.current_company_id:
            return
        self.ncf_data = {}
        for prefix, name in NCF_TYPES.items():
            try:
                last_seq = 0
                if hasattr(self.logic, "get_ncf_last_seq"):
                    last_seq = int(self.logic.get_ncf_last_seq(int(self.current_company_id), prefix))
                elif hasattr(self.logic, "_max_seq_for_prefix"):
                    last_seq = int(self.logic._max_seq_for_prefix(int(self.current_company_id), prefix))
                self.ncf_data[prefix] = {
                    "name": name,
                    "seq": last_seq,
                    "new_prefix": NCF_2026_MAPPING.get(prefix, prefix),
                    "activation_date": "2026-07-01",
                    "enabled": prefix != "E31"
                }
            except Exception as e:
                print(f"[NCF] Error loading sequence for {prefix}: {e}")
                self.ncf_data[prefix] = {
                    "name": name, "seq": 0,
                    "new_prefix": NCF_2026_MAPPING.get(prefix, prefix),
                    "activation_date": "2026-07-01",
                    "enabled": prefix != "E31"
                }

    def _populate_tables(self):
        # Tabla 1
        self.table.setRowCount(0)
        for prefix in sorted(NCF_TYPES.keys()):
            data = self.ncf_data.get(prefix, {})
            row = self.table.rowCount(); self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(data.get('name', NCF_TYPES[prefix])))
            self.table.setItem(row, 1, QTableWidgetItem(prefix))
            pad_len = 11 if prefix.startswith('E') else 8
            seq_str = str(data.get('seq', 0)).zfill(pad_len)
            self.table.setItem(row, 2, QTableWidgetItem(seq_str))
            edit_cell_btn = QPushButton("📝"); edit_cell_btn.setToolTip(f"Editar secuencia de {prefix}")
            edit_cell_btn.clicked.connect(lambda _c=False, p=prefix: self._edit_specific_sequence(p))
            self.table.setCellWidget(row, 3, edit_cell_btn)

        # Tabla 2 (placeholder de configuración 2026)
        self.table_2026.setRowCount(0)
        for prefix in sorted(NCF_TYPES.keys()):
            data = self.ncf_data.get(prefix, {})
            row = self.table_2026.rowCount(); self.table_2026.insertRow(row)
            self.table_2026.setItem(row, 0, QTableWidgetItem(NCF_TYPES[prefix]))
            self.table_2026.setItem(row, 1, QTableWidgetItem(prefix))
            self.table_2026.setItem(row, 2, QTableWidgetItem(data.get('new_prefix', prefix)))
            self.table_2026.setItem(row, 3, QTableWidgetItem(data.get('activation_date', '2026-07-01')))
            chk = QCheckBox(); chk.setChecked(data.get('enabled', False)); chk.setProperty('prefix', prefix)
            self.table_2026.setCellWidget(row, 4, chk)

    def _edit_sequence(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Advertencia", "Seleccione una fila para editar"); return
        prefix_item = self.table.item(row, 1)
        if not prefix_item: return
        self._edit_specific_sequence(prefix_item.text())

    def _edit_specific_sequence(self, prefix):
        from PyQt6.QtWidgets import QInputDialog
        current_seq = int(self.ncf_data.get(prefix, {}).get('seq', 0))
        pad_len = 11 if prefix.startswith('E') else 8
        new_seq, ok = QInputDialog.getInt(
            self, "Editar Secuencia",
            f"Ingrese la ÚLTIMA secuencia usada para {prefix} ({NCF_TYPES[prefix]}):",
            value=current_seq, min=0, max=10**pad_len - 1
        )
        if ok:
            self.ncf_data[prefix]['seq'] = int(new_seq)
            self._populate_tables()

    def _reset_sequence(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Advertencia", "Seleccione una fila para resetear"); return
        prefix_item = self.table.item(row, 1)
        if not prefix_item: return
        prefix = prefix_item.text()
        reply = QMessageBox.question(
            self, "Confirmar Reseteo",
            f"¿Resetear la secuencia de {prefix} ({NCF_TYPES[prefix]}) a cero?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ncf_data[prefix]['seq'] = 0
            self._populate_tables()

    def _save_config(self):
        if not self.current_company_id:
            QMessageBox.warning(self, "Error", "No hay empresa seleccionada"); return
        try:
            # Actualizar meta de 2026 desde tabla 2026 (opcional, no persiste aún)
            for row in range(self.table_2026.rowCount()):
                prefix_item = self.table_2026.item(row, 1)
                if not prefix_item: continue
                prefix = prefix_item.text()
                new_prefix_item = self.table_2026.item(row, 2)
                date_item = self.table_2026.item(row, 3)
                chk = self.table_2026.cellWidget(row, 4)
                if prefix in self.ncf_data:
                    self.ncf_data[prefix]['new_prefix'] = new_prefix_item.text() if new_prefix_item else prefix
                    self.ncf_data[prefix]['activation_date'] = date_item.text() if date_item else '2026-07-01'
                    self.ncf_data[prefix]['enabled'] = chk.isChecked() if chk else False

            # Persistir last_seq en ncf_sequences
            self._persist_ncf_config()
            QMessageBox.information(self, "Éxito", f"Secuencias guardadas para {self.company_combo.currentText()}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar configuración:\n{str(e)}")

    def _persist_ncf_config(self):
        if not hasattr(self.logic, "set_ncf_last_seq"):
            print("[NCF] Backend no soporta persistencia de secuencias (set_ncf_last_seq)."); return
        for prefix, data in self.ncf_data.items():
            try:
                last_seq_user = int(data.get("seq", 0))
                self.logic.set_ncf_last_seq(int(self.current_company_id), prefix, last_seq_user)
            except Exception as e:
                print(f"[NCF] Error guardando secuencia {prefix}: {e}")


def show_ncf_config_dialog(logic, parent=None):
    dialog = NCFConfigDialog(logic, parent)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted