from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QLineEdit, QTextEdit, QDateEdit, QMessageBox, QCheckBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from db_manager import DBManager
import datetime
from utils import (
    generate_invoice_pdf, generate_invoice_excel,
    generate_quotation_pdf, generate_quotation_excel
)
from PyQt6.QtWidgets import QFileDialog
import os
from PyQt6.QtWidgets import QInputDialog
from items_management_window import ItemsManagementWindow
from PyQt6.QtWidgets import QHeaderView

# --- Constantes que puedes mover a un archivo aparte si prefieres ---
NCF_TYPES = {
    "Crédito Fiscal (B01)": "B01",
    "Consumidor Final (B02)": "B02",
    "Gubernamental (B15)": "B15",
    "Régimen Especial (B14)": "B14",
    "Nota de Crédito (B04)": "B04",
}
ITBIS_RATE = 0.18
DEFAULT_CURRENCY = "RD$"

import sys

# --- Configuración y lógica ---
import config_facot  # Configuración (si usas este archivo)
import facot_config  # Configuración (si usas este archivo)
from logic import LogicController

# --- PyQt6 Widgets y GUI ---
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QLineEdit, QTextEdit, QDateEdit, 
    QMessageBox, QCheckBox, QSpacerItem, QSizePolicy, QMenuBar, QMenu, QFileDialog
)
from PyQt6.QtGui import QAction  # Importa QAction desde QtGui en PyQt6

# --- Ventanas secundarias ---
from settings_window import SettingsWindow
from company_management_window import CompanyManagementWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Facturas y Cotizaciones")
        self.resize(1100, 790)
        self._init_db()
        self._setup_ui()
        self._setup_menu()

    def _init_db(self):
        import facot_config
        db_path = facot_config.get_db_path()
        if not db_path or not os.path.isfile(db_path):
            filename, _ = QFileDialog.getOpenFileName(self, "Selecciona tu archivo de base de datos", "", "Database Files (*.db);;Todos los archivos (*)")
            if filename:
                facot_config.set_db_path(filename)
                db_path = filename
            else:
                QMessageBox.critical(self, "Error", "No se seleccionó una base de datos. El programa se cerrará.")
                sys.exit(1)
        self.logic = LogicController(db_path)


    def _setup_menu(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # --- Menú Archivo ---
        archivo_menu = QMenu("&Archivo", self)
        menu_bar.addMenu(archivo_menu)

        abrir_base_action = QAction("Abrir Base de Datos...", self)
        abrir_base_action.triggered.connect(self._abrir_base_de_datos)
        archivo_menu.addAction(abrir_base_action)

        crear_base_action = QAction("Crear Nueva Base de Datos...", self)
        crear_base_action.triggered.connect(self._crear_nueva_base_de_datos)
        archivo_menu.addAction(crear_base_action)

        backup_action = QAction("Hacer Backup...", self)
        backup_action.triggered.connect(self._hacer_backup)
        archivo_menu.addAction(backup_action)

        archivo_menu.addSeparator()
        salir_action = QAction("Salir", self)
        salir_action.triggered.connect(self.close)
        archivo_menu.addAction(salir_action)

        # --- Menú Reportes ---
        reportes_menu = QMenu("&Reportes", self)
        menu_bar.addMenu(reportes_menu)
        reporte_ventas_action = QAction("Reporte de Ventas", self)
        reporte_ventas_action.triggered.connect(self._abrir_reporte_ventas)
        reportes_menu.addAction(reporte_ventas_action)
        reporte_clientes_action = QAction("Reporte por Cliente", self)
        reporte_clientes_action.triggered.connect(self._abrir_reporte_clientes)
        reportes_menu.addAction(reporte_clientes_action)
        # ...agrega más reportes...

        # --- Menú Opciones ---
        opciones_menu = QMenu("&Opciones", self)
        menu_bar.addMenu(opciones_menu)
        config_rutas_action = QAction("Configurar Rutas...", self)
        config_rutas_action.triggered.connect(self._abrir_configuracion)
        opciones_menu.addAction(config_rutas_action)

        gestionar_empresas_action = QAction("Gestionar Empresas...", self)
        gestionar_empresas_action.triggered.connect(self._abrir_gestion_empresas)
        opciones_menu.addAction(gestionar_empresas_action)

        gestion_items_action = QAction("Gestionar Ítems...", self)
        gestion_items_action.triggered.connect(self._abrir_gestion_items)
        opciones_menu.addAction(gestion_items_action)
    # --- Métodos de acciones del menú ---
    def _abrir_base_de_datos(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir Base de Datos", "", "Database Files (*.db);;Todos los archivos (*)")
        if filename:
            import facot_config
            facot_config.set_db_path(filename)
            self.logic = LogicController(filename)
            self._populate_companies()
            QMessageBox.information(self, "Base de Datos", "Base de datos abierta correctamente.")

    def _crear_nueva_base_de_datos(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Crear Nueva Base de Datos", "", "Database Files (*.db);;Todos los archivos (*)")
        if filename:
            import facot_config
            facot_config.set_db_path(filename)
            self.logic = LogicController(filename)
            self._populate_companies()
            QMessageBox.information(self, "Base de Datos", "Nueva base de datos creada correctamente.")

    def _hacer_backup(self):
        import shutil
        db_path = self.logic.db_path
        backup_path, _ = QFileDialog.getSaveFileName(self, "Guardar Backup de la Base de Datos", "", "Database Files (*.db);;Todos los archivos (*)")
        if backup_path:
            shutil.copy2(db_path, backup_path)
            QMessageBox.information(self, "Backup", f"Backup guardado en:\n{backup_path}")

    def _abrir_configuracion(self):
        dlg = SettingsWindow(self.logic, self)
        dlg.exec()

    def _abrir_gestion_empresas(self):
        dlg = CompanyManagementWindow(self, self.logic)
        dlg.exec()

    def _abrir_reporte_ventas(self):
        # Implementa apertura de tu ventana de reportes de ventas
        QMessageBox.information(self, "Reporte", "Aquí se abriría el reporte de ventas.")

    def _abrir_reporte_clientes(self):
        # Implementa apertura de tu ventana de reportes por cliente
        QMessageBox.information(self, "Reporte", "Aquí se abriría el reporte por cliente.")

    def _populate_companies(self):
        self.company_selector.clear()
        companies = self.logic.get_all_companies()
        self.companies = {str(c['name']): c for c in companies}
        self.company_selector.addItems(self.companies.keys())

    # --- LEER LA RUTA DE PLANTILLA ---
    def _get_template_path(self):
        path = facot_config.get_template_path()
        if not path or not os.path.isfile(path):
            filename, _ = QFileDialog.getOpenFileName(self, "Selecciona la plantilla de factura", "", "Archivos Excel (*.xlsx);;Todos los archivos (*)")
            if filename:
                facot_config.set_template_path(filename)
                path = filename
        return path

    # --- LEER LA CARPETA DE SALIDA ---
    def _get_output_folder(self):
        folder = facot_config.get_output_folder()
        if not folder or not os.path.isdir(folder):
            foldername = QFileDialog.getExistingDirectory(self, "Selecciona la carpeta de salida")
            if foldername:
                facot_config.set_output_folder(foldername)
                folder = foldername
        return folder

    # --- GUARDAR EMPRESA ACTIVA ---
    def _set_empresa_activa(self, company_id):
        facot_config.set_empresa_activa(company_id)

    # --- LEER EMPRESA ACTIVA ---
    def _get_empresa_activa(self):
        return facot_config.get_empresa_activa()

    # --- LEER Y GUARDAR CONFIGURACIÓN POR EMPRESA ---
    def _get_empresa_config(self, company_id):
        return facot_config.get_empresa_config(company_id)

    def _set_empresa_config(self, company_id, empresa_cfg):
        facot_config.set_empresa_config(company_id, empresa_cfg)
        
    def _setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # --- Selector de Empresa ---
        self.company_selector = QComboBox()
        self._populate_companies()
        layout.addWidget(QLabel("Empresa:"))
        layout.addWidget(self.company_selector)
        self.company_selector.currentIndexChanged.connect(self._on_company_change)  # <-- Agrega aquí

        # --- Tabs: Factura / Cotización ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self._factura_tab(), "Factura")
        self.tabs.addTab(self._cotizacion_tab(), "Cotización")
        self.tabs.addTab(self._historial_factura_tab(), "Historial de Facturas")
        self.tabs.addTab(self._historial_cotizacion_tab(), "Historial de Cotizaciones")
        layout.addWidget(self.tabs)        

    # ----- TAB FACTURA -----
    def _factura_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # --- 1. Datos de la Factura ---
        factura_group = QWidget()
        factura_layout = QHBoxLayout(factura_group)

        # Tipo de NCF
        self.ncf_type_combo = QComboBox()
        self.ncf_type_combo.addItems(NCF_TYPES.keys())
        self.ncf_type_combo.currentIndexChanged.connect(self._update_ncf_sequence)
        factura_layout.addWidget(QLabel("Tipo de NCF:"))
        factura_layout.addWidget(self.ncf_type_combo)

        # NCF asignado (solo lectura)
        self.ncf_number_edit = QLineEdit()
        self.ncf_number_edit.setReadOnly(True)
        factura_layout.addWidget(QLabel("NCF Asignado:"))
        factura_layout.addWidget(self.ncf_number_edit)

        # Fecha y vencimiento
        self.invoice_date = QDateEdit(QDate.currentDate())
        self.invoice_date.setCalendarPopup(True)
        factura_layout.addWidget(QLabel("Fecha:"))
        factura_layout.addWidget(self.invoice_date)
        self.invoice_due_date = QDateEdit(QDate.currentDate())
        self.invoice_due_date.setCalendarPopup(True)
        factura_layout.addWidget(QLabel("Vencimiento:"))
        factura_layout.addWidget(self.invoice_due_date)

        layout.addWidget(QLabel("1. Datos de la Factura"))
        layout.addWidget(factura_group)

        # --- 2. Datos del Cliente ---
        cliente_group = QWidget()
        cliente_layout = QHBoxLayout(cliente_group)
        self.client_rnc = QLineEdit()
        self.client_name = QLineEdit()
        self.client_rnc.setPlaceholderText("Buscar RNC/Cédula...")
        self.client_name.setPlaceholderText("Buscar nombre/razón social...")
        self.client_rnc.textChanged.connect(lambda: self._suggest_third_party('rnc'))
        self.client_name.textChanged.connect(lambda: self._suggest_third_party('name'))

        cliente_layout.addWidget(QLabel("RNC/Cédula:"))
        cliente_layout.addWidget(self.client_rnc)
        cliente_layout.addWidget(QLabel("Nombre/Razón Social:"))
        cliente_layout.addWidget(self.client_name)

        # Sugerencias tipo combobox para cliente
        self.suggestion_combo = QComboBox()
        self.suggestion_combo.hide()
        self.suggestion_combo.setEditable(False)
        self.suggestion_combo.activated.connect(self._select_suggestion)
        cliente_layout.addWidget(self.suggestion_combo)
        layout.addWidget(QLabel("2. Datos del Cliente"))
        layout.addWidget(cliente_group)

        # --- 3. Detalles de la Factura ---
        details_group = QWidget()
        details_layout = QVBoxLayout(details_group)

        # Formulario para agregar un item
        item_form = QHBoxLayout()
        self.item_desc = QLineEdit(); self.item_desc.setPlaceholderText("Descripción")
        self.item_qty = QLineEdit(); self.item_qty.setPlaceholderText("Cantidad")
        self.item_price = QLineEdit(); self.item_price.setPlaceholderText("Precio Unitario")
        btn_add_item = QPushButton("Agregar Detalle")
        btn_add_item.clicked.connect(self._add_invoice_item_row)
        item_form.addWidget(QLabel("Descripción:")); item_form.addWidget(self.item_desc)
        item_form.addWidget(QLabel("Cant:")); item_form.addWidget(self.item_qty)
        item_form.addWidget(QLabel("Precio Unit:")); item_form.addWidget(self.item_price)
        item_form.addWidget(btn_add_item)
        details_layout.addLayout(item_form)

        # Tabla de items
        self.invoice_items_table = QTableWidget(0, 7)
        self.invoice_items_table.setHorizontalHeaderLabels(["#", "Código", "Descripción", "Unidad", "Cantidad", "Precio Unitario", "Subtotal"])
        self.invoice_items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        details_layout.addWidget(self.invoice_items_table)
        btn_remove_item = QPushButton("Eliminar Detalle Seleccionado")
        btn_remove_item.clicked.connect(self._remove_invoice_item_row)
        details_layout.addWidget(btn_remove_item)

        layout.addWidget(QLabel("3. Detalles de la Factura"))
        layout.addWidget(details_group)

        # --- Totales y opciones ---
        totales_group = QWidget()
        totales_layout = QHBoxLayout(totales_group)

        self.apply_itbis_checkbox = QCheckBox("Aplicar ITBIS (18%)")
        self.apply_itbis_checkbox.setChecked(True)
        self.apply_itbis_checkbox.stateChanged.connect(self._recalculate_invoice_totals)
        totales_layout.addWidget(self.apply_itbis_checkbox)

        self.subtotal_label = QLabel("Subtotal: RD$ 0.00")
        self.itbis_label = QLabel("ITBIS: RD$ 0.00")
        self.total_label = QLabel("Total: RD$ 0.00")
        totales_layout.addWidget(self.subtotal_label)
        totales_layout.addWidget(self.itbis_label)
        totales_layout.addWidget(self.total_label)

        layout.addWidget(totales_group)

                # --- Selector de moneda ---
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["RD$", "USD", "EUR"])
        self.currency_combo.setCurrentText(DEFAULT_CURRENCY)
        factura_layout.addWidget(QLabel("Moneda:"))
        factura_layout.addWidget(self.currency_combo)

        # --- Campo tasa de cambio (oculto por defecto) ---
        self.exchange_rate_edit = QLineEdit("1.00")
        self.exchange_rate_edit.setVisible(False)
        factura_layout.addWidget(QLabel("Tasa de cambio:"))
        factura_layout.addWidget(self.exchange_rate_edit)

        # Conectar evento para mostrar/ocultar campo de tasa de cambio
        self.currency_combo.currentIndexChanged.connect(self._on_currency_change)

        # --- Botones de acción ---
        btn_generate_excel = QPushButton("Vista Previa / Generar Factura en Excel")
        btn_generate_excel.clicked.connect(self._generate_invoice_excel)
        btn_generate_pdf = QPushButton("Generar Factura en PDF")
        btn_generate_pdf.clicked.connect(self._generate_invoice_pdf)
        btn_save_invoice = QPushButton("Guardar en Base de Datos")
        btn_save_invoice.clicked.connect(self._save_invoice)
        layout.addWidget(btn_generate_excel)
        layout.addWidget(btn_generate_pdf)
        layout.addWidget(btn_save_invoice)

        # Inicializar NCF
        self._update_ncf_sequence()
        return tab

    # --- Sugerencia de cliente por nombre/RNC ---
    def _suggest_third_party(self, search_by):
        query = self.client_rnc.text() if search_by == "rnc" else self.client_name.text()
        if len(query) < 2:
            self.suggestion_combo.hide()
            return
        # Aquí deberías conectar con tu controlador/db para obtener las sugerencias
        results = []  # TODO: Integrar con db_manager (busca terceros)
        if hasattr(self.logic, "search_third_parties"):
            results = self.logic.search_third_parties(query, search_by=search_by)
        self.suggestion_combo.clear()
        for item in results:
            self.suggestion_combo.addItem(f"{item['rnc']} - {item['name']}")
        if results:
            self.suggestion_combo.show()
        else:
            self.suggestion_combo.hide()

    def _select_suggestion(self, idx):
        val = self.suggestion_combo.currentText()
        if " - " in val:
            rnc, name = val.split(" - ", 1)
            self.client_rnc.setText(rnc)
            self.client_name.setText(name)
        self.suggestion_combo.hide()

    # --- NCF automático por tipo ---
    def _update_ncf_sequence(self):
        selected_type = self.ncf_type_combo.currentText()
        prefix = NCF_TYPES.get(selected_type)
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        next_ncf = ""
        if prefix and company and hasattr(self.logic, "get_next_ncf"):
            next_ncf = self.logic.get_next_ncf(company['id'], prefix)
        self.ncf_number_edit.setText(next_ncf)
    # --- Agregar row a la tabla de items ---
    def _add_invoice_item_row(self):
        desc = self.item_desc.text().strip()
        try:
            qty = float(self.item_qty.text().strip())
            price = float(self.item_price.text().strip())
        except Exception:
            QMessageBox.warning(self, "Error", "Cantidad y Precio deben ser números.")
            return
        if not desc:
            QMessageBox.warning(self, "Dato Faltante", "La descripción no puede estar vacía.")
            return
        subtotal = qty * price
        row = self.invoice_items_table.rowCount()
        self.invoice_items_table.insertRow(row)
        self.invoice_items_table.setItem(row, 0, QTableWidgetItem(desc))
        self.invoice_items_table.setItem(row, 1, QTableWidgetItem(f"{qty:,.2f}"))
        self.invoice_items_table.setItem(row, 2, QTableWidgetItem(f"{price:,.2f}"))
        self.invoice_items_table.setItem(row, 3, QTableWidgetItem(f"{subtotal:,.2f}"))
        self.item_desc.clear(); self.item_qty.clear(); self.item_price.clear()
        self._recalculate_invoice_totals()

    def _remove_invoice_item_row(self):
        selected = self.invoice_items_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un detalle para eliminar.")
            return
        self.invoice_items_table.removeRow(selected)
        self._recalculate_invoice_totals()

    def _recalculate_invoice_totals(self):
        subtotal = 0.0
        for row in range(self.invoice_items_table.rowCount()):
            val = self.invoice_items_table.item(row, 3)
            try:
                subtotal += float(val.text().replace(",", "")) if val and val.text() else 0.0
            except Exception:
                continue
        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis
        self.subtotal_label.setText(f"Subtotal: RD$ {subtotal:,.2f}")
        self.itbis_label.setText(f"ITBIS ({ITBIS_RATE*100:.0f}%): RD$ {itbis:,.2f}")
        self.total_label.setText(f"Total: RD$ {total:,.2f}")

    # --- Generar Excel (placeholder para integración con tu lógica) ---
    def _generate_invoice_excel(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        invoice_data = {
            "company_id": company['id'],
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": self.ncf_number_edit.text(),
            "client_name": self.client_name.text(),
            "client_rnc": self.client_rnc.text(),
            "currency": "RD$",
        }
        items = []
        for row in range(self.invoice_items_table.rowCount()):
            desc = self.invoice_items_table.item(row, 0)
            qty = self.invoice_items_table.item(row, 1)
            price = self.invoice_items_table.item(row, 2)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        # Seleccionar ruta Excel
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como Excel", "", "Excel Files (*.xlsx)")
        if filename:
            save_path = filename if filename.endswith(".xlsx") else filename + ".xlsx"
            generate_invoice_excel(invoice_data, items, save_path, company_name)
            QMessageBox.information(self, "Excel", f"Factura guardada como Excel en:\n{save_path}")

    def _generate_invoice_pdf(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        invoice_data = {
            "company_id": company['id'],
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": self.ncf_number_edit.text(),
            "client_name": self.client_name.text(),
            "client_rnc": self.client_rnc.text(),
            "currency": "RD$",
        }
        items = []
        for row in range(self.invoice_items_table.rowCount()):
            desc = self.invoice_items_table.item(row, 0)
            qty = self.invoice_items_table.item(row, 1)
            price = self.invoice_items_table.item(row, 2)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        # Seleccionar ruta PDF
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como PDF", "", "PDF Files (*.pdf)")
        if filename:
            save_path = filename if filename.endswith(".pdf") else filename + ".pdf"
            generate_invoice_pdf(invoice_data, items, save_path, company_name)
            QMessageBox.information(self, "PDF", f"Factura guardada como PDF en:\n{save_path}")

    # --- Guardar en la base de datos ---
    def _save_invoice(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return

        # Validar cliente (nombre y RNC)
        cliente_nombre = self.client_name.text().strip()
        cliente_rnc = self.client_rnc.text().strip()
        if not cliente_nombre or not cliente_rnc:
            QMessageBox.warning(self, "Cliente", "Debe completar el nombre y RNC del cliente antes de guardar la factura.")
            return

        # Moneda y tasa de cambio
        moneda = self.currency_combo.currentText()
        try:
            tasa_cambio = float(self.exchange_rate_edit.text().replace(",", "")) if self.exchange_rate_edit.text().strip() else 1.0
            if tasa_cambio <= 0:
                tasa_cambio = 1.0
        except Exception:
            tasa_cambio = 1.0

        # Calcular subtotal, items y total
        items = []
        subtotal = 0.0
        for row in range(self.invoice_items_table.rowCount()):
            desc = self.invoice_items_table.item(row, 0)
            qty = self.invoice_items_table.item(row, 1)
            price = self.invoice_items_table.item(row, 2)
            subtotal_item = self.invoice_items_table.item(row, 3)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
                subtotal_val = float(subtotal_item.text().replace(",", "")) if subtotal_item and subtotal_item.text().strip() else qty_val * price_val
            except Exception:
                qty_val = 0.0
                price_val = 0.0
                subtotal_val = 0.0
            subtotal += subtotal_val
            items.append({
                "description": desc.text() if desc else "",
                "quantity": qty_val,
                "unit_price": price_val
            })

        # Calcular ITBIS y totales
        itbis = subtotal * ITBIS_RATE if self.apply_itbis_checkbox.isChecked() else 0.0
        total = subtotal + itbis
        total_rd = total * tasa_cambio

        invoice_data = {
            "company_id": company['id'],
            "invoice_type": "emitida",
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": self.ncf_number_edit.text(),
            "third_party_name": cliente_nombre,
            "rnc": cliente_rnc,
            "currency": moneda,
            "itbis": itbis,
            "total_amount": total,
            "exchange_rate": tasa_cambio,
            "total_amount_rd": total_rd,
            "excel_path": "",
            "pdf_path": "",
        }

        self.total_label.setText(f"Total: {invoice_data['currency']} {total:,.2f}   |   Total RD$: {total_rd:,.2f}")

        invoice_id = self.logic.add_invoice(invoice_data, items)
        QMessageBox.information(self, "Factura", f"Factura creada correctamente (ID: {invoice_id})")

        # Limpiar formulario
        self._clear_invoice_form()

        # Refrescar historial
        self._refresh_facturas_list()


#    # ----- TAB COTIZACIÓN -----
    def _cotizacion_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # --- 1. Datos de la Cotización ---
        cotiz_group = QWidget()
        cotiz_layout = QHBoxLayout(cotiz_group)

        self.quotation_date = QDateEdit(QDate.currentDate())
        self.quotation_date.setCalendarPopup(True)
        cotiz_layout.addWidget(QLabel("Fecha:"))
        cotiz_layout.addWidget(self.quotation_date)

        self.quotation_client_rnc = QLineEdit()
        self.quotation_client_name = QLineEdit()
        self.quotation_client_rnc.setPlaceholderText("Buscar RNC/Cédula...")
        self.quotation_client_name.setPlaceholderText("Buscar nombre/razón social...")
        self.quotation_client_rnc.textChanged.connect(lambda: self._suggest_quotation_third_party('rnc'))
        self.quotation_client_name.textChanged.connect(lambda: self._suggest_quotation_third_party('name'))

        cotiz_layout.addWidget(QLabel("RNC/Cédula:"))
        cotiz_layout.addWidget(self.quotation_client_rnc)
        cotiz_layout.addWidget(QLabel("Nombre/Razón Social:"))
        cotiz_layout.addWidget(self.quotation_client_name)

        self.quotation_suggestion_combo = QComboBox()
        self.quotation_suggestion_combo.hide()
        self.quotation_suggestion_combo.setEditable(False)
        self.quotation_suggestion_combo.activated.connect(self._select_quotation_suggestion)
        cotiz_layout.addWidget(self.quotation_suggestion_combo)

        self.quotation_currency = QLineEdit(DEFAULT_CURRENCY)
        cotiz_layout.addWidget(QLabel("Moneda:"))
        cotiz_layout.addWidget(self.quotation_currency)

        layout.addWidget(QLabel("1. Datos de la Cotización"))
        layout.addWidget(cotiz_group)

        # --- 2. Notas ---
        layout.addWidget(QLabel("Notas (opcional):"))
        self.quotation_notes = QTextEdit()
        layout.addWidget(self.quotation_notes)

        # --- 3. Detalles de la Cotización ---
        details_group = QWidget()
        details_layout = QVBoxLayout(details_group)

        # Formulario para agregar item
        item_form = QHBoxLayout()
        self.quotation_item_desc = QLineEdit(); self.quotation_item_desc.setPlaceholderText("Descripción")
        self.quotation_item_qty = QLineEdit(); self.quotation_item_qty.setPlaceholderText("Cantidad")
        self.quotation_item_price = QLineEdit(); self.quotation_item_price.setPlaceholderText("Precio Unitario")
        btn_add_item = QPushButton("Agregar Detalle")
        btn_add_item.clicked.connect(self._add_quotation_item_row)
        item_form.addWidget(QLabel("Descripción:")); item_form.addWidget(self.quotation_item_desc)
        item_form.addWidget(QLabel("Cant:")); item_form.addWidget(self.quotation_item_qty)
        item_form.addWidget(QLabel("Precio Unit:")); item_form.addWidget(self.quotation_item_price)
        item_form.addWidget(btn_add_item)
        details_layout.addLayout(item_form)

        # Tabla de items
        self.quotation_items_table = QTableWidget(0, 7)
        self.quotation_items_table.setHorizontalHeaderLabels([
            "#", "Código", "Descripción", "Unidad", "Cantidad", "Precio Unitario", "Subtotal"
        ])
        self.quotation_items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        details_layout.addWidget(self.quotation_items_table)
        btn_remove_item = QPushButton("Eliminar Detalle Seleccionado")
        btn_remove_item.clicked.connect(self._remove_quotation_item_row)
        details_layout.addWidget(btn_remove_item)

        layout.addWidget(QLabel("2. Detalles de la Cotización"))
        layout.addWidget(details_group)

        # --- Totales ---
        totales_group = QWidget()
        totales_layout = QHBoxLayout(totales_group)
        self.quotation_subtotal_label = QLabel("Subtotal: RD$ 0.00")
        self.quotation_total_label = QLabel("Total: RD$ 0.00")
        totales_layout.addWidget(self.quotation_subtotal_label)
        totales_layout.addWidget(self.quotation_total_label)
        layout.addWidget(totales_group)

        # --- Botones de acción ---
        btn_generate_excel = QPushButton("Vista Previa / Generar Cotización en Excel")
        btn_generate_excel.clicked.connect(self._generate_quotation_excel)
        btn_generate_pdf = QPushButton("Generar Cotización en PDF")
        btn_generate_pdf.clicked.connect(self._generate_quotation_pdf)
        btn_save_quotation = QPushButton("Guardar Cotización")
        btn_save_quotation.clicked.connect(self._save_quotation)
        btn_edit_quotation = QPushButton("Guardar Cambios de Cotización")
        btn_edit_quotation.clicked.connect(self._edit_quotation)
        btn_edit_quotation.hide() # Se muestra solo si editando
        self.btn_edit_quotation = btn_edit_quotation
        layout.addWidget(btn_generate_excel)
        layout.addWidget(btn_generate_pdf)
        layout.addWidget(btn_save_quotation)
        layout.addWidget(btn_edit_quotation)

        # SOLO limpieza y edición, NO historial aquí.
        return tab

    def _suggest_quotation_third_party(self, search_by):
        query = self.quotation_client_rnc.text() if search_by == "rnc" else self.quotation_client_name.text()
        if len(query) < 2:
            self.quotation_suggestion_combo.hide()
            return
        results = []
        if hasattr(self.logic, "search_third_parties"):
            results = self.logic.search_third_parties(query, search_by=search_by)
        self.quotation_suggestion_combo.clear()
        for item in results:
            self.quotation_suggestion_combo.addItem(f"{item['rnc']} - {item['name']}")
        if results:
            self.quotation_suggestion_combo.show()
        else:
            self.quotation_suggestion_combo.hide()

    def _select_quotation_suggestion(self, idx):
        val = self.quotation_suggestion_combo.currentText()
        if " - " in val:
            rnc, name = val.split(" - ", 1)
            self.quotation_client_rnc.setText(rnc)
            self.quotation_client_name.setText(name)
        self.quotation_suggestion_combo.hide()

    def _add_quotation_item_row(self):
        desc = self.quotation_item_desc.text().strip()
        try:
            qty = float(self.quotation_item_qty.text().strip())
            price = float(self.quotation_item_price.text().strip())
        except Exception:
            QMessageBox.warning(self, "Error", "Cantidad y Precio deben ser números.")
            return
        if not desc:
            QMessageBox.warning(self, "Dato Faltante", "La descripción no puede estar vacía.")
            return
        subtotal = qty * price
        row = self.quotation_items_table.rowCount()
        self.quotation_items_table.insertRow(row)
        self.quotation_items_table.setItem(row, 0, QTableWidgetItem(desc))
        self.quotation_items_table.setItem(row, 1, QTableWidgetItem(f"{qty:,.2f}"))
        self.quotation_items_table.setItem(row, 2, QTableWidgetItem(f"{price:,.2f}"))
        self.quotation_items_table.setItem(row, 3, QTableWidgetItem(f"{subtotal:,.2f}"))
        self.quotation_item_desc.clear(); self.quotation_item_qty.clear(); self.quotation_item_price.clear()
        self._recalculate_quotation_totals()

    def _remove_quotation_item_row(self):
        selected = self.quotation_items_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un detalle para eliminar.")
            return
        self.quotation_items_table.removeRow(selected)
        self._recalculate_quotation_totals()

    def _recalculate_quotation_totals(self):
        subtotal = 0.0
        for row in range(self.quotation_items_table.rowCount()):
            val = self.quotation_items_table.item(row, 3)
            try:
                subtotal += float(val.text().replace(",", "")) if val and val.text() else 0.0
            except Exception:
                continue
        self.quotation_subtotal_label.setText(f"Subtotal: RD$ {subtotal:,.2f}")
        self.quotation_total_label.setText(f"Total: RD$ {subtotal:,.2f}")

    def _generate_quotation_excel(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        quotation_data = {
            "company_id": company['id'],
            "quotation_date": self.quotation_date.date().toString("yyyy-MM-dd"),
            "client_name": self.quotation_client_name.text(),
            "client_rnc": self.quotation_client_rnc.text(),
            "notes": self.quotation_notes.toPlainText(),
            "currency": self.quotation_currency.text(),
        }
        items = []
        for row in range(self.quotation_items_table.rowCount()):
            desc = self.quotation_items_table.item(row, 0)
            qty = self.quotation_items_table.item(row, 1)
            price = self.quotation_items_table.item(row, 2)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como Excel", "", "Excel Files (*.xlsx)")
        if filename:
            save_path = filename if filename.endswith(".xlsx") else filename + ".xlsx"
            generate_quotation_excel(quotation_data, items, save_path, company_name)
            QMessageBox.information(self, "Excel", f"Cotización guardada como Excel en:\n{save_path}")

    def _generate_quotation_pdf(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        quotation_data = {
            "company_id": company['id'],
            "quotation_date": self.quotation_date.date().toString("yyyy-MM-dd"),
            "client_name": self.quotation_client_name.text(),
            "client_rnc": self.quotation_client_rnc.text(),
            "notes": self.quotation_notes.toPlainText(),
            "currency": self.quotation_currency.text(),
        }
        items = []
        for row in range(self.quotation_items_table.rowCount()):
            desc = self.quotation_items_table.item(row, 0)
            qty = self.quotation_items_table.item(row, 1)
            price = self.quotation_items_table.item(row, 2)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como PDF", "", "PDF Files (*.pdf)")
        if filename:
            save_path = filename if filename.endswith(".pdf") else filename + ".pdf"
            generate_quotation_pdf(quotation_data, items, save_path, company_name)
            QMessageBox.information(self, "PDF", f"Cotización guardada como PDF en:\n{save_path}")

    def _save_quotation(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        quotation_data = {
            "company_id": company['id'],
            "quotation_date": self.quotation_date.date().toString("yyyy-MM-dd"),
            "client_name": self.quotation_client_name.text(),
            "client_rnc": self.quotation_client_rnc.text(),
            "notes": self.quotation_notes.toPlainText(),
            "currency": self.quotation_currency.text(),
            "total_amount": 0.0,
            "excel_path": "",
            "pdf_path": "",
        }
        items = []
        total = 0.0
        for row in range(self.quotation_items_table.rowCount()):
            desc = self.quotation_items_table.item(row, 0)
            qty = self.quotation_items_table.item(row, 1)
            price = self.quotation_items_table.item(row, 2)
            subtotal = self.quotation_items_table.item(row, 3)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
                subtotal_val = float(subtotal.text().replace(",", "")) if subtotal and subtotal.text().strip() else 0.0
            except ValueError:
                qty_val = 0.0
                price_val = 0.0
                subtotal_val = 0.0
            total += subtotal_val
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        quotation_data["total_amount"] = total
        self.quotation_total_label.setText(f"Total: {quotation_data['currency']} {total:,.2f}")

        quotation_id = self.logic.add_quotation(quotation_data, items)
        self._refresh_quotation_list()
        self.btn_edit_quotation.hide()
        self._clear_quotation_form()

    def _edit_quotation(self):
        if not hasattr(self, 'current_edit_quotation_id'):
            QMessageBox.warning(self, "Edición", "No hay cotización cargada para editar.")
            return
        quotation_id = self.current_edit_quotation_id
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        quotation_data = {
            "quotation_date": self.quotation_date.date().toString("yyyy-MM-dd"),
            "client_name": self.quotation_client_name.text(),
            "client_rnc": self.quotation_client_rnc.text(),
            "notes": self.quotation_notes.toPlainText(),
            "currency": self.quotation_currency.text(),
            "total_amount": 0.0,
            "excel_path": "",
            "pdf_path": "",
        }
        items = []
        total = 0.0
        for row in range(self.quotation_items_table.rowCount()):
            desc = self.quotation_items_table.item(row, 0)
            qty = self.quotation_items_table.item(row, 1)
            price = self.quotation_items_table.item(row, 2)
            subtotal = self.quotation_items_table.item(row, 3)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
                subtotal_val = float(subtotal.text().replace(",", "")) if subtotal and subtotal.text().strip() else 0.0
            except ValueError:
                qty_val = 0.0
                price_val = 0.0
                subtotal_val = 0.0
            total += subtotal_val
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        quotation_data["total_amount"] = total
        self.quotation_total_label.setText(f"Total: {quotation_data['currency']} {total:,.2f}")

        self.logic.update_quotation(quotation_id, quotation_data, items)
        QMessageBox.information(self, "Cotización", f"Cotización actualizada correctamente (ID: {quotation_id})")
        self.btn_edit_quotation.hide()
        self._refresh_quotation_list()
        self._clear_quotation_form()

    def _refresh_quotation_list(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            return
        quotations = self.logic.get_quotations(company['id'])
        self.quotation_list_table.setRowCount(0)
        for q in quotations:
            row = self.quotation_list_table.rowCount()
            self.quotation_list_table.insertRow(row)
            self.quotation_list_table.setItem(row, 0, QTableWidgetItem(str(q['id'])))
            self.quotation_list_table.setItem(row, 1, QTableWidgetItem(q['quotation_date']))
            self.quotation_list_table.setItem(row, 2, QTableWidgetItem(q['client_name']))
            self.quotation_list_table.setItem(row, 3, QTableWidgetItem(q['client_rnc']))
            self.quotation_list_table.setItem(row, 4, QTableWidgetItem(q['currency']))
            self.quotation_list_table.setItem(row, 5, QTableWidgetItem(f"{q['total_amount']:,.2f}"))
            self.quotation_list_table.setItem(row, 6, QTableWidgetItem(q['notes']))

    def _load_selected_quotation(self):
        selected = self.quotation_list_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Edición", "Seleccione una cotización para editar")
            return
        quotation_id = int(self.quotation_list_table.item(selected, 0).text())
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            return
        quotation = next((q for q in self.logic.get_quotations(company['id']) if q['id'] == quotation_id), None)
        if not quotation:
            QMessageBox.warning(self, "Edición", "No se encontró la cotización")
            return
        self.quotation_date.setDate(QDate.fromString(quotation['quotation_date'], "yyyy-MM-dd"))
        self.quotation_client_name.setText(quotation['client_name'])
        self.quotation_client_rnc.setText(quotation['client_rnc'])
        self.quotation_notes.setPlainText(quotation['notes'])
        self.quotation_currency.setText(quotation['currency'])
        items = self.logic.get_quotation_items(quotation_id)
        self.quotation_items_table.setRowCount(0)
        for item in items:
            row = self.quotation_items_table.rowCount()
            self.quotation_items_table.insertRow(row)
            self.quotation_items_table.setItem(row, 0, QTableWidgetItem(item['description']))
            self.quotation_items_table.setItem(row, 1, QTableWidgetItem(str(item['quantity'])))
            self.quotation_items_table.setItem(row, 2, QTableWidgetItem(str(item['unit_price'])))
            subtotal = float(item['quantity']) * float(item['unit_price'])
            self.quotation_items_table.setItem(row, 3, QTableWidgetItem(f"{subtotal:,.2f}"))
        self.btn_edit_quotation.show()
        self.current_edit_quotation_id = quotation_id
        self._recalculate_quotation_totals()

    def _delete_selected_quotation(self):
        selected = self.quotation_list_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Eliminar", "Seleccione una cotización para eliminar")
            return
        quotation_id = int(self.quotation_list_table.item(selected, 0).text())
        confirm = QMessageBox.question(self, "Eliminar", "¿Seguro que desea eliminar la cotización?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.logic.delete_quotation(quotation_id)
            self._refresh_quotation_list()
            self._clear_quotation_form()
            self.btn_edit_quotation.hide()

    def _clear_quotation_form(self):
        self.quotation_date.setDate(QDate.currentDate())
        self.quotation_client_name.clear()
        self.quotation_client_rnc.clear()
        self.quotation_notes.clear()
        self.quotation_currency.setText(DEFAULT_CURRENCY)
        self.quotation_items_table.setRowCount(0)
        self.quotation_subtotal_label.setText("Subtotal: RD$ 0.00")
        self.quotation_total_label.setText("Total: RD$ 0.00")
        if hasattr(self, 'current_edit_quotation_id'):
            del self.current_edit_quotation_id

    def _generate_invoice_excel(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        invoice_data = {
            "company_id": company['id'],
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": self.ncf_number_edit.text(),
            "client_name": self.client_name.text(),
            "client_rnc": self.client_rnc.text(),
            "currency": "RD$",
        }
        items = []
        for row in range(self.invoice_items_table.rowCount()):
            desc = self.invoice_items_table.item(row, 0)
            qty = self.invoice_items_table.item(row, 1)
            price = self.invoice_items_table.item(row, 2)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        # Seleccionar ruta Excel
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como Excel", "", "Excel Files (*.xlsx)")
        if filename:
            save_path = filename if filename.endswith(".xlsx") else filename + ".xlsx"
            generate_invoice_excel(invoice_data, items, save_path, company_name)
            QMessageBox.information(self, "Excel", f"Factura guardada como Excel en:\n{save_path}")

    def _generate_invoice_pdf(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            QMessageBox.warning(self, "Empresa", "Seleccione una empresa válida")
            return
        invoice_data = {
            "company_id": company['id'],
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_number": self.ncf_number_edit.text(),
            "client_name": self.client_name.text(),
            "client_rnc": self.client_rnc.text(),
            "currency": "RD$",
        }
        items = []
        for row in range(self.invoice_items_table.rowCount()):
            desc = self.invoice_items_table.item(row, 0)
            qty = self.invoice_items_table.item(row, 1)
            price = self.invoice_items_table.item(row, 2)
            try:
                qty_val = float(qty.text().replace(",", "")) if qty and qty.text().strip() else 0.0
                price_val = float(price.text().replace(",", "")) if price and price.text().strip() else 0.0
            except Exception:
                qty_val = 0.0
                price_val = 0.0
            items.append({"description": desc.text() if desc else "", "quantity": qty_val, "unit_price": price_val})
        # Seleccionar ruta PDF
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como PDF", "", "PDF Files (*.pdf)")
        if filename:
            save_path = filename if filename.endswith(".pdf") else filename + ".pdf"
            generate_invoice_pdf(invoice_data, items, save_path, company_name)
            QMessageBox.information(self, "PDF", f"Factura guardada como PDF en:\n{save_path}")

    def _historial_factura_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Historial de Facturas"))

        self.facturas_list_table = QTableWidget(0, 8)
        self.facturas_list_table.setHorizontalHeaderLabels([
            "ID", "Fecha", "NCF", "Cliente", "RNC", "Moneda", "Total", "Ver/Eliminar"
        ])
        layout.addWidget(self.facturas_list_table)

        btn_refresh = QPushButton("Refrescar Historial")
        btn_refresh.clicked.connect(self._refresh_facturas_list)
        layout.addWidget(btn_refresh)

        # Puedes agregar botones de "Ver Detalle" y "Eliminar"
        btn_ver = QPushButton("Ver Factura Seleccionada")
        btn_ver.clicked.connect(self._ver_factura_seleccionada)
        btn_delete = QPushButton("Eliminar Factura Seleccionada")
        btn_delete.clicked.connect(self._delete_factura_seleccionada)
        layout.addWidget(btn_ver)
        layout.addWidget(btn_delete)

        self._refresh_facturas_list()
        return tab

    def _refresh_facturas_list(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            return
        facturas = self.logic.get_facturas(company['id'])  # <-- usa self.logic
        self.facturas_list_table.setRowCount(0)
        for f in facturas:
            row = self.facturas_list_table.rowCount()
            self.facturas_list_table.insertRow(row)
            self.facturas_list_table.setItem(row, 0, QTableWidgetItem(str(f['id'])))
            self.facturas_list_table.setItem(row, 1, QTableWidgetItem(f['invoice_date']))
            self.facturas_list_table.setItem(row, 2, QTableWidgetItem(f.get('invoice_number', '')))
            self.facturas_list_table.setItem(row, 3, QTableWidgetItem(f.get('third_party_name', '')))  # <-- este campo
            self.facturas_list_table.setItem(row, 4, QTableWidgetItem(f.get('rnc', '')))              # <-- este campo
            self.facturas_list_table.setItem(row, 5, QTableWidgetItem(f.get('currency', '')))
            self.facturas_list_table.setItem(row, 6, QTableWidgetItem(f"{f.get('total_amount',0):,.2f}"))
            self.facturas_list_table.setItem(row, 7, QTableWidgetItem(""))  # Para acciones

    def _historial_cotizacion_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Historial de Cotizaciones"))

        self.cotizaciones_list_table = QTableWidget(0, 7)
        self.cotizaciones_list_table.setHorizontalHeaderLabels([
            "ID", "Fecha", "Cliente", "RNC", "Moneda", "Total", "Notas"
        ])
        layout.addWidget(self.cotizaciones_list_table)

        btn_refresh = QPushButton("Refrescar Historial")
        btn_refresh.clicked.connect(self._refresh_cotizaciones_list)
        layout.addWidget(btn_refresh)

        btn_ver = QPushButton("Ver Cotización Seleccionada")
        btn_ver.clicked.connect(self._ver_cotizacion_seleccionada)
        btn_delete = QPushButton("Eliminar Cotización Seleccionada")
        btn_delete.clicked.connect(self._delete_cotizacion_seleccionada)
        layout.addWidget(btn_ver)
        layout.addWidget(btn_delete)

        self._refresh_cotizaciones_list()
        return tab

    def _refresh_cotizaciones_list(self):
        company_name = self.company_selector.currentText()
        company = self.companies.get(company_name)
        if not company:
            return
        cotizaciones = self.logic.get_quotations(company['id'])  # <--- usa self.logic
        self.cotizaciones_list_table.setRowCount(0)
        for q in cotizaciones:
            row = self.cotizaciones_list_table.rowCount()
            self.cotizaciones_list_table.insertRow(row)
            self.cotizaciones_list_table.setItem(row, 0, QTableWidgetItem(str(q['id'])))
            self.cotizaciones_list_table.setItem(row, 1, QTableWidgetItem(q['quotation_date']))
            self.cotizaciones_list_table.setItem(row, 2, QTableWidgetItem(q['client_name']))
            self.cotizaciones_list_table.setItem(row, 3, QTableWidgetItem(q['client_rnc']))
            self.cotizaciones_list_table.setItem(row, 4, QTableWidgetItem(q['currency']))
            self.cotizaciones_list_table.setItem(row, 5, QTableWidgetItem(f"{q['total_amount']:,.2f}"))
            self.cotizaciones_list_table.setItem(row, 6, QTableWidgetItem(q['notes']))



    def _ver_factura_seleccionada(self):
        selected = self.facturas_list_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Ver Factura", "Seleccione una factura para ver.")
            return
        factura_id = int(self.facturas_list_table.item(selected, 0).text())
        # Aquí puedes abrir un diálogo o ventana con los detalles de la factura
        # Ejemplo mínimo:
        QMessageBox.information(self, "Detalle Factura", f"Factura seleccionada (ID): {factura_id}")

    def _delete_factura_seleccionada(self):
        selected = self.facturas_list_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Eliminar Factura", "Seleccione una factura para eliminar.")
            return
        factura_id = int(self.facturas_list_table.item(selected, 0).text())
        confirm = QMessageBox.question(self, "Eliminar", "¿Seguro que desea eliminar la factura?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.logic.delete_factura(factura_id)
            self._refresh_facturas_list()

    def _ver_cotizacion_seleccionada(self):
        selected = self.cotizaciones_list_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Ver Cotización", "Seleccione una cotización para ver.")
            return
        cotizacion_id = int(self.cotizaciones_list_table.item(selected, 0).text())
        # Aquí puedes abrir un diálogo o ventana con los detalles de la cotización
        QMessageBox.information(self, "Detalle Cotización", f"Cotización seleccionada (ID): {cotizacion_id}")

    def _delete_cotizacion_seleccionada(self):
        selected = self.cotizaciones_list_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Eliminar Cotización", "Seleccione una cotización para eliminar.")
            return
        cotizacion_id = int(self.cotizaciones_list_table.item(selected, 0).text())
        confirm = QMessageBox.question(self, "Eliminar", "¿Seguro que desea eliminar la cotización?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.logic.delete_quotation(cotizacion_id)
            self._refresh_cotizaciones_list()

    def _select_template_path(self):
        from PyQt6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getOpenFileName(self, "Selecciona la plantilla de factura", "", "Archivos Excel (*.xlsx);;Todos los archivos (*)")
        if filename:
            config_facot.set_template_path(filename)

    def _select_output_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Selecciona la carpeta de salida para facturas")
        if folder:
            config_facot.set_output_folder(folder)

    def _suggest_third_party(self, search_by):
        query = self.client_rnc.text() if search_by == "rnc" else self.client_name.text()
        if len(query) < 2:
            self.suggestion_combo.hide()
            return
        results = self.logic.search_third_parties(query, search_by=search_by)
        self.suggestion_combo.clear()
        for item in results:
            self.suggestion_combo.addItem(f"{item['rnc']} - {item['name']}")
        if results:
            self.suggestion_combo.show()
        else:
            self.suggestion_combo.hide()

    def _select_suggestion(self, idx):
        val = self.suggestion_combo.currentText()
        if " - " in val:
            rnc, name = val.split(" - ", 1)
            self.client_rnc.setText(rnc)
            self.client_name.setText(name)
        self.suggestion_combo.hide()



    def _on_currency_change(self):
        moneda = self.currency_combo.currentText()
        if moneda != "RD$":
            self.exchange_rate_edit.setVisible(True)
            # Solicita la tasa de cambio si cambia a otra moneda
            tasa, ok = QInputDialog.getDouble(
                self, 
                "Tasa de cambio", 
                f"Ingrese la tasa de cambio para {moneda} a RD$:", 
                value=1.00, min=0.01, decimals=4
            )
            if ok:
                self.exchange_rate_edit.setText(str(tasa))
            else:
                self.exchange_rate_edit.setText("1.00")
        else:
            self.exchange_rate_edit.setText("1.00")
            self.exchange_rate_edit.setVisible(False)


    def _clear_invoice_form(self):
        self.invoice_date.setDate(QDate.currentDate())
        self.invoice_due_date.setDate(QDate.currentDate())
        self.ncf_number_edit.clear()
        self.client_rnc.clear()
        self.client_name.clear()
        self.currency_combo.setCurrentText(DEFAULT_CURRENCY)
        self.exchange_rate_edit.setText("1.00")
        self.exchange_rate_edit.setVisible(False)
        self.invoice_items_table.setRowCount(0)
        self.subtotal_label.setText("Subtotal: RD$ 0.00")
        self.itbis_label.setText("ITBIS: RD$ 0.00")
        self.total_label.setText("Total: RD$ 0.00")

    def _on_company_change(self, index):
        self._clear_invoice_form()
        self._update_ncf_sequence()
        self._refresh_facturas_list()
        self._clear_quotation_form()
        self._refresh_cotizaciones_list()

    def _abrir_gestion_items(self):
        dlg = ItemsManagementWindow(self)
        dlg.exec()