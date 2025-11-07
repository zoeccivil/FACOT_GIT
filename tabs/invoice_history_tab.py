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
    from dialogs.invoice_preview_dialog import InvoicePreviewDialog
except Exception:
    InvoicePreviewDialog = None

# Carga de plantilla
try:
    from utils.template_manager import load_template
except Exception:
    def load_template(company_id: int):
        return {}

# Resolver logo relativo -> file:///
from utils.asset_paths import resolve_logo_uri

try:
    from utils.template_integration import export_invoice_pdf_with_template, export_invoice_excel_with_template
except Exception:
    def export_invoice_pdf_with_template(*args, **kwargs):
        raise RuntimeError("export_invoice_pdf_with_template no disponible")

    def export_invoice_excel_with_template(*args, **kwargs):
        raise RuntimeError("export_invoice_excel_with_template no disponible")


class InvoiceHistoryTab(QWidget):
    def __init__(self, logic, get_current_company_callable, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.get_current_company = get_current_company_callable
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Historial de Facturas"))
        # Add an actions column at the end
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Fecha", "NCF", "Cliente", "RNC", "Moneda", "Total", "Acciones"])
        # Stretch columns and auto-size actions
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
        facturas = self.logic.get_facturas(company['id']) if hasattr(self.logic, "get_facturas") else []
        self.table.setRowCount(0)
        for f in facturas:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(f.get('id', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(f.get('invoice_date', '')))
            self.table.setItem(row, 2, QTableWidgetItem(f.get('invoice_number', '') or f.get('ncf', '')))
            self.table.setItem(row, 3, QTableWidgetItem(f.get('third_party_name', '') or f.get('client_name', '')))
            self.table.setItem(row, 4, QTableWidgetItem(f.get('rnc', '') or f.get('client_rnc', '')))
            self.table.setItem(row, 5, QTableWidgetItem(f.get('currency', '')))
            total = f.get('total_amount', f.get('total', 0.0)) or 0.0
            self.table.setItem(row, 6, QTableWidgetItem(f"{total:,.2f}"))
            # Actions cell (buttons)
            self._add_invoice_action_buttons(row, f)

    def _add_invoice_action_buttons(self, row: int, record: Dict[str, Any]):
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

        # Connect handlers capturing the record
        btn_preview.clicked.connect(lambda _, rec=record: self._open_invoice_preview(rec))
        btn_pdf.clicked.connect(lambda _, rec=record: self._export_invoice_pdf(rec))
        btn_excel.clicked.connect(lambda _, rec=record: self._export_invoice_excel(rec))

        self.table.setCellWidget(row, 7, widget)

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
        # Fallback de dirección desde plantilla si está vacía
        if (not company_data["address_line1"] or company_data["address_line1"].strip() == "") and tpl.get("header_lines"):
            header_lines = tpl.get("header_lines") or []
            comp_addr = " · ".join([ln for ln in header_lines if ln and ln.strip()])
            if comp_addr:
                company_data["address_line1"] = comp_addr

        # Resolver logo relativo usando assets_root
        logo_rel = tpl.get("logo_path") or company.get("logo_path") or ""
        company_data["logo_path"] = resolve_logo_uri(logo_rel) or ""
        return company_data, tpl

    def _get_record_items(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = record.get('items') or record.get('details') or []
        if not items and hasattr(self.logic, "get_invoice_items"):
            try:
                items = self.logic.get_invoice_items(record.get('id'))
            except Exception:
                items = []
        normalized = []
        for it in items:
            normalized.append({
                "code": it.get("code") or it.get("codigo") or it.get("item_code") or "",
                "description": it.get("description") or it.get("descripcion") or it.get("nombre") or "",
                "unit": it.get("unit") or it.get("unidad") or it.get("u") or "",
                "quantity": float(it.get("quantity", it.get("cantidad", 0)) or 0),
                "unit_price": float(it.get("unit_price", it.get("precio", it.get("valor", 0))) or 0)
            })
        return normalized

    def _open_invoice_preview(self, record: Dict[str, Any]):
        company_data, tpl = self._resolve_company_and_template()
        inv_type = record.get("invoice_type") or record.get("type") or "FACTURA"
        if isinstance(inv_type, str) and inv_type.lower() == "emitida":
            inv_type = "FACTURA"
        ncf_val = record.get("invoice_number") or record.get("ncf") or ""
        display_number = self._build_display_invoice_number(company_data, ncf_val, prefix_label="FACT", last_digits=6)

        # ✅ CAMBIO CLAVE: Detectar si la factura original tenía ITBIS
        # Método 1: Si el record tiene el campo explícito
        apply_itbis = record.get("apply_itbis")
        
        # Método 2 (fallback): Inferir por diferencia entre subtotal e itbis
        if apply_itbis is None:
            try:
                total = float(record.get("total_amount", 0) or 0)
                itbis = float(record.get("itbis", 0) or 0)
                # Si hay ITBIS registrado y es >0, entonces sí se aplicó
                apply_itbis = (itbis > 0.01)
            except Exception:
                apply_itbis = True  # Por defecto True en facturas si no se puede determinar

        invoice_payload = {
            "company_id": record.get("company_id", company_data.get("id")),
            "number": record.get("invoice_number") or record.get("number") or ncf_val,
            "ncf": ncf_val,
            "date": record.get("invoice_date") or record.get("date") or "",
            "client_name": record.get("third_party_name") or record.get("client_name") or "",
            "client_rnc": record.get("rnc") or record.get("client_rnc") or "",
            "currency": record.get("currency") or "",
            "items": self._get_record_items(record),
            "notes": record.get("notes", "") or "",
            "type": inv_type,
            "display_number": display_number,
            "apply_itbis": apply_itbis,  # ✅ USAR EL VALOR REAL
        }

        if InvoicePreviewDialog is None:
            QMessageBox.warning(self, "Vista Previa", "InvoicePreviewDialog no disponible.")
            return

        template_path = os.path.join(os.getcwd(), "templates", "invoice_template.html")
        dlg = InvoicePreviewDialog(company=company_data, template=tpl, invoice=invoice_payload, parent=self, template_path=template_path, debug=False)
        dlg.exec()

    def _export_invoice_pdf(self, record: Dict[str, Any]):
        company = self.get_current_company()
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida"); return
        
        # ✅ Detectar apply_itbis igual que en preview
        apply_itbis = record.get("apply_itbis")
        if apply_itbis is None:
            try:
                itbis = float(record.get("itbis", 0) or 0)
                apply_itbis = (itbis > 0.01)
            except Exception:
                apply_itbis = True
        
        invoice_payload = {
            "company_id": record.get("company_id", company.get('id')),
            "company_name": company.get('name', ''),
            "invoice_date": record.get("invoice_date", ""),
            "invoice_number": record.get("invoice_number") or record.get("ncf") or "",
            "client_name": record.get("third_party_name") or record.get("client_name") or "",
            "client_rnc": record.get("rnc") or record.get("client_rnc") or "",
            "apply_itbis": apply_itbis,  # ✅ USAR EL VALOR REAL
            "itbis_rate": ITBIS_RATE
        }
        items = self._get_record_items(record)
        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como PDF", f"factura_{invoice_payload.get('invoice_number','')}.pdf", "PDF Files (*.pdf)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".pdf") else fn + ".pdf"
        try:
            export_invoice_pdf_with_template(invoice_payload, items, save_path, company_name=company.get('name',''))
            QMessageBox.information(self, "PDF", f"Factura guardada como PDF en:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar la factura a PDF:\n{e}")

    def _export_invoice_excel(self, record: Dict[str, Any]):
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
                apply_itbis = True
        
        invoice_payload = {
            "company_id": record.get("company_id", company.get('id')),
            "company_name": company.get('name', ''),
            "invoice_date": record.get("invoice_date", ""),
            "invoice_number": record.get("invoice_number") or record.get("ncf") or "",
            "client_name": record.get("third_party_name") or record.get("client_name") or "",
            "client_rnc": record.get("rnc") or record.get("client_rnc") or "",
            "apply_itbis": apply_itbis,  # ✅ USAR EL VALOR REAL
            "itbis_rate": ITBIS_RATE
        }
        items = self._get_record_items(record)
        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como Excel", f"factura_{invoice_payload.get('invoice_number','')}.xlsx", "Excel Files (*.xlsx)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".xlsx") else fn + ".xlsx"
        try:
            export_invoice_excel_with_template(invoice_payload, items, save_path, company_name=company.get('name',''))
            QMessageBox.information(self, "Excel", f"Factura guardada como Excel en:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar la factura a Excel:\n{e}")

