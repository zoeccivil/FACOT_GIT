"""
Tabla mejorada de ítems para FACOT con funcionalidades avanzadas de UX.

Implementa PR2: Mejoras de UX para tabla de ítems
- Atajos de teclado (Ctrl+N, Supr, Ctrl+D, F2)
- Descuentos por línea y descuento global
- Drag-and-drop para reordenar
- Pegar desde Excel/portapapeles
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QMessageBox, QInputDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QDragEnterEvent, QDropEvent
from typing import List, Dict, Any, Optional, Callable
import re


class EnhancedItemsTable(QTableWidget):
    """
    Tabla mejorada de ítems con funcionalidades avanzadas.
    
    Características:
    - Atajos de teclado: Ctrl+N (nuevo), Supr (eliminar), Ctrl+D (duplicar), F2 (editar)
    - Descuentos por línea (columna adicional)
    - Drag-and-drop para reordenar filas
    - Pegar desde Excel/portapapeles
    - Menú contextual
    - Cálculo automático con descuentos
    
    Signals:
        items_changed: Emitido cuando cambian los ítems
        totals_changed: Emitido cuando cambian los totales
    """
    
    items_changed = pyqtSignal()
    totals_changed = pyqtSignal()
    
    # Índices de columnas
    COL_NUM = 0
    COL_CODE = 1
    COL_DESC = 2
    COL_UNIT = 3
    COL_QTY = 4
    COL_PRICE = 5
    COL_DISCOUNT = 6  # Nueva: descuento por línea (%)
    COL_SUBTOTAL = 7
    
    def __init__(self, parent=None, with_discounts: bool = True):
        """
        Inicializa la tabla mejorada.
        
        Args:
            parent: Widget padre
            with_discounts: Si True, incluye columna de descuentos
        """
        num_cols = 8 if with_discounts else 7
        super().__init__(0, num_cols, parent)
        
        self.with_discounts = with_discounts
        self.item_picker_callback: Optional[Callable] = None
        
        self._setup_headers()
        self._setup_behavior()
        self._setup_shortcuts()
        
    def _setup_headers(self):
        """Configura los encabezados de la tabla."""
        if self.with_discounts:
            headers = ["#", "Código", "Descripción", "Unidad", "Cantidad", 
                      "Precio", "Desc(%)", "Subtotal"]
        else:
            headers = ["#", "Código", "Descripción", "Unidad", "Cantidad", 
                      "Precio Unitario", "Subtotal"]
        
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False)
        
        # Columnas no editables
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
    
    def _setup_behavior(self):
        """Configura el comportamiento de la tabla."""
        # Habilitar drag and drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Menú contextual
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Conectar cambios
        self.itemChanged.connect(self._on_item_changed)
    
    def _setup_shortcuts(self):
        """Configura los atajos de teclado."""
        # Ctrl+N: Nuevo ítem
        self.shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.add_new_item)
        
        # Supr/Delete: Eliminar ítem
        self.shortcut_delete = QShortcut(QKeySequence.StandardKey.Delete, self)
        self.shortcut_delete.activated.connect(self.delete_selected_item)
        
        # Ctrl+D: Duplicar ítem
        self.shortcut_duplicate = QShortcut(QKeySequence("Ctrl+D"), self)
        self.shortcut_duplicate.activated.connect(self.duplicate_selected_item)
        
        # F2: Editar ítem (abrir diálogo)
        self.shortcut_edit = QShortcut(QKeySequence("F2"), self)
        self.shortcut_edit.activated.connect(self.edit_selected_item)
        
        # Ctrl+V: Pegar desde portapapeles
        self.shortcut_paste = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.shortcut_paste.activated.connect(self.paste_from_clipboard)
    
    def set_item_picker_callback(self, callback: Callable):
        """
        Establece el callback para abrir el selector de ítems.
        
        Args:
            callback: Función que abre el selector de ítems
        """
        self.item_picker_callback = callback
    
    def _show_context_menu(self, position):
        """Muestra el menú contextual."""
        menu = QMenu(self)
        
        # Nuevo ítem
        action_new = menu.addAction("➕ Nuevo ítem (Ctrl+N)")
        action_new.triggered.connect(self.add_new_item)
        
        # Si hay ítem seleccionado
        if self.currentRow() >= 0:
            menu.addSeparator()
            
            # Editar
            action_edit = menu.addAction("✏️ Editar ítem (F2)")
            action_edit.triggered.connect(self.edit_selected_item)
            
            # Duplicar
            action_duplicate = menu.addAction("📋 Duplicar ítem (Ctrl+D)")
            action_duplicate.triggered.connect(self.duplicate_selected_item)
            
            # Eliminar
            action_delete = menu.addAction("🗑️ Eliminar ítem (Supr)")
            action_delete.triggered.connect(self.delete_selected_item)
            
            menu.addSeparator()
            
            # Aplicar descuento
            if self.with_discounts:
                action_discount = menu.addAction("💰 Aplicar descuento...")
                action_discount.triggered.connect(self.apply_discount_to_selected)
        
        menu.addSeparator()
        
        # Pegar desde clipboard
        action_paste = menu.addAction("📄 Pegar desde Excel (Ctrl+V)")
        action_paste.triggered.connect(self.paste_from_clipboard)
        
        menu.exec(self.mapToGlobal(position))
    
    def add_new_item(self):
        """Agrega un nuevo ítem (Ctrl+N)."""
        if self.item_picker_callback:
            self.item_picker_callback()
        else:
            # Agregar fila vacía
            self.add_item_row("", "", "", "UND", 1.0, 0.0, 0.0)
    
    def delete_selected_item(self):
        """Elimina el ítem seleccionado (Supr)."""
        row = self.currentRow()
        if row >= 0:
            reply = QMessageBox.question(
                self,
                "Eliminar Ítem",
                f"¿Desea eliminar el ítem #{row + 1}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.removeRow(row)
                self._renumber_rows()
                self.items_changed.emit()
                self.totals_changed.emit()
    
    def duplicate_selected_item(self):
        """Duplica el ítem seleccionado (Ctrl+D)."""
        row = self.currentRow()
        if row >= 0:
            # Obtener datos de la fila
            code = self._get_cell_text(row, self.COL_CODE)
            desc = self._get_cell_text(row, self.COL_DESC)
            unit = self._get_cell_text(row, self.COL_UNIT)
            qty = self._get_cell_float(row, self.COL_QTY)
            price = self._get_cell_float(row, self.COL_PRICE)
            
            if self.with_discounts:
                discount = self._get_cell_float(row, self.COL_DISCOUNT)
            else:
                discount = 0.0
            
            # Agregar nuevo ítem duplicado
            self.add_item_row(code, desc, unit, unit, qty, price, discount)
            
            QMessageBox.information(
                self,
                "Ítem Duplicado",
                f"Ítem duplicado exitosamente."
            )
    
    def edit_selected_item(self):
        """Edita el ítem seleccionado (F2)."""
        row = self.currentRow()
        if row >= 0:
            # Hacer editable temporalmente
            self.editItem(self.item(row, self.COL_DESC))
    
    def apply_discount_to_selected(self):
        """Aplica un descuento al ítem seleccionado."""
        if not self.with_discounts:
            return
        
        row = self.currentRow()
        if row < 0:
            return
        
        current_discount = self._get_cell_float(row, self.COL_DISCOUNT)
        
        discount, ok = QInputDialog.getDouble(
            self,
            "Aplicar Descuento",
            "Ingrese el descuento (%):",
            current_discount,
            0.0,  # mínimo
            100.0,  # máximo
            2  # decimales
        )
        
        if ok:
            self.setItem(row, self.COL_DISCOUNT, QTableWidgetItem(f"{discount:.2f}"))
            self._recalculate_row_subtotal(row)
            self.totals_changed.emit()
    
    def paste_from_clipboard(self):
        """Pega ítems desde el portapapeles (Excel/CSV)."""
        from PyQt6.QtWidgets import QApplication
        
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text.strip():
            QMessageBox.warning(
                self,
                "Portapapeles Vacío",
                "No hay datos en el portapapeles para pegar."
            )
            return
        
        # Parsear datos del portapapeles
        lines = text.strip().split('\n')
        items_added = 0
        
        for line in lines:
            # Separar por tabulador (Excel) o coma (CSV)
            if '\t' in line:
                parts = line.split('\t')
            else:
                parts = [p.strip() for p in line.split(',')]
            
            if len(parts) < 3:
                continue  # Línea inválida
            
            # Parsear: Código, Descripción, Unidad, Cantidad, Precio, [Descuento]
            try:
                code = parts[0].strip() if len(parts) > 0 else ""
                desc = parts[1].strip() if len(parts) > 1 else ""
                unit = parts[2].strip() if len(parts) > 2 else "UND"
                qty = float(parts[3]) if len(parts) > 3 else 1.0
                price = float(parts[4]) if len(parts) > 4 else 0.0
                discount = float(parts[5]) if len(parts) > 5 and self.with_discounts else 0.0
                
                self.add_item_row(code, desc, unit, unit, qty, price, discount)
                items_added += 1
            
            except (ValueError, IndexError):
                continue  # Ignorar líneas con formato incorrecto
        
        if items_added > 0:
            QMessageBox.information(
                self,
                "Ítems Pegados",
                f"Se agregaron {items_added} ítem(s) desde el portapapeles."
            )
            self.items_changed.emit()
            self.totals_changed.emit()
        else:
            QMessageBox.warning(
                self,
                "Sin Ítems",
                "No se pudieron parsear ítems del portapapeles.\n\n"
                "Formato esperado (separado por tabuladores o comas):\n"
                "Código, Descripción, Unidad, Cantidad, Precio[, Descuento%]"
            )
    
    def add_item_row(self, code: str, name: str, unit_code: str, unit: str,
                     qty: float, price: float, discount: float = 0.0):
        """
        Agrega una fila de ítem a la tabla.
        
        Args:
            code: Código del ítem
            name: Descripción
            unit_code: Código de unidad (no usado, por compatibilidad)
            unit: Unidad de medida
            qty: Cantidad
            price: Precio unitario
            discount: Descuento en porcentaje (0-100)
        """
        row = self.rowCount()
        self.insertRow(row)
        
        # Calcular subtotal con descuento
        subtotal_before_discount = qty * price
        discount_amount = subtotal_before_discount * (discount / 100.0)
        subtotal = subtotal_before_discount - discount_amount
        
        # Llenar columnas
        self.setItem(row, self.COL_NUM, QTableWidgetItem(str(row + 1)))
        self.setItem(row, self.COL_CODE, QTableWidgetItem(code or ""))
        self.setItem(row, self.COL_DESC, QTableWidgetItem(name or ""))
        self.setItem(row, self.COL_UNIT, QTableWidgetItem((unit or "").strip()))
        self.setItem(row, self.COL_QTY, QTableWidgetItem(f"{float(qty):.2f}"))
        self.setItem(row, self.COL_PRICE, QTableWidgetItem(f"{float(price):.2f}"))
        
        if self.with_discounts:
            self.setItem(row, self.COL_DISCOUNT, QTableWidgetItem(f"{float(discount):.2f}"))
            self.setItem(row, self.COL_SUBTOTAL, QTableWidgetItem(f"{float(subtotal):,.2f}"))
        else:
            self.setItem(row, self.COL_SUBTOTAL - 1, QTableWidgetItem(f"{float(subtotal):,.2f}"))
        
        # Hacer columnas no editables excepto cantidad, precio y descuento
        for col in [self.COL_NUM, self.COL_CODE, self.COL_DESC, self.COL_UNIT, self.COL_SUBTOTAL]:
            item = self.item(row, col)
            if item:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        self.items_changed.emit()
    
    def get_items(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los ítems de la tabla.
        
        Returns:
            Lista de diccionarios con los datos de cada ítem
        """
        items = []
        for row in range(self.rowCount()):
            item_data = {
                "code": self._get_cell_text(row, self.COL_CODE),
                "name": self._get_cell_text(row, self.COL_DESC),
                "unit": self._get_cell_text(row, self.COL_UNIT),
                "qty": self._get_cell_float(row, self.COL_QTY),
                "price": self._get_cell_float(row, self.COL_PRICE),
            }
            
            if self.with_discounts:
                item_data["discount"] = self._get_cell_float(row, self.COL_DISCOUNT)
            
            items.append(item_data)
        
        return items
    
    def clear_all_items(self):
        """Elimina todos los ítems de la tabla."""
        self.setRowCount(0)
        self.items_changed.emit()
        self.totals_changed.emit()
    
    def _renumber_rows(self):
        """Renumera las filas después de eliminar o reordenar."""
        for i in range(self.rowCount()):
            self.setItem(i, self.COL_NUM, QTableWidgetItem(str(i + 1)))
    
    def _recalculate_row_subtotal(self, row: int):
        """Recalcula el subtotal de una fila."""
        qty = self._get_cell_float(row, self.COL_QTY)
        price = self._get_cell_float(row, self.COL_PRICE)
        
        subtotal_before_discount = qty * price
        
        if self.with_discounts:
            discount = self._get_cell_float(row, self.COL_DISCOUNT)
            discount_amount = subtotal_before_discount * (discount / 100.0)
            subtotal = subtotal_before_discount - discount_amount
            col_subtotal = self.COL_SUBTOTAL
        else:
            subtotal = subtotal_before_discount
            col_subtotal = self.COL_SUBTOTAL - 1
        
        self.setItem(row, col_subtotal, QTableWidgetItem(f"{float(subtotal):,.2f}"))
    
    def _on_item_changed(self, item: QTableWidgetItem):
        """Callback cuando cambia un ítem."""
        if item is None:
            return
        
        row = item.row()
        col = item.column()
        
        # Si cambió cantidad, precio o descuento, recalcular
        if col in [self.COL_QTY, self.COL_PRICE] or (col == self.COL_DISCOUNT and self.with_discounts):
            self._recalculate_row_subtotal(row)
            self.totals_changed.emit()
    
    def _get_cell_text(self, row: int, col: int) -> str:
        """Obtiene el texto de una celda."""
        item = self.item(row, col)
        return item.text() if item else ""
    
    def _get_cell_float(self, row: int, col: int) -> float:
        """Obtiene el valor float de una celda."""
        text = self._get_cell_text(row, col)
        # Limpiar formato de números
        text = text.replace(',', '').strip()
        try:
            return float(text)
        except (ValueError, AttributeError):
            return 0.0
    
    def dropEvent(self, event: QDropEvent):
        """Maneja el evento de soltar (drag and drop)."""
        super().dropEvent(event)
        self._renumber_rows()
        self.items_changed.emit()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Maneja el evento de entrar arrastrando."""
        event.accept()
