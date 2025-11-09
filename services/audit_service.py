"""
Servicio de auditoría para FACOT.
Registra todas las operaciones críticas en la base de datos.
"""
import json
import sqlite3
import socket
from datetime import datetime
from typing import Optional, Dict, Any, List


class AuditService:
    """Servicio centralizado de auditoría."""
    
    def __init__(self, db_path: str):
        """
        Inicializa el servicio de auditoría.
        
        Args:
            db_path: Ruta a la base de datos
        """
        self.db_path = db_path
        self._ensure_audit_log_table()
    
    def _ensure_audit_log_table(self):
        """Crea la tabla audit_log si no existe."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    user TEXT,
                    timestamp TEXT NOT NULL,
                    payload_before TEXT,
                    payload_after TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)
            
            # Índices para optimización
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_entity 
                ON audit_log(entity_type, entity_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                ON audit_log(timestamp DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_action 
                ON audit_log(action)
            """)
    
    def log_action(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        payload_before: Optional[Dict[str, Any]] = None,
        payload_after: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None
    ) -> int:
        """
        Registra una acción en el log de auditoría.
        
        Args:
            entity_type: Tipo de entidad ('invoice', 'company', 'ncf', etc.)
            entity_id: ID de la entidad
            action: Acción realizada ('create', 'update', 'delete')
            payload_before: Estado anterior (JSON serializable)
            payload_after: Estado posterior (JSON serializable)
            user: Usuario que realizó la acción
        
        Returns:
            ID del registro de auditoría
        """
        # Obtener información del sistema
        hostname = socket.gethostname()
        if user is None:
            user = hostname
        
        # Serializar payloads a JSON
        payload_before_json = json.dumps(payload_before) if payload_before else None
        payload_after_json = json.dumps(payload_after) if payload_after else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO audit_log 
                (entity_type, entity_id, action, user, timestamp, 
                 payload_before, payload_after, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_type,
                entity_id,
                action,
                user,
                datetime.now().isoformat(),
                payload_before_json,
                payload_after_json,
                hostname,
                None  # user_agent para uso futuro web
            ))
            return cursor.lastrowid
    
    def get_audit_trail(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de auditoría.
        
        Args:
            entity_type: Filtrar por tipo de entidad
            entity_id: Filtrar por ID de entidad
            action: Filtrar por acción
            limit: Número máximo de registros
        
        Returns:
            Lista de registros de auditoría
        """
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        if entity_id is not None:
            query += " AND entity_id = ?"
            params.append(entity_id)
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                record = dict(row)
                
                # Deserializar payloads JSON
                if record['payload_before']:
                    try:
                        record['payload_before'] = json.loads(record['payload_before'])
                    except json.JSONDecodeError:
                        pass
                
                if record['payload_after']:
                    try:
                        record['payload_after'] = json.loads(record['payload_after'])
                    except json.JSONDecodeError:
                        pass
                
                results.append(record)
            
            return results
    
    def log_invoice_create(self, invoice_id: int, invoice_data: Dict[str, Any], user: Optional[str] = None):
        """Helper: Log de creación de factura."""
        return self.log_action(
            entity_type='invoice',
            entity_id=invoice_id,
            action='create',
            payload_after=invoice_data,
            user=user
        )
    
    def log_invoice_update(
        self,
        invoice_id: int,
        invoice_before: Dict[str, Any],
        invoice_after: Dict[str, Any],
        user: Optional[str] = None
    ):
        """Helper: Log de actualización de factura."""
        return self.log_action(
            entity_type='invoice',
            entity_id=invoice_id,
            action='update',
            payload_before=invoice_before,
            payload_after=invoice_after,
            user=user
        )
    
    def log_invoice_delete(self, invoice_id: int, invoice_data: Dict[str, Any], user: Optional[str] = None):
        """Helper: Log de eliminación de factura."""
        return self.log_action(
            entity_type='invoice',
            entity_id=invoice_id,
            action='delete',
            payload_before=invoice_data,
            user=user
        )
    
    def log_ncf_assignment(
        self,
        invoice_id: int,
        ncf: str,
        company_id: int,
        user: Optional[str] = None
    ):
        """Helper: Log de asignación de NCF."""
        return self.log_action(
            entity_type='ncf',
            entity_id=invoice_id,
            action='assign',
            payload_after={
                'ncf': ncf,
                'company_id': company_id,
                'invoice_id': invoice_id
            },
            user=user
        )
    
    def get_invoice_history(self, invoice_id: int) -> List[Dict[str, Any]]:
        """Obtiene el historial completo de una factura."""
        return self.get_audit_trail(entity_type='invoice', entity_id=invoice_id)
    
    def get_recent_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene las acciones más recientes."""
        return self.get_audit_trail(limit=limit)
    
    def get_changes_summary(self, entity_type: str, entity_id: int) -> Dict[str, Any]:
        """
        Obtiene un resumen de cambios de una entidad.
        
        Returns:
            Dict con información de creación, última modificación, y total de cambios
        """
        trail = self.get_audit_trail(entity_type=entity_type, entity_id=entity_id, limit=1000)
        
        if not trail:
            return {
                'created_at': None,
                'created_by': None,
                'last_modified_at': None,
                'last_modified_by': None,
                'total_changes': 0,
                'actions': {}
            }
        
        # Encontrar creación
        create_record = next((r for r in reversed(trail) if r['action'] == 'create'), None)
        
        # Contar acciones
        actions_count = {}
        for record in trail:
            action = record['action']
            actions_count[action] = actions_count.get(action, 0) + 1
        
        return {
            'created_at': create_record['timestamp'] if create_record else None,
            'created_by': create_record['user'] if create_record else None,
            'last_modified_at': trail[0]['timestamp'] if trail else None,
            'last_modified_by': trail[0]['user'] if trail else None,
            'total_changes': len(trail),
            'actions': actions_count
        }
