"""
FirebaseClient - Cliente unificado para Firebase (Firestore, Storage, Auth).

Proporciona inicialización y acceso a servicios de Firebase para FACOT.

Uso:
    client = FirebaseClient()
    db = client.get_firestore()
    storage = client.get_storage()
    auth = client.get_auth()
"""

from __future__ import annotations
import os
import json
from typing import Optional, Dict, Any

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage, auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("[FIREBASE] Firebase Admin SDK no disponible. Instalar con: pip install firebase-admin")


class FirebaseClient:
    """
    Cliente singleton para servicios de Firebase.
    
    Inicializa Firebase Admin SDK y proporciona acceso a:
    - Firestore (base de datos)
    - Storage (archivos/logos)
    - Auth (autenticación)
    
    Configuración vía variables de entorno o archivo de credenciales.
    """
    
    _instance: Optional[FirebaseClient] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern - una sola instancia del cliente."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa Firebase si no está ya inicializado."""
        if not self._initialized and FIREBASE_AVAILABLE:
            self._initialize_firebase()
            FirebaseClient._initialized = True
    
    def _initialize_firebase(self):
        """
        Inicializa Firebase Admin SDK.
        
        Busca credenciales en este orden:
        1. Variable de entorno FIREBASE_CREDENTIALS_PATH
        2. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS
        3. Archivo firebase-credentials.json en directorio actual
        4. Archivo firebase-credentials.json en APPDATA/FACOT
        """
        # Si ya está inicializado, no hacer nada
        try:
            firebase_admin.get_app()
            print("[FIREBASE] Ya inicializado")
            return
        except ValueError:
            pass
        
        # Buscar archivo de credenciales
        cred_path = self._find_credentials_file()
        
        if not cred_path:
            print("[FIREBASE] ⚠️ No se encontró archivo de credenciales Firebase")
            print("[FIREBASE] Configurar FIREBASE_CREDENTIALS_PATH o colocar firebase-credentials.json")
            return
        
        try:
            # Inicializar con credenciales
            cred = credentials.Certificate(cred_path)
            
            # Obtener configuración de storage bucket
            storage_bucket = self._get_storage_bucket(cred_path)
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': storage_bucket
            })
            
            print(f"[FIREBASE] ✓ Inicializado correctamente")
            print(f"[FIREBASE]   Credenciales: {cred_path}")
            print(f"[FIREBASE]   Storage Bucket: {storage_bucket}")
            
        except Exception as e:
            print(f"[FIREBASE] ✗ Error al inicializar: {e}")
    
    def _find_credentials_file(self) -> Optional[str]:
        """Busca el archivo de credenciales en ubicaciones comunes."""
        # 1. Variable de entorno específica
        env_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if env_path and os.path.exists(env_path):
            return env_path
        
        # 2. Variable de entorno de Google
        google_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if google_path and os.path.exists(google_path):
            return google_path
        
        # 3. Directorio actual
        local_path = os.path.join(os.getcwd(), "firebase-credentials.json")
        if os.path.exists(local_path):
            return local_path
        
        # 4. APPDATA/FACOT
        try:
            appdata = os.environ.get("APPDATA") or str(os.path.expanduser("~"))
            facot_path = os.path.join(appdata, "FACOT", "firebase-credentials.json")
            if os.path.exists(facot_path):
                return facot_path
        except Exception:
            pass
        
        return None
    
    def _get_storage_bucket(self, cred_path: str) -> str:
        """
        Obtiene el nombre del bucket de Storage desde las credenciales.
        
        Formato: {project_id}.appspot.com
        """
        try:
            with open(cred_path, 'r') as f:
                cred_data = json.load(f)
                project_id = cred_data.get('project_id', 'facot-app')
                return f"{project_id}.appspot.com"
        except Exception:
            return "facot-app.appspot.com"
    
    def is_available(self) -> bool:
        """Verifica si Firebase está disponible y correctamente inicializado."""
        if not FIREBASE_AVAILABLE:
            return False
        
        try:
            firebase_admin.get_app()
            return True
        except ValueError:
            return False
    
    def get_firestore(self):
        """
        Obtiene cliente de Firestore.
        
        Returns:
            firestore.Client o None si no disponible
        """
        if not self.is_available():
            print("[FIREBASE] Firestore no disponible")
            return None
        
        try:
            return firestore.client()
        except Exception as e:
            print(f"[FIREBASE] Error al obtener Firestore: {e}")
            return None
    
    def get_storage(self):
        """
        Obtiene cliente de Storage.
        
        Returns:
            storage.bucket() o None si no disponible
        """
        if not self.is_available():
            print("[FIREBASE] Storage no disponible")
            return None
        
        try:
            return storage.bucket()
        except Exception as e:
            print(f"[FIREBASE] Error al obtener Storage: {e}")
            return None
    
    def get_auth(self):
        """
        Obtiene módulo de Auth.
        
        Returns:
            auth module o None si no disponible
        """
        if not self.is_available():
            print("[FIREBASE] Auth no disponible")
            return None
        
        return auth
    
    def get_current_user_id(self) -> Optional[str]:
        """
        Obtiene el ID del usuario actual (si está autenticado).
        
        En desktop app, esto podría venir de:
        - Token guardado localmente
        - Variable de sesión
        - Configuración
        
        Returns:
            User ID o None
        """
        # Por ahora, retornar None - se implementará con Auth real
        # TODO: Implementar gestión de sesión de usuario
        return None


# Instancia global (singleton)
_firebase_client = None


def get_firebase_client() -> FirebaseClient:
    """
    Obtiene la instancia global del FirebaseClient.
    
    Returns:
        FirebaseClient instance
    """
    global _firebase_client
    if _firebase_client is None:
        _firebase_client = FirebaseClient()
    return _firebase_client
