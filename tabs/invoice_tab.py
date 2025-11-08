from __future__ import annotations
from utils.app_paths import resource_path
import os
import datetime
from typing import Dict, Any, List
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QDateEdit, QCheckBox, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog,
    QHeaderView, QGroupBox, QFormLayout, QDialog, QInputDialog
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

from constants import (
    NCF_TYPES,
    ITBIS_RATE,
    DEFAULT_CURRENCY,
    NCF_CATEGORY_DEFAULT_PREFIX,
)

from utils.quotation_templates import (
    generate_quotation_excel as generate_invoice_excel,
    generate_quotation_pdf as generate_invoice_pdf,
)

from dialogs.item_picker_dialog import ItemPickerDialog
    # noqa: E402
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

# Config para vencimientos y logos
try:
    import config_facot
except Exception:
    class _Cfg:
        QUOTATION_DUE_DAYS = 30
        INVOICE_DUE_DAYS = 30
        INVOICE_FIXED_DUE_DATE = ""  # "YYYY-MM-DD"
        COMPANY_LOGOS = {}
        DEFAULT_LOGO_PATH = ""
    config_facot = _Cfg()

# Fallback de unidad: usa el estándar de tu tabla (UND)
DEFAULT_UNIT_FALLBACK = "UND"


class InvoiceTab(QWidget):
    invoice_saved = pyqtSignal(int)

    def __init__(self, logic, get_current_company_callable, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.get_current_company = get_current_company_callable
        # Traza para confirmar qué archivo está cargando esta clase
        try:
            print(f"[LOAD] InvoiceTab module: {__file__}")
        except Exception:
            pass
        self._build_ui()

    # -------------------------
    # UI
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
        top_btn_row.addWidget(self.edit_template_btn)
        self.edit_template_btn.clicked.connect(self._on_edit_template)

        self.edit_company_btn = QPushButton("Editar empresa")
        top_btn_row.addWidget(self.edit_company_btn)
        self.edit_company_btn.clicked.connect(self._open_company_manager)

        self.btn_next_ncf = QPushButton("Siguiente NCF")
        self.btn_next_ncf.setToolTip("Calcular el siguiente NCF según Tipo Factura")
        top_btn_row.addWidget(self.btn_next_ncf)
        self.btn_next_ncf.clicked.connect(self._on_next_ncf_clicked)

        self.btn_configure_ncf = QPushButton("Configurar NCF...")
        self.btn_configure_ncf.setToolTip("Administrar prefijos y secuencias por empresa")
        top_btn_row.addWidget(self.btn_configure_ncf)
        self.btn_configure_ncf.clicked.connect(self._open_ncf_sequence_config)

        top_btn_row.addStretch(1)
        layout.addLayout(top_btn_row)

        # 1. Datos de la Factura
        datos_box = QGroupBox("1. Datos de la Factura")
        datos_form = QFormLayout(datos_box)
        top_row = QHBoxLayout()

        self.ncf_type_combo = QComboBox()
        self.ncf_type_combo.addItems(NCF_TYPES.keys())
        self.ncf_type_combo.currentIndexChanged.connect(self._update_ncf_sequence)

        self.ncf_number_edit = QLineEdit()
        self.ncf_number_edit.setClearButtonEnabled(True)
        self._setup_ncf_validator()

        self.invoice_kind_combo = QComboBox()
        self.invoice_kind_combo.addItems([
            "FACTURA PRIVADA",
            "FACTURA GUBERNAMENTAL",
            "FACTURA CONSUMIDOR FINAL",
            "FACTURA EXENTA",
        ])
        self.invoice_kind_combo.currentIndexChanged.connect(self._update_ncf_sequence)

        self.invoice_date = QDateEdit(QDate.currentDate()); self.invoice_date.setCalendarPopup(True)
        self.invoice_due_date = QDateEdit(QDate.currentDate()); self.invoice_due_date.setCalendarPopup(True)

        self.currency_combo = QComboBox(); self.currency_combo.addItems(["RD$", "USD", "EUR"])
        try:
            self.currency_combo.setCurrentText(DEFAULT_CURRENCY)
        except Exception:
            pass
        self.exchange_rate_edit = QLineEdit("1.00"); self.exchange_rate_edit.setVisible(False)
        self.currency_combo.currentIndexChanged.connect(self._on_currency_change)

        top_row.addWidget(QLabel("Tipo de NCF:")); top_row.addWidget(self.ncf_type_combo)
        top_row.addWidget(QLabel("NCF Asignado:")); top_row.addWidget(self.ncf_number_edit, 1)
        top_row.addWidget(QLabel("Tipo Factura:")); top_row.addWidget(self.invoice_kind_combo)
        top_row.addWidget(QLabel("Fecha:")); top_row.addWidget(self.invoice_date)
        top_row.addWidget(QLabel("Vencimiento:")); top_row.addWidget(self.invoice_due_date)
        top_row.addWidget(QLabel("Moneda:")); top_row.addWidget(self.currency_combo)
        top_row.addWidget(QLabel("Tasa:")); top_row.addWidget(self.exchange_rate_edit)
        datos_form.addRow(top_row)
        layout.addWidget(datos_box)

        # 2. Datos del Cliente
        cliente_box = QGroupBox("2. Datos del Cliente")
        cliente_row = QHBoxLayout(cliente_box)
        self.client_rnc = QLineEdit(); self.client_rnc.setPlaceholderText("Buscar RNC/Cédula…")
        self.client_name = QLineEdit(); self.client_name.setPlaceholderText("Buscar nombre/razón social…")
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
        totales_row.addWidget(self.apply_itbis_checkbox)
        totales_row.addStretch(1)
        totales_row.addWidget(self.subtotal_label)
        totales_row.addWidget(self.itbis_label)
        totales_row.addWidget(self.total_label)
        layout.addWidget(totales_box)

        # Dentro de _build_ui(), REEMPLAZA el bloque "Botones inferiores" por este:

        # Botones inferiores
        btn_preview_html = QPushButton("Vista Previa / PDF")
        btn_preview_html.setToolTip("Abrir vista previa HTML y exportar a PDF (WYSIWYG)")
        btn_preview_html.clicked.connect(self._preview_invoice)

        btn_save_invoice = QPushButton("Guardar en Base de Datos")
        btn_save_invoice.clicked.connect(self._save_invoice)

        layout.addWidget(btn_preview_html)
        layout.addWidget(btn_save_invoice)
        # Política de vencimiento (facturas)
        self._apply_default_due_date()
        self.invoice_date.dateChanged.connect(self._on_invoice_date_changed)

        # Sugerir NCF inicial
        self._update_ncf_sequence()

    # -------------------------
    # Helpers NCF
    # -------------------------
    def _setup_ncf_validator(self):
        pattern = r"^(E[0-9]{13}|(?!E)[A-Z][0-9]{10})$"
        regex = QRegularExpression(pattern)
        self.ncf_number_edit.setValidator(QRegularExpressionValidator(regex, self.ncf_number_edit))
        self.ncf_number_edit.textEdited.connect(lambda _: self._enforce_upper(self.ncf_number_edit))
        self.ncf_number_edit.setPlaceholderText("Formato: ETTSSSSSSSSSSS o LTTSSSSSSSS (E+13 o letra≠E+10)")

    def _enforce_upper(self, edit: QLineEdit):
        try:
            pos = edit.cursorPosition()
            edit.setText((edit.text() or "").upper())
            edit.setCursorPosition(pos)
        except Exception:
            pass

    def _category_prefix(self) -> str:
        cat = (self.invoice_kind_combo.currentText() or "").strip().upper()
        default_prefix = NCF_CATEGORY_DEFAULT_PREFIX.get(
            cat,
            NCF_TYPES.get(self.ncf_type_combo.currentText(), "B01"),
        )
        company = self.get_current_company()
        if company and hasattr(self.logic, "resolve_ncf_prefix"):
            try:
                resolved = self.logic.resolve_ncf_prefix(
                    int(company.get("id")),
                    cat,
                    default_prefix=default_prefix,
                )
                if resolved:
                    return (resolved or default_prefix or "B01").upper()
            except Exception:
                pass
        return (default_prefix or "B01").upper()

    def _update_ncf_sequence(self):
        company = self.get_current_company()
        if not company:
            self.ncf_number_edit.clear()
            return
        prefix3 = self._category_prefix()
        category = (self.invoice_kind_combo.currentText() or "").strip().upper()
        try:
            next_ncf = self.logic.get_next_ncf(int(company['id']), prefix3, category)
        except Exception:
            next_ncf = ""
        self.ncf_number_edit.setText(next_ncf or "")

    def _on_next_ncf_clicked(self):
        comp = self.get_current_company()
        if not comp:
            QMessageBox.warning(self, "NCF", "Seleccione una empresa.")
            return
        prefix3 = self._category_prefix()
        category = (self.invoice_kind_combo.currentText() or "").strip().upper()
        try:
            next_ncf = self.logic.get_next_ncf(int(comp.get("id")), prefix3, category)
            self.ncf_number_edit.setText(next_ncf)
        except Exception as e:
            QMessageBox.critical(self, "NCF", f"No se pudo calcular el siguiente NCF:\n{e}")

    def _open_ncf_sequence_config(self):
        company = self.get_current_company()
        current_company_id = None
        if company:
            try:
                current_company_id = int(company.get("id"))
            except Exception:
                current_company_id = None
        try:
            from dialogs.ncf_sequence_dialog import NCFSequenceDialog
        except Exception as exc:
            QMessageBox.critical(
                self,
                "NCF",
                f"No se pudo cargar el diálogo de secuencias NCF:\n{exc}"
            )
            return

        try:
            companies = []
            if hasattr(self.logic, "get_all_companies"):
                companies = self.logic.get_all_companies()
            dialog = NCFSequenceDialog(
                logic=self.logic,
                companies=companies,
                current_company_id=current_company_id,
                parent=self,
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._update_ncf_sequence()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "NCF",
                f"Error al abrir la configuración de secuencias:\n{exc}"
            )

    # -------------------------
    # Moneda / Fechas
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
    # Cliente / ítems / totales
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

    def _remove_invoice_item_row(self):
        r = self.invoice_items_table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un detalle para eliminar."); return
        self.invoice_items_table.removeRow(r)
        for i in range(self.invoice_items_table.rowCount()):
            self.invoice_items_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
        self._recalculate_invoice_totals()

    def _recalculate_invoice_totals(self):
        subtotal = 0.0
        for r in range(self.invoice_items_table.rowCount()):
            cell = self.invoice_items_table.item(r, 6)
            try:
                subtotal += float((cell.text() if cell else "0").replace(",", ""))
            except Exception:
                pass
        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis
        self.subtotal_label.setText(f"Subtotal: RD$ {subtotal:,.2f}")
        self.itbis_label.setText(f"ITBIS ({ITBIS_RATE*100:.0f}%): RD$ {itbis:,.2f}")
        self.total_label.setText(f"Total: RD$ {total:,.2f}")

    # -------------------------
    # Exportar / Preview
    # -------------------------
    def _generate_invoice_excel(self):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida"); return

        # Usa la misma colección robusta (si tu template Excel la aprovecha)
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
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida"); return

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

    # ---- Empresa / payload preview (firma, dirección, logo) ----
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
        """
        Carga datos completos de la empresa desde la BD para el preview (firma, dirección, contacto, logo).
        Siempre prioriza los campos de logic.get_company_details(company_id).
        """
        try:
            import inspect
            print(f"[WHERE] _get_company_payload_for_preview at {inspect.getsourcefile(self._get_company_payload_for_preview)}:{self._get_company_payload_for_preview.__code__.co_firstlineno}")
        except Exception:
            pass

        company_min = self.get_current_company() or {}
        company_id = company_min.get("id")

        if not company_id:
            print("[InvoiceTab] ERROR: No se pudo obtener company_id")
            return {}, {}

        # Consultar SIEMPRE la BD
        details = {}
        try:
            if hasattr(self.logic, "get_company_details"):
                details = self.logic.get_company_details(company_id) or {}
                print(f"[InvoiceTab] get_company_details({company_id}) returned: {details}")
            else:
                print("[InvoiceTab] ERROR: self.logic no tiene el método get_company_details")
        except Exception as e:
            print(f"[InvoiceTab] ERROR en get_company_details: {e}")
            details = {}

        if not details:
            print("[InvoiceTab] WARNING: get_company_details devolvió vacío, usando company_min como fallback")
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

        # Prints específicos de LOGO: qué viene y qué mandamos
        print("\n[INV-LOGO] InvoiceTab._get_company_payload_for_preview()")
        print(f"  company_id={company_id}")
        print(f"  details.logo_path='{details.get('logo_path')}'")
        print(f"  company_min.logo_path='{company_min.get('logo_path')}'")
        print(f"  -> payload.logo_path (raw, sin file:/// aún)='{logo_rel}'\n")

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
            "invoice_due_date": (details.get("invoice_due_date") or "").strip(),  # <- importante
        }

        # Prefill del widget con la fecha fija de la empresa si existe
        try:
            self._set_invoice_due_date_widget(payload.get("invoice_due_date") or "")
        except Exception:
            pass
        # Cargar plantilla (template) de la empresa
        tpl = {}
        try:
            tpl = load_template(int(company_id)) or {}
        except Exception as e:
            print(f"[InvoiceTab] ERROR al cargar template: {e}")
            tpl = {}

        print(f"[InvoiceTab] company_payload_for_preview FINAL: {payload}")
        return payload, tpl
  
    def _preview_invoice(self):
            # Asegúrate de importar esto en la parte superior del archivo invoice_tab.py:
            # from utils.app_paths import get_resource_path as resource_path
            
            company = self.get_current_company()
            if not company:
                QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
                return

            print("[HIT] _preview_invoice start")

            # 1. Obtener data completa de la empresa y template (sin fallbacks redundantes aquí)
            company_data, tpl = self._get_company_payload_for_preview()

            self._ensure_ncf_assigned_and_mark(company)
            ncf_text = (self.ncf_number_edit.text() or "").strip().upper()

            # 2. Recolectar ítems
            items = self._collect_items_for_export()
            
            if not items:
                QMessageBox.warning(self, "Ítems", "Agrega al menos un ítem a la factura antes de previsualizar.")
                return
                
            # 3. Construir el Payload FINAL (Factura)
            invoice_data = {
                "company_id": company_data.get('id'),
                "number": f"INV-DRAFT-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}",
                "ncf": ncf_text,
                "date": self.invoice_date.date().toString("yyyy-MM-dd"),
                "due_date": self.invoice_due_date.date().toString("yyyy-MM-dd"),
                "client_name": self.client_name.text(),
                "client_rnc": self.client_rnc.text(),
                "currency": self.currency_combo.currentText(),
                "exchange_rate": self._safe_float(self.exchange_rate_edit.text(), 1.0),
                "items": items,
                "notes": self._safe_text_attr("notes_edit"),
                "invoice_category": self.invoice_kind_combo.currentText(),
                "type": self.invoice_kind_combo.currentText(),
                "apply_itbis": self.apply_itbis_checkbox.isChecked(),  # ✅ AÑADIR ESTA LÍNEA
            }
            
            invoice_data["display_number"] = self._build_display_invoice_number(company_data, ncf_text, prefix_label="FACT", last_digits=6)
            
            print(f"[ITAB-DUE] PREVIEW payload due={invoice_data.get('due_date')} display_number={invoice_data.get('display_number')}")
            
            # 4. Carga la ruta del template usando el helper de PyInstaller (resource_path)
            # Usaremos el template de cotización unificado (si renombraste invoice_template.html a quotation_template.html para unificar)
            template_path = resource_path("templates", "quotation_template.html") # <--- USAR EL TEMPLATE UNIFICADO
            
            if InvoicePreviewDialog is None:
                QMessageBox.critical(self, "Vista Previa", "InvoicePreviewDialog no está disponible.")
                return

            print("[DEBUG] injected objects:", {"COMPANY": company_data, "TEMPLATE": tpl, "INVOICE": invoice_data})

            # 5. Abrir diálogo
            dlg = InvoicePreviewDialog(company=company_data, template=tpl, invoice=invoice_data, parent=self, template_path=template_path, debug=False)
            dlg.exec()
    # -------------------------
    # Unidad: helpers con trazas
    # -------------------------
    def _normalize_name(self, s: str) -> str:
        try:
            self._dbg_origin(self._normalize_name, "normalize_name")
        except Exception:
            pass
        print("[HIT] _normalize_name")
        s = (s or "").strip().upper()
        return " ".join(s.split())

    def _lookup_unit_by_code_or_name(self, code: str, name: str) -> str:
        try:
            self._dbg_origin(self._lookup_unit_by_code_or_name, "lookup_unit")
        except Exception:
            pass
        print(f"[HIT] _lookup_unit_by_code_or_name code='{code}' name='{name}'")

        if code and hasattr(self.logic, "get_item_by_code"):
            try:
                found = self.logic.get_item_by_code(code) or {}
                u = (found.get("unit") or "").strip()
                print("[HIT] get_item_by_code ->", found)
                if u:
                    return u
            except Exception as e:
                print("[InvoiceTab] get_item_by_code error:", e)

        if name and hasattr(self.logic, "get_items_like"):
            try:
                target = self._normalize_name(name)
                cands = self.logic.get_items_like(name, limit=25) or []
                print(f"[HIT] get_items_like count={len(cands)} first5={[c.get('name') for c in cands[:5]]}")
                for c in cands:
                    if self._normalize_name(c.get("name")) == target:
                        u = (c.get("unit") or "").strip()
                        if u:
                            return u
            except Exception as e:
                print("[InvoiceTab] get_items_like error:", e)

        return ""

    def _collect_items_for_export(self):
        try:
            self._dbg_origin(self._collect_items_for_export, "items")
        except Exception:
            pass
        print("[HIT] _collect_items_for_export")

        items: List[Dict[str, Any]] = []
        for r in range(self.invoice_items_table.rowCount()):
            code_item = self.invoice_items_table.item(r, 1)
            desc_item = self.invoice_items_table.item(r, 2)
            unit_item = self.invoice_items_table.item(r, 3)
            qty_item  = self.invoice_items_table.item(r, 4)
            price_item= self.invoice_items_table.item(r, 5)

            code = (code_item.text().strip() if code_item and code_item.text() else "")
            desc = (desc_item.text().strip() if desc_item and desc_item.text() else "")
            unit = (unit_item.text().strip() if unit_item and unit_item.text() else "")

            try:
                qty = float((qty_item.text() if qty_item else "0").replace(",", "").strip() or 0)
            except Exception:
                qty = 0.0
            try:
                price = float((price_item.text() if price_item else "0").replace(",", "").strip() or 0)
            except Exception:
                price = 0.0

            # CLAVE: PRIORIDAD AL MAESTRO
            unit_from_master = self._lookup_unit_by_code_or_name(code, desc)
            resolved_unit = unit_from_master or unit or DEFAULT_UNIT_FALLBACK
            if resolved_unit != unit:
                try:
                    self.invoice_items_table.setItem(r, 3, QTableWidgetItem(resolved_unit))
                except Exception:
                    pass

            print(f"[HIT] item row={r} code='{code}' name='{desc}' unit_master='{unit_from_master}' unit_before='{unit}' unit_after='{resolved_unit}'")

            items.append({
                "code": code,
                "description": desc,
                "unit": resolved_unit,
                "quantity": qty,
                "unit_price": price,
            })
        return items
    # -------------------------
    # Empresa / plantillas
    # -------------------------
    def _on_edit_template(self):
        try:
            company = self.get_current_company()
        except Exception:
            company = None
        if not company:
            QMessageBox.warning(self, "Plantilla", "Seleccione primero una empresa válida.")
            return
        company_id = company.get("id") or company.get("company_id") or company.get("pk")
        if not company_id:
            QMessageBox.warning(self, "Plantilla", "La empresa seleccionada no tiene identificador.")
            return
        try:
            dlg = TemplateEditorDialog(company_id=company_id, parent=self)
            if dlg.exec():
                QMessageBox.information(self, "Plantilla", "Plantilla guardada correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Plantilla", f"No se pudo abrir el editor de plantillas:\n{e}")

    def _open_company_manager(self):
        if CompanyManagementWindow is None:
            QMessageBox.warning(self, "Empresas", "No se encontró dialogs/company_management_window.py")
            return
        try:
            dlg = CompanyManagementWindow(parent=self, logic_controller=self.logic)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Empresas", f"No se pudo abrir el editor de empresas:\n{e}")
            return
        self._notify_companies_changed()
        try:
            self.on_company_change()
        except Exception:
            self._update_ncf_sequence()

    def _notify_companies_changed(self):
        p = self.parent(); safety = 0
        while p is not None and safety < 10:
            if hasattr(p, "_populate_companies"):
                try:
                    p._populate_companies()
                except Exception:
                    pass
                break
            p = p.parent(); safety += 1

    # -------------------------
    # Guardar
    # -------------------------
    def _validate_ncf_or_warn(self) -> bool:
        ncf = (self.ncf_number_edit.text() or "").strip().upper()
        if not self.logic.validate_ncf(ncf):
            QMessageBox.critical(self, "NCF", "NCF inválido. Formatos válidos: E + 13 dígitos, o letra≠E + 10 dígitos.")
            return False
        return True

    def _ensure_ncf_assigned_and_mark(self, company: Dict[str, Any]):
        if not company:
            return None
        current = (self.ncf_number_edit.text() or "").strip()
        prefix = self._category_prefix()
        category = (self.invoice_kind_combo.currentText() or "").strip().upper()
        assigned = current
        try:
            if not current:
                if hasattr(self.logic, "get_next_ncf"):
                    assigned = self.logic.get_next_ncf(int(company['id']), prefix, category)
                    if assigned:
                        self.ncf_number_edit.setText(assigned)
                else:
                    assigned = ""
            if assigned and hasattr(self.logic, "mark_ncf_used"):
                try:
                    self.logic.mark_ncf_used(int(company['id']), assigned)
                except Exception:
                    pass
            elif assigned and hasattr(self.logic, "reserve_ncf"):
                try:
                    self.logic.reserve_ncf(int(company['id']), assigned)
                except Exception:
                    pass
            return assigned
        except Exception as ex:
            print("[InvoiceTab] _ensure_ncf_assigned_and_mark error:", ex)
            return assigned

    def _company_initials(self, company_name: str, max_chars: int = 6) -> str:
        if not company_name:
            return "COMP"
        parts = [p for p in company_name.replace(',', ' ').split() if p]
        if len(parts) == 1:
            s = parts[0][:max_chars].upper()
            return ''.join([c for c in s if c.isalnum()])[:max_chars]
        initials = ''.join([p[0].upper() for p in parts[:3]])
        return initials[:max_chars]

    def _build_display_invoice_number(self, company: Dict[str, Any], ncf: str, prefix_label: str = "FACT", last_digits: int = 6) -> str:
        initials = self._company_initials(company.get('name', 'COMPANY'))
        digits = ''.join(ch for ch in (ncf or "") if ch.isdigit())
        tail = digits[-last_digits:] if digits else ''
        if tail:
            return f"{prefix_label}-{initials}-{tail}"
        return f"{prefix_label}-{initials}-{ncf or ''}"

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
            try:
                subtotal += (it.get('quantity', 0.0) or 0.0) * (it.get('unit_price', 0.0) or 0.0)
            except Exception:
                pass

        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis
        total_rd = total * tasa

        payload = {
            "company_id": int(company['id']),
            "invoice_type": "emitida",
            "invoice_category": self.invoice_kind_combo.currentText(),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": (self.ncf_number_edit.text() or "").strip().upper(),
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

        self._ensure_ncf_assigned_and_mark(company)

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
        try:
            self.suggestion_combo.hide()
        except Exception:
            pass
        self._clear_invoice_form()
        self._apply_default_due_date()
        self._update_ncf_sequence()

    # Helper para ver el origen de los métodos activos
    def _dbg_origin(self, fn, tag=""):
        try:
            import inspect, sys
            mod = sys.modules.get(fn.__module__)
            mod_path = getattr(mod, "__file__", "(sin __file__)")
            print(f"[WHERE] {tag} -> {fn.__name__} defined at {inspect.getsourcefile(fn)}:{fn.__code__.co_firstlineno} | module={mod_path}")
        except Exception as e:
            print(f"[WHERE] {tag} -> {fn} (no inspect) err={e}")

    def _qdate_to_str(self, qdate) -> str:
        try:
            return f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        except Exception:
            return ""

    def _compute_invoice_due_date(self, company_payload: dict, invoice_date_str: str) -> str:
        due = (company_payload or {}).get("invoice_due_date") or ""
        print(f"[ITAB-DUE] company.fixed='{due}' invoice_date='{invoice_date_str}'")
        return (due or "").strip()

    def _set_invoice_due_date_widget(self, due_str: str) -> None:
        """Setea el QDateEdit de vencimiento si existe y viene la fecha fija de empresa."""
        try:
            if not hasattr(self, "invoice_due_date"):
                return
            if not due_str:
                return
            y, m, d = [int(x) for x in due_str[:10].split("-")]
            self.invoice_due_date.setDate(QDate(y, m, d))
            print(f"[ITAB-DUE] Prefill widget invoice_due_date <- {due_str}")
        except Exception as e:
            print(f"[ITAB-DUE] error prefill widget: {e}")