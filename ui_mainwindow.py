from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QComboBox, QMessageBox,
    QMenuBar, QMenu, QFileDialog, QStatusBar
)
from PyQt6.QtGui import QAction
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt6.QtCore import QUrl
import os, sys

import facot_config
from logic import LogicController
from widgets.connection_status_bar import ConnectionStatusBar

# Tabs modulares
from tabs.invoice_tab import InvoiceTab
import sys
# Fuerza recarga de módulos
if 'tabs.quotation_tab' in sys.modules:
    del sys.modules['tabs.quotation_tab']
from tabs.quotation_tab import QuotationTab
from tabs.invoice_history_tab import InvoiceHistoryTab
from tabs.quotation_history_tab import QuotationHistoryTab

# Ventanas secundarias
from settings_window import SettingsWindow
from company_management_window import CompanyManagementWindow
from items_management_window import ItemsManagementWindow

# Dialog para editar plantillas (botón/menú)
from dialogs.template_editor_dialog import TemplateEditorDialog

# -*- coding: utf-8 -*-


# ahora las importaciones normales
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
    QDateEdit, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QComboBox,
    QHeaderView, QGroupBox, QToolButton, QCheckBox
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal
# ... el resto de imports ...

class HybridLogicWrapper:
    """
    Wrapper híbrido que combina logic (SQLite) y data_access (Firebase).
    
    Intercepta llamadas de atributos y las redirige al backend correcto:
    - Si data_access tiene el método, lo usa (Firebase)
    - Si no, delega a logic (SQLite)
    
    Esto permite que tabs existentes funcionen con ambos backends
    sin modificar su código.
    """
    
    def __init__(self, logic, data_access=None):
        self._logic = logic
        self._data_access = data_access
        self._use_firebase = data_access is not None
        
        # Para debugging
        if self._use_firebase:
            print(f"[HYBRID] Created hybrid wrapper with Firebase backend")
        else:
            print(f"[HYBRID] Created hybrid wrapper with SQLite only")
    
    def __getattr__(self, name):
        """
        Intercepta acceso a atributos/métodos.
        
        Prioridad:
        1. Si data_access existe y tiene el método -> usar Firebase
        2. Sino -> usar logic (SQLite)
        """
        # Si tenemos data_access y tiene el método, usarlo
        if self._use_firebase and self._data_access and hasattr(self._data_access, name):
            attr = getattr(self._data_access, name)
            # Si es callable, retornar función que logguea
            if callable(attr):
                def logged_call(*args, **kwargs):
                    # print(f"[HYBRID] Using Firebase for: {name}")
                    return attr(*args, **kwargs)
                return logged_call
            return attr
        
        # Sino, delegar a logic
        if hasattr(self._logic, name):
            attr = getattr(self._logic, name)
            if callable(attr):
                def logged_call(*args, **kwargs):
                    # print(f"[HYBRID] Using SQLite for: {name}")
                    return attr(*args, **kwargs)
                return logged_call
            return attr
        
        # Si no existe en ninguno, error estándar
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    # Propiedades que deben accederse directamente
    @property
    def conn(self):
        """Retorna conexión SQLite para compatibilidad."""
        return self._logic.conn if hasattr(self._logic, 'conn') else None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Facturas y Cotizaciones")
        self.resize(1100, 790)
        self.data_access = None  # Will hold DataAccess instance
        self.current_access_mode = "SQLITE"  # Track current mode
        self.hybrid_logic = None  # Will hold HybridLogicWrapper
        self._init_db()
        self._setup_ui()
        self._setup_menu()
        self._setup_connection_status()
        self._check_online_status()
        self._detect_and_set_connection_mode()

    def _init_db(self):
        db_path = facot_config.get_db_path()
        if not db_path or not os.path.isfile(db_path):
            filename, _ = QFileDialog.getOpenFileName(self, "Selecciona tu archivo de base de datos", "", "Database Files (*.db);;Todos los archivos (*)")
            if filename:
                facot_config.set_db_path(filename); db_path = filename
            else:
                QMessageBox.critical(self, "Error", "No se seleccionó una base de datos. El programa se cerrará.")
                sys.exit(1)
        self.logic = LogicController(db_path)
        
        # Initialize data_access with preferred mode from config
        try:
            from data_access import get_data_access, DataAccessMode
            from config_facot import get_connection_mode
            
            # Cargar modo preferido de configuración
            preferred_mode = get_connection_mode()  # "SQLITE", "FIREBASE", or "AUTO"
            print(f"[MAIN] Modo de conexión preferido: {preferred_mode}")
            
            # Convertir a DataAccessMode enum
            mode_enum = DataAccessMode[preferred_mode]
            
            # Inicializar data_access con el modo preferido
            self.data_access = get_data_access(logic_controller=self.logic, mode=mode_enum)
            self.current_access_mode = preferred_mode
            
            # Crear wrapper híbrido que combina logic y data_access
            self.hybrid_logic = HybridLogicWrapper(self.logic, self.data_access)
            print(f"[MAIN] Created hybrid logic wrapper")
            
        except Exception as e:
            print(f"[MAIN] Warning: Could not initialize data_access: {e}")
            self.data_access = None
            self.current_access_mode = "SQLITE"
            # Wrapper solo con logic
            self.hybrid_logic = HybridLogicWrapper(self.logic, None)

    def _setup_ui(self):
        central = QWidget(); layout = QVBoxLayout(central); self.setCentralWidget(central)

        # Selector de empresa
        self.company_selector = QComboBox()
        layout.addWidget(QLabel("Empresa:")); layout.addWidget(self.company_selector)
        self._populate_companies()
        self.company_selector.currentIndexChanged.connect(self._on_company_change)

        # Función para obtener la empresa actual (las pestañas usan get_current_company inyectado)
        get_company = lambda: self.companies.get(self.company_selector.currentText())

        # Tabs modulares
        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()

        # Usar hybrid_logic en lugar de logic directo
        # Esto permite que los tabs usen Firebase o SQLite transparentemente
        logic_to_pass = self.hybrid_logic if self.hybrid_logic else self.logic
        
        self.invoice_tab = InvoiceTab(logic_to_pass, get_company)
        self.quotation_tab = QuotationTab(logic_to_pass, get_company)
        self.invoice_history_tab = InvoiceHistoryTab(logic_to_pass, get_company)
        self.quotation_history_tab = QuotationHistoryTab(logic_to_pass, get_company)

        # Conexiones: refrescar historial al guardar
        self.invoice_tab.invoice_saved.connect(lambda _id: self.invoice_history_tab.refresh())
        self.quotation_tab.quotation_saved.connect(lambda _id: self.quotation_history_tab.refresh())

        self.tabs.addTab(self.invoice_tab, "Factura")
        self.tabs.addTab(self.quotation_tab, "Cotización")
        self.tabs.addTab(self.invoice_history_tab, "Historial de Facturas")
        self.tabs.addTab(self.quotation_history_tab, "Historial de Cotizaciones")
        layout.addWidget(self.tabs)

    def _setup_menu(self):
        menu_bar = QMenuBar(self); self.setMenuBar(menu_bar)
        archivo_menu = QMenu("&Archivo", self); menu_bar.addMenu(archivo_menu)

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
        salir_action = QAction("Salir", self); salir_action.triggered.connect(self.close)
        archivo_menu.addAction(salir_action)

        # Menú Reportes (placeholders)
        reportes_menu = QMenu("&Reportes", self); menu_bar.addMenu(reportes_menu)
        reporte_ventas_action = QAction("Reporte de Ventas", self)
        reporte_ventas_action.triggered.connect(lambda: QMessageBox.information(self, "Reporte", "Aquí se abriría el reporte de ventas."))
        reportes_menu.addAction(reporte_ventas_action)
        reporte_clientes_action = QAction("Reporte por Cliente", self)
        reporte_clientes_action.triggered.connect(lambda: QMessageBox.information(self, "Reporte", "Aquí se abriría el reporte por cliente."))
        reportes_menu.addAction(reporte_clientes_action)

        # Menú Herramientas
        herramientas_menu = QMenu("&Herramientas", self); menu_bar.addMenu(herramientas_menu)
        migrar_firebase_action = QAction("🔄 Migrar a Firebase...", self)
        migrar_firebase_action.setShortcut("Ctrl+Shift+M")
        migrar_firebase_action.setToolTip("Migrar datos de SQLite a Firebase")
        migrar_firebase_action.triggered.connect(self._abrir_dialogo_migracion)
        herramientas_menu.addAction(migrar_firebase_action)
        
        ncf_config_action = QAction("🔢 Configurar Secuencias NCF...", self)
        ncf_config_action.setShortcut("Ctrl+Shift+N")
        ncf_config_action.setToolTip("Configurar secuencias de NCF por empresa y tipo de comprobante")
        ncf_config_action.triggered.connect(self._abrir_configuracion_ncf)
        herramientas_menu.addAction(ncf_config_action)

        # Menú Opciones
        opciones_menu = QMenu("&Opciones", self); menu_bar.addMenu(opciones_menu)
        config_rutas_action = QAction("Configurar Rutas...", self)
        config_rutas_action.triggered.connect(self._abrir_configuracion)
        opciones_menu.addAction(config_rutas_action)

        gestionar_empresas_action = QAction("Gestionar Empresas...", self)
        gestionar_empresas_action.triggered.connect(self._abrir_gestion_empresas)
        opciones_menu.addAction(gestionar_empresas_action)

        gestion_items_action = QAction("Gestionar Ítems...", self)
        gestion_items_action.triggered.connect(self._abrir_gestion_items)
        opciones_menu.addAction(gestion_items_action)

        # Acción: Editar plantilla (abre el editor de plantillas para la empresa seleccionada)
        action_edit_template = QAction("Editar plantilla...", self)
        action_edit_template.setStatusTip("Editar plantilla para la empresa seleccionada")
        action_edit_template.triggered.connect(self._menu_edit_template)
        opciones_menu.addAction(action_edit_template)

    # --------- Menu handlers ----------
    def _abrir_base_de_datos(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir Base de Datos", "", "Database Files (*.db);;Todos los archivos (*)")
        if filename:
            facot_config.set_db_path(filename)
            self.logic = LogicController(filename)
            self._populate_companies()
            # Reinyectar lógica en tabs
            get_company = lambda: self.companies.get(self.company_selector.currentText())
            self.invoice_tab.logic = self.logic; self.quotation_tab.logic = self.logic
            self.invoice_history_tab.logic = self.logic; self.quotation_history_tab.logic = self.logic
            self._on_company_change()
            QMessageBox.information(self, "Base de Datos", "Base de datos abierta correctamente.")

    def _crear_nueva_base_de_datos(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Crear Nueva Base de Datos", "", "Database Files (*.db);;Todos los archivos (*)")
        if filename:
            facot_config.set_db_path(filename)
            self.logic = LogicController(filename)
            self._populate_companies()
            self._on_company_change()
            QMessageBox.information(self, "Base de Datos", "Nueva base de datos creada correctamente.")

    def _hacer_backup(self):
        import shutil
        db_path = self.logic.db_path
        backup_path, _ = QFileDialog.getSaveFileName(self, "Guardar Backup de la Base de Datos", "", "Database Files (*.db);;Todos los archivos (*)")
        if backup_path:
            shutil.copy2(db_path, backup_path)
            QMessageBox.information(self, "Backup", f"Backup guardado en:\n{backup_path}")

    def _abrir_configuracion(self):
        dlg = SettingsWindow(self.logic, self); dlg.exec()

    def _abrir_gestion_empresas(self):
        dlg = CompanyManagementWindow(self, self.logic); dlg.exec()
        # Si cambian empresas, repoblar
        self._populate_companies()
        self._on_company_change()

    def _abrir_gestion_items(self):
        dlg = ItemsManagementWindow(self); dlg.exec()

    def _abrir_dialogo_migracion(self):
        """Abre el diálogo de migración SQLite → Firebase"""
        from dialogs.migration_dialog import MigrationDialog
        
        dialog = MigrationDialog(self)
        dialog.exec()
    
    def _abrir_configuracion_ncf(self):
        """Abre el diálogo de configuración de secuencias NCF"""
        from dialogs.ncf_config_dialog import NCFConfigDialog
        
        # PASAR EL BACKEND CORRECTO (híbrido si existe)
        backend = self.hybrid_logic if self.hybrid_logic else self.logic
        dialog = NCFConfigDialog(backend, self)
        dialog.exec()

    # --------- Empresas ----------
    def _populate_companies(self):
        self.company_selector.clear()
        
        # Use data_access if available, otherwise fallback to logic
        if self.data_access:
            companies = self.data_access.get_all_companies()
        else:
            companies = self.logic.get_all_companies()
        
        self.companies = {str(c['name']): c for c in companies}
        self.company_selector.addItems(self.companies.keys())

    def _on_company_change(self):
        # Notifica a las pestañas
        self.invoice_tab.on_company_change()
        self.quotation_tab.on_company_change()
        self.invoice_history_tab.refresh()
        self.quotation_history_tab.refresh()

    # Helper para obtener la empresa actual desde cualquier lugar
    def get_current_company(self):
        return self.companies.get(self.company_selector.currentText())

    # --- Compatibilidad: algunos diálogos llaman MainWindow.get_all_companies() ---
    def get_all_companies(self):
        """
        Delegado de compatibilidad para obtener empresas desde la ventana principal.
        Intenta híbrido, luego data_access, luego logic.
        """
        try:
            if self.hybrid_logic and hasattr(self.hybrid_logic, "get_all_companies"):
                return self.hybrid_logic.get_all_companies() or []
        except Exception as e:
            print(f"[MainWindow] hybrid get_all_companies error: {e}")
        try:
            if self.data_access and hasattr(self.data_access, "get_all_companies"):
                return self.data_access.get_all_companies() or []
        except Exception as e:
            print(f"[MainWindow] data_access get_all_companies error: {e}")
        try:
            if self.logic and hasattr(self.logic, "get_all_companies"):
                return self.logic.get_all_companies() or []
        except Exception as e:
            print(f"[MainWindow] logic get_all_companies error: {e}")
        return []

    # Menú: abrir editor de plantillas para la empresa seleccionada
    def _menu_edit_template(self):
        company = self.get_current_company()
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
    def _setup_connection_status(self):
        """Configura la barra de estado de conexión."""
        # Crear barra de estado
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Crear widget de estado de conexión
        self.connection_status = ConnectionStatusBar(self)
        
        # Configurar estado inicial (SQLite por defecto)
        db_path = facot_config.get_db_path()
        self.connection_status.set_mode("SQLITE", db_path)
        
        # Conectar señales
        self.connection_status.database_changed.connect(self._on_database_changed)
        self.connection_status.mode_changed.connect(self._on_connection_mode_changed)
        
        # Agregar a la barra de estado
        status_bar.addPermanentWidget(self.connection_status)
    
    def _check_online_status(self):
        """Verifica si hay conexión a internet."""
        # Crear network manager
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_network_check_finished)
        
        # Hacer request a un servidor confiable
        request = QNetworkRequest(QUrl("https://www.google.com"))
        request.setTransferTimeout(3000)  # 3 segundos timeout
        self.network_manager.get(request)
    
    def _on_network_check_finished(self, reply):
        """Callback cuando se completa la verificación de red."""
        is_online = (reply.error() == 0)
        self.connection_status.set_online_status(is_online)
        reply.deleteLater()
    
    def _detect_and_set_connection_mode(self):
        """
        Detecta si se está usando Firebase y actualiza el widget de estado.
        """
        try:
            from data_access import get_current_mode, DataAccessMode
            from firebase import get_firebase_client
            
            # Verificar si data_access es realmente FirebaseDataAccess
            is_using_firebase = (
                self.data_access is not None and 
                "Firebase" in type(self.data_access).__name__
            )
            
            # Verificar si Firebase está disponible
            firebase_client = get_firebase_client()
            firebase_available = firebase_client.is_available()
            
            if is_using_firebase and firebase_available:
                self.current_access_mode = "FIREBASE"
                self.connection_status.set_mode("FIREBASE")
                self.connection_status.set_online_status(True)
                print("[MAIN] Detected Firebase mode - updating status bar")
            else:
                self.current_access_mode = "SQLITE"
                db_path = facot_config.get_db_path()
                self.connection_status.set_mode("SQLITE", db_path)
                print(f"[MAIN] Using SQLite mode: {db_path}")
                
        except Exception as e:
            print(f"[MAIN] Error detecting connection mode: {e}")
            # Fallback to SQLite
            self.current_access_mode = "SQLITE"
            db_path = facot_config.get_db_path()
            self.connection_status.set_mode("SQLITE", db_path)
    
    def _on_database_changed(self, new_db_path: str):
        """
        Callback cuando el usuario cambia la base de datos.
        
        Args:
            new_db_path: Ruta a la nueva base de datos
        """
        try:
            # Actualizar configuración
            facot_config.set_db_path(new_db_path)
            
            # Recrear LogicController con nueva base
            self.logic = LogicController(new_db_path)
            
            # Recreate data_access with new logic controller
            from data_access import get_data_access, DataAccessMode
            self.data_access = get_data_access(logic_controller=self.logic, mode=DataAccessMode.SQLITE)
            self.current_access_mode = "SQLITE"
            
            # Actualizar companies
            self._populate_companies()
            
            # Reinyectar lógica en tabs
            self.invoice_tab.logic = self.logic
            self.quotation_tab.logic = self.logic
            self.invoice_history_tab.logic = self.logic
            self.quotation_history_tab.logic = self.logic
            
            # Refrescar
            self.invoice_tab.on_company_change()
            self.quotation_tab.on_company_change()
            self.invoice_history_tab.refresh()
            self.quotation_history_tab.refresh()
            
            QMessageBox.information(
                self,
                "Base de Datos",
                f"Base de datos cambiada exitosamente:\n{os.path.basename(new_db_path)}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cambiar la base de datos:\n{str(e)}"
            )
    
    def _on_connection_mode_changed(self, new_mode: str):
        """
        Callback cuando el usuario cambia el modo de conexión.
        
        Args:
            new_mode: Nuevo modo (SQLITE, FIREBASE, AUTO)
        """
        try:
            from data_access import set_data_access_mode, DataAccessMode, get_data_access
            
            # Mapear string a enum
            mode_map = {
                "SQLITE": DataAccessMode.SQLITE,
                "FIREBASE": DataAccessMode.FIREBASE,
                "AUTO": DataAccessMode.AUTO
            }
            
            mode = mode_map.get(new_mode.upper())
            if mode:
                set_data_access_mode(mode)
                self.current_access_mode = new_mode.upper()
                
                # Recreate data_access with new mode
                try:
                    if mode == DataAccessMode.SQLITE:
                        self.data_access = get_data_access(logic_controller=self.logic, mode=mode)
                    elif mode == DataAccessMode.FIREBASE:
                        self.data_access = get_data_access(user_id=None, mode=mode)
                    else:  # AUTO
                        self.data_access = get_data_access(logic_controller=self.logic, user_id=None, mode=mode)
                    
                    # Reload companies with new data access
                    self._populate_companies()
                    
                    # Update connection status display
                    self._detect_and_set_connection_mode()
                    
                    QMessageBox.information(
                        self,
                        "Modo de Conexión",
                        f"Modo de conexión cambiado a: {new_mode}\n\n"
                        f"La aplicación ahora usará {new_mode} para acceder a los datos."
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"No se pudo cambiar al modo {new_mode}:\n{str(e)}\n\n"
                        "Revirtiendo a SQLite."
                    )
                    # Revert to SQLite
                    set_data_access_mode(DataAccessMode.SQLITE)
                    self.data_access = get_data_access(logic_controller=self.logic, mode=DataAccessMode.SQLITE)
                    self.current_access_mode = "SQLITE"
                    self._detect_and_set_connection_mode()
                
                # Si se cambió a Firebase o AUTO, verificar que esté configurado
                if new_mode in ["FIREBASE", "AUTO"]:
                    self._check_firebase_availability()
        
        except ImportError:
            QMessageBox.warning(
                self,
                "Modo de Conexión",
                "El módulo de Firebase no está disponible.\n"
                "Solo se puede usar SQLite."
            )
    
    def _check_firebase_availability(self):
        """Verifica si Firebase está disponible y configurado."""
        try:
            from firebase import get_firebase_client
            
            client = get_firebase_client()
            if not client.is_available():
                QMessageBox.warning(
                    self,
                    "Firebase",
                    "Firebase no está disponible o no está configurado correctamente.\n\n"
                    "Verifique que:\n"
                    "1. firebase-admin esté instalado (pip install firebase-admin)\n"
                    "2. El archivo de credenciales exista\n"
                    "3. Las credenciales sean válidas\n\n"
                    "La aplicación usará SQLite como fallback."
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Firebase",
                f"Error al verificar Firebase:\n{str(e)}\n\n"
                "La aplicación usará SQLite como fallback."
            )