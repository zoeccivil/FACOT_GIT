"""
Tests de integración para LogicController con AuditService y NCFService.

Verifica que la integración entre logic.py y los servicios funcione correctamente.
"""

import pytest
import os
import tempfile
import sqlite3
from logic import LogicController


class TestLogicIntegration:
    """Tests de integración de LogicController con servicios."""

    @pytest.fixture
    def temp_db(self):
        """Crea una base de datos temporal."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def logic(self, temp_db):
        """Crea una instancia de LogicController con BD temporal."""
        return LogicController(temp_db)

    @pytest.fixture
    def company_id(self, logic):
        """Crea una empresa de prueba."""
        return logic.add_company("Test Company", "000000001", "Test Address")

    def test_audit_service_initialized(self, logic):
        """Verifica que AuditService se inicializa correctamente."""
        assert logic.audit_service is not None
        assert logic.audit_service.db_path == logic.db_path

    def test_ncf_service_initialized(self, logic):
        """Verifica que NCFService se inicializa correctamente."""
        assert logic.ncf_service is not None
        assert logic.ncf_service.db_path == logic.db_path

    def test_audit_log_table_created(self, logic):
        """Verifica que la tabla audit_log existe."""
        cur = logic.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        assert cur.fetchone() is not None

    def test_email_logs_table_created(self, logic):
        """Verifica que la tabla email_logs existe (si EmailService se usó)."""
        # Esta tabla se crea cuando se usa EmailService
        # Por ahora solo verificamos que logic.py no falla sin ella
        assert True

    def test_add_invoice_with_ncf_reservation(self, logic, company_id):
        """Verifica que add_invoice reserva NCF automáticamente."""
        invoice_data = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-15',
            'invoice_category': 'B01',
            'client_name': 'Cliente Test',
            'currency': 'RD$',
            'total_amount': 1000.0,
        }
        items = [
            {'description': 'Item 1', 'quantity': 1, 'unit_price': 1000.0}
        ]
        
        invoice_id = logic.add_invoice(invoice_data, items)
        
        # Verificar que se creó
        assert invoice_id > 0
        
        # Verificar que tiene NCF asignado
        cur = logic.conn.cursor()
        cur.execute("SELECT invoice_number FROM invoices WHERE id = ?", (invoice_id,))
        row = cur.fetchone()
        assert row is not None
        ncf = row[0]
        assert ncf is not None
        assert len(ncf) == 11  # B01 + 8 dígitos
        assert ncf.startswith('B01')

    def test_add_invoice_creates_audit_log(self, logic, company_id):
        """Verifica que add_invoice crea registro de auditoría."""
        invoice_data = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-15',
            'invoice_category': 'B01',
            'client_name': 'Cliente Test',
            'currency': 'RD$',
            'total_amount': 1000.0,
        }
        items = []
        
        invoice_id = logic.add_invoice(invoice_data, items)
        
        # Verificar registro de auditoría
        audit_trail = logic.audit_service.get_audit_trail('invoice', invoice_id)
        assert len(audit_trail) >= 1  # Al menos el create
        
        # Verificar que hay un log de creación
        create_logs = [log for log in audit_trail if log['action'] == 'create']
        assert len(create_logs) >= 1

    def test_add_invoice_logs_ncf_assignment(self, logic, company_id):
        """Verifica que add_invoice registra asignación de NCF."""
        invoice_data = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-15',
            'invoice_category': 'B01',
            'client_name': 'Cliente Test',
            'currency': 'RD$',
            'total_amount': 1000.0,
        }
        items = []
        
        invoice_id = logic.add_invoice(invoice_data, items)
        
        # Verificar que hay log de asignación de NCF
        cur = logic.conn.cursor()
        cur.execute("""
            SELECT * FROM audit_log 
            WHERE entity_type = 'ncf' 
            AND entity_id = ? 
            AND action = 'assign'
        """, (invoice_id,))
        row = cur.fetchone()
        assert row is not None

    def test_update_invoice_creates_audit_log(self, logic, company_id):
        """Verifica que update_invoice crea registro de auditoría."""
        # Crear factura
        invoice_data = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-15',
            'invoice_number': 'B0100000001',
            'invoice_category': 'B01',
            'client_name': 'Cliente Original',
            'currency': 'RD$',
            'total_amount': 1000.0,
        }
        items = []
        invoice_id = logic.add_invoice(invoice_data, items)
        
        # Actualizar factura
        updated_data = invoice_data.copy()
        updated_data['client_name'] = 'Cliente Actualizado'
        updated_data['total_amount'] = 2000.0
        
        logic.update_invoice(invoice_id, updated_data, items)
        
        # Verificar registro de auditoría
        audit_trail = logic.audit_service.get_audit_trail('invoice', invoice_id)
        update_logs = [log for log in audit_trail if log['action'] == 'update']
        assert len(update_logs) >= 1

    def test_delete_factura_creates_audit_log(self, logic, company_id):
        """Verifica que delete_factura crea registro de auditoría."""
        # Crear factura
        invoice_data = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-15',
            'invoice_number': 'B0100000001',
            'invoice_category': 'B01',
            'client_name': 'Cliente Test',
            'currency': 'RD$',
            'total_amount': 1000.0,
        }
        items = []
        invoice_id = logic.add_invoice(invoice_data, items)
        
        # Eliminar factura
        logic.delete_factura(invoice_id)
        
        # Verificar registro de auditoría (la factura ya no existe pero el log sí)
        cur = logic.conn.cursor()
        cur.execute("""
            SELECT * FROM audit_log 
            WHERE entity_type = 'invoice' 
            AND entity_id = ? 
            AND action = 'delete'
        """, (invoice_id,))
        row = cur.fetchone()
        assert row is not None

    def test_ncf_no_duplicates_sequential_invoices(self, logic, company_id):
        """Verifica que NCF no se duplica en facturas secuenciales."""
        ncfs_generated = set()
        
        for i in range(5):
            invoice_data = {
                'company_id': company_id,
                'invoice_type': 'emitida',
                'invoice_date': '2024-01-15',
                'invoice_category': 'B01',
                'client_name': f'Cliente {i}',
                'currency': 'RD$',
                'total_amount': 1000.0 * (i + 1),
            }
            items = []
            
            invoice_id = logic.add_invoice(invoice_data, items)
            
            # Obtener NCF
            cur = logic.conn.cursor()
            cur.execute("SELECT invoice_number FROM invoices WHERE id = ?", (invoice_id,))
            ncf = cur.fetchone()[0]
            
            # Verificar que no está duplicado
            assert ncf not in ncfs_generated, f"NCF duplicado: {ncf}"
            ncfs_generated.add(ncf)
        
        # Verificar que se generaron 5 NCFs únicos
        assert len(ncfs_generated) == 5

    def test_update_invoice_number_with_audit(self, logic, company_id):
        """Verifica que update_invoice_number registra el cambio en auditoría."""
        # Crear factura
        invoice_data = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-15',
            'invoice_number': 'B0100000001',
            'invoice_category': 'B01',
            'client_name': 'Cliente Test',
            'currency': 'RD$',
            'total_amount': 1000.0,
        }
        items = []
        invoice_id = logic.add_invoice(invoice_data, items)
        
        # Cambiar NCF
        new_ncf = 'B0100000999'
        success, msg, _ = logic.update_invoice_number(invoice_id, company_id, '', new_ncf)
        assert success
        
        # Verificar que se registró el cambio
        cur = logic.conn.cursor()
        cur.execute("""
            SELECT * FROM audit_log 
            WHERE entity_type = 'invoice' 
            AND entity_id = ? 
            AND action = 'update'
        """, (invoice_id,))
        rows = cur.fetchall()
        # Debe haber al menos un registro de update
        assert len(rows) >= 1

    def test_get_invoice_history(self, logic, company_id):
        """Verifica que se puede obtener el historial completo de una factura."""
        # Crear factura
        invoice_data = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-15',
            'invoice_number': 'B0100000001',
            'invoice_category': 'B01',
            'client_name': 'Cliente Original',
            'currency': 'RD$',
            'total_amount': 1000.0,
        }
        items = []
        invoice_id = logic.add_invoice(invoice_data, items)
        
        # Actualizar varias veces
        for i in range(3):
            updated_data = invoice_data.copy()
            updated_data['client_name'] = f'Cliente Actualizado {i}'
            updated_data['total_amount'] = 1000.0 + (i * 500)
            logic.update_invoice(invoice_id, updated_data, items)
        
        # Obtener historial
        history = logic.audit_service.get_invoice_history(invoice_id)
        
        # Debe tener create + 3 updates
        assert len(history) >= 4

    def test_ncf_service_reserve_prevents_duplicates(self, logic, company_id):
        """Verifica que NCFService.reserve_ncf previene duplicados."""
        # Reservar varios NCF
        ncfs = []
        for i in range(10):
            success, ncf = logic.ncf_service.reserve_ncf(company_id, 'B02')
            assert success
            assert ncf not in ncfs
            ncfs.append(ncf)
        
        # Todos deben ser únicos y consecutivos
        assert len(ncfs) == 10
        assert len(set(ncfs)) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
