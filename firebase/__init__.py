"""
Paquete Firebase para FACOT.

Proporciona cliente de Firebase (Firestore, Storage, Auth) y
acceso a datos unificado con SQLite.
"""

from .firebase_client import FirebaseClient

__all__ = ["FirebaseClient"]
