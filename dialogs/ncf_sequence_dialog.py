from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from constants import NCF_CATEGORY_DEFAULT_PREFIX

try:
    from PyQt6.QtWidgets import QPlainTextEdit
except ImportError:  # pragma: no cover - PyQt6 siempre disponible en runtime
    QPlainTextEdit = None  # type: ignore


class NCFSequenceDialog(QDialog):
    """Diálogo para administrar prefijos y secuencias de NCF por empresa."""

    def __init__(
        self,
        logic,
        companies: Optional[List[Dict[str, Any]]] = None,
        current_company_id: Optional[int] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.logic = logic
        self.setWindowTitle("Configurar Secuencias de NCF")
        self.resize(760, 520)

        self._categories = sorted({key.upper() for key in NCF_CATEGORY_DEFAULT_PREFIX.keys()})
        self._companies = companies[:] if companies else []
        self._build_ui()
        self._load_companies(current_company_id)
        self._refresh_table()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Selección de empresa
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Empresa:"))
        self.company_combo = QComboBox()
        selector_row.addWidget(self.company_combo, stretch=1)
        layout.addLayout(selector_row)
        self.company_combo.currentIndexChanged.connect(self._refresh_table)

        # Tabla de configuraciones
        self.sequence_table = QTableWidget(0, 6, self)
        self.sequence_table.setHorizontalHeaderLabels([
            "Tipo / Comprobante",
            "Prefijo",
            "Próximo NCF",
            "Último asignado",
            "Vigente desde",
            "Estado",
        ])
        header = self.sequence_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, header.ResizeMode.ResizeToContents)
        layout.addWidget(self.sequence_table, stretch=1)

        # Botonera
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Agregar configuración")
        self.btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(self.btn_add)

        self.btn_edit = QPushButton("Editar")
        self.btn_edit.clicked.connect(self._on_edit)
        btn_row.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self.btn_delete)

        btn_row.addStretch(1)
        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self._refresh_table)
        btn_row.addWidget(self.btn_refresh)

        layout.addLayout(btn_row)

        self.info_label = QLabel(
            "Configure aquí los prefijos actuales y futuros por empresa."
        )
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

    def _load_companies(self, current_company_id: Optional[int]) -> None:
        if not self._companies and hasattr(self.logic, "get_all_companies"):
            try:
                self._companies = self.logic.get_all_companies()
            except Exception:
                self._companies = []

        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        for comp in self._companies:
            name = str(comp.get("name") or comp.get("nombre") or "Empresa")
            self.company_combo.addItem(name, comp)
        self.company_combo.blockSignals(False)

        if current_company_id is not None:
            for idx, comp in enumerate(self._companies):
                try:
                    cid = int(comp.get("id"))
                except Exception:
                    continue
                if cid == current_company_id:
                    self.company_combo.setCurrentIndex(idx)
                    break

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _current_company(self) -> Optional[Dict[str, Any]]:
        data = self.company_combo.currentData()
        if isinstance(data, dict):
            return data
        idx = self.company_combo.currentIndex()
        if idx < 0 or idx >= len(self._companies):
            return None
        return self._companies[idx]

    def _current_company_id(self) -> Optional[int]:
        comp = self._current_company()
        if not comp:
            return None
        try:
            return int(comp.get("id"))
        except Exception:
            return None

    def _refresh_table(self) -> None:
        company_id = self._current_company_id()
        if company_id is None:
            self.sequence_table.setRowCount(0)
            return

        sequences: List[Dict[str, Any]] = []
        if hasattr(self.logic, "list_ncf_sequence_configs"):
            try:
                sequences = self.logic.list_ncf_sequence_configs(company_id)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "NCF",
                    f"No se pudo recuperar la configuración de NCF:\n{exc}",
                )
                sequences = []
        else:
            QMessageBox.warning(
                self,
                "NCF",
                "El backend actual no soporta configuración de secuencias.",
            )
            sequences = []

        today = datetime.date.today().isoformat()
        self.sequence_table.setRowCount(len(sequences))
        for row, seq in enumerate(sequences):
            category = str(seq.get("category") or "").upper()
            prefix = str(seq.get("prefix") or "")
            next_ncf = str(seq.get("next_ncf") or "")
            last_assigned = str(seq.get("last_assigned") or "")
            effective_from = str(seq.get("effective_from") or "")
            is_active = bool(seq.get("is_active"))
            state = "Actual" if is_active else ("Futura" if effective_from > today else "Histórica")

            values = [category, prefix, next_ncf, last_assigned, effective_from, state]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, seq.get("id"))
                if seq.get("notes"):
                    item.setToolTip(str(seq.get("notes")))
                self.sequence_table.setItem(row, col, item)

        self.sequence_table.resizeRowsToContents()

    def _selected_config_id(self) -> Optional[Any]:
        current = self.sequence_table.currentItem()
        if not current:
            return None
        return current.data(Qt.ItemDataRole.UserRole)

    def _selected_config(self) -> Optional[Dict[str, Any]]:
        config_id = self._selected_config_id()
        if config_id is None:
            return None
        company_id = self._current_company_id()
        if company_id is None:
            return None
        if not hasattr(self.logic, "list_ncf_sequence_configs"):
            return None
        try:
            configs = self.logic.list_ncf_sequence_configs(company_id)
        except Exception:
            return None
        for cfg in configs:
            if str(cfg.get("id")) == str(config_id):
                return cfg
        return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_add(self) -> None:
        company_id = self._current_company_id()
        if company_id is None:
            QMessageBox.warning(self, "NCF", "Seleccione primero una empresa.")
            return

        dialog = _NCFSequenceFormDialog(
            logic=self.logic,
            categories=self._categories,
            company_id=company_id,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            payload = dialog.get_data()
            self._save_config(company_id, payload)

    def _on_edit(self) -> None:
        company_id = self._current_company_id()
        if company_id is None:
            QMessageBox.warning(self, "NCF", "Seleccione primero una empresa.")
            return
        config = self._selected_config()
        if not config:
            QMessageBox.information(self, "NCF", "Seleccione una configuración para editar.")
            return

        dialog = _NCFSequenceFormDialog(
            logic=self.logic,
            categories=self._categories,
            company_id=company_id,
            existing=config,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            payload = dialog.get_data()
            self._save_config(company_id, payload)

    def _on_delete(self) -> None:
        company_id = self._current_company_id()
        if company_id is None:
            QMessageBox.warning(self, "NCF", "Seleccione primero una empresa.")
            return
        config_id = self._selected_config_id()
        if config_id is None:
            QMessageBox.information(self, "NCF", "Seleccione una configuración para eliminar.")
            return

        if QMessageBox.question(
            self,
            "Confirmar",
            "¿Desea eliminar la configuración seleccionada?",
        ) != QMessageBox.StandardButton.Yes:
            return

        if hasattr(self.logic, "delete_ncf_sequence_config"):
            try:
                self.logic.delete_ncf_sequence_config(company_id, config_id)
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "NCF",
                    f"No se pudo eliminar la configuración seleccionada:\n{exc}",
                )
        self._refresh_table()

    def _save_config(self, company_id: int, payload: Dict[str, Any]) -> None:
        if not hasattr(self.logic, "save_ncf_sequence_config"):
            QMessageBox.warning(
                self,
                "NCF",
                "El backend actual no soporta guardar configuraciones de NCF.",
            )
            return
        try:
            self.logic.save_ncf_sequence_config(company_id, payload)
            self._refresh_table()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "NCF",
                f"No se pudo guardar la configuración:\n{exc}",
            )


class _NCFSequenceFormDialog(QDialog):
    """Formulario para crear/editar una configuración de secuencia NCF."""

    def __init__(
        self,
        logic,
        categories: List[str],
        company_id: int,
        existing: Optional[Dict[str, Any]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.logic = logic
        self.company_id = company_id
        self.categories = categories
        self._existing = existing or {}
        self._result: Dict[str, Any] = {}

        self.setWindowTitle("Configurar secuencia NCF")
        self.resize(420, 360)
        self._build_ui()
        self._populate_defaults()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        for cat in self.categories:
            self.category_combo.addItem(cat)
        form.addRow("Tipo / Comprobante", self.category_combo)

        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("Ej: B01")
        form.addRow("Prefijo", self.prefix_edit)

        self.last_ncf_edit = QLineEdit()
        self.last_ncf_edit.setPlaceholderText("Ej: B0100000001")
        form.addRow("Último NCF emitido", self.last_ncf_edit)

        self.next_sequence_edit = QLineEdit()
        self.next_sequence_edit.setPlaceholderText("Próximo correlativo (solo números)")
        form.addRow("Próximo correlativo", self.next_sequence_edit)

        self.effective_from_edit = QDateEdit(calendarPopup=True)
        self.effective_from_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Vigente desde", self.effective_from_edit)

        if QPlainTextEdit:
            self.notes_edit = QPlainTextEdit()
            self.notes_edit.setPlaceholderText("Notas u observaciones opcionales")
            form.addRow("Notas", self.notes_edit)
        else:
            self.notes_edit = QLineEdit()
            form.addRow("Notas", self.notes_edit)

        layout.addLayout(form)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.last_ncf_edit.editingFinished.connect(self._sync_sequence_from_last)

    def _populate_defaults(self) -> None:
        today = QDate.currentDate()
        self.effective_from_edit.setDate(today)

        if not self._existing:
            # Prefijo por defecto al cambiar de categoría
            self._on_category_changed(self.category_combo.currentText())
            return

        category = str(self._existing.get("category") or "").upper()
        prefix = str(self._existing.get("prefix") or "")
        last_assigned = str(self._existing.get("last_assigned") or "")
        next_sequence = str(self._existing.get("next_sequence") or "")
        effective_from = str(self._existing.get("effective_from") or "")
        notes = str(self._existing.get("notes") or "")

        if category:
            idx = self.category_combo.findText(category, Qt.MatchFlag.MatchFixedString)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setCurrentText(category)
        if prefix:
            self.prefix_edit.setText(prefix)
        if last_assigned:
            self.last_ncf_edit.setText(last_assigned)
        if next_sequence:
            self.next_sequence_edit.setText(str(next_sequence))
        if effective_from:
            try:
                year, month, day = [int(part) for part in effective_from[:10].split("-")]
                self.effective_from_edit.setDate(QDate(year, month, day))
            except Exception:
                self.effective_from_edit.setDate(today)
        if notes:
            if isinstance(self.notes_edit, QPlainTextEdit):
                self.notes_edit.setPlainText(notes)
            else:
                self.notes_edit.setText(notes)

    def _on_category_changed(self, text: str) -> None:
        current_prefix = (self.prefix_edit.text() or "").strip()
        if current_prefix:
            return
        default = NCF_CATEGORY_DEFAULT_PREFIX.get(text.upper())
        if default:
            self.prefix_edit.setText(default)

    def _sync_sequence_from_last(self) -> None:
        ncf = (self.last_ncf_edit.text() or "").strip().upper()
        if not ncf:
            return
        prefix = (self.prefix_edit.text() or "").strip().upper()
        if prefix and not ncf.startswith(prefix):
            # Actualiza prefijo automáticamente
            self.prefix_edit.setText(ncf[:3])
            prefix = ncf[:3]
        seq = self._extract_sequence(ncf)
        if seq is not None and seq > 0:
            self.next_sequence_edit.setText(str(seq + 1))

    def _extract_sequence(self, ncf: str) -> Optional[int]:
        if len(ncf) < 4:
            return None
        digits = ncf[3:]
        if not digits.isdigit():
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    def get_data(self) -> Dict[str, Any]:
        return self._result

    def accept(self) -> None:  # type: ignore[override]
        try:
            payload = self._build_payload()
        except ValueError as exc:
            QMessageBox.warning(self, "NCF", str(exc))
            return
        self._result = payload
        super().accept()

    def _build_payload(self) -> Dict[str, Any]:
        category = (self.category_combo.currentText() or "").strip().upper()
        if not category:
            raise ValueError("Debe especificar el tipo o categoría del comprobante.")

        prefix = (self.prefix_edit.text() or "").strip().upper()
        if len(prefix) != 3 or not prefix[0].isalpha() or not prefix[1:].isdigit():
            raise ValueError("El prefijo debe tener el formato LETRA + 2 dígitos (ej. B01, E31).")

        last_assigned = (self.last_ncf_edit.text() or "").strip().upper()
        next_seq_text = (self.next_sequence_edit.text() or "").strip()

        if last_assigned and len(last_assigned) < 4:
            raise ValueError("El último NCF debe contener prefijo y correlativo completo.")
        if last_assigned and not last_assigned.startswith(prefix):
            raise ValueError("El último NCF debe coincidir con el prefijo configurado.")
        if last_assigned and hasattr(self.logic, "validate_ncf"):
            if not self.logic.validate_ncf(last_assigned):
                raise ValueError("El último NCF ingresado no tiene un formato válido.")

        next_sequence: Optional[int] = None
        if next_seq_text:
            if not next_seq_text.isdigit():
                raise ValueError("El próximo correlativo debe ser un número válido.")
            next_sequence = int(next_seq_text)
            if next_sequence <= 0:
                raise ValueError("El próximo correlativo debe ser mayor a cero.")

        if not next_sequence:
            seq = self._extract_sequence(last_assigned)
            if seq is not None:
                next_sequence = seq + 1

        effective_qdate = self.effective_from_edit.date()
        effective_from = f"{effective_qdate.year():04d}-{effective_qdate.month():02d}-{effective_qdate.day():02d}"

        notes_value: str = ""
        if isinstance(self.notes_edit, QPlainTextEdit):
            notes_value = self.notes_edit.toPlainText().strip()
        elif isinstance(self.notes_edit, QLineEdit):
            notes_value = self.notes_edit.text().strip()

        payload: Dict[str, Any] = {
            "category": category,
            "prefix": prefix,
            "effective_from": effective_from,
            "notes": notes_value,
        }
        if last_assigned:
            payload["last_assigned"] = last_assigned
        if next_sequence:
            payload["next_sequence"] = next_sequence
        if self._existing.get("id"):
            payload["id"] = self._existing.get("id")
        return payload
