"""
Factory para crear instancias de DataAccess.

Permite seleccionar entre SQLite y Firebase según configuración.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional

from .base import DataAccess
from .sqlite_data_access import SQLiteDataAccess
from .firebase_data_access import FirebaseDataAccess


class DataAccessMode(Enum):
    """Modos de acceso a datos disponibles."""
    SQLITE = "sqlite"
    FIREBASE = "firebase"
    AUTO = "auto"  # Intenta Firebase, fallback a SQLite


# Modo global (puede configurarse desde config o UI)
_current_mode = DataAccessMode.AUTO


def set_data_access_mode(mode: DataAccessMode) -> None:
    """
    Configura el modo de acceso a datos globalmente.
    
    Args:
        mode: Modo a usar (SQLITE, FIREBASE, AUTO)
    """
    global _current_mode
    _current_mode = mode
    print(f"[DATA_ACCESS] Modo configurado a: {mode.value}")


def get_current_mode() -> DataAccessMode:
    """Obtiene el modo actual de acceso a datos."""
    return _current_mode


def get_data_access(
    logic_controller=None,
    user_id: Optional[str] = None,
    mode: Optional[DataAccessMode] = None
) -> DataAccess:
    """
    Crea una instancia de DataAccess según el modo especificado.
    
    Args:
        logic_controller: LogicController para SQLite (requerido si mode=SQLITE)
        user_id: ID de usuario para Firebase
        mode: Modo específico a usar (None = usar modo global)
    
    Returns:
        Instancia de DataAccess (SQLite o Firebase)
    
    Raises:
        RuntimeError: Si no se puede crear instancia con el modo especificado
    """
    if mode is None:
        mode = _current_mode
    
    # Modo SQLITE
    if mode == DataAccessMode.SQLITE:
        if logic_controller is None:
            raise RuntimeError("logic_controller requerido para modo SQLITE")
        
        print("[DATA_ACCESS] Usando SQLite")
        return SQLiteDataAccess(logic_controller)
    
    # Modo FIREBASE
    if mode == DataAccessMode.FIREBASE:
        try:
            print("[DATA_ACCESS] Usando Firebase")
            return FirebaseDataAccess(user_id)
        except Exception as e:
            raise RuntimeError(f"No se pudo inicializar Firebase: {e}")
    
    # Modo AUTO: Intenta Firebase, fallback a SQLite
    if mode == DataAccessMode.AUTO:
        try:
            from firebase import get_firebase_client
            client = get_firebase_client()
            
            if client.is_available():
                print("[DATA_ACCESS] AUTO: Usando Firebase (disponible)")
                return FirebaseDataAccess(user_id)
        except Exception as e:
            print(f"[DATA_ACCESS] AUTO: Firebase no disponible ({e})")
        
        # Fallback a SQLite
        if logic_controller is None:
            raise RuntimeError(
                "Firebase no disponible y logic_controller no proporcionado para fallback a SQLite"
            )
        
        print("[DATA_ACCESS] AUTO: Usando SQLite (fallback)")
        return SQLiteDataAccess(logic_controller)
    
    raise RuntimeError(f"Modo de acceso a datos no soportado: {mode}")
