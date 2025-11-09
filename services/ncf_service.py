"""
Servicio de gestión de NCF con transacciones seguras.
Previene duplicados usando transacciones exclusivas de SQLite.
"""
import sqlite3
from typing import Tuple, Optional
import re


class NCFService:
    """Servicio de gestión de NCF con transacciones."""
    
    # Tipos de NCF válidos
    VALID_NCF_TYPES = ['B01', 'B02', 'B04', 'B14', 'B15']
    
    # Formato: Prefijo (B01) + 8 dígitos
    NCF_PATTERN = re.compile(r'^(B\d{2})(\d{8})$')
    
    def __init__(self, db_path: str):
        """
        Inicializa el servicio de NCF.
        
        Args:
            db_path: Ruta a la base de datos
        """
        self.db_path = db_path
        self._ensure_ncf_sequences_table()
    
    def _ensure_ncf_sequences_table(self):
        """Crea la tabla ncf_sequences si no existe."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ncf_sequences (
                    company_id INTEGER NOT NULL,
                    prefix3 TEXT NOT NULL,
                    last_seq INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (company_id, prefix3)
                )
            """)
    
    def reserve_ncf(
        self,
        company_id: int,
        ncf_type: str,
        timeout: int = 30
    ) -> Tuple[bool, str]:
        """
        Reserva un NCF de forma segura usando transacciones exclusivas.
        
        Esta función usa BEGIN EXCLUSIVE para garantizar que solo un proceso
        puede reservar un NCF a la vez, previniendo duplicados incluso en
        escenarios de concurrencia.
        
        Args:
            company_id: ID de la empresa
            ncf_type: Tipo de NCF (B01, B02, etc.)
            timeout: Timeout para la transacción en segundos
        
        Returns:
            Tuple de (success: bool, ncf_or_error: str)
        """
        # Validar tipo de NCF
        if ncf_type not in self.VALID_NCF_TYPES:
            return False, f"Tipo de NCF inválido: {ncf_type}"
        
        conn = None
        try:
            # Conectar con timeout
            conn = sqlite3.connect(self.db_path, timeout=timeout)
            conn.row_factory = sqlite3.Row
            
            # Iniciar transacción EXCLUSIVA
            # Esto bloquea la BD para escritura hasta que se haga commit/rollback
            conn.execute("BEGIN EXCLUSIVE")
            
            try:
                # Obtener o crear secuencia
                cursor = conn.execute("""
                    SELECT last_seq 
                    FROM ncf_sequences 
                    WHERE company_id = ? AND prefix3 = ?
                """, (company_id, ncf_type))
                
                row = cursor.fetchone()
                
                if row:
                    last_seq = row['last_seq']
                else:
                    # Primera vez, sembrar con máximo histórico de invoices
                    cursor = conn.execute("""
                        SELECT invoice_number 
                        FROM invoices 
                        WHERE company_id = ? 
                          AND invoice_category = ?
                          AND invoice_number LIKE ?
                        ORDER BY invoice_number DESC
                        LIMIT 1
                    """, (company_id, ncf_type, f"{ncf_type}%"))
                    
                    last_invoice = cursor.fetchone()
                    if last_invoice:
                        last_ncf = last_invoice['invoice_number']
                        match = self.NCF_PATTERN.match(last_ncf)
                        if match:
                            _, number_str = match.groups()
                            last_seq = int(number_str)
                        else:
                            last_seq = 0
                    else:
                        last_seq = 0
                    
                    # Crear registro de secuencia
                    conn.execute("""
                        INSERT INTO ncf_sequences (company_id, prefix3, last_seq, updated_at)
                        VALUES (?, ?, ?, datetime('now'))
                    """, (company_id, ncf_type, last_seq))
                
                # Calcular siguiente NCF
                next_seq = last_seq + 1
                
                if next_seq > 99999999:
                    raise ValueError(f"Se agotaron los números de NCF para {ncf_type}")
                
                next_ncf = f"{ncf_type}{next_seq:08d}"
                
                # Doble verificación: asegurar que el NCF no existe en invoices
                cursor = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM invoices 
                    WHERE company_id = ? AND invoice_number = ?
                """, (company_id, next_ncf))
                
                count = cursor.fetchone()['count']
                if count > 0:
                    raise ValueError(f"NCF {next_ncf} ya existe (colisión detectada)")
                
                # Actualizar secuencia
                conn.execute("""
                    UPDATE ncf_sequences 
                    SET last_seq = ?, updated_at = datetime('now')
                    WHERE company_id = ? AND prefix3 = ?
                """, (next_seq, company_id, ncf_type))
                
                # Commit de la transacción
                conn.commit()
                
                return True, next_ncf
                
            except Exception as e:
                # Rollback en caso de error
                conn.rollback()
                raise e
                
        except sqlite3.OperationalError as e:
            return False, f"Error de bloqueo de BD: {str(e)}"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Error al reservar NCF: {str(e)}"
        finally:
            if conn:
                conn.close()
    
    def _calculate_next_ncf(self, last_ncf: str, ncf_type: str) -> str:
        """
        Calcula el siguiente NCF basado en el último.
        
        Args:
            last_ncf: Último NCF usado (ej: "B0100000025")
            ncf_type: Tipo de NCF (ej: "B01")
        
        Returns:
            Siguiente NCF (ej: "B0100000026")
        """
        # Validar formato
        match = self.NCF_PATTERN.match(last_ncf)
        if not match:
            # Si el formato no es válido, empezar desde 1
            return f"{ncf_type}00000001"
        
        prefix, number_str = match.groups()
        
        # Verificar que el prefijo coincide
        if prefix != ncf_type:
            return f"{ncf_type}00000001"
        
        # Incrementar número
        current_number = int(number_str)
        next_number = current_number + 1
        
        # Validar que no excede 8 dígitos
        if next_number > 99999999:
            raise ValueError(f"Se agotaron los números de NCF para {ncf_type}")
        
        # Formatear con 8 dígitos
        return f"{ncf_type}{next_number:08d}"
    
    def validate_ncf_format(self, ncf: str) -> Tuple[bool, str]:
        """
        Valida el formato de un NCF.
        
        Args:
            ncf: NCF a validar
        
        Returns:
            Tuple de (valid: bool, message: str)
        """
        if not ncf:
            return False, "NCF vacío"
        
        match = self.NCF_PATTERN.match(ncf)
        if not match:
            return False, f"Formato de NCF inválido: {ncf}. Debe ser XXX########"
        
        prefix, number_str = match.groups()
        
        if prefix not in self.VALID_NCF_TYPES:
            return False, f"Tipo de NCF no válido: {prefix}"
        
        return True, "NCF válido"
    
    def check_ncf_exists(self, company_id: int, ncf: str) -> bool:
        """
        Verifica si un NCF ya está siendo usado.
        
        Args:
            company_id: ID de la empresa
            ncf: NCF a verificar
        
        Returns:
            True si el NCF existe, False si no
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) 
                FROM invoices 
                WHERE company_id = ? AND invoice_number = ?
            """, (company_id, ncf))
            
            count = cursor.fetchone()[0]
            return count > 0
    
    def get_ncf_sequence_info(self, company_id: int, ncf_type: str) -> dict:
        """
        Obtiene información sobre la secuencia de NCF.
        
        Args:
            company_id: ID de la empresa
            ncf_type: Tipo de NCF
        
        Returns:
            Dict con información de la secuencia
        """
        with sqlite3.connect(self.db_path) as conn:
            # Último NCF
            cursor = conn.execute("""
                SELECT invoice_number 
                FROM invoices 
                WHERE company_id = ? 
                  AND invoice_category = ?
                  AND invoice_number LIKE ?
                ORDER BY invoice_number DESC
                LIMIT 1
            """, (company_id, ncf_type, f"{ncf_type}%"))
            
            last_ncf_row = cursor.fetchone()
            last_ncf = last_ncf_row[0] if last_ncf_row else None
            
            # Contar total de NCF de este tipo
            cursor = conn.execute("""
                SELECT COUNT(*) 
                FROM invoices 
                WHERE company_id = ? AND invoice_category = ?
            """, (company_id, ncf_type))
            
            total_count = cursor.fetchone()[0]
            
            # Calcular siguiente
            if last_ncf:
                next_ncf = self._calculate_next_ncf(last_ncf, ncf_type)
            else:
                next_ncf = f"{ncf_type}00000001"
            
            return {
                'ncf_type': ncf_type,
                'last_ncf': last_ncf,
                'next_ncf': next_ncf,
                'total_issued': total_count,
                'remaining': 99999999 - (int(next_ncf[-8:]) if next_ncf else 0)
            }
