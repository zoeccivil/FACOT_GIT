from __future__ import annotations

import os
from typing import List, Dict, Any, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QWidget as QWidgetAlias, QFileDialog, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

from constants import ITBIS_RATE

try:
    from dialogs.quotation_preview_dialog import QuotationPreviewDialog
except Exception:
    QuotationPreviewDialog = None

# Carga de plantilla
try:
    from utils.template_manager import load_template
except Exception:
    def load_template(company_id: int):
        return {}

# Resolver logo relativo -> file:///
from utils.asset_paths import resolve_logo_uri

try:
    from utils.template_integration import export_quotation_pdf_with_template, export_quotation_excel_with_template
except Exception:
    def export_quotation_pdf_with_template(*args, **kwargs):
        raise RuntimeError("export_quotation_pdf_with_template no disponible")

    def export_quotation_excel_with_template(*args, **kwargs):
        raise RuntimeError("export_quotation_excel_with_template no disponible")


class QuotationHistoryTab(QWidget):
    def __init__(self, logic, get_current_company_callable, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.get_current_company = get_current_company_callable
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Historial de Cotizaciones"))
        # add actions column
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Fecha", "Cliente", "RNC", "Moneda", "Total", "Notas", "Acciones"])
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        btn_refresh = QPushButton("Refrescar Historial")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

    def refresh(self):
        company = self.get_current_company()
        if not company:
            return
        cotizaciones = self.logic.get_quotations(company['id']) if hasattr(self.logic, "get_quotations") else []
        self.table.setRowCount(0)
        for q in cotizaciones:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(q.get('id', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(q.get('quotation_date', '')))
            self.table.setItem(row, 2, QTableWidgetItem(q.get('client_name', '')))
            self.table.setItem(row, 3, QTableWidgetItem(q.get('client_rnc', '')))
            self.table.setItem(row, 4, QTableWidgetItem(q.get('currency', '')))
            total = q.get('total_amount', q.get('total', 0.0)) or 0.0
            self.table.setItem(row, 5, QTableWidgetItem(f"{total:,.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(q.get('notes', '')))
            # actions
            self._add_quotation_action_buttons(row, q)

    def _add_quotation_action_buttons(self, row: int, record: Dict[str, Any]):
        widget = QWidgetAlias()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        btn_preview = QPushButton("Vista Previa")
        btn_pdf = QPushButton("PDF")
        btn_excel = QPushButton("Excel")
        layout.addWidget(btn_preview)
        layout.addWidget(btn_pdf)
        layout.addWidget(btn_excel)
        widget.setLayout(layout)

        btn_preview.clicked.connect(lambda _, rec=record: self._open_quotation_preview(rec))
        btn_pdf.clicked.connect(lambda _, rec=record: self._export_quotation_pdf(rec))
        btn_excel.clicked.connect(lambda _, rec=record: self._export_quotation_excel(rec))

        self.table.setCellWidget(row, 7, widget)

    def _resolve_company_and_template(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        company = self.get_current_company() or {}
        tpl = {}
        try:
            tpl = load_template(int(company.get('id')))
        except Exception:
            tpl = {}
        company_data = {
            "id": company.get('id'),
            "name": company.get('name'),
            "rnc": company.get('rnc') or company.get('rnc_number') or "",
            "address_line1": company.get('address') or company.get('address_line1') or "",
            "address_line2": company.get('address_line2') or "",
            "phone": company.get('phone') or company.get('telefono') or "",
            "email": company.get('email') or company.get('correo') or "",
            "logo_path": ""
        }
        # Resolver logo relativo usando assets_root
        logo_rel = tpl.get("logo_path") or company.get("logo_path") or ""
        company_data["logo_path"] = resolve_logo_uri(logo_rel) or ""
        return company_data, tpl

    def _get_record_items(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = record.get('items') or record.get('details') or []
        if not items and hasattr(self.logic, "get_quotation_items"):
            try:
                items = self.logic.get_quotation_items(record.get('id'))
            except Exception:
                items = []
        normalized = []
        for it in items:
            normalized.append({
                "code": it.get("code") or it.get("codigo") or "",
                "description": it.get("description") or it.get("descripcion") or "",
                "unit": it.get("unit") or it.get("unidad") or "",
                "quantity": float(it.get("quantity", it.get("cantidad", 0)) or 0),
                "unit_price": float(it.get("unit_price", it.get("precio", 0)) or 0)
            })
        return normalized

    def _open_quotation_preview(self, record: Dict[str, Any]):
        company_data, tpl = self._resolve_company_and_template()
        
        # ✅ CAMBIO CLAVE: Detectar si la cotización original tenía ITBIS
        apply_itbis = record.get("apply_itbis")
        if apply_itbis is None:
            try:
                total = float(record.get("total_amount", 0) or 0)
                itbis = float(record.get("itbis", 0) or 0)
                apply_itbis = (itbis > 0.01)
            except Exception:
                apply_itbis = False  # Por defecto False en cotizaciones
        
        quotation_payload = {
            "id": record.get("id"),
            "number": record.get("quotation_number") or record.get("number") or "",
            "date": record.get("quotation_date") or record.get("date") or "",
            "client_name": record.get("client_name") or record.get("third_party_name") or "",
            "client_rnc": record.get("client_rnc") or record.get("rnc") or "",
            "currency": record.get("currency") or "",
            "items": self._get_record_items(record),
            "notes": record.get("notes", "") or "",
            "apply_itbis": apply_itbis,  # ✅ USAR EL VALOR REAL
        }

        if QuotationPreviewDialog is None:
            QMessageBox.warning(self, "Vista Previa", "QuotationPreviewDialog no disponible.")
            return

        template_path = os.path.join(os.getcwd(), "templates", "quotation_template.html")
        dlg = QuotationPreviewDialog(company=company_data, template=tpl, quotation=quotation_payload, parent=self, template_path=template_path, debug=False)
        dlg.exec()

    def _export_quotation_pdf(self, record: Dict[str, Any]):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida"); return
        
        # ✅ Detectar apply_itbis
        apply_itbis = record.get("apply_itbis")
        if apply_itbis is None:
            try:
                itbis = float(record.get("itbis", 0) or 0)
                apply_itbis = (itbis > 0.01)
            except Exception:
                apply_itbis = False  # Default false en cotizaciones
        
        invoice_payload = {
            "company_id": record.get("company_id", company.get('id')),
            "company_name": company.get('name', ''),
            "quotation_date": record.get("quotation_date", ""),
            "quotation_number": record.get("quotation_number") or record.get("number") or "",
            "client_name": record.get("client_name") or record.get("third_party_name") or "",
            "client_rnc": record.get("client_rnc") or record.get("rnc") or "",
            "apply_itbis": apply_itbis,  # ✅ USAR EL VALOR REAL
            "itbis_rate": ITBIS_RATE
        }
        items = self._get_record_items(record)
        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como PDF", f"cotizacion_{invoice_payload.get('quotation_number','')}.pdf", "PDF Files (*.pdf)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".pdf") else fn + ".pdf"
        try:
            export_quotation_pdf_with_template(invoice_payload, items, save_path, company_name=company.get('name',''))
            QMessageBox.information(self, "PDF", f"Cotización guardada como PDF en:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar la cotización a PDF:\n{e}")

    def _export_quotation_excel(self, record: Dict[str, Any]):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida"); return
        
        # ✅ Detectar apply_itbis
        apply_itbis = record.get("apply_itbis")
        if apply_itbis is None:
            try:
                itbis = float(record.get("itbis", 0) or 0)
                apply_itbis = (itbis > 0.01)
            except Exception:
                apply_itbis = False
        
        invoice_payload = {
            "company_id": record.get("company_id", company.get('id')),
            "company_name": company.get('name', ''),
            "quotation_date": record.get("quotation_date", ""),
            "quotation_number": record.get("quotation_number") or record.get("number") or "",
            "client_name": record.get("client_name") or record.get("third_party_name") or "",
            "client_rnc": record.get("client_rnc") or record.get("rnc") or "",
            "apply_itbis": apply_itbis,  # ✅ USAR EL VALOR REAL
            "itbis_rate": ITBIS_RATE
        }
        items = self._get_record_items(record)
        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como Excel", f"cotizacion_{invoice_payload.get('quotation_number','')}.xlsx", "Excel Files (*.xlsx)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".xlsx") else fn + ".xlsx"
        try:
            export_quotation_excel_with_template(invoice_payload, items, save_path, company_name=company.get('name',''))
            QMessageBox.information(self, "Excel", f"Cotización guardada como Excel en:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar la cotización a Excel:\n{e}")