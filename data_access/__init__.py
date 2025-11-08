"""
Capa de abstracción de acceso a datos para FACOT.

Proporciona interfaces y implementaciones para SQLite y Firebase,
permitiendo cambiar entre backends sin modificar la lógica de negocio.
"""

from .base import DataAccess
from .sqlite_data_access import SQLiteDataAccess
from .firebase_data_access import FirebaseDataAccess
from .factory import (
    get_data_access,
    DataAccessMode,
    get_current_mode,
    set_data_access_mode
)

__all__ = [
    "DataAccess",
    "SQLiteDataAccess",
    "FirebaseDataAccess",
    "get_data_access",
    "DataAccessMode",
    "get_current_mode",
    "set_data_access_mode",
]
