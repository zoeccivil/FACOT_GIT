"""
Tests para ItemsTableModel.
"""
import pytest
from PyQt6.QtCore import Qt, QModelIndex
from models.items_table_model import ItemsTableModel


class TestItemsTableModel:
    """Tests para el modelo de items."""
    
    def test_initial_state(self):
        """Test del estado inicial del modelo."""
        model = ItemsTableModel()
        assert model.rowCount() == 0
        assert model.columnCount() == 7
    
    def test_column_headers(self):
        """Test de los encabezados de columnas."""
        model = ItemsTableModel()
        expected_headers = [
            "Código", "Descripción", "Cantidad", "Unidad",
            "Precio Unit.", "Descuento (%)", "Subtotal"
        ]
        
        for col, expected in enumerate(expected_headers):
            header = model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            assert header == expected
    
    def test_add_item(self):
        """Test de agregar un item."""
        model = ItemsTableModel()
        
        item = {
            'code': 'PROD001',
            'description': 'Producto Test',
            'quantity': 10,
            'unit': 'UND',
            'unit_price': 1000.00,
            'discount_percent': 0.0
        }
        
        model.addItem(item)
        assert model.rowCount() == 1
        
        # Verificar datos
        assert model.data(model.index(0, ItemsTableModel.COL_CODE)) == 'PROD001'
        assert model.data(model.index(0, ItemsTableModel.COL_DESC)) == 'Producto Test'
        assert model.data(model.index(0, ItemsTableModel.COL_QTY), Qt.ItemDataRole.EditRole) == 10
        assert model.data(model.index(0, ItemsTableModel.COL_UNIT)) == 'UND'
        assert model.data(model.index(0, ItemsTableModel.COL_PRICE), Qt.ItemDataRole.EditRole) == 1000.00
    
    def test_insert_rows(self):
        """Test de insertar filas."""
        model = ItemsTableModel()
        
        result = model.insertRows(0, 3)
        assert result is True
        assert model.rowCount() == 3
    
    def test_remove_rows(self):
        """Test de eliminar filas."""
        model = ItemsTableModel()
        model.insertRows(0, 5)
        
        result = model.removeRows(1, 2)
        assert result is True
        assert model.rowCount() == 3
    
    def test_edit_quantity(self):
        """Test de editar cantidad."""
        model = ItemsTableModel()
        model.insertRows(0, 1)
        
        index = model.index(0, ItemsTableModel.COL_QTY)
        result = model.setData(index, 25.5, Qt.ItemDataRole.EditRole)
        
        assert result is True
        assert model.data(index, Qt.ItemDataRole.EditRole) == 25.5
    
    def test_edit_price(self):
        """Test de editar precio."""
        model = ItemsTableModel()
        model.insertRows(0, 1)
        
        index = model.index(0, ItemsTableModel.COL_PRICE)
        result = model.setData(index, 1500.00, Qt.ItemDataRole.EditRole)
        
        assert result is True
        assert model.data(index, Qt.ItemDataRole.EditRole) == 1500.00
    
    def test_negative_quantity_rejected(self):
        """Test de rechazo de cantidad negativa."""
        model = ItemsTableModel()
        model.insertRows(0, 1)
        
        index = model.index(0, ItemsTableModel.COL_QTY)
        result = model.setData(index, -5, Qt.ItemDataRole.EditRole)
        
        assert result is False
    
    def test_negative_price_rejected(self):
        """Test de rechazo de precio negativo."""
        model = ItemsTableModel()
        model.insertRows(0, 1)
        
        index = model.index(0, ItemsTableModel.COL_PRICE)
        result = model.setData(index, -100, Qt.ItemDataRole.EditRole)
        
        assert result is False
    
    def test_discount_validation(self):
        """Test de validación de descuento."""
        model = ItemsTableModel()
        model.insertRows(0, 1)
        
        index = model.index(0, ItemsTableModel.COL_DISCOUNT)
        
        # Descuento válido
        assert model.setData(index, 15.0, Qt.ItemDataRole.EditRole) is True
        
        # Descuento > 100 rechazado
        assert model.setData(index, 150.0, Qt.ItemDataRole.EditRole) is False
        
        # Descuento negativo rechazado
        assert model.setData(index, -10.0, Qt.ItemDataRole.EditRole) is False
    
    def test_calculate_subtotal_simple(self):
        """Test de cálculo de subtotal simple."""
        model = ItemsTableModel()
        
        item = {
            'code': 'PROD001',
            'description': 'Producto Test',
            'quantity': 10,
            'unit': 'UND',
            'unit_price': 1000.00,
            'discount_percent': 0.0
        }
        
        model.addItem(item)
        
        # Subtotal debe ser 10 * 1000 = 10,000
        subtotal_index = model.index(0, ItemsTableModel.COL_SUBTOTAL)
        subtotal_text = model.data(subtotal_index)
        
        # Verificar que el subtotal sea correcto (con formato de miles)
        assert "10,000" in subtotal_text
    
    def test_calculate_subtotal_with_discount(self):
        """Test de cálculo de subtotal con descuento."""
        model = ItemsTableModel()
        
        item = {
            'code': 'PROD001',
            'description': 'Producto Test',
            'quantity': 10,
            'unit': 'UND',
            'unit_price': 1000.00,
            'discount_percent': 15.0  # 15% de descuento
        }
        
        model.addItem(item)
        
        # Subtotal debe ser 10 * 1000 * 0.85 = 8,500
        items = model.getItems()
        assert abs(items[0]['subtotal'] - 8500.00) < 0.01
    
    def test_calculate_subtotal_with_decimals(self):
        """Test de cálculo con decimales."""
        model = ItemsTableModel()
        
        item = {
            'code': 'PROD001',
            'description': 'Producto Test',
            'quantity': 5.5,
            'unit': 'M3',
            'unit_price': 850.75,
            'discount_percent': 10.0
        }
        
        model.addItem(item)
        
        # Subtotal = 5.5 * 850.75 * 0.9 = 4,209.71
        items = model.getItems()
        expected = 5.5 * 850.75 * 0.9
        assert abs(items[0]['subtotal'] - expected) < 0.01
    
    def test_duplicate_row(self):
        """Test de duplicar fila."""
        model = ItemsTableModel()
        
        item = {
            'code': 'PROD001',
            'description': 'Producto Test',
            'quantity': 10,
            'unit': 'UND',
            'unit_price': 1000.00,
            'discount_percent': 5.0
        }
        
        model.addItem(item)
        result = model.duplicateRow(0)
        
        assert result is True
        assert model.rowCount() == 2
        
        # Verificar que los datos se duplicaron
        assert model.data(model.index(1, ItemsTableModel.COL_CODE)) == 'PROD001'
        assert model.data(model.index(1, ItemsTableModel.COL_DESC)) == 'Producto Test'
    
    def test_get_items(self):
        """Test de obtener todos los items."""
        model = ItemsTableModel()
        
        items_to_add = [
            {
                'code': 'PROD001',
                'description': 'Producto 1',
                'quantity': 10,
                'unit': 'UND',
                'unit_price': 1000.00,
                'discount_percent': 0.0
            },
            {
                'code': 'PROD002',
                'description': 'Producto 2',
                'quantity': 5,
                'unit': 'KG',
                'unit_price': 500.00,
                'discount_percent': 10.0
            }
        ]
        
        for item in items_to_add:
            model.addItem(item)
        
        items = model.getItems()
        assert len(items) == 2
        assert 'subtotal' in items[0]
        assert 'subtotal' in items[1]
    
    def test_set_items(self):
        """Test de establecer items de una vez."""
        model = ItemsTableModel()
        
        items = [
            {
                'code': 'PROD001',
                'description': 'Producto 1',
                'quantity': 10,
                'unit': 'UND',
                'unit_price': 1000.00
            },
            {
                'code': 'PROD002',
                'description': 'Producto 2',
                'quantity': 5,
                'unit': 'KG',
                'unit_price': 500.00
            }
        ]
        
        model.setItems(items)
        assert model.rowCount() == 2
    
    def test_clear(self):
        """Test de limpiar modelo."""
        model = ItemsTableModel()
        model.insertRows(0, 5)
        
        model.clear()
        assert model.rowCount() == 0
    
    def test_get_total_amount(self):
        """Test de calcular monto total."""
        model = ItemsTableModel()
        
        items = [
            {
                'code': 'PROD001',
                'description': 'Producto 1',
                'quantity': 10,
                'unit': 'UND',
                'unit_price': 1000.00,
                'discount_percent': 0.0
            },
            {
                'code': 'PROD002',
                'description': 'Producto 2',
                'quantity': 5,
                'unit': 'KG',
                'unit_price': 500.00,
                'discount_percent': 10.0
            }
        ]
        
        for item in items:
            model.addItem(item)
        
        # Total = (10 * 1000) + (5 * 500 * 0.9) = 10,000 + 2,250 = 12,250
        total = model.getTotalAmount()
        expected = 10000.00 + 2250.00
        assert abs(total - expected) < 0.01
    
    def test_subtotal_not_editable(self):
        """Test de que el subtotal no es editable."""
        model = ItemsTableModel()
        model.insertRows(0, 1)
        
        index = model.index(0, ItemsTableModel.COL_SUBTOTAL)
        result = model.setData(index, 9999, Qt.ItemDataRole.EditRole)
        
        assert result is False
    
    def test_flags_for_editable_cells(self):
        """Test de flags para celdas editables."""
        model = ItemsTableModel()
        model.insertRows(0, 1)
        
        # Celdas editables
        for col in [ItemsTableModel.COL_CODE, ItemsTableModel.COL_DESC, 
                    ItemsTableModel.COL_QTY, ItemsTableModel.COL_PRICE]:
            index = model.index(0, col)
            flags = model.flags(index)
            assert Qt.ItemFlag.ItemIsEditable in Qt.ItemFlag(flags)
        
        # Subtotal no editable
        subtotal_index = model.index(0, ItemsTableModel.COL_SUBTOTAL)
        subtotal_flags = model.flags(subtotal_index)
        assert Qt.ItemFlag.ItemIsEditable not in Qt.ItemFlag(subtotal_flags)
