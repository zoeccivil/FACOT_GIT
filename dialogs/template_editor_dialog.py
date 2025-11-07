
from __future__ import annotations

import os
from typing import Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QColorDialog, QFileDialog, QMessageBox, QTextEdit
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from utils.template_manager import load_template, save_template, copy_logo_to_company_dir

class TemplateEditorDialog(QDialog):
    def __init__(self, company_id: int, parent=None):
        super().__init__(parent)
        self.company_id = company_id
        self.template = load_template(company_id)
        self.setWindowTitle(f"Editor de Plantilla - Empresa ID: {company_id}")
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        v = QVBoxLayout(self)
        # logo selector
        logo_row = QHBoxLayout()
        self.logo_edit = QLineEdit()
        btn_logo = QPushButton("Seleccionar logo")
        btn_logo.clicked.connect(self._pick_logo)
        logo_row.addWidget(QLabel("Logo:"))
        logo_row.addWidget(self.logo_edit)
        logo_row.addWidget(btn_logo)
        v.addLayout(logo_row)

        # header lines
        self.header1 = QLineEdit()
        self.header2 = QLineEdit()
        self.header3 = QLineEdit()
        v.addWidget(QLabel("Header (líneas)"))
        v.addWidget(self.header1)
        v.addWidget(self.header2)
        v.addWidget(self.header3)

        # footer
        v.addWidget(QLabel("Footer"))
        self.footer_edit = QTextEdit()
        self.footer_edit.setFixedHeight(80)
        v.addWidget(self.footer_edit)

        # color picker
        color_row = QHBoxLayout()
        self.color_edit = QLineEdit()
        btn_color = QPushButton("Elegir color primario")
        btn_color.clicked.connect(self._pick_color)
        color_row.addWidget(QLabel("Color (hex):"))
        color_row.addWidget(self.color_edit)
        color_row.addWidget(btn_color)
        v.addLayout(color_row)

        # botones
        row = QHBoxLayout()
        btn_save = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(btn_save)
        row.addWidget(btn_cancel)
        v.addLayout(row)

    def _load_values(self):
        tpl = self.template or {}
        # logo path is relative to data root; show as-is
        self.logo_edit.setText(tpl.get("logo_path", ""))
        hl = tpl.get("header_lines", ["", "", ""])
        self.header1.setText(hl[0] if len(hl) > 0 else "")
        self.header2.setText(hl[1] if len(hl) > 1 else "")
        self.header3.setText(hl[2] if len(hl) > 2 else "")
        self.footer_edit.setPlainText("\n".join(tpl.get("footer_lines", [])))
        self.color_edit.setText(tpl.get("primary_color", "#1f4e79"))

    def _pick_logo(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen del logo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not fn:
            return
        # Copiar la imagen al directorio data/company_{id}/
        rel = copy_logo_to_company_dir(fn, self.company_id)
        if rel:
            # Guardamos la ruta relativa (a data root), por ejemplo "company_1/logo.png"
            self.logo_edit.setText(rel)
            QMessageBox.information(self, "Logo", f"Logo copiado a: {rel}")
        else:
            QMessageBox.warning(self, "Logo", "No se pudo copiar el logo. Se usará la ruta original.")
            self.logo_edit.setText(fn)

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self.color_edit.text() or "#1f4e79"), self)
        if col.isValid():
            self.color_edit.setText(col.name())

    def _on_save(self):
        tpl = {
            "logo_path": self.logo_edit.text().strip(),
            "show_logo": bool(self.logo_edit.text().strip()),
            "header_lines": [self.header1.text().strip(), self.header2.text().strip(), self.header3.text().strip()],
            "footer_lines": [l for l in self.footer_edit.toPlainText().splitlines() if l.strip()],
            "primary_color": self.color_edit.text().strip() or "#1f4e79",
        }
        try:
            save_template(self.company_id, tpl)
            QMessageBox.information(self, "Plantilla", "Plantilla guardada.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la plantilla:\n{e}")