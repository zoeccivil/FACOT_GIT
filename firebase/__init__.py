"""
Paquete Firebase para FACOT.

Proporciona cliente de Firebase (Firestore, Storage, Auth) y
acceso a datos unificado con SQLite.
"""

from .firebase_client import FirebaseClient, get_firebase_client

__all__ = ["FirebaseClient", "get_firebase_client"]
