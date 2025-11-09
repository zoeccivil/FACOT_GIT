"""
Tests para audit_service.py
"""
import json
import pytest
from services.audit_service import AuditService


class TestAuditService:
    """Tests para el servicio de auditoría."""
    
    def test_initialization(self, temp_db):
        """Test de inicialización."""
        service = AuditService(temp_db)
        assert service.db_path == temp_db
    
    def test_audit_log_table_created(self, temp_db):
        """Test de creación de tabla audit_log."""
        import sqlite3
        
        service = AuditService(temp_db)
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='audit_log'
            """)
            tables = cursor.fetchall()
            assert len(tables) == 1
    
    def test_log_action_create(self, temp_db):
        """Test de logging de acción create."""
        service = AuditService(temp_db)
        
        payload = {
            'invoice_number': 'B0100000001',
            'total_amount': 11800.00
        }
        
        log_id = service.log_action(
            entity_type='invoice',
            entity_id=1,
            action='create',
            payload_after=payload,
            user='test_user'
        )
        
        assert log_id > 0
        
        # Verificar que se guardó
        trail = service.get_audit_trail(entity_type='invoice', entity_id=1)
        assert len(trail) == 1
        assert trail[0]['action'] == 'create'
        assert trail[0]['user'] == 'test_user'
        assert trail[0]['payload_after']['invoice_number'] == 'B0100000001'
    
    def test_log_action_update(self, temp_db):
        """Test de logging de acción update."""
        service = AuditService(temp_db)
        
        before = {'total_amount': 10000.00}
        after = {'total_amount': 12000.00}
        
        log_id = service.log_action(
            entity_type='invoice',
            entity_id=1,
            action='update',
            payload_before=before,
            payload_after=after
        )
        
        assert log_id > 0
        
        trail = service.get_audit_trail(entity_type='invoice', entity_id=1)
        assert trail[0]['payload_before']['total_amount'] == 10000.00
        assert trail[0]['payload_after']['total_amount'] == 12000.00
    
    def test_log_action_delete(self, temp_db):
        """Test de logging de acción delete."""
        service = AuditService(temp_db)
        
        payload = {
            'invoice_number': 'B0100000001',
            'total_amount': 11800.00
        }
        
        service.log_action(
            entity_type='invoice',
            entity_id=1,
            action='delete',
            payload_before=payload
        )
        
        trail = service.get_audit_trail(entity_type='invoice', entity_id=1)
        assert trail[0]['action'] == 'delete'
        assert trail[0]['payload_before'] is not None
    
    def test_log_invoice_create_helper(self, temp_db):
        """Test del helper de creación de factura."""
        service = AuditService(temp_db)
        
        invoice_data = {
            'invoice_number': 'B0100000001',
            'total_amount': 11800.00,
            'customer': 'Test Customer'
        }
        
        log_id = service.log_invoice_create(1, invoice_data, 'admin')
        assert log_id > 0
        
        trail = service.get_invoice_history(1)
        assert len(trail) == 1
        assert trail[0]['action'] == 'create'
    
    def test_log_invoice_update_helper(self, temp_db):
        """Test del helper de actualización de factura."""
        service = AuditService(temp_db)
        
        before = {'total_amount': 10000.00}
        after = {'total_amount': 12000.00}
        
        service.log_invoice_update(1, before, after, 'admin')
        
        trail = service.get_invoice_history(1)
        assert trail[0]['action'] == 'update'
    
    def test_log_invoice_delete_helper(self, temp_db):
        """Test del helper de eliminación de factura."""
        service = AuditService(temp_db)
        
        invoice_data = {'invoice_number': 'B0100000001'}
        service.log_invoice_delete(1, invoice_data, 'admin')
        
        trail = service.get_invoice_history(1)
        assert trail[0]['action'] == 'delete'
    
    def test_log_ncf_assignment(self, temp_db):
        """Test de logging de asignación de NCF."""
        service = AuditService(temp_db)
        
        service.log_ncf_assignment(1, 'B0100000001', 1, 'admin')
        
        trail = service.get_audit_trail(entity_type='ncf', entity_id=1)
        assert len(trail) == 1
        assert trail[0]['payload_after']['ncf'] == 'B0100000001'
    
    def test_get_audit_trail_filters(self, temp_db):
        """Test de filtros en audit trail."""
        service = AuditService(temp_db)
        
        # Crear varios logs
        service.log_action('invoice', 1, 'create')
        service.log_action('invoice', 1, 'update')
        service.log_action('invoice', 2, 'create')
        service.log_action('company', 1, 'create')
        
        # Filtrar por tipo y ID
        trail = service.get_audit_trail(entity_type='invoice', entity_id=1)
        assert len(trail) == 2
        
        # Filtrar por tipo
        trail = service.get_audit_trail(entity_type='invoice')
        assert len(trail) == 3
        
        # Filtrar por acción
        trail = service.get_audit_trail(action='create')
        assert len(trail) == 3
    
    def test_get_recent_actions(self, temp_db):
        """Test de obtener acciones recientes."""
        service = AuditService(temp_db)
        
        # Crear varios logs
        for i in range(10):
            service.log_action('invoice', i, 'create')
        
        recent = service.get_recent_actions(limit=5)
        assert len(recent) == 5
    
    def test_get_changes_summary(self, temp_db):
        """Test de resumen de cambios."""
        service = AuditService(temp_db)
        
        # Crear historial
        service.log_action('invoice', 1, 'create', user='user1')
        service.log_action('invoice', 1, 'update', user='user2')
        service.log_action('invoice', 1, 'update', user='user2')
        
        summary = service.get_changes_summary('invoice', 1)
        
        assert summary['created_by'] == 'user1'
        assert summary['last_modified_by'] == 'user2'
        assert summary['total_changes'] == 3
        assert summary['actions']['create'] == 1
        assert summary['actions']['update'] == 2
    
    def test_get_changes_summary_no_records(self, temp_db):
        """Test de resumen sin registros."""
        service = AuditService(temp_db)
        
        summary = service.get_changes_summary('invoice', 999)
        
        assert summary['created_at'] is None
        assert summary['total_changes'] == 0
    
    def test_payload_serialization(self, temp_db):
        """Test de serialización de payloads complejos."""
        service = AuditService(temp_db)
        
        complex_payload = {
            'string': 'test',
            'number': 123,
            'float': 123.45,
            'bool': True,
            'null': None,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'}
        }
        
        service.log_action('test', 1, 'create', payload_after=complex_payload)
        
        trail = service.get_audit_trail(entity_type='test', entity_id=1)
        retrieved_payload = trail[0]['payload_after']
        
        assert retrieved_payload == complex_payload
    
    def test_timestamp_format(self, temp_db):
        """Test de formato de timestamp."""
        service = AuditService(temp_db)
        
        service.log_action('invoice', 1, 'create')
        
        trail = service.get_audit_trail()
        timestamp = trail[0]['timestamp']
        
        # Verificar formato ISO
        assert 'T' in timestamp
        assert len(timestamp) > 10
