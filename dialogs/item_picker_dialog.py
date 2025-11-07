from __future__ import annotations

import sqlite3
from typing import List, Dict, Tuple, Optional

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QDoubleValidator, QFontMetrics
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QWidget, QHeaderView, QMessageBox, QGroupBox, QFormLayout, QSplitter,
    QComboBox, QStyledItemDelegate, QSizePolicy, QDialogButtonBox
)

import facot_config
from items_management_window import ItemsManagementWindow
from PyQt6.QtGui import QDoubleValidator, QFontMetrics, QAction
from PyQt6.QtWidgets import (QMenu)

def get_db_path() -> str:
    return facot_config.get_db_path() or ""


class NumericItemDelegate(QStyledItemDelegate):
    """Delegate numérico para edición de celdas (float)."""
    def __init__(self, decimals: int = 4, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.decimals = decimals

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setValidator(QDoubleValidator(0.0, 1e12, self.decimals, parent))
        return editor

    def setEditorData(self, editor, index):
        text = index.data() or ""
        editor.setText(text)

    def setModelData(self, editor, model, index):
        try:
            val = float((editor.text() or "0").replace(",", ""))
        except Exception:
            val = 0.0
        model.setData(index, f"{val:.2f}")


class ItemEditDialog(QDialog):
    """
    Editor rápido de un ítem (código, nombre, unidad, precio y categoría).
    Carga/guarda directamente desde la BD SQLite.
    """
    def __init__(self, code: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Ítem - {code}")
        self.setModal(True)
        self._original_code = code
        self._item_id: Optional[int] = None
        self._categories: List[Tuple[int, str]] = []  # (id, name)
        self._build_ui()
        ok = self._load_item(code)
        if not ok:
            QMessageBox.critical(self, "Ítem", f"No se encontró el ítem con código '{code}'.")
            self.reject()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        form = QFormLayout()
        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.unit_edit = QLineEdit()
        self.price_edit = QLineEdit()
        self.price_edit.setValidator(QDoubleValidator(0.0, 1e12, 4, self))

        self.category_combo = QComboBox()
        self._load_categories()

        form.addRow("Código:", self.code_edit)
        form.addRow("Nombre:", self.name_edit)
        form.addRow("Unidad:", self.unit_edit)
        form.addRow("Precio:", self.price_edit)
        form.addRow("Categoría:", self.category_combo)

        lay.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)


    def _load_categories(self):
        self._categories.clear()
        self.category_combo.clear()
        db = get_db_path()
        if not db:
            return
        with sqlite3.connect(db) as conn:
            rows = conn.execute("SELECT id, IFNULL(name,'') FROM categories ORDER BY name").fetchall()
        for cid, name in rows:
            self._categories.append((cid, name))
            self.category_combo.addItem(name, cid)

    def _load_item(self, code: str) -> bool:
        db = get_db_path()
        if not db:
            return False
        with sqlite3.connect(db) as conn:
            row = conn.execute(
                "SELECT id, code, IFNULL(name,''), IFNULL(unit,''), IFNULL(price,0), IFNULL(category_id, NULL) "
                "FROM items WHERE code = ?",
                (code,)
            ).fetchone()
        if not row:
            return False
        self._item_id = int(row[0])
        self.code_edit.setText(row[1] or "")
        self.name_edit.setText(row[2] or "")
        self.unit_edit.setText(row[3] or "")
        self.price_edit.setText(f"{float(row[4] or 0.0):.2f}")
        cat_id = row[5]
        if cat_id is not None:
            idx = self.category_combo.findData(cat_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
        return True

    def _on_save(self):
        code = (self.code_edit.text() or "").strip()
        name = (self.name_edit.text() or "").strip()
        unit = (self.unit_edit.text() or "").strip()
        try:
            price = float((self.price_edit.text() or "0").replace(",", ""))
        except Exception:
            price = 0.0
        cat_id = self.category_combo.currentData()

        if not code or not name:
            QMessageBox.warning(self, "Validación", "Código y Nombre son obligatorios.")
            return
        if self._item_id is None:
            QMessageBox.critical(self, "Ítem", "No hay ID de ítem para guardar.")
            return

        db = get_db_path()
        try:
            with sqlite3.connect(db) as conn:
                conn.execute(
                    "UPDATE items SET code = ?, name = ?, unit = ?, price = ?, category_id = ? WHERE id = ?",
                    (code, name, unit, price, cat_id, self._item_id)
                )
                conn.commit()
            self.accept()
        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Guardar", f"No se pudo guardar el ítem (código duplicado?):\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Guardar", f"Error al guardar:\n{e}")

    def get_result(self) -> Dict:
        return {
            "original_code": self._original_code,
            "code": (self.code_edit.text() or "").strip(),
            "name": (self.name_edit.text() or "").strip(),
            "unit": (self.unit_edit.text() or "").strip(),
            "price": float((self.price_edit.text() or "0").replace(",", "")) if (self.price_edit.text() or "").strip() else 0.0,
            "category_id": self.category_combo.currentData(),
        }


class ItemPickerDialog(QDialog):
    """
    Diálogo para buscar ítems, agregarlos con cantidad y precio a un 'carrito'
    y devolverlos al tab de Factura/Cotización.
    - Búsqueda por texto + filtro por categoría
    - Edición en línea de Cantidad/Precio en el carrito
    - Re-cálculo automático de subtotales y total del carrito
    - Abrir Gestión de Ítems y refrescar al volver
    - Expandible y con botón de maximizar
    """
    def __init__(self, parent=None, title: str = "Agregar ítems"):
        super().__init__(parent)
        self.setWindowTitle(title)

        # Habilitar maximizar/minimizar y expansión
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowFlags(self.windowFlags()
                            | Qt.WindowType.WindowMinMaxButtonsHint
                            | Qt.WindowType.WindowMaximizeButtonHint)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setSizeGripEnabled(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.resize(980, 600)

        self._updating_cart = False
        self.categories: List[Tuple[int, str, str]] = []

        self._build_ui()
        self._load_categories()
        self._search_items()
        self._restore_geometry()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.setStyleSheet("""
        QGroupBox {
            border: 1px solid #555; border-radius: 6px; margin-top: 8px; 
            padding: 8px; 
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        """)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        root.addWidget(splitter, stretch=1)

        # Panel izquierdo
        left = QWidget(); left_lay = QVBoxLayout(left)
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        filters_box = QGroupBox("Buscar ítems")
        filters_lay = QHBoxLayout(filters_box)
        self.category_filter = QComboBox(); self.category_filter.currentIndexChanged.connect(self._search_items)
        self.category_filter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("Escribe código o nombre…")
        self.search_edit.textChanged.connect(self._search_items)
        btn_refresh = QPushButton("Refrescar"); btn_refresh.clicked.connect(self._search_items)

        filters_lay.addWidget(QLabel("Categoría:"))
        filters_lay.addWidget(self.category_filter, stretch=2)
        filters_lay.addWidget(QLabel("Texto:"))
        filters_lay.addWidget(self.search_edit, stretch=3)
        filters_lay.addWidget(btn_refresh)
        left_lay.addWidget(filters_box)

        # Resultados: Código, Nombre, Unidad, Precio, Categoría(oculta)
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Código", "Nombre", "Unidad", "Precio", "Categoría"])
        header = self.results_table.horizontalHeader()
        # Modos de redimensionamiento
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # La columna Nombre se estira con la ventana
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Ocultar la columna Categoría (index 4)
        self.results_table.setColumnHidden(4, True)
        # Doble clic: editar ítem
        self.results_table.itemDoubleClicked.connect(self._on_result_double_clicked)
        # Al cambiar selección: precargar precio y cantidad
        self.results_table.currentCellChanged.connect(self._on_results_current_changed)
        left_lay.addWidget(self.results_table, stretch=1)
        # Dentro de _build_ui(), justo después de configurar self.results_table:
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._on_results_context_menu)
        # Aplicar anchos iniciales
        self._apply_results_column_layout()

        # Panel derecho
        right = QWidget(); right_lay = QVBoxLayout(right)
        right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        controls_box = QGroupBox("Detalle de selección")
        controls_form = QFormLayout(controls_box)
        self.qty_edit = QLineEdit("1"); self.qty_edit.setValidator(QDoubleValidator(0.0, 1e9, 4, self))
        self.price_edit = QLineEdit(""); self.price_edit.setValidator(QDoubleValidator(0.0, 1e12, 4, self))
        btn_add = QPushButton("Agregar al carrito"); btn_add.clicked.connect(self._add_selected_to_cart)
        btn_manage = QPushButton("Gestionar Ítems…"); btn_manage.clicked.connect(self._open_items_management)
        row_btns = QHBoxLayout(); row_btns.addWidget(btn_add); row_btns.addWidget(btn_manage)
        controls_form.addRow("Cantidad:", self.qty_edit)
        controls_form.addRow("Precio:", self.price_edit)
        controls_form.addRow(row_btns)
        right_lay.addWidget(controls_box)

        cart_box = QGroupBox("Ítems seleccionados")
        cart_lay = QVBoxLayout(cart_box)
        self.cart_table = QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels(["Código", "Descripción", "Unidad", "Cantidad", "Precio Unitario", "Subtotal"])
        cart_header = self.cart_table.horizontalHeader()
        cart_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        cart_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Descripción se estira
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cart_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked)
        # Delegate numérico en Cantidad (3) y Precio (4)
        self.cart_table.setItemDelegateForColumn(3, NumericItemDelegate(4, self.cart_table))
        self.cart_table.setItemDelegateForColumn(4, NumericItemDelegate(4, self.cart_table))
        self.cart_table.itemChanged.connect(self._on_cart_item_changed)
        self.cart_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cart_lay.addWidget(self.cart_table)

        # Anchos sugeridos para el carrito
        self._apply_cart_column_layout()

        cart_bottom = QHBoxLayout()
        self.cart_total_label = QLabel("Total carrito: 0.00")
        cart_bottom.addWidget(self.cart_total_label)
        cart_bottom.addStretch(1)
        btn_remove = QPushButton("Quitar seleccionado"); btn_remove.clicked.connect(self._remove_selected_cart)
        btn_clear = QPushButton("Vaciar carrito"); btn_clear.clicked.connect(self._clear_cart)
        cart_bottom.addWidget(btn_remove); cart_bottom.addWidget(btn_clear)
        cart_lay.addLayout(cart_bottom)
        right_lay.addWidget(cart_box, stretch=1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Botonera pie
        actions = QHBoxLayout()
        actions.addStretch(1)
        ok = QPushButton("Aceptar"); ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancelar"); cancel.clicked.connect(self.reject)
        actions.addWidget(ok); actions.addWidget(cancel)
        root.addLayout(actions)

    # ------- Ajuste de columnas -------
    def _apply_results_column_layout(self):
        """
        Resultados: Código (6 dígitos aprox), Nombre (ancho dinámico), Unidad (~3-4 chars), Precio (~9-12 chars), Categoría (oculta)
        """
        fm = QFontMetrics(self.results_table.font())
        code_w = fm.horizontalAdvance("999999") + 24           # 6 dígitos + padding
        unit_w = fm.horizontalAdvance("UNID") + 24             # 3-4 chars
        price_w = fm.horizontalAdvance("9,999,999.99") + 28    # 9-12 chars con separadores

        header = self.results_table.horizontalHeader()
        header.resizeSection(0, max(80, code_w))
        header.resizeSection(2, max(60, unit_w))
        header.resizeSection(3, max(110, price_w))
        # Categoría (4) está oculta
        self.results_table.setColumnHidden(4, True)

    def _apply_cart_column_layout(self):
        fm = QFontMetrics(self.cart_table.font())
        code_w = fm.horizontalAdvance("999999") + 24
        unit_w = fm.horizontalAdvance("UNID") + 24
        qty_w = fm.horizontalAdvance("9999.99") + 24
        price_w = fm.horizontalAdvance("9,999,999.99") + 28
        subtotal_w = price_w + 10

        header = self.cart_table.horizontalHeader()
        header.resizeSection(0, max(80, code_w))       # Código
        header.resizeSection(2, max(60, unit_w))       # Unidad
        header.resizeSection(3, max(80, qty_w))        # Cantidad
        header.resizeSection(4, max(110, price_w))     # Precio
        header.resizeSection(5, max(120, subtotal_w))  # Subtotal
        # Descripción (1) se estira con la ventana (Stretch)

    # ------- Persistencia de geometría -------
    def _restore_geometry(self):
        s = QSettings("FACOT", "ItemPickerDialog")
        geom = s.value("geometry", None)
        if geom:
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass

    def _save_geometry(self):
        s = QSettings("FACOT", "ItemPickerDialog")
        s.setValue("geometry", self.saveGeometry())

    def accept(self):
        self._save_geometry()
        super().accept()

    def reject(self):
        self._save_geometry()
        super().reject()

    # ------- Datos auxiliares -------
    def _load_categories(self):
        db = get_db_path()
        self.categories.clear()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Todas", None)
        if db:
            with sqlite3.connect(db) as conn:
                rows = conn.execute(
                    "SELECT id, IFNULL(name,''), IFNULL(code_prefix,'') FROM categories ORDER BY name"
                ).fetchall()
            for cid, name, prefix in rows:
                self.categories.append((cid, name, prefix))
                self.category_filter.addItem(f"{name} ({prefix})", cid)
        self.category_filter.blockSignals(False)

    # ------- Acciones -------
    def _open_items_management(self):
        dlg = ItemsManagementWindow(self)
        dlg.exec()
        current_cid = self.category_filter.currentData()
        self._load_categories()
        if current_cid:
            idx = self.category_filter.findData(current_cid)
            if idx >= 0:
                self.category_filter.setCurrentIndex(idx)
        self._search_items()

    def _search_items(self):
        text = (self.search_edit.text() or "").strip().lower()
        sel_cid = self.category_filter.currentData()
        db = get_db_path()
        if not db:
            QMessageBox.warning(self, "Base de datos", "No hay base de datos seleccionada.")
            return
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            base_q = """
                SELECT i.code, i.name, i.unit, i.price, IFNULL(c.name,'')
                FROM items i
                LEFT JOIN categories c ON c.id = i.category_id
                WHERE (LOWER(i.code) LIKE ? OR LOWER(i.name) LIKE ? OR LOWER(IFNULL(c.name,'')) LIKE ?)
            """
            params = [f"%{text}%", f"%{text}%", f"%{text}%"]
            if sel_cid:
                base_q += " AND i.category_id = ?"
                params.append(sel_cid)
            base_q += " ORDER BY i.name"
            cur.execute(base_q, params)
            rows = cur.fetchall()
        self.results_table.setRowCount(0)
        for r, row in enumerate(rows):
            self.results_table.insertRow(r)
            for c, val in enumerate(row):
                # Precio en formato con 2 decimales
                if c == 3:
                    try:
                        val = f"{float(val or 0.0):.2f}"
                    except Exception:
                        val = "0.00"
                self.results_table.setItem(r, c, QTableWidgetItem(str(val)))
        # Restablecer layout (por si cambió la fuente o DPI)
        self._apply_results_column_layout()

    # Doble click en resultados -> Editar ítem
    def _on_result_double_clicked(self, item: QTableWidgetItem):
        if not item:
            return
        r = item.row()
        code_it = self.results_table.item(r, 0)
        if not code_it:
            return
        old_code = code_it.text()
        dlg = ItemEditDialog(old_code, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_result()
            # Refrescar resultados y re-seleccionar el código (nuevo o el mismo)
            self._search_items()
            self._reselect_result_by_code(updated.get("code") or old_code)
            # Actualizar carrito si existía ese código
            self._update_cart_rows_after_edit(updated.get("original_code") or old_code, updated)

    def _reselect_result_by_code(self, code: str):
        if not code:
            return
        for r in range(self.results_table.rowCount()):
            it = self.results_table.item(r, 0)
            if it and it.text() == code:
                self.results_table.selectRow(r)
                # Disparar el precargado de precio
                self._on_results_current_changed(r, 0, -1, -1)
                break

    # Al cambiar selección en resultados -> precargar precio y cantidad=1
    def _on_results_current_changed(self, cur_row: int, cur_col: int, prev_row: int, prev_col: int):
        try:
            if cur_row < 0:
                return
            price_cell = self.results_table.item(cur_row, 3)
            price_def = float(price_cell.text()) if price_cell and price_cell.text() else 0.0
            self.price_edit.setText(f"{price_def:.2f}")
            self.qty_edit.setText("1")
        except Exception:
            pass

    def _add_selected_to_cart_quick(self, row: int, col: int):
        # Conservamos esta función por compatibilidad, pero ya no está conectada a doble click
        self._add_selected_to_cart(default_qty=True)

    def _add_selected_to_cart(self, default_qty: bool = False):
        r = self.results_table.currentRow()
        if r < 0:
            QMessageBox.information(self, "Selección", "Selecciona un ítem en la lista de resultados.")
            return
        code = self.results_table.item(r, 0).text()
        name = self.results_table.item(r, 1).text()
        unit = self.results_table.item(r, 2).text()
        price_cell = self.results_table.item(r, 3)
        price_def = float(price_cell.text()) if price_cell and price_cell.text() else 0.0

        try:
            qty = 1.0 if default_qty else float(self.qty_edit.text().replace(",", ".") or "1")
            price_input = (self.price_edit.text() or "").replace(",", ".")
            price = price_def if (default_qty and (price_input.strip() == "")) else float(price_input or price_def)
        except ValueError:
            QMessageBox.warning(self, "Validación", "Cantidad y Precio deben ser numéricos.")
            return
        if qty <= 0:
            QMessageBox.warning(self, "Validación", "La cantidad debe ser mayor a cero.")
            return
        if price < 0:
            QMessageBox.warning(self, "Validación", "El precio no puede ser negativo.")
            return

        found_row = -1
        for i in range(self.cart_table.rowCount()):
            if self.cart_table.item(i, 0).text() == code:
                found_row = i
                break
        if found_row >= 0:
            old_qty = float(self.cart_table.item(found_row, 3).text().replace(",", ""))
            new_qty = old_qty + qty
            self._updating_cart = True
            self.cart_table.setItem(found_row, 3, QTableWidgetItem(f"{new_qty:.2f}"))
            self.cart_table.setItem(found_row, 4, QTableWidgetItem(f"{price:.2f}"))
            self.cart_table.setItem(found_row, 5, QTableWidgetItem(f"{new_qty * price:.2f}"))
            self._updating_cart = False
        else:
            row = self.cart_table.rowCount()
            self.cart_table.insertRow(row)
            self.cart_table.setItem(row, 0, QTableWidgetItem(code))
            self.cart_table.setItem(row, 1, QTableWidgetItem(name))
            self.cart_table.setItem(row, 2, QTableWidgetItem(unit))
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"{qty:.2f}"))
            self.cart_table.setItem(row, 4, QTableWidgetItem(f"{price:.2f}"))
            self.cart_table.setItem(row, 5, QTableWidgetItem(f"{qty * price:.2f}"))

        self.qty_edit.setText("1")
        self._update_cart_total()

    def _on_cart_item_changed(self, item: QTableWidgetItem):
        if self._updating_cart:
            return
        row = item.row()
        col = item.column()
        if col not in (3, 4):
            return
        try:
            qty = float(self.cart_table.item(row, 3).text().replace(",", "")) if self.cart_table.item(row, 3) else 0.0
            price = float(self.cart_table.item(row, 4).text().replace(",", "")) if self.cart_table.item(row, 4) else 0.0
        except Exception:
            qty = 0.0; price = 0.0
        qty = max(0.0, qty); price = max(0.0, price)
        self._updating_cart = True
        self.cart_table.setItem(row, 3, QTableWidgetItem(f"{qty:.2f}"))
        self.cart_table.setItem(row, 4, QTableWidgetItem(f"{price:.2f}"))
        self.cart_table.setItem(row, 5, QTableWidgetItem(f"{qty * price:.2f}"))
        self._updating_cart = False
        self._update_cart_total()

    def _remove_selected_cart(self):
        r = self.cart_table.currentRow()
        if r >= 0:
            self.cart_table.removeRow(r)
            self._update_cart_total()

    def _clear_cart(self):
        self.cart_table.setRowCount(0)
        self._update_cart_total()

    def _update_cart_total(self):
        total = 0.0
        for r in range(self.cart_table.rowCount()):
            try:
                val = float(self.cart_table.item(r, 5).text().replace(",", "")) if self.cart_table.item(r, 5) else 0.0
            except Exception:
                val = 0.0
            total += val
        self.cart_total_label.setText(f"Total carrito: {total:,.2f}")

    def _update_cart_rows_after_edit(self, old_code: str, updated: Dict):
        """
        Si un ítem editado existe en el carrito, actualizar sus datos visibles (código/nombre/unidad/precio).
        """
        if not updated:
            return
        new_code = updated.get("code", old_code)
        new_name = updated.get("name", "")
        new_unit = updated.get("unit", "")
        new_price = float(updated.get("price", 0.0) or 0.0)

        for r in range(self.cart_table.rowCount()):
            code_it = self.cart_table.item(r, 0)
            if not code_it:
                continue
            if code_it.text() == old_code:
                # Actualizar celdas
                self.cart_table.setItem(r, 0, QTableWidgetItem(new_code))
                if new_name:
                    self.cart_table.setItem(r, 1, QTableWidgetItem(new_name))
                if new_unit:
                    self.cart_table.setItem(r, 2, QTableWidgetItem(new_unit))
                if new_price > 0:
                    # Mantener cantidad y recalcular subtotal
                    try:
                        qty = float(self.cart_table.item(r, 3).text().replace(",", ""))
                    except Exception:
                        qty = 0.0
                    self.cart_table.setItem(r, 4, QTableWidgetItem(f"{new_price:.2f}"))
                    self.cart_table.setItem(r, 5, QTableWidgetItem(f"{qty * new_price:.2f}"))
        self._update_cart_total()

    def get_selected_items(self) -> List[Dict]:
        items: List[Dict] = []
        for r in range(self.cart_table.rowCount()):
            code = self.cart_table.item(r, 0).text()
            name = self.cart_table.item(r, 1).text()
            unit = self.cart_table.item(r, 2).text()
            qty = float(self.cart_table.item(r, 3).text().replace(",", ""))
            price = float(self.cart_table.item(r, 4).text().replace(",", ""))
            subtotal = float(self.cart_table.item(r, 5).text().replace(",", ""))
            items.append({
                "codigo": code,
                "nombre": name,
                "unidad": unit,
                "cantidad": qty,
                "precio": price,
                "subtotal": subtotal,
            })
        return items
    
    def _on_results_context_menu(self, pos):
        """
        Menú contextual sobre la tabla de resultados:
        - Agregar al carrito
        - Editar ítem
        """
        # Determinar fila bajo el cursor
        index = self.results_table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        # Seleccionar la fila bajo el cursor y fijar celda actual para disparar precarga de precio/cantidad
        try:
            self.results_table.selectRow(row)
            self.results_table.setCurrentCell(row, 0)
            # Esto hace que _on_results_current_changed precargue precio y cantidad=1
            self._on_results_current_changed(row, 0, -1, -1)
        except Exception:
            pass

        menu = QMenu(self)
        act_add = QAction("Agregar al carrito", self)
        act_edit = QAction("Editar ítem…", self)

        # Handlers
        act_add.triggered.connect(lambda: self._add_selected_to_cart(default_qty=True))
        act_edit.triggered.connect(self._edit_selected_result)

        menu.addAction(act_add)
        menu.addSeparator()
        menu.addAction(act_edit)

        # Posición global del menú
        global_pos = self.results_table.viewport().mapToGlobal(pos)
        menu.exec(global_pos)


    def _edit_selected_result(self):
        """
        Abre el editor rápido para el ítem seleccionado en la tabla de resultados.
        Tras guardar, refresca la lista, re-selecciona el ítem (código nuevo si cambió),
        y actualiza el carrito si existía ese código.
        """
        r = self.results_table.currentRow()
        if r < 0:
            QMessageBox.information(self, "Selección", "Selecciona un ítem para editar.")
            return
        code_it = self.results_table.item(r, 0)
        if not code_it:
            return

        old_code = code_it.text()
        dlg = ItemEditDialog(old_code, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_result()
            # Refrescar resultados y re-seleccionar el código (nuevo o el mismo)
            self._search_items()
            self._reselect_result_by_code(updated.get("code") or old_code)
            # Actualizar carrito si existía ese código
            self._update_cart_rows_after_edit(updated.get("original_code") or old_code, updated)