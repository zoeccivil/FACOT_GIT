"""
Modelo Qt para la tabla de items de factura/cotización.
Implementa el patrón Model-View de Qt para mejor separación de lógica.
"""
from typing import Any, List, Dict, Optional
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFont


class ItemsTableModel(QAbstractTableModel):
    """
    Modelo para gestionar items en facturas/cotizaciones.
    
    Columnas:
    0. Código
    1. Descripción
    2. Cantidad
    3. Unidad
    4. Precio Unit.
    5. Descuento (%)
    6. Subtotal
    """
    
    # Signal emitido cuando cambian los datos
    dataChangedSignal = pyqtSignal()
    
    # Definición de columnas
    COLUMNS = [
        "Código",
        "Descripción", 
        "Cantidad",
        "Unidad",
        "Precio Unit.",
        "Descuento (%)",
        "Subtotal"
    ]
    
    # Índices de columnas
    COL_CODE = 0
    COL_DESC = 1
    COL_QTY = 2
    COL_UNIT = 3
    COL_PRICE = 4
    COL_DISCOUNT = 5
    COL_SUBTOTAL = 6
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[Dict[str, Any]] = []
        
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Retorna el número de filas."""
        if parent.isValid():
            return 0
        return len(self._items)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Retorna el número de columnas."""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Retorna los datos para mostrar en la vista."""
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._items):
            return None
        
        item = self._items[row]
        
        # Datos a mostrar
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if col == self.COL_CODE:
                return item.get('code', '')
            elif col == self.COL_DESC:
                return item.get('description', '')
            elif col == self.COL_QTY:
                qty = item.get('quantity', 0)
                return f"{qty:.2f}" if role == Qt.ItemDataRole.DisplayRole else qty
            elif col == self.COL_UNIT:
                return item.get('unit', '')
            elif col == self.COL_PRICE:
                price = item.get('unit_price', 0)
                return f"{price:,.2f}" if role == Qt.ItemDataRole.DisplayRole else price
            elif col == self.COL_DISCOUNT:
                discount = item.get('discount_percent', 0)
                return f"{discount:.2f}" if role == Qt.ItemDataRole.DisplayRole else discount
            elif col == self.COL_SUBTOTAL:
                subtotal = self._calculate_subtotal(item)
                return f"{subtotal:,.2f}"
        
        # Alineación de texto
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [self.COL_QTY, self.COL_PRICE, self.COL_DISCOUNT, self.COL_SUBTOTAL]:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        # Fuente para subtotal (negrita)
        elif role == Qt.ItemDataRole.FontRole:
            if col == self.COL_SUBTOTAL:
                font = QFont()
                font.setBold(True)
                return font
        
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Establece los datos cuando se edita una celda."""
        if not index.isValid():
            return False
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._items):
            return False
        
        # Columna subtotal no es editable
        if col == self.COL_SUBTOTAL:
            return False
        
        item = self._items[row]
        
        try:
            if col == self.COL_CODE:
                item['code'] = str(value)
            elif col == self.COL_DESC:
                item['description'] = str(value)
            elif col == self.COL_QTY:
                qty = float(value) if value else 0.0
                if qty < 0:
                    return False  # No permitir cantidades negativas
                item['quantity'] = qty
            elif col == self.COL_UNIT:
                item['unit'] = str(value)
            elif col == self.COL_PRICE:
                price = float(value) if value else 0.0
                if price < 0:
                    return False  # No permitir precios negativos
                item['unit_price'] = price
            elif col == self.COL_DISCOUNT:
                discount = float(value) if value else 0.0
                if discount < 0 or discount > 100:
                    return False  # Descuento entre 0 y 100%
                item['discount_percent'] = discount
            
            # Emitir señal de cambio para recalcular subtotales
            self.dataChanged.emit(index, index, [role])
            self.dataChangedSignal.emit()
            
            # Si cambió cantidad, precio o descuento, actualizar subtotal
            if col in [self.COL_QTY, self.COL_PRICE, self.COL_DISCOUNT]:
                subtotal_index = self.index(row, self.COL_SUBTOTAL)
                self.dataChanged.emit(subtotal_index, subtotal_index)
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Define qué celdas son editables."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        # Subtotal no es editable
        if index.column() == self.COL_SUBTOTAL:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Retorna los encabezados de columnas."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self.COLUMNS):
                    return self.COLUMNS[section]
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None
    
    def insertRows(self, row: int, count: int = 1, parent: QModelIndex = QModelIndex()) -> bool:
        """Inserta filas vacías en la posición especificada."""
        if row < 0 or row > len(self._items):
            row = len(self._items)
        
        self.beginInsertRows(parent, row, row + count - 1)
        
        for i in range(count):
            new_item = {
                'code': '',
                'description': '',
                'quantity': 1.0,
                'unit': 'UND',
                'unit_price': 0.0,
                'discount_percent': 0.0
            }
            self._items.insert(row + i, new_item)
        
        self.endInsertRows()
        self.dataChangedSignal.emit()
        return True
    
    def removeRows(self, row: int, count: int = 1, parent: QModelIndex = QModelIndex()) -> bool:
        """Elimina filas."""
        if row < 0 or row + count > len(self._items):
            return False
        
        self.beginRemoveRows(parent, row, row + count - 1)
        
        for i in range(count):
            del self._items[row]
        
        self.endRemoveRows()
        self.dataChangedSignal.emit()
        return True
    
    def addItem(self, item: Dict[str, Any]) -> None:
        """Agrega un item al final de la tabla."""
        row = len(self._items)
        self.insertRows(row, 1)
        
        # Establecer datos del item
        for col, key in [
            (self.COL_CODE, 'code'),
            (self.COL_DESC, 'description'),
            (self.COL_QTY, 'quantity'),
            (self.COL_UNIT, 'unit'),
            (self.COL_PRICE, 'unit_price'),
            (self.COL_DISCOUNT, 'discount_percent')
        ]:
            if key in item:
                index = self.index(row, col)
                self.setData(index, item[key])
    
    def duplicateRow(self, row: int) -> bool:
        """Duplica una fila existente."""
        if row < 0 or row >= len(self._items):
            return False
        
        item_copy = self._items[row].copy()
        self._items.insert(row + 1, item_copy)
        
        self.beginInsertRows(QModelIndex(), row + 1, row + 1)
        self.endInsertRows()
        self.dataChangedSignal.emit()
        return True
    
    def getItems(self) -> List[Dict[str, Any]]:
        """Retorna todos los items con subtotales calculados."""
        items_with_subtotal = []
        for item in self._items:
            item_copy = item.copy()
            item_copy['subtotal'] = self._calculate_subtotal(item)
            items_with_subtotal.append(item_copy)
        return items_with_subtotal
    
    def setItems(self, items: List[Dict[str, Any]]) -> None:
        """Establece todos los items de una vez."""
        self.beginResetModel()
        self._items = []
        for item in items:
            self._items.append({
                'code': item.get('code', ''),
                'description': item.get('description', ''),
                'quantity': float(item.get('quantity', 1.0)),
                'unit': item.get('unit', 'UND'),
                'unit_price': float(item.get('unit_price', 0.0)),
                'discount_percent': float(item.get('discount_percent', 0.0))
            })
        self.endResetModel()
        self.dataChangedSignal.emit()
    
    def clear(self) -> None:
        """Limpia todos los items."""
        self.beginResetModel()
        self._items = []
        self.endResetModel()
        self.dataChangedSignal.emit()
    
    def getTotalAmount(self) -> float:
        """Calcula el monto total de todos los items."""
        return sum(self._calculate_subtotal(item) for item in self._items)
    
    def _calculate_subtotal(self, item: Dict[str, Any]) -> float:
        """Calcula el subtotal de un item con descuento."""
        quantity = item.get('quantity', 0.0)
        unit_price = item.get('unit_price', 0.0)
        discount_percent = item.get('discount_percent', 0.0)
        
        subtotal = quantity * unit_price
        discount_amount = subtotal * (discount_percent / 100.0)
        return subtotal - discount_amount
