import sqlite3
from PyQt6.QtWidgets import (
    QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QPushButton, QWidget, QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt

# Lee la ruta de la BD desde la configuración
import facot_config  # Debe exponer get_db_path()


from PyQt6.QtWidgets import (
    QHBoxLayout, QLineEdit, QTableView, QVBoxLayout,  # Cambiado QTableWidget por QTableView
    QPushButton, QWidget, QLabel, QHeaderView, QMessageBox
)
from models.items_table_model import ItemsTableModel

def get_db_path() -> str:
    return facot_config.get_db_path() or ""

def ensure_items_schema(db_path: str):
    if not db_path:
        return
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                unit TEXT NOT NULL,
                cost REAL NOT NULL DEFAULT 0,
                price REAL NOT NULL DEFAULT 0,
                category_id INTEGER,
                description TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE INDEX IF NOT EXISTS idx_items_code ON items(code);
            CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
        """)

class DetalleItemsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.sugerencias = []
        self.seleccion_actual = None

        # Garantiza que existan las tablas en la BD activa
        db_path = get_db_path()
        ensure_items_schema(db_path)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Buscador de ítems ---
        buscador_layout = QHBoxLayout()
        buscador_layout.addWidget(QLabel("Buscar producto/servicio:"))
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Escriba código, nombre o categoría")
        buscador_layout.addWidget(self.buscador)
        layout.addLayout(buscador_layout)

        # --- Tabla de sugerencias ---
        self.sugerencias_table = QTableWidget(0, 5)
        self.sugerencias_table.setHorizontalHeaderLabels(["Código", "Nombre", "Unidad", "Precio", "Categoría"])
        self.sugerencias_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sugerencias_table.verticalHeader().setVisible(False)
        self.sugerencias_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sugerencias_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.sugerencias_table)

        # --- Campos seleccionados para agregar detalle ---
        campos_layout = QHBoxLayout()
        self.codigo_edit = QLineEdit(); self.codigo_edit.setPlaceholderText("Código"); self.codigo_edit.setReadOnly(True)
        self.nombre_edit = QLineEdit(); self.nombre_edit.setPlaceholderText("Nombre"); self.nombre_edit.setReadOnly(True)
        self.unidad_edit = QLineEdit(); self.unidad_edit.setPlaceholderText("Unidad"); self.unidad_edit.setReadOnly(True)
        self.precio_edit = QLineEdit(); self.precio_edit.setPlaceholderText("Precio Unitario")
        self.cantidad_edit = QLineEdit(); self.cantidad_edit.setPlaceholderText("Cantidad")
        campos_layout.addWidget(self.codigo_edit)
        campos_layout.addWidget(self.nombre_edit)
        campos_layout.addWidget(self.unidad_edit)
        campos_layout.addWidget(self.precio_edit)
        campos_layout.addWidget(self.cantidad_edit)
        layout.addLayout(campos_layout)

        self.btn_agregar = QPushButton("Agregar Detalle")
        layout.addWidget(self.btn_agregar)

        # Señales
        self.buscador.textChanged.connect(self._search_items)
        self.sugerencias_table.cellClicked.connect(self._on_sugerencia_select)

    def _search_items(self):
        texto = self.buscador.text().strip()
        if len(texto) < 1:
            self.sugerencias_table.setRowCount(0)
            return

        db_path = get_db_path()
        if not db_path:
            QMessageBox.warning(self, "Base de datos", "No hay una base de datos seleccionada.")
            return

        # Asegura el esquema por si la BD fue cambiada en caliente
        ensure_items_schema(db_path)

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT items.code, items.name, items.unit, items.price, IFNULL(categories.name, '')
                FROM items
                LEFT JOIN categories ON items.category_id = categories.id
                WHERE items.code LIKE ? OR items.name LIKE ? OR IFNULL(categories.name,'') LIKE ?
                ORDER BY items.name
            """, (f"%{texto}%", f"%{texto}%", f"%{texto}%"))
            self.sugerencias = cur.fetchall()
        except sqlite3.OperationalError as e:
            # Intento de recuperación: crear tablas y reintentar una vez
            ensure_items_schema(db_path)
            try:
                cur.execute("""
                    SELECT items.code, items.name, items.unit, items.price, IFNULL(categories.name, '')
                    FROM items
                    LEFT JOIN categories ON items.category_id = categories.id
                    WHERE items.code LIKE ? OR items.name LIKE ? OR IFNULL(categories.name,'') LIKE ?
                    ORDER BY items.name
                """, (f"%{texto}%", f"%{texto}%", f"%{texto}%"))
                self.sugerencias = cur.fetchall()
            except Exception as e2:
                QMessageBox.critical(self, "BD", f"Error consultando ítems:\n{e2}")
                self.sugerencias = []
        finally:
            try:
                conn.close()
            except Exception:
                pass

        self.sugerencias_table.setRowCount(0)
        for idx, row in enumerate(self.sugerencias):
            self.sugerencias_table.insertRow(idx)
            for col, val in enumerate(row):
                self.sugerencias_table.setItem(idx, col, QTableWidgetItem(str(val)))

    def _on_sugerencia_select(self, row, col):
        if row < 0 or row >= len(self.sugerencias):
            return
        codigo, nombre, unidad, precio, categoria = self.sugerencias[row]
        self.codigo_edit.setText(str(codigo))
        self.nombre_edit.setText(str(nombre))
        self.unidad_edit.setText(str(unidad))
        self.precio_edit.setText(str(precio))
        self.cantidad_edit.setFocus()
        self.seleccion_actual = self.sugerencias[row]

    def get_detalle(self):
        # Devuelve el detalle listo para agregar a la tabla principal
        try:
            cantidad = float(self.cantidad_edit.text())
            precio = float(self.precio_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Cantidad y precio deben ser numéricos")
            return None
        subtotal = cantidad * precio
        return {
            "codigo": self.codigo_edit.text(),
            "nombre": self.nombre_edit.text(),
            "unidad": self.unidad_edit.text(),
            "cantidad": cantidad,
            "precio": precio,
            "subtotal": subtotal
        }

    def clear_detalle(self):
        self.codigo_edit.clear()
        self.nombre_edit.clear()
        self.unidad_edit.clear()
        self.precio_edit.clear()
        self.cantidad_edit.clear()
        self.seleccion_actual = None