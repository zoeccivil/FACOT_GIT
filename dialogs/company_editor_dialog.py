from __future__ import annotations
from typing import Dict, Any, Optional
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox,
    QLabel, QPushButton, QFileDialog, QColorDialog, QWidget, QMessageBox, QDateEdit
)
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox,
    QLabel, QPushButton, QFileDialog, QColorDialog, QWidget, QMessageBox
)
from PyQt6.QtGui import QColor

from utils.asset_paths import copy_logo_to_assets, relativize_if_under_assets

class CompanyEditorDialog(QDialog):
    """
    Editor de datos de la empresa.
    Requiere que self.logic exponga:
      - get_company(company_id) -> dict
      - update_company(company_id, payload: dict) -> None
      - (opcional) update_template(company_id, tpl: dict) -> None  para guardar primary_color/logo_path relativo
    """
    def __init__(self, logic, company_id: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Editar datos de la empresa")
        self.logic = logic
        self.company_id = company_id

        self.name_edit = QLineEdit()
        self.rnc_edit = QLineEdit()
        self.address1_edit = QLineEdit()
        self.address2_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.signature_edit = QLineEdit()

        # NUEVO: fecha fija de vencimiento para facturas
        self.invoice_due_date_edit = QDateEdit()
        self.invoice_due_date_edit.setCalendarPopup(True)
        self.invoice_due_date_edit.setDisplayFormat("yyyy-MM-dd")

        self.logo_path_edit = QLineEdit()
        self.btn_browse_logo = QPushButton("Seleccionar logo…")
        self.btn_browse_logo.clicked.connect(self._pick_logo)

        self.primary_color_edit = QLineEdit()
        self.btn_pick_color = QPushButton("Color…")
        self.btn_pick_color.clicked.connect(self._pick_color)

        form = QFormLayout()
        form.addRow(QLabel("Nombre:"), self.name_edit)
        form.addRow(QLabel("RNC:"), self.rnc_edit)
        form.addRow(QLabel("Dirección 1:"), self.address1_edit)
        form.addRow(QLabel("Dirección 2:"), self.address2_edit)
        form.addRow(QLabel("Teléfono:"), self.phone_edit)
        form.addRow(QLabel("Email:"), self.email_edit)
        form.addRow(QLabel("Firma autorizada (nombre):"), self.signature_edit)
        form.addRow(QLabel("Vencimiento fijo facturas:"), self.invoice_due_date_edit)  # NUEVO

        row_logo = QWidget(); row_logo_layout = QFormLayout(row_logo)
        row_logo_layout.addRow(self.logo_path_edit, self.btn_browse_logo)
        form.addRow(QLabel("Logo (ruta absoluta o file:///):"), row_logo)

        row_color = QWidget(); row_color_layout = QFormLayout(row_color)
        row_color_layout.addRow(self.primary_color_edit, self.btn_pick_color)
        form.addRow(QLabel("Color primario (#RRGGBB):"), row_color)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

        self._load_company()

    def _load_company(self):
        try:
            data = {}
            if hasattr(self.logic, "get_company"):
                data = self.logic.get_company(self.company_id) or {}
            self.name_edit.setText(data.get("name", ""))
            self.rnc_edit.setText(data.get("rnc") or data.get("rnc_number", ""))
            self.address1_edit.setText(data.get("address") or data.get("address_line1", ""))
            self.address2_edit.setText(data.get("address_line2", ""))
            self.phone_edit.setText(data.get("phone") or data.get("telefono", ""))
            self.email_edit.setText(data.get("email") or data.get("correo", ""))
            self.signature_edit.setText(data.get("signature_name", ""))

            # Cargar vencimiento fijo si existe
            dd = (data.get("invoice_due_date") or "").strip()
            if dd:
                try:
                    y, m, d = [int(x) for x in dd[:10].split("-")]
                    self.invoice_due_date_edit.setDate(QDate(y, m, d))
                except Exception:
                    self.invoice_due_date_edit.setDate(QDate.currentDate())
            else:
                self.invoice_due_date_edit.setDate(QDate.currentDate())

            # logo_path
            self.logo_path_edit.setText(data.get("logo_path", ""))

            # Color desde plantilla si tu lógica lo centraliza allí
            if hasattr(self.logic, "get_template"):
                tpl = self.logic.get_template(self.company_id) or {}
                self.primary_color_edit.setText(tpl.get("primary_color", ""))
        except Exception as e:
            QMessageBox.warning(self, "Empresa", f"No se pudo cargar datos de la empresa:\n{e}")

    def _pick_logo(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Seleccionar logo", "", "Imágenes (*.png *.jpg *.jpeg *.svg)")
        if fn:
            try:
                # Copiar dentro de assets y guardar relativo
                rel = copy_logo_to_assets(fn, self.company_id)
                self.logo_path_edit.setText(rel)
            except Exception as e:
                QMessageBox.warning(self, "Logo", f"No se pudo copiar el logo:\n{e}")

    def _pick_color(self):
        initial = QColor(self.primary_color_edit.text() or "#0087C3")
        color = QColorDialog.getColor(initial, self, "Seleccionar color primario")
        if color.isValid():
            self.primary_color_edit.setText(color.name())

    def _save(self):
        try:
            due_qdate = self.invoice_due_date_edit.date()
            due_str = f"{due_qdate.year():04d}-{due_qdate.month():02d}-{due_qdate.day():02d}"

            payload = {
                "name": self.name_edit.text().strip(),
                "rnc": self.rnc_edit.text().strip(),
                "address_line1": self.name_edit.text().strip() and self.address1_edit.text().strip() or self.address1_edit.text().strip(),
                "address_line2": self.address2_edit.text().strip(),
                "phone": self.phone_edit.text().strip(),
                "email": self.email_edit.text().strip(),
                "signature_name": self.signature_edit.text().strip(),
                "logo_path": self.logo_path_edit.text().strip(),
                "invoice_due_date": due_str,  # NUEVO
            }
            if hasattr(self.logic, "update_company"):
                self.logic.update_company(self.company_id, payload)

            primary = self.primary_color_edit.text().strip()
            if primary and hasattr(self.logic, "update_template"):
                self.logic.update_template(self.company_id, {"primary_color": primary})
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Guardar empresa", f"No se pudo guardar:\n{e}")