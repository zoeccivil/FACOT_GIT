"""
Tests para db_manager.py y logic.py
"""
import sqlite3
import pytest
from logic import LogicController


class TestLogicController:
    """Tests para LogicController (gestión de base de datos)."""

    def test_initialization(self, temp_db):
        """Test de inicialización del controlador."""
        logic = LogicController(temp_db)
        assert logic.conn is not None
        assert logic.db_path == temp_db
        logic.close_connection()

    def test_database_tables_created(self, temp_db):
        """Verifica que las tablas se crean correctamente."""
        logic = LogicController(temp_db)
        
        # Verificar que existen las tablas principales
        cursor = logic.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN (
                'companies', 'invoices', 'invoice_items', 
                'third_parties', 'currencies'
            )
        """)
        tables = {row[0] for row in cursor.fetchall()}
        
        assert 'companies' in tables
        assert 'invoices' in tables
        assert 'invoice_items' in tables
        assert 'third_parties' in tables
        assert 'currencies' in tables
        
        logic.close_connection()

    def test_add_company(self, temp_db):
        """Test de agregar una empresa."""
        logic = LogicController(temp_db)
        
        success, message = logic.add_company("Test Company SA", "123456789")
        assert success is True
        assert "exitosamente" in message.lower()
        
        # Verificar que se agregó
        companies = logic.get_all_companies()
        assert len(companies) == 1
        assert companies[0]['name'] == "Test Company SA"
        
        logic.close_connection()

    def test_add_duplicate_company(self, temp_db):
        """Test de agregar empresa duplicada."""
        logic = LogicController(temp_db)
        
        logic.add_company("Test Company SA", "123456789")
        success, message = logic.add_company("Test Company SA", "123456789")
        
        assert success is False
        assert "existe" in message.lower()
        
        logic.close_connection()

    def test_add_invoice(self, temp_db, sample_invoice_data, sample_items):
        """Test de agregar una factura."""
        logic = LogicController(temp_db)
        
        # Primero crear una empresa
        logic.add_company("Test Company", "123456789")
        
        # Agregar factura
        invoice_id = logic.add_invoice(sample_invoice_data, sample_items)
        assert invoice_id is not None
        assert invoice_id > 0
        
        # Verificar que se guardó
        invoice = logic.get_invoice_by_id(invoice_id)
        assert invoice is not None
        assert invoice['invoice_number'] == "B0100000001"
        
        # Verificar items
        items = logic.get_invoice_items(invoice_id)
        assert len(items) == 2
        assert items[0]['description'] == "Cemento Gris 50kg"
        
        logic.close_connection()

    def test_update_invoice(self, temp_db, sample_invoice_data, sample_items):
        """Test de actualizar una factura."""
        logic = LogicController(temp_db)
        
        # Crear empresa y factura
        logic.add_company("Test Company", "123456789")
        invoice_id = logic.add_invoice(sample_invoice_data, sample_items)
        
        # Actualizar factura
        updated_data = sample_invoice_data.copy()
        updated_data['total_amount'] = 15000.00
        updated_data['total_amount_rd'] = 17700.00
        
        logic.update_invoice(invoice_id, updated_data, sample_items)
        
        # Verificar actualización
        invoice = logic.get_invoice_by_id(invoice_id)
        assert invoice['total_amount'] == 15000.00
        
        logic.close_connection()

    def test_delete_invoice(self, temp_db, sample_invoice_data, sample_items):
        """Test de eliminar una factura."""
        logic = LogicController(temp_db)
        
        # Crear empresa y factura
        logic.add_company("Test Company", "123456789")
        invoice_id = logic.add_invoice(sample_invoice_data, sample_items)
        
        # Eliminar factura
        success, message = logic.delete_invoice(invoice_id)
        assert success is True
        
        # Verificar que se eliminó
        invoice = logic.get_invoice_by_id(invoice_id)
        assert invoice is None
        
        logic.close_connection()

    def test_currencies_initialized(self, temp_db):
        """Verifica que las monedas se inicializan correctamente."""
        logic = LogicController(temp_db)
        
        currencies = logic.get_all_currencies()
        assert len(currencies) >= 2
        assert "RD$" in currencies
        assert "USD" in currencies
        
        logic.close_connection()

    def test_third_parties_directory(self, temp_db):
        """Test del directorio de terceros."""
        logic = LogicController(temp_db)
        
        # Agregar tercero
        logic.add_or_update_third_party("123456789", "Cliente Test")
        
        # Buscar
        results = logic.search_third_parties("Cliente", search_by='name')
        assert len(results) > 0
        assert results[0]['name'] == "Cliente Test"
        
        logic.close_connection()

    def test_get_next_ncf(self, temp_db):
        """Test de generación de NCF secuencial."""
        logic = LogicController(temp_db)
        
        # Crear empresa
        logic.add_company("Test Company", "123456789")
        companies = logic.get_all_companies()
        company_id = companies[0]['id']
        
        # Obtener primer NCF
        ncf1 = logic.get_next_ncf(company_id, "B01")
        assert ncf1 == "B0100000001"
        
        # Simular que se usó ese NCF
        invoice_data = {
            "company_id": company_id,
            "invoice_type": "emitida",
            "invoice_date": "2025-01-15",
            "invoice_number": ncf1,
            "invoice_category": "B01",
            "rnc": "999999999",
            "third_party_name": "Cliente",
            "currency": "RD$",
            "itbis": 0,
            "total_amount": 1000,
            "exchange_rate": 1.0,
            "total_amount_rd": 1000
        }
        logic.add_invoice(invoice_data, [])
        
        # Obtener siguiente NCF
        ncf2 = logic.get_next_ncf(company_id, "B01")
        assert ncf2 == "B0100000002"
        
        logic.close_connection()

    def test_dashboard_data(self, temp_db, sample_invoice_data, sample_items):
        """Test de obtención de datos del dashboard."""
        logic = LogicController(temp_db)
        
        # Crear empresa y facturas
        logic.add_company("Test Company", "123456789")
        companies = logic.get_all_companies()
        company_id = companies[0]['id']
        
        sample_invoice_data['company_id'] = company_id
        logic.add_invoice(sample_invoice_data, sample_items)
        
        # Obtener datos del dashboard
        dashboard = logic.get_dashboard_data(company_id)
        
        assert dashboard is not None
        assert 'summary' in dashboard
        assert 'all_transactions' in dashboard
        assert dashboard['summary']['total_ingresos'] > 0
        
        logic.close_connection()
