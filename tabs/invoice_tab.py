from __future__ import annotations
import os
from typing import Dict, Any, List
from datetime import datetime as dt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QDateEdit, QCheckBox, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog,
    QHeaderView, QGroupBox, QGridLayout, QDialog, QInputDialog
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

from constants import NCF_TYPES, ITBIS_RATE, DEFAULT_CURRENCY

from utils.quotation_templates import (
    generate_quotation_excel as generate_invoice_excel,
    generate_quotation_pdf as generate_invoice_pdf,
)

from dialogs.item_picker_dialog import ItemPickerDialog
from dialogs.template_editor_dialog import TemplateEditorDialog

from utils.template_integration import (
    export_invoice_excel_with_template,
    export_invoice_pdf_with_template,
)

try:
    from utils.template_manager import load_template, get_data_root
except Exception:
    def load_template(company_id: int):
        return {}
    def get_data_root():
        return os.getcwd()

try:
    from dialogs.invoice_preview_dialog import InvoicePreviewDialog
except Exception:
    InvoicePreviewDialog = None

from utils.asset_paths import resolve_logo_uri

try:
    from company_management_window import CompanyManagementWindow
except Exception:
    CompanyManagementWindow = None

try:
    import config_facot
except Exception:
    class _Cfg:
        QUOTATION_DUE_DAYS = 30
        INVOICE_DUE_DAYS = 30
        INVOICE_FIXED_DUE_DATE = ""
        COMPANY_LOGOS = {}
        DEFAULT_LOGO_PATH = ""
    config_facot = _Cfg()

CATEGORY_TO_PREFIX = {
    "FACTURA PRIVADA": "B01",
    "FACTURA GUBERNAMENTAL": "B15",
    "FACTURA GUBERMAMENTAL": "B15",
    "FACTURA CONSUMIDOR FINAL": "B02",
    "FACTURA EXENTA": "B14",
    "FACTURA EXENTA (REGIMEN ESPECIAL)": "B14",
    "FACTURA EXCENTA (REGIMEN ESPECIAL)": "B14",
}
DEFAULT_UNIT_FALLBACK = "UND"


class InvoiceTab(QWidget):
    """
    Pestaña de Facturas:
    - Secuencias NCF persistentes (preview vs consumo)
    - Ítems con unidad desde maestro
    - Exportación y vista previa
    """
    invoice_saved = pyqtSignal(int)

    def __init__(self, logic, get_current_company_callable, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.get_current_company = get_current_company_callable
        try:
            print(f"[LOAD] InvoiceTab module: {__file__}")
        except Exception:
            pass
        self._build_ui()

    # -------------------------
    # UI principal
    # -------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("""
        QGroupBox {
            border: 1px solid #555; border-radius: 6px; margin-top: 10px;
            padding: 8px 10px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)

        # Barra superior
        top_btn_row = QHBoxLayout()
        self.edit_template_btn = QPushButton("Editar plantilla")
        self.edit_template_btn.clicked.connect(self._on_edit_template)
        top_btn_row.addWidget(self.edit_template_btn)

        self.edit_company_btn = QPushButton("Editar empresa")
        self.edit_company_btn.clicked.connect(self._open_company_manager)
        top_btn_row.addWidget(self.edit_company_btn)

        self.btn_next_ncf = QPushButton("Siguiente NCF")
        self.btn_next_ncf.setToolTip("Asignar y consumir el siguiente NCF real")
        self.btn_next_ncf.clicked.connect(self._on_next_ncf_clicked)
        top_btn_row.addWidget(self.btn_next_ncf)

        top_btn_row.addStretch(1)
        layout.addLayout(top_btn_row)

        # 1. Datos de la Factura
        datos_box = QGroupBox("1. Datos de la Factura")
        g = QGridLayout(datos_box)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)

        # Tipo de NCF
        self.ncf_type_combo = QComboBox()
        if isinstance(NCF_TYPES, dict):
            self._ncf_type_display_to_prefix = {}
            for prefix, desc in NCF_TYPES.items():
                display = desc if desc else prefix
                self.ncf_type_combo.addItem(display)
                self._ncf_type_display_to_prefix[display] = prefix
        else:
            for k in NCF_TYPES:
                self.ncf_type_combo.addItem(k)

        # NCF asignado
        self.ncf_number_edit = QLineEdit()
        self.ncf_number_edit.setClearButtonEnabled(True)
        self._setup_ncf_validator()

        # Tipo/Categoría
        self.invoice_kind_combo = QComboBox()
        self.invoice_kind_combo.addItems([
            "FACTURA PRIVADA",
            "FACTURA GUBERNAMENTAL",
            "FACTURA CONSUMIDOR FINAL",
            "FACTURA EXENTA",
        ])

        # Fecha y vencimiento
        self.invoice_date = QDateEdit(QDate.currentDate()); self.invoice_date.setCalendarPopup(True)
        self.invoice_due_date = QDateEdit(QDate.currentDate()); self.invoice_due_date.setCalendarPopup(True)

        # Moneda/Tasa
        self.currency_combo = QComboBox(); self.currency_combo.addItems(["RD$", "USD", "EUR"])
        try: self.currency_combo.setCurrentText(DEFAULT_CURRENCY)
        except Exception: pass
        self.exchange_rate_edit = QLineEdit("1.00"); self.exchange_rate_edit.setVisible(False)

        # Fila 0
        g.addWidget(QLabel("Tipo de NCF:"), 0, 0); g.addWidget(self.ncf_type_combo, 0, 1)
        g.addWidget(QLabel("NCF Asignado:"), 0, 2); g.addWidget(self.ncf_number_edit, 0, 3)
        self.btn_refresh_ncf = QPushButton("↻"); self.btn_refresh_ncf.setToolTip("Mostrar el próximo NCF (preview)")
        self.btn_refresh_ncf.clicked.connect(self._update_ncf_sequence)
        g.addWidget(self.btn_refresh_ncf, 0, 4)
        g.addWidget(QLabel("Tipo Factura:"), 0, 5); g.addWidget(self.invoice_kind_combo, 0, 6)
        g.addWidget(QLabel("Fecha:"), 0, 7); g.addWidget(self.invoice_date, 0, 8)

        # Fila 1
        g.addWidget(QLabel("Vencimiento:"), 1, 0); g.addWidget(self.invoice_due_date, 1, 1)
        g.addWidget(QLabel("Moneda:"), 1, 2); g.addWidget(self.currency_combo, 1, 3)
        g.addWidget(QLabel("Tasa:"), 1, 4); g.addWidget(self.exchange_rate_edit, 1, 5)

        # stretches
        g.setColumnStretch(1, 2); g.setColumnStretch(3, 2); g.setColumnStretch(6, 2); g.setColumnStretch(8, 2)
        layout.addWidget(datos_box)

        # Conexiones
        self.ncf_type_combo.currentIndexChanged.connect(self._update_ncf_sequence)
        self.invoice_kind_combo.currentIndexChanged.connect(self._update_ncf_sequence)
        self.invoice_date.dateChanged.connect(self._maybe_new_year_reset)
        self.currency_combo.currentIndexChanged.connect(self._on_currency_change)

        # 2. Cliente
        cliente_box = QGroupBox("2. Datos del Cliente")
        cliente_row = QHBoxLayout(cliente_box)
        self.client_rnc = QLineEdit(); self.client_rnc.setPlaceholderText("RNC/Cédula…")
        self.client_name = QLineEdit(); self.client_name.setPlaceholderText("Nombre / Razón Social…")
        self.suggestion_combo = QComboBox(); self.suggestion_combo.hide(); self.suggestion_combo.setEditable(False)
        self.client_rnc.textChanged.connect(lambda: self._suggest_third_party('rnc'))
        self.client_name.textChanged.connect(lambda: self._suggest_third_party('name'))
        self.suggestion_combo.activated.connect(self._select_suggestion)
        cliente_row.addWidget(QLabel("RNC/Cédula:")); cliente_row.addWidget(self.client_rnc)
        cliente_row.addWidget(QLabel("Nombre/Razón Social:")); cliente_row.addWidget(self.client_name)
        cliente_row.addWidget(self.suggestion_combo)
        layout.addWidget(cliente_box)

        # 3. Detalles
        detalles_box = QGroupBox("3. Detalles de la Factura")
        detalles_layout = QVBoxLayout(detalles_box)
        actions = QHBoxLayout()
        btn_add_items = QPushButton("Agregar ítems…"); btn_add_items.clicked.connect(self._open_item_picker)
        btn_remove_item = QPushButton("Eliminar detalle seleccionado"); btn_remove_item.clicked.connect(self._remove_invoice_item_row)
        actions.addWidget(btn_add_items); actions.addWidget(btn_remove_item); actions.addStretch(1)
        detalles_layout.addLayout(actions)

        self.invoice_items_table = QTableWidget(0, 7)
        self.invoice_items_table.setHorizontalHeaderLabels(["#", "Código", "Descripción", "Unidad", "Cantidad", "Precio Unitario", "Subtotal"])
        self.invoice_items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoice_items_table.verticalHeader().setVisible(False)
        detalles_layout.addWidget(self.invoice_items_table)
        layout.addWidget(detalles_box)

        # Totales
        totales_box = QGroupBox("Totales")
        totales_row = QHBoxLayout(totales_box)
        self.apply_itbis_checkbox = QCheckBox("Aplicar ITBIS (18%)"); self.apply_itbis_checkbox.setChecked(True)
        self.apply_itbis_checkbox.stateChanged.connect(self._recalculate_invoice_totals)
        self.subtotal_label = QLabel("Subtotal: RD$ 0.00")
        self.itbis_label = QLabel("ITBIS: RD$ 0.00")
        self.total_label = QLabel("Total: RD$ 0.00")
        totales_row.addWidget(self.apply_itbis_checkbox); totales_row.addStretch(1)
        totales_row.addWidget(self.subtotal_label); totales_row.addWidget(self.itbis_label); totales_row.addWidget(self.total_label)
        layout.addWidget(totales_box)

        # Botones inferiores
        btn_preview_html = QPushButton("Vista Previa / PDF")
        btn_preview_html.setToolTip("Abrir vista previa HTML y exportar a PDF")
        btn_preview_html.clicked.connect(self._preview_invoice)

        btn_save_invoice = QPushButton("Guardar en Base de Datos")
        btn_save_invoice.clicked.connect(self._save_invoice)

        layout.addWidget(btn_preview_html)
        layout.addWidget(btn_save_invoice)

        # Vencimiento inicial y NCF inicial (preview)
        self._apply_default_due_date()
        self.invoice_date.dateChanged.connect(self._on_invoice_date_changed)
        self._update_ncf_sequence()

    # -------------------------
    # NCF helpers
    # -------------------------
    def _setup_ncf_validator(self):
        pattern = r"^(E[0-9]{13}|(?!E)[A-Z][0-9]{10})$"
        regex = QRegularExpression(pattern)
        self.ncf_number_edit.setValidator(QRegularExpressionValidator(regex, self.ncf_number_edit))
        self.ncf_number_edit.textEdited.connect(lambda _: self._enforce_upper(self.ncf_number_edit))
        self.ncf_number_edit.setPlaceholderText("Formato: ETTSSSSSSSSSSS o LTTSSSSSSSS (E+13 / letra≠E+10)")

    def _enforce_upper(self, edit: QLineEdit):
        try:
            pos = edit.cursorPosition()
            edit.setText((edit.text() or "").upper())
            edit.setCursorPosition(pos)
        except Exception:
            pass

    def _category_prefix(self) -> str:
        cat = (self.invoice_kind_combo.currentText() or "").strip().upper()
        if cat in CATEGORY_TO_PREFIX:
            return CATEGORY_TO_PREFIX[cat]
        display = self.ncf_type_combo.currentText()
        if hasattr(self, "_ncf_type_display_to_prefix"):
            return self._ncf_type_display_to_prefix.get(display, "B01")
        return display if len(display) == 3 else "B01"

    def _dedupe_ncf(self, ncf: str, prefix3: str) -> str:
        n = (ncf or "").upper()
        p = (prefix3 or "").upper()
        if len(n) >= 4 and len(p) == 3:
            if n[0] == n[1] and n[1:].startswith(p):
                return n[1:]
        return n

    def _update_ncf_sequence(self):
        """
        Muestra el PRÓXIMO NCF (preview) sin consumir/incrementar.
        """
        company = self.get_current_company()
        if not company:
            self.ncf_number_edit.clear(); return
        prefix3 = self._category_prefix()
        preview = ""
        try:
            if hasattr(self.logic, "get_ncf_preview"):
                preview = self.logic.get_ncf_preview(int(company['id']), prefix3)
            elif hasattr(self.logic, "get_next_ncf"):  # fallback histórico
                preview = self.logic.get_next_ncf(int(company['id']), prefix3)
        except Exception as e:
            print(f"[NCF] Error preview: {e}")
        preview = self._dedupe_ncf(preview, prefix3)
        self.ncf_number_edit.setText(preview or "")

    def _on_next_ncf_clicked(self):
        """
        Consume/asigna el siguiente NCF (incrementa secuencia en BD).
        """
        comp = self.get_current_company()
        if not comp:
            QMessageBox.warning(self, "NCF", "Seleccione una empresa."); return
        prefix3 = self._category_prefix()
        try:
            if hasattr(self.logic, "allocate_next_ncf"):
                next_ncf = self.logic.allocate_next_ncf(int(comp['id']), prefix3)
            else:  # fallback
                next_ncf = self.logic.get_next_ncf(int(comp['id']), prefix3)
            next_ncf = self._dedupe_ncf(next_ncf, prefix3)
            self.ncf_number_edit.setText(next_ncf)
        except Exception as e:
            QMessageBox.critical(self, "NCF", f"No se pudo asignar el siguiente NCF:\n{e}")

    def _maybe_new_year_reset(self):
        self._update_ncf_sequence()

    def _validate_ncf_or_warn(self) -> bool:
        ncf = (self.ncf_number_edit.text() or "").strip().upper()
        if not hasattr(self.logic, "validate_ncf"):
            return True
        if not self.logic.validate_ncf(ncf):
            QMessageBox.critical(self, "NCF", "NCF inválido. Formatos válidos: E + 13 dígitos, o letra≠E + 10 dígitos.")
            return False
        return True

    def _ensure_ncf_assigned_and_mark(self, company: Dict[str, Any]):
        """
        Garantiza que el campo tenga un NCF asignado y consumido si corresponde.
        Regla:
        - Si el campo está vacío → allocate_next_ncf.
        - Si el campo coincide con el preview actual → allocate_next_ncf (para persistir consumo).
        - Si el campo es distinto (usuario escribió uno válido), no se incrementa automáticamente.
        """
        if not company:
            return None
        prefix = self._category_prefix()
        current = (self.ncf_number_edit.text() or "").strip().upper()
        try:
            if hasattr(self.logic, "get_ncf_preview"):
                preview = self.logic.get_ncf_preview(int(company['id']), prefix)
            else:
                preview = self.logic.get_next_ncf(int(company['id']), prefix)
        except Exception:
            preview = ""
        try:
            if not current or (preview and current == preview):
                if hasattr(self.logic, "allocate_next_ncf"):
                    assigned = self.logic.allocate_next_ncf(int(company['id']), prefix)
                else:
                    assigned = self.logic.get_next_ncf(int(company['id']), prefix)
                assigned = self._dedupe_ncf(assigned, prefix)
                if assigned:
                    self.ncf_number_edit.setText(assigned)
                    current = assigned
        except Exception as ex:
            print("[InvoiceTab] _ensure_ncf_assigned_and_mark error:", ex)
        return current

    # -------------------------
    # Moneda / fechas
    # -------------------------
    def _on_currency_change(self):
        moneda = self.currency_combo.currentText()
        if moneda != "RD$":
            self.exchange_rate_edit.setVisible(True)
            try:
                tasa, ok = QInputDialog.getDouble(
                    self, "Tasa de cambio",
                    f"Ingrese la tasa para {moneda} → RD$: ",
                    value=self._safe_float(self.exchange_rate_edit.text(), 1.0),
                    min=0.0001, decimals=4
                )
            except Exception:
                ok = False; tasa = 1.0
            self.exchange_rate_edit.setText(f"{tasa:.4f}" if ok else "1.00")
        else:
            self.exchange_rate_edit.setText("1.00"); self.exchange_rate_edit.setVisible(False)

    def _apply_default_due_date(self):
        fixed = getattr(config_facot, "INVOICE_FIXED_DUE_DATE", "") or ""
        days = int(getattr(config_facot, "INVOICE_DUE_DAYS", 0) or 0)
        if fixed:
            try:
                y, m, d = [int(x) for x in fixed.split("-")]
                self.invoice_due_date.setDate(QDate(y, m, d))
                return
            except Exception:
                pass
        if days > 0:
            base = self.invoice_date.date()
            self.invoice_due_date.setDate(base.addDays(days))

    def _on_invoice_date_changed(self, new_date: QDate):
        fixed = getattr(config_facot, "INVOICE_FIXED_DUE_DATE", "") or ""
        days = int(getattr(config_facot, "INVOICE_DUE_DAYS", 0) or 0)
        if fixed:
            return
        if days > 0:
            self.invoice_due_date.setDate(new_date.addDays(days))

    # -------------------------
    # Cliente / sugerencias
    # -------------------------
    def _suggest_third_party(self, search_by):
        query = self.client_rnc.text() if search_by == "rnc" else self.client_name.text()
        if len(query) < 2:
            self.suggestion_combo.hide(); return
        results = self.logic.search_third_parties(query, search_by=search_by) if hasattr(self.logic, "search_third_parties") else []
        self.suggestion_combo.clear()
        for item in results:
            self.suggestion_combo.addItem(f"{item['rnc']} - {item['name']}")
        self.suggestion_combo.setVisible(bool(results))

    def _select_suggestion(self, idx: int):
        try:
            text = self.suggestion_combo.currentText() or ""
            if " - " in text:
                rnc, name = text.split(" - ", 1)
                self.client_rnc.setText(rnc.strip())
                self.client_name.setText(name.strip())
            else:
                if text:
                    self.client_name.setText(text.strip())
            self.suggestion_combo.hide()
        except Exception:
            self.suggestion_combo.hide()

    # -------------------------
    # Ítems
    # -------------------------
    def _open_item_picker(self):
        dlg = ItemPickerDialog(self, title="Agregar ítems a la Factura")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        items = dlg.get_selected_items()
        for it in items:
            code = it.get("code") or it.get("codigo") or it.get("item_code") or ""
            name = it.get("name") or it.get("nombre") or it.get("description") or ""
            unit = it.get("unit") or it.get("unidad") or ""
            qty = it.get("quantity") or it.get("cantidad") or 0
            price = it.get("unit_price") or it.get("precio") or 0.0
            self._append_row(code, name, unit, qty, price)
        self._recalculate_invoice_totals()

    def _append_row(self, code, name, unit, qty, price, subtotal=None):
        if subtotal is None:
            try:
                subtotal = float(qty) * float(price)
            except Exception:
                subtotal = 0.0
        row = self.invoice_items_table.rowCount()
        self.invoice_items_table.insertRow(row)
        self.invoice_items_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.invoice_items_table.setItem(row, 1, QTableWidgetItem(code or ""))
        self.invoice_items_table.setItem(row, 2, QTableWidgetItem(name or ""))
        self.invoice_items_table.setItem(row, 3, QTableWidgetItem((unit or "").strip()))
        self.invoice_items_table.setItem(row, 4, QTableWidgetItem(f"{float(qty):.2f}" if qty is not None else "0.00"))
        self.invoice_items_table.setItem(row, 5, QTableWidgetItem(f"{float(price):.2f}" if price is not None else "0.00"))
        self.invoice_items_table.setItem(row, 6, QTableWidgetItem(f"{float(subtotal):,.2f}"))
        self._recalculate_invoice_totals()

    def _remove_invoice_item_row(self):
        r = self.invoice_items_table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un detalle para eliminar."); return
        self.invoice_items_table.removeRow(r)
        for i in range(self.invoice_items_table.rowCount()):
            self.invoice_items_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
        self._recalculate_invoice_totals()

    def _recalculate_invoice_totals(self):
        subtotal = 0.0
        for r in range(self.invoice_items_table.rowCount()):
            cell = self.invoice_items_table.item(r, 6)
            if not cell:
                continue
            txt = (cell.text() or "").replace(",", "").strip()
            try:
                subtotal += float(txt) if txt else 0.0
            except Exception:
                pass
        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis
        self.subtotal_label.setText(f"Subtotal: RD$ {subtotal:,.2f}")
        self.itbis_label.setText(f"ITBIS ({ITBIS_RATE*100:.0f}%): RD$ {itbis:,.2f}")
        self.total_label.setText(f"Total: RD$ {total:,.2f}")

    # -------------------------
    # Vista previa / exportación
    # -------------------------
    def _preview_invoice(self):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return

        print("[HIT] _preview_invoice start")

        company_data, tpl = self._get_company_payload_for_preview()
        self._ensure_ncf_assigned_and_mark(company)
        ncf_text = (self.ncf_number_edit.text() or "").strip().upper()

        items = self._collect_items_for_export()
        if not items:
            QMessageBox.warning(self, "Ítems", "Agrega al menos un ítem antes de previsualizar.")
            return

        invoice_data = {
            "company_id": company_data.get('id'),
            "number": f"INV-DRAFT-{dt.now().strftime('%y%m%d%H%M%S')}",
            "ncf": ncf_text,
            "date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "due_date": self.invoice_due_date.date().toString("yyyy-MM-dd"),
            "client_name": self.client_name.text(),
            "client_rnc": self.client_rnc.text(),
            "currency": self.currency_combo.currentText(),
            "exchange_rate": self._safe_float(self.exchange_rate_edit.text(), 1.0),
            "items": items,
            "notes": "",
            "invoice_category": self.invoice_kind_combo.currentText(),
            "type": self.invoice_kind_combo.currentText(),
            "apply_itbis": self.apply_itbis_checkbox.isChecked(),
        }
        invoice_data["display_number"] = self._build_display_invoice_number(company_data, ncf_text, prefix_label="FACT", last_digits=6)

        template_path = os.path.join(get_data_root(), "templates", "quotation_template.html")

        if InvoicePreviewDialog is None:
            QMessageBox.critical(self, "Vista Previa", "InvoicePreviewDialog no está disponible.")
            return

        dlg = InvoicePreviewDialog(
            company=company_data,
            template=tpl,
            invoice=invoice_data,
            parent=self,
            template_path=template_path,
            debug=False
        )
        dlg.exec()

    def _generate_invoice_excel(self):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return

        items_for_export = []
        for r in range(self.invoice_items_table.rowCount()):
            desc = self.invoice_items_table.item(r, 2)
            qty = self.invoice_items_table.item(r, 4)
            price = self.invoice_items_table.item(r, 5)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0; price_val = 0.0
            items_for_export.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})

        data = {
            "company_id": int(company['id']),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": (self.ncf_number_edit.text() or "").strip(),
            "invoice_type": "emitida",
            "invoice_category": self.invoice_kind_combo.currentText(),
            "client_name": self.client_name.text(),
            "client_rnc": self.client_rnc.text(),
            "currency": self.currency_combo.currentText(),
        }

        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como Excel", "", "Excel Files (*.xlsx)")
        if fn:
            save_path = fn if fn.endswith(".xlsx") else fn + ".xlsx"
            self._ensure_ncf_assigned_and_mark(company)
            generate_invoice_excel(data, items_for_export, save_path, company.get('name', ''))

    def _generate_invoice_pdf(self):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return

        items_for_export = []
        for r in range(self.invoice_items_table.rowCount()):
            desc = self.invoice_items_table.item(r, 2)
            qty = self.invoice_items_table.item(r, 4)
            price = self.invoice_items_table.item(r, 5)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0; price_val = 0.0
            items_for_export.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})

        data = {
            "company_id": int(company['id']),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": (self.ncf_number_edit.text() or "").strip(),
            "invoice_type": "emitida",
            "invoice_category": self.invoice_kind_combo.currentText(),
            "client_name": self.client_name.text(),
            "client_rnc": self.client_rnc.text(),
            "currency": self.currency_combo.currentText(),
        }

        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como PDF", "", "PDF Files (*.pdf)")
        if fn:
            save_path = fn if fn.endswith(".pdf") else fn + ".pdf"
            self._ensure_ncf_assigned_and_mark(company)
            generate_invoice_pdf(data, items_for_export, save_path, company.get('name', ''))

    # -------------------------
    # Utilidades numéricas / texto
    # -------------------------
    def _safe_float(self, txt: str, default: float = 0.0) -> float:
        try:
            return float((txt or "").replace(",", "").strip())
        except Exception:
            return default

    def _safe_text_attr(self, attr_name: str) -> str:
        w = getattr(self, attr_name, None)
        try:
            if w is None:
                return ""
            if hasattr(w, "text"):
                return (w.text() or "").strip()
            if hasattr(w, "toPlainText"):
                return (w.toPlainText() or "").strip()
        except Exception:
            pass
        return ""

    # -------------------------
    # Empresa / payload para preview
    # -------------------------
    def _company_display_address(self, details: Dict[str, Any], company_fallback: Dict[str, Any]) -> str:
        a1 = (details.get("address_line1") or company_fallback.get("address_line1") or "").strip()
        a2 = (details.get("address_line2") or company_fallback.get("address_line2") or "").strip()
        addr = (details.get("address") or company_fallback.get("address") or "").strip()
        if a1 or a2:
            parts = [p for p in [a1, a2] if p]
            return " ".join(parts)
        return addr or "Dirección no especificada"

    def _resolve_company_logo(self, company_id: Any, details: Dict[str, Any], company_fallback: Dict[str, Any]) -> str:
        cand = (details.get("logo_path") or company_fallback.get("logo_path") or "").strip()
        if not cand:
            logos = getattr(config_facot, "COMPANY_LOGOS", {}) or {}
            key_id = str(company_id) if company_id is not None else ""
            cand = logos.get(key_id) or logos.get(details.get("name") or company_fallback.get("name") or "", "")
        if not cand:
            cand = getattr(config_facot, "DEFAULT_LOGO_PATH", "") or ""
        return resolve_logo_uri(cand) or ""

    def _get_company_payload_for_preview(self):
        company_min = self.get_current_company() or {}
        company_id = company_min.get("id")
        if not company_id:
            print("[InvoiceTab] ERROR: No se pudo obtener company_id")
            return {}, {}

        details = {}
        try:
            if hasattr(self.logic, "get_company_details"):
                details = self.logic.get_company_details(company_id) or {}
            else:
                print("[InvoiceTab] ERROR: self.logic no tiene get_company_details")
        except Exception as e:
            print(f"[InvoiceTab] ERROR en get_company_details: {e}")
            details = {}

        if not details:
            details = company_min

        a1 = (details.get("address_line1") or "").strip()
        a2 = (details.get("address_line2") or "").strip()
        addr = (details.get("address") or "").strip()
        if a1 or a2:
            address_full = f"{a1} {a2}".strip()
        else:
            address_full = addr or "Dirección no especificada"

        signature = (details.get("signature_name") or "").strip()
        logo_rel = (details.get("logo_path") or "").strip()

        payload = {
            "id": company_id,
            "name": details.get("name") or company_min.get("name", ""),
            "rnc": details.get("rnc") or details.get("rnc_number") or company_min.get("rnc", ""),
            "address_line1": a1,
            "address_line2": a2,
            "address": address_full,
            "phone": details.get("phone") or details.get("telefono") or company_min.get("phone", ""),
            "email": details.get("email") or details.get("correo") or company_min.get("email", ""),
            "signature_name": signature,
            "authorized_name": signature,
            "logo_path": logo_rel,
            "invoice_due_date": (details.get("invoice_due_date") or "").strip(),
        }

        try:
            self._set_invoice_due_date_widget(payload.get("invoice_due_date") or "")
        except Exception:
            pass

        tpl = {}
        try:
            tpl = load_template(int(company_id)) or {}
        except Exception as e:
            print(f"[InvoiceTab] ERROR al cargar template: {e}")
            tpl = {}
        return payload, tpl

    # -------------------------
    # Guardar factura
    # -------------------------
    def _build_display_invoice_number(self, company: Dict[str, Any], ncf: str, prefix_label: str = "FACT", last_digits: int = 6) -> str:
        initials = self._company_initials(company.get('name', 'COMPANY'))
        digits = ''.join(ch for ch in (ncf or "") if ch.isdigit())
        tail = digits[-last_digits:] if digits else ''
        if tail:
            return f"{prefix_label}-{initials}-{tail}"
        return f"{prefix_label}-{initials}-{ncf or ''}"

    def _company_initials(self, company_name: str, max_chars: int = 6) -> str:
        if not company_name:
            return "COMP"
        parts = [p for p in company_name.replace(',', ' ').split() if p]
        if len(parts) == 1:
            s = parts[0][:max_chars].upper()
            return ''.join([c for c in s if c.isalnum()])[:max_chars]
        initials = ''.join([p[0].upper() for p in parts[:3]])
        return initials[:max_chars]

    def _save_invoice(self):
        if not self._validate_ncf_or_warn():
            return
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida"); return

        cliente_nombre = self.client_name.text().strip()
        cliente_rnc = self.client_rnc.text().strip()
        if not cliente_nombre or not cliente_rnc:
            QMessageBox.warning(self, "Cliente", "Complete nombre y RNC del cliente."); return

        moneda = self.currency_combo.currentText()
        try:
            tasa = float(self.exchange_rate_edit.text().replace(",", "")) if self.exchange_rate_edit.text().strip() else 1.0
            if tasa <= 0: tasa = 1.0
        except Exception:
            tasa = 1.0

        items = self._collect_items_for_export()
        subtotal = 0.0
        for it in items:
            try: subtotal += (it.get('quantity', 0.0) or 0.0) * (it.get('unit_price', 0.0) or 0.0)
            except Exception: pass

        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis
        total_rd = total * tasa

        # Asegurar consumo si el campo está vacío o igual al preview
        self._ensure_ncf_assigned_and_mark(company)

        # Dedup antes de guardar
        raw_ncf = (self.ncf_number_edit.text() or "").strip().upper()
        prefix3 = self._category_prefix()
        invoice_number = self._dedupe_ncf(raw_ncf, prefix3)

        payload = {
            "company_id": int(company['id']),
            "invoice_type": "emitida",
            "invoice_category": self.invoice_kind_combo.currentText(),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": invoice_number,
            "third_party_name": cliente_nombre,
            "rnc": cliente_rnc,
            "currency": moneda,
            "itbis": itbis,
            "total_amount": total,
            "exchange_rate": tasa,
            "total_amount_rd": total_rd,
            "excel_path": "",
            "pdf_path": "",
        }

        invoice_id = self.logic.add_invoice(payload, items)
        QMessageBox.information(self, "Factura", f"Factura creada (ID: {invoice_id})")
        self._clear_invoice_form()
        self.invoice_saved.emit(invoice_id)

    def _clear_invoice_form(self):
        self.invoice_date.setDate(QDate.currentDate())
        self.invoice_due_date.setDate(QDate.currentDate())
        self.ncf_number_edit.clear()
        self.client_rnc.clear(); self.client_name.clear()
        self.currency_combo.setCurrentText(DEFAULT_CURRENCY)
        self.exchange_rate_edit.setText("1.00"); self.exchange_rate_edit.setVisible(False)
        self.invoice_items_table.setRowCount(0)
        self.subtotal_label.setText("Subtotal: RD$ 0.00")
        self.itbis_label.setText("ITBIS: RD$ 0.00")
        self.total_label.setText("Total: RD$ 0.00")

    def on_company_change(self):
        try: self.suggestion_combo.hide()
        except Exception: pass
        self._clear_invoice_form()
        self._apply_default_due_date()
        self._update_ncf_sequence()

    # -------------------------
    # Direcciones / vencimiento fijo
    # -------------------------
    def _compute_invoice_due_date(self, company_payload: dict, invoice_date_str: str) -> str:
        due = (company_payload or {}).get("invoice_due_date") or ""
        return (due or "").strip()

    def _set_invoice_due_date_widget(self, due_str: str) -> None:
        try:
            if not due_str: return
            y, m, d = [int(x) for x in due_str[:10].split("-")]
            self.invoice_due_date.setDate(QDate(y, m, d))
            print(f"[ITAB-DUE] Prefill widget invoice_due_date <- {due_str}")
        except Exception as e:
            print(f"[ITAB-DUE] error prefill widget: {e}")

    # -------------------------
    # Empresa / plantillas / gestión
    # -------------------------
    def _on_edit_template(self):
        company = None
        try: company = self.get_current_company()
        except Exception: pass
        if not company:
            QMessageBox.warning(self, "Plantilla", "Seleccione primero una empresa válida.")
            return
        company_id = (company.get("id") or company.get("company_id") or company.get("pk"))
        if not company_id:
            QMessageBox.warning(self, "Plantilla", "Empresa sin identificador."); return
        if TemplateEditorDialog is None:
            QMessageBox.critical(self, "Plantilla", "TemplateEditorDialog no disponible."); return
        try:
            dlg = TemplateEditorDialog(company_id=company_id, parent=self)
            if dlg.exec():
                QMessageBox.information(self, "Plantilla", "Plantilla guardada correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Plantilla", f"No se pudo abrir el editor:\n{e}")

    def _open_company_manager(self):
        if CompanyManagementWindow is None:
            QMessageBox.warning(self, "Empresas", "No se encontró CompanyManagementWindow."); return
        try:
            dlg = CompanyManagementWindow(parent=self, logic_controller=self.logic)
            dlg.exec()
        except TypeError:
            try:
                dlg = CompanyManagementWindow(self, self.logic); dlg.exec()
            except Exception as e:
                QMessageBox.critical(self, "Empresas", f"No se pudo abrir gestión de empresas:\n{e}")
                return
        except Exception as e:
            QMessageBox.critical(self, "Empresas", f"No se pudo abrir gestión de empresas:\n{e}")
            return
        self._notify_companies_changed()
        try: self.on_company_change()
        except Exception: self._update_ncf_sequence()

    def _notify_companies_changed(self):
        p = self.parent(); safety = 0
        while p is not None and safety < 12:
            if hasattr(p, "_populate_companies"):
                try: p._populate_companies()
                except Exception: pass
                break
            p = p.parent(); safety += 1