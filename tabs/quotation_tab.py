from __future__ import annotations
from datetime import datetime, timedelta
import os
import datetime
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
    QDateEdit, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QComboBox,
    QHeaderView, QGroupBox, QToolButton, QCheckBox, QDialog
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal

from dialogs.item_picker_dialog import ItemPickerDialog
from dialogs.template_editor_dialog import TemplateEditorDialog
from dialogs.quotation_preview_dialog import QuotationPreviewDialog

from utils.template_manager import load_template, get_data_root
from utils.template_integration import (
    export_quotation_excel_with_template,
    export_quotation_pdf_with_template,
)
from constants import DEFAULT_CURRENCY, ITBIS_RATE
from utils.asset_paths import resolve_logo_uri
# --- imports de dialogs ---
from dialogs.invoice_preview_dialog import InvoicePreviewDialog
from utils.app_paths import resource_path
DEFAULT_UNIT_FALLBACK = "UND"

# -------------------------
# ItemsLookupMixin (debe ir antes de InvoiceTab)
# -------------------------
class ItemsLookupMixin:
    def _normalize_name(self, s: str) -> str:
        s = (s or "").strip().upper()
        return " ".join(s.split())

    def _lookup_unit_by_code_or_name(self, code: str, name: str) -> str:
        print(f"[HIT] _lookup_unit_by_code_or_name code='{code}' name='{name}'")

        if code and hasattr(self.logic, "get_item_by_code"):
            try:
                found = self.logic.get_item_by_code(code) or {}
                u = (found.get("unit") or "").strip()
                if u:
                    return u
            except Exception:
                pass

        if name and hasattr(self.logic, "get_items_like"):
            try:
                target = self._normalize_name(name)
                cands = self.logic.get_items_like(name, limit=25) or []
                for c in cands:
                    if self._normalize_name(c.get("name")) == target:
                        u = (c.get("unit") or "").strip()
                        if u:
                            return u
            except Exception:
                pass

        return ""


class QuotationTab(QWidget, ItemsLookupMixin):
    quotation_saved = pyqtSignal(int)

    def __init__(self, logic, get_current_company_callable, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.get_current_company = get_current_company_callable
        
        # **TRAZA DE CARGA**
        try:
            print(f"[LOAD] QuotationTab module: {__file__}")
        except Exception:
            pass
        
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.setStyleSheet("""
        QGroupBox {
            border: 1px solid #555; border-radius: 6px; margin-top: 10px;
            padding: 8px 10px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)

        # 1. Datos cotización
        datos_box = QGroupBox("1. Datos de la Cotización")
        datos_row = QHBoxLayout(datos_box)
        self.quotation_date = QDateEdit(QDate.currentDate()); self.quotation_date.setCalendarPopup(True)

        # Campo de solo lectura para vencimiento (nuevo)
        self.quotation_due_display = QLineEdit()
        self.quotation_due_display.setReadOnly(True)
        self.quotation_due_display.setPlaceholderText("N/A")
        self.quotation_due_display.setToolTip("Vencimiento automático = Fecha de emisión + 30 días")

        self.quotation_currency = QLineEdit(DEFAULT_CURRENCY)

        datos_row.addWidget(QLabel("Fecha:")); datos_row.addWidget(self.quotation_date)
        datos_row.addWidget(QLabel("Moneda:")); datos_row.addWidget(self.quotation_currency)

        # Inserta “Vence:” y el campo de solo lectura
        datos_row.addWidget(QLabel("Vence:"))
        datos_row.addWidget(self.quotation_due_display)

        datos_row.addStretch(1)
        layout.addWidget(datos_box)

        # BOTÓN: Editar plantilla para la empresa seleccionada (está global en la App)
        btn_row = QHBoxLayout()
        self.edit_template_btn = QPushButton("Editar plantilla")
        self.edit_template_btn.setToolTip("Editar plantilla para la empresa seleccionada")
        btn_row.addWidget(self.edit_template_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        self.edit_template_btn.clicked.connect(self._on_edit_template)

        # 2. Datos del Cliente
        cliente_box = QGroupBox("2. Datos del Cliente")
        cliente_row = QHBoxLayout(cliente_box)
        self.quotation_client_rnc = QLineEdit(); self.quotation_client_rnc.setPlaceholderText("Buscar RNC/Cédula…")
        self.quotation_client_name = QLineEdit(); self.quotation_client_name.setPlaceholderText("Buscar nombre/razón social…")
        self.quotation_suggestion_combo = QComboBox(); self.quotation_suggestion_combo.hide(); self.quotation_suggestion_combo.setEditable(False)
        self.quotation_client_rnc.textChanged.connect(lambda: self._suggest_third_party('rnc'))
        self.quotation_client_name.textChanged.connect(lambda: self._suggest_third_party('name'))
        self.quotation_suggestion_combo.activated.connect(self._select_suggestion)
        cliente_row.addWidget(QLabel("RNC/Cédula:")); cliente_row.addWidget(self.quotation_client_rnc)
        cliente_row.addWidget(QLabel("Nombre/Razón Social:")); cliente_row.addWidget(self.quotation_client_name)
        cliente_row.addWidget(self.quotation_suggestion_combo)
        layout.addWidget(cliente_box)

        # Notas colapsables
        notes_toggle_row = QHBoxLayout()
        self.notes_toggle = QToolButton()
        self.notes_toggle.setText("Notas (opcional)")
        self.notes_toggle.setCheckable(True)
        self.notes_toggle.setChecked(False)
        self.notes_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.notes_toggle.toggled.connect(self._toggle_notes)
        notes_toggle_row.addWidget(self.notes_toggle)
        notes_toggle_row.addStretch(1)
        layout.addLayout(notes_toggle_row)

        self.notes_box = QGroupBox()
        notes_lay = QVBoxLayout(self.notes_box)
        self.quotation_notes = QTextEdit()
        self.quotation_notes.setPlaceholderText("Notas para la cotización…")
        self.quotation_notes.setMinimumHeight(80)
        notes_lay.addWidget(self.quotation_notes)
        self.notes_box.setVisible(False)
        layout.addWidget(self.notes_box)

        # Detalles
        detalles_box = QGroupBox("3. Detalles de la Cotización")
        detalles_layout = QVBoxLayout(detalles_box)
        actions = QHBoxLayout()
        btn_add_items = QPushButton("Agregar ítems…")
        btn_add_items.clicked.connect(self._open_item_picker)
        btn_remove_item = QPushButton("Eliminar detalle seleccionado")
        btn_remove_item.clicked.connect(self._remove_item_row)
        actions.addWidget(btn_add_items)
        actions.addWidget(btn_remove_item)
        actions.addStretch(1)
        detalles_layout.addLayout(actions)

        self.quotation_items_table = QTableWidget(0, 7)
        self.quotation_items_table.setHorizontalHeaderLabels(["#", "Código", "Descripción", "Unidad", "Cantidad", "Precio Unitario", "Subtotal"])
        self.quotation_items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.quotation_items_table.verticalHeader().setVisible(False)
        detalles_layout.addWidget(self.quotation_items_table)
        layout.addWidget(detalles_box)

        # Totales
        totales_box = QGroupBox("Totales")
        totales_row = QHBoxLayout(totales_box)
        self.apply_itbis_checkbox = QCheckBox("Aplicar ITBIS (18%)")
        self.apply_itbis_checkbox.setChecked(False)
        self.apply_itbis_checkbox.stateChanged.connect(self._recalculate_totals)
        self.quotation_subtotal_label = QLabel("Subtotal: RD$ 0.00")
        self.quotation_itbis_label = QLabel("ITBIS: RD$ 0.00")
        self.quotation_total_label = QLabel("Total: RD$ 0.00")
        totales_row.addWidget(self.apply_itbis_checkbox)
        totales_row.addStretch(1)
        totales_row.addWidget(self.quotation_subtotal_label)
        totales_row.addWidget(self.quotation_itbis_label)
        totales_row.addWidget(self.quotation_total_label)
        layout.addWidget(totales_box)

        # Dentro de _build_ui(), REEMPLAZA el bloque equivalente de botones por este:
        # Nota: asumo que tus handlers son _preview_quotation y _save_quotation
        # (ajusta los nombres si los tienes diferentes).

        # Botones inferiores
        btn_preview_html = QPushButton("Vista Previa / PDF")
        btn_preview_html.setToolTip("Abrir vista previa HTML y exportar a PDF (WYSIWYG)")
        btn_preview_html.clicked.connect(self._preview_quotation)

        btn_save_quotation = QPushButton("Guardar en Base de Datos")
        btn_save_quotation.clicked.connect(self._save_quotation)

        layout.addWidget(btn_preview_html)
        layout.addWidget(btn_save_quotation)
    # Conexión para actualizar el vencimiento cuando cambia la fecha
        self.quotation_date.dateChanged.connect(lambda _d: self._refresh_due_date_label())

        # Inicializar el campo al cargar la UI
        self._refresh_due_date_label()
    # -----------------------
    # Small helpers & handlers
    # -----------------------
    def _toggle_notes(self, checked: bool):
        self.notes_toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.notes_box.setVisible(checked)

    def _open_item_picker(self):
        dlg = ItemPickerDialog(self, title="Agregar ítems a la Cotización")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        items = dlg.get_selected_items()
        for it in items:
            self._append_row(it.get("codigo"), it.get("nombre"), it.get("unidad"), it.get("cantidad"), it.get("precio"), it.get("subtotal"))
        self._recalculate_totals()

    def _append_row(self, code, name, unit, qty, price, subtotal=None):
        if subtotal is None:
            subtotal = qty * price
        row = self.quotation_items_table.rowCount()
        self.quotation_items_table.insertRow(row)
        self.quotation_items_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.quotation_items_table.setItem(row, 1, QTableWidgetItem(code))
        self.quotation_items_table.setItem(row, 2, QTableWidgetItem(name))
        self.quotation_items_table.setItem(row, 3, QTableWidgetItem(unit))
        self.quotation_items_table.setItem(row, 4, QTableWidgetItem(f"{qty:.2f}"))
        self.quotation_items_table.setItem(row, 5, QTableWidgetItem(f"{price:.2f}"))
        self.quotation_items_table.setItem(row, 6, QTableWidgetItem(f"{subtotal:.2f}"))

    def on_company_change(self):
        self._clear_form()

    def _suggest_third_party(self, search_by):
        query = self.quotation_client_rnc.text() if search_by == "rnc" else self.quotation_client_name.text()
        if len(query) < 2:
            self.quotation_suggestion_combo.hide(); return
        results = self.logic.search_third_parties(query, search_by=search_by) if hasattr(self.logic, "search_third_parties") else []
        self.quotation_suggestion_combo.clear()
        for item in results:
            self.quotation_suggestion_combo.addItem(f"{item['rnc']} - {item['name']}")
        self.quotation_suggestion_combo.setVisible(bool(results))

    def _select_suggestion(self, idx):
        val = self.quotation_suggestion_combo.currentText()
        if " - " in val:
            rnc, name = val.split(" - ", 1)
            self.quotation_client_rnc.setText(rnc); self.quotation_client_name.setText(name)
        self.quotation_suggestion_combo.hide()

    def _remove_item_row(self):
        r = self.quotation_items_table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un detalle para eliminar."); return
        self.quotation_items_table.removeRow(r)
        for i in range(self.quotation_items_table.rowCount()):
            self.quotation_items_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
        self._recalculate_totals()

    def _recalculate_totals(self):
        subtotal = 0.0
        for r in range(self.quotation_items_table.rowCount()):
            cell = self.quotation_items_table.item(r, 6)
            try:
                subtotal += float((cell.text() if cell else "0").replace(",", ""))
            except Exception:
                pass
        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis
        self.quotation_subtotal_label.setText(f"Subtotal: RD$ {subtotal:,.2f}")
        self.quotation_itbis_label.setText(f"ITBIS ({ITBIS_RATE*100:.0f}%): RD$ {itbis:,.2f}")
        self.quotation_total_label.setText(f"Total: RD$ {total:,.2f}")

    # -----------------------
    # Export / Preview handlers
    # -----------------------
    def _generate_quotation_template(self):
        try:
            fn, _ = QFileDialog.getSaveFileName(self, "Guardar plantilla de Cotización", "plantilla_cotizacion.xlsx", "Excel Files (*.xlsx)")
            if not fn:
                return
            save_path = fn if fn.lower().endswith(".xlsx") else fn + ".xlsx"
            from utils.quotation_templates import generate_quotation_template
            generate_quotation_template(save_path)
            QMessageBox.information(self, "Plantilla", f"Plantilla de cotización creada en:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla:\n{e}")

    def _generate_quotation_excel(self):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return

        quotation_data = {
            "company_id": company.get('id'),
            "company_name": company.get('name', ''),
            "quotation_date": self.quotation_date.date().toString("yyyy-MM-dd"),
            "client_name": self.quotation_client_name.text(),
            "client_rnc": self.quotation_client_rnc.text(),
            "notes": self.quotation_notes.toPlainText() if getattr(self, "notes_box", None) and self.notes_box.isVisible() else "",
            "currency": self.quotation_currency.text(),
            "apply_itbis": getattr(self, "apply_itbis_checkbox", None) and self.apply_itbis_checkbox.isChecked(),
            "itbis_rate": ITBIS_RATE,
        }

        items: List[Dict] = []
        for r in range(self.quotation_items_table.rowCount()):
            code_item = self.quotation_items_table.item(r, 1)
            desc = self.quotation_items_table.item(r, 2)
            unit_item = self.quotation_items_table.item(r, 3)
            qty = self.quotation_items_table.item(r, 4)
            price = self.quotation_items_table.item(r, 5)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({
                "code": code_item.text() if code_item else "",
                "description": desc.text() if desc else "",
                "unit": unit_item.text() if unit_item else "",
                "quantity": qty_val,
                "unit_price": price_val
            })

        if not items:
            QMessageBox.warning(self, "Ítems", "Agrega al menos un ítem a la cotización antes de exportar.")
            return

        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como Excel", "", "Excel Files (*.xlsx)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".xlsx") else fn + ".xlsx"
        quotation_data["company_id"] = company.get('id')
        try:
            export_quotation_excel_with_template(quotation_data, items, save_path, company_name=company.get('name', ''))
            QMessageBox.information(self, "Excel", f"Cotización guardada como Excel en:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar la cotización a Excel:\n{e}")

    def _generate_quotation_pdf(self):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return

        quotation_data = {
            "company_id": company.get('id'),
            "company_name": company.get('name', ''),
            "quotation_date": self.quotation_date.date().toString("yyyy-MM-dd"),
            "client_name": self.quotation_client_name.text(),
            "client_rnc": self.quotation_client_rnc.text(),
            "notes": self.quotation_notes.toPlainText() if getattr(self, "notes_box", None) and self.notes_box.isVisible() else "",
            "currency": self.quotation_currency.text(),
            "apply_itbis": getattr(self, "apply_itbis_checkbox", None) and self.apply_itbis_checkbox.isChecked(),
            "itbis_rate": ITBIS_RATE,
        }

        items: List[Dict] = []
        for r in range(self.quotation_items_table.rowCount()):
            code_item = self.quotation_items_table.item(r, 1)
            desc = self.quotation_items_table.item(r, 2)
            unit_item = self.quotation_items_table.item(r, 3)
            qty = self.quotation_items_table.item(r, 4)
            price = self.quotation_items_table.item(r, 5)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({
                "code": code_item.text() if code_item else "",
                "description": desc.text() if desc else "",
                "unit": unit_item.text() if unit_item else "",
                "quantity": qty_val,
                "unit_price": price_val
            })

        if not items:
            QMessageBox.warning(self, "Ítems", "Agrega al menos un ítem a la cotización antes de exportar.")
            return

        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como PDF", "", "PDF Files (*.pdf)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".pdf") else fn + ".pdf"
        quotation_data["company_id"] = company.get('id')
        try:
            export_quotation_pdf_with_template(quotation_data, items, save_path, company_name=company.get('name', ''))
            QMessageBox.information(self, "PDF", f"Cotización guardada como PDF en:\n{save_path}")
        except RuntimeError as re:
            QMessageBox.critical(self, "Dependencia", f"No se pudo generar PDF. Instala reportlab:\n{re}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar la cotización a PDF:\n{e}")

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

# Asegúrate de tener estos helpers en tu clase QuotationTab (o actualízalos)
    def _qdate_to_str(self, qdate) -> str:
        try:
            return f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        except Exception:
            return ""

    def _compute_quotation_due_date(self, quotation_date_str: str) -> str:
        """
        Devuelve quotation_date + 30 días en formato YYYY-MM-DD.
        """
        if not quotation_date_str:
            return ""
        try:
            d = datetime.strptime(quotation_date_str[:10], "%Y-%m-%d")
            return (d + timedelta(days=30)).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"[QTAB-DUE] error parse base: {e}")
            return ""

    def _refresh_due_date_label(self) -> None:
        """
        Actualiza el campo de solo lectura en la UI con el vencimiento calculado (+30 días).
        Muestra en dd/MM/yyyy para lectura rápida.
        """
        try:
            if not hasattr(self, "quotation_date") or not hasattr(self, "quotation_due_display"):
                return
            base_str = self._qdate_to_str(self.quotation_date.date())
            due_str = self._compute_quotation_due_date(base_str)
            if due_str:
                qd = QDate.fromString(due_str, "yyyy-MM-dd")
                pretty = qd.toString("dd/MM/yyyy") if qd.isValid() else due_str
            else:
                pretty = "N/A"
            self.quotation_due_display.setText(pretty)
            # Para que también puedas recuperar el valor exacto (yyyy-MM-dd) si lo necesitas:
            self.quotation_due_display.setProperty("raw_due_date", due_str)
            print(f"[QTAB-DUE] UI updated: base={base_str} -> due={due_str} (display={pretty})")
        except Exception as e:
            print(f"[QTAB-DUE] _refresh_due_date_label error: {e}")


    def _preview_quotation(self):
            """
            Vista previa de COTIZACIÓN.
            Utiliza el mismo template de diseño que la factura (quotation_template.html)
            y el mismo diálogo de vista previa.
            """
            import os, datetime
            
            # Asumimos que estas funciones se han importado
            from utils.app_paths import get_resource_path as resource_path
            from dialogs.quotation_preview_dialog import QuotationPreviewDialog as DocumentPreviewDialog
            from dialogs.invoice_preview_dialog import InvoicePreviewDialog # Mantener la referencia si existe

            company = self.get_current_company()
            if not company:
                QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
                return

            print("\n" + "="*80)
            print("[QUOTATION_TAB] _preview_quotation INICIO")
            print("="*80 + "\n")
            
            # 1) Carga base de empresa y plantilla (DEBE traer data completa)
            try:
                company_data, tpl = self._get_company_payload_for_preview()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo cargar la data de la empresa para la vista previa:\n{e}")
                return
            
            # 2) Fechas y número
            try:
                quotation_date_str = self.quotation_date.date().toString("yyyy-MM-dd")
            except Exception:
                quotation_date_str = datetime.date.today().strftime("%Y-%m-%d")
            
            # 3) Ítems + unidades
            try:
                items = self._collect_items_for_export()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al recolectar ítems:\n{e}")
                return

            if not items:
                QMessageBox.warning(self, "Ítems", "Agrega al menos un ítem a la cotización antes de previsualizar.")
                return

            # 4) Vencimiento automático
            try:
                due_auto = self._compute_quotation_due_date(quotation_date_str)
            except Exception:
                due_auto = ""
            
            # 5) Crear el Payload FINAL
            def _safe_text(name: str) -> str:
                # Helper: simplificado para evitar código redundante.
                w = getattr(self, name, None)
                if w is None: return ""
                if hasattr(w, "currentText"): return (w.currentText() or "").strip()
                if hasattr(w, "text"):        return (w.text() or "").strip()
                if hasattr(w, "toPlainText"): return (w.toPlainText() or "").strip()
                return ""

            quotation_data = {
                "type": "COTIZACIÓN", # CLAVE: Para que el template JS sepa qué mostrar
                "invoice_category": "Cotización", 
                
                "company_id": company_data.get("id"),
                "number": "", # El template JS lo calcula
                "ncf": "",
                "date": quotation_date_str,
                "due_date": due_auto, 
                
                "client_name": _safe_text("quotation_client_name"),
                "client_rnc":  _safe_text("quotation_client_rnc"),
                "currency":       _safe_text("quotation_currency"),
                "items": items,
                "notes": (self.quotation_notes.toPlainText() if getattr(self, "notes_box", None) and self.notes_box.isVisible() else _safe_text("quotation_notes")),
                "apply_itbis": self.apply_itbis_checkbox.isChecked(),
            }
            
            # Calcular display_number (usando lógica de factura si existe, o un placeholder)
            if hasattr(self, "_build_display_invoice_number"):
                quotation_data["display_number"] = self._build_display_invoice_number(company_data, "", prefix_label="COT", last_digits=6)
            else:
                # Placeholder, el JS lo recalculará
                quotation_data["display_number"] = f"COT-DRAFT-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}" 

            print(f"[QTAB-DUE] PREVIEW payload due='{due_auto}' from base='{quotation_date_str}'")
            
            # 6) Carga la ruta del template usando el helper de PyInstaller (resource_path)
            template_path = resource_path("templates", "quotation_template.html")
            print("[CHK] Template path (Resolved):", template_path, "exists=", os.path.exists(template_path))

            # 7) Abrir diálogo (usando InvoicePreviewDialog como alias del único diálogo disponible)
            if InvoicePreviewDialog is None:
                QMessageBox.critical(self, "Vista Previa", "DocumentPreviewDialog (alias) no está disponible.")
                return

            try:
                print("[QUOTATION_TAB] Abriendo Preview Dialog...")
                dlg = InvoicePreviewDialog(
                    company=company_data,
                    template=tpl,
                    invoice=quotation_data, # Usamos 'invoice' como nombre de parámetro en el diálogo genérico
                    parent=self,
                    template_path=template_path,
                    debug=False,
                )
                dlg.exec()
                print("[QUOTATION_TAB] Dialog cerrado")
            except Exception as e:
                QMessageBox.critical(self, "Vista Previa", f"No se pudo abrir la vista previa:\n{e}")    
  
    def _save_quotation(self):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida"); return

        subtotal = 0.0
        for r in range(self.quotation_items_table.rowCount()):
            sub = self.quotation_items_table.item(r, 6)
            try:
                subtotal += float(sub.text().replace(",", "")) if sub and sub.text().strip() else 0.0
            except Exception:
                pass
        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis

        data = {
            "company_id": company['id'],
            "quotation_date": self.quotation_date.date().toString("yyyy-MM-dd"),
            "client_name": self.quotation_client_name.text(),
            "client_rnc": self.quotation_client_rnc.text(),
            "notes": self.quotation_notes.toPlainText() if self.notes_box.isVisible() else "",
            "currency": self.quotation_currency.text(),
            "total_amount": total,
            "excel_path": "",
            "pdf_path": "",
        }
        items = []
        for r in range(self.quotation_items_table.rowCount()):
            desc = self.quotation_items_table.item(r, 2)
            qty = self.quotation_items_table.item(r, 4)
            price = self.quotation_items_table.item(r, 5)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0; price_val = 0.0
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})

        quotation_id = self.logic.add_quotation(data, items)
        QMessageBox.information(self, "Cotización", f"Cotización creada (ID: {quotation_id})")
        self._clear_form()
        self.quotation_saved.emit(quotation_id)

    def _clear_form(self):
        self.quotation_date.setDate(QDate.currentDate())
        self.quotation_client_name.clear(); self.quotation_client_rnc.clear()
        self.quotation_notes.clear()
        self.notes_box.setVisible(False)
        self.notes_toggle.setChecked(False)
        self.notes_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.quotation_currency.setText(DEFAULT_CURRENCY)
        self.quotation_items_table.setRowCount(0)
        self.quotation_subtotal_label.setText("Subtotal: RD$ 0.00")
        self.quotation_itbis_label.setText("ITBIS: RD$ 0.00")
        self.quotation_total_label.setText("Total: RD$ 0.00")
        self.apply_itbis_checkbox.setChecked(False)

    def _get_company_payload_for_preview(self):
            """
            Carga datos completos de la empresa desde la BD para el preview.
            Prioriza los datos completos de la BD sobre los datos básicos de la GUI.
            """
            company_min = self.get_current_company() or {}
            company_id = company_min.get("id")

            if not company_id:
                print("[QuotationTab] ERROR: No se pudo obtener company_id")
                return {}, {}

            # **PASO CRÍTICO: Obtener detalles completos de la BD**
            details_db = {}
            try:
                if hasattr(self.logic, "get_company_details"):
                    details_db = self.logic.get_company_details(company_id) or {}
                    print(f"[QuotationTab] get_company_details({company_id}) RESULTADO COMPLETO: {details_db}") 
                else:
                    print("[QuotationTab] ERROR: self.logic no tiene el método get_company_details")
            except Exception as e:
                print(f"[QuotationTab] ERROR en get_company_details: {e}")
                details_db = {}

            # Consolidar datos, dando prioridad a details_db
            details = {**company_min, **details_db} # Combina ambos diccionarios

            # Composición de campos:

            # Dirección
            a1 = (details.get("address_line1") or "").strip()
            a2 = (details.get("address_line2") or "").strip()
            addr = (details.get("address") or "").strip()
            
            if a1 or a2:
                address_full = f"{a1} {a2}".strip()
            else:
                address_full = addr
            if not address_full:
                address_full = "Dirección no especificada"

            # Firma
            signature = (details.get("signature_name") or "").strip()
            
            logo_rel = (details.get("logo_path") or "").strip()

            payload = {
                "id": company_id,
                "name": details.get("name", "N/A"),
                "rnc": details.get("rnc", "N/A"),
                "address_line1": a1,
                "address_line2": a2,
                "address": address_full, # RESUELTO
                "phone": details.get("phone", ""),
                "email": details.get("email", ""),
                "signature_name": signature, # RESUELTO
                "authorized_name": signature,
                "logo_path": logo_rel,
            }

            tpl = {}
            try:
                tpl = load_template(int(company_id)) or {}
            except Exception:
                tpl = {}

            print(f"[QuotationTab] company_payload_for_preview FINAL: {payload}")

            return payload, tpl


    def _collect_items_for_export(self):
        """
        Cotización: devuelve los ítems tomando SIEMPRE la unidad desde el maestro 'items.unit'.
        Usa la tabla correcta (quotation_items_table).
        """
        print("[HIT] _collect_items_for_export (QUOTATION)")
        return self._collect_items_for_export_from_table(self.quotation_items_table)


    def _collect_items_for_export_from_table(self, table):
        """
        Recorre la tabla de cotización y construye el payload de ítems.
        - Prioriza SIEMPRE la unidad desde la BD (items.unit).
        - Primero intenta por código; si no hay, intenta por nombre EXACTO.
        - Actualiza visualmente la celda 'Unidad' en la tabla con la unidad del maestro.
        """
        DEFAULT_UNIT_FALLBACK = "UND"  # usa un único fallback consistente
        items = []

        row_count = table.rowCount() if table else 0
        for r in range(row_count):
            code_item = table.item(r, 1)  # Código
            desc_item = table.item(r, 2)  # Descripción
            unit_item = table.item(r, 3)  # Unidad (será sobrescrita por la del maestro)
            qty_item  = table.item(r, 4)  # Cantidad
            price_item= table.item(r, 5)  # P. Unitario

            code = (code_item.text().strip() if code_item and code_item.text() else "")
            desc = (desc_item.text().strip() if desc_item and desc_item.text() else "")

            # 1) Intentar unidad por código en 'items'
            unit_master = ""
            try:
                if code and hasattr(self.logic, "get_item_by_code"):
                    found = self.logic.get_item_by_code(code) or {}
                    unit_master = (found.get("unit") or "").strip()
            except Exception as e:
                print(f"[QUOTATION] get_item_by_code error: {e}")

            # 2) Si no hay code o no devolvió, intenta por nombre EXACTO en 'items'
            if not unit_master and desc:
                try:
                    if hasattr(self.logic, "conn") and self.logic.conn:
                        cur = self.logic.conn.cursor()
                        cur.execute("SELECT unit FROM items WHERE name = ? LIMIT 1", (desc,))
                        row = cur.fetchone()
                        if row:
                            # row puede ser sqlite3.Row o tupla según row_factory
                            unit_master = (row["unit"] if isinstance(row, dict) else row[0]) or ""
                            unit_master = unit_master.strip()
                except Exception as e:
                    print(f"[QUOTATION] lookup unit by exact name error: {e}")

            # 3) Resolver unidad final
            resolved_unit = unit_master or DEFAULT_UNIT_FALLBACK

            # 4) Actualizar UI si difiere
            try:
                from PyQt6.QtWidgets import QTableWidgetItem  # por si no estaba importado en este archivo
                current_unit = (unit_item.text().strip() if unit_item and unit_item.text() else "")
                if resolved_unit != current_unit:
                    table.setItem(r, 3, QTableWidgetItem(resolved_unit))
            except Exception:
                pass

            # 5) Cantidad y precio
            try:
                qty = float((qty_item.text() if qty_item else "0").replace(",", "").strip() or 0)
            except Exception:
                qty = 0.0
            try:
                price = float((price_item.text() if price_item else "0").replace(",", "").strip() or 0)
            except Exception:
                price = 0.0

            print(f"[QUOTATION] row={r} code='{code}' desc='{desc}' unit_master='{unit_master}' unit_final='{resolved_unit}'")

            items.append({
                "code": code,
                "description": desc,
                "unit": resolved_unit,        # SIEMPRE del maestro
                "quantity": qty,
                "unit_price": price,
            })

        return items