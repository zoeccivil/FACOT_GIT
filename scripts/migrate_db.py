#!/usr/bin/env python3
"""
Script de migración de base de datos.

Crea las tablas necesarias para:
- Auditoría (audit_log)
- Email logs (email_logs)
- Actualiza esquemas existentes

Uso:
    python scripts/migrate_db.py [ruta_bd]
    python scripts/migrate_db.py facturas_cotizaciones.db
"""

import sys
import os
import sqlite3
from datetime import datetime

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.audit_service import AuditService
from services.ncf_service import NCFService


def migrate_database(db_path: str):
    """
    Ejecuta todas las migraciones necesarias en la base de datos.
    
    Args:
        db_path: Ruta al archivo de base de datos SQLite
    """
    print(f"🔧 Migrando base de datos: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: La base de datos no existe: {db_path}")
        return False
    
    # Crear backup
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"📦 Creando backup: {backup_path}")
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup creado exitosamente")
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo crear backup: {e}")
        response = input("¿Continuar sin backup? (s/n): ")
        if response.lower() != 's':
            print("❌ Migración cancelada")
            return False
    
    try:
        # Inicializar servicios (esto crea las tablas automáticamente)
        print("\n📝 Creando/actualizando tabla audit_log...")
        audit_service = AuditService(db_path)
        print("✅ Tabla audit_log lista")
        
        print("\n📝 Creando/actualizando tabla email_logs...")
        from utils.mail_utils import EmailService, EmailConfig
        # Crear configuración desde env o dummy
        os.environ.setdefault('SMTP_HOST', 'dummy.smtp.com')
        os.environ.setdefault('SMTP_USER', 'dummy@example.com')
        os.environ.setdefault('SMTP_PASSWORD', 'dummy')
        
        config_dict = EmailConfig.get_config()
        email_service = EmailService(config_dict, db_path)
        print("✅ Tabla email_logs lista")
        
        # Verificar tablas creadas
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        print("\n🔍 Verificando tablas...")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]
        
        required_tables = ['audit_log', 'email_logs']
        for table in required_tables:
            if table in tables:
                print(f"  ✅ {table}")
                # Contar registros
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"     ({count} registros)")
            else:
                print(f"  ❌ {table} - NO ENCONTRADA")
        
        conn.close()
        
        print("\n✅ Migración completada exitosamente")
        print(f"📦 Backup guardado en: {backup_path}")
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n💡 Puede restaurar desde el backup: {backup_path}")
        return False


def verify_migration(db_path: str):
    """
    Verifica que la migración se haya completado correctamente.
    
    Args:
        db_path: Ruta al archivo de base de datos SQLite
    """
    print(f"\n🔍 Verificando migración en: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Verificar audit_log
        print("\n📋 Verificando tabla audit_log...")
        cur.execute("PRAGMA table_info(audit_log)")
        columns = [row[1] for row in cur.fetchall()]
        required_columns = ['id', 'entity_type', 'entity_id', 'action', 'user', 
                          'timestamp', 'payload_before', 'payload_after']
        
        for col in required_columns:
            if col in columns:
                print(f"  ✅ Columna: {col}")
            else:
                print(f"  ❌ Falta columna: {col}")
        
        # Verificar email_logs
        print("\n📋 Verificando tabla email_logs...")
        cur.execute("PRAGMA table_info(email_logs)")
        columns = [row[1] for row in cur.fetchall()]
        required_columns = ['id', 'invoice_id', 'to_email', 'subject', 'sent_at', 
                          'status', 'error_message']
        
        for col in required_columns:
            if col in columns:
                print(f"  ✅ Columna: {col}")
            else:
                print(f"  ❌ Falta columna: {col}")
        
        # Verificar índices de audit_log
        print("\n🔍 Verificando índices de audit_log...")
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='audit_log'")
        indexes = [row[0] for row in cur.fetchall()]
        print(f"  Índices encontrados: {len(indexes)}")
        for idx in indexes:
            print(f"    • {idx}")
        
        conn.close()
        
        print("\n✅ Verificación completada")
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante verificación: {e}")
        return False


def main():
    """Función principal del script."""
    print("=" * 60)
    print("  MIGRACIÓN DE BASE DE DATOS - FACOT")
    print("=" * 60)
    
    # Determinar ruta de BD
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Usar ruta por defecto
        db_path = "facturas_cotizaciones.db"
    
    print(f"\n📂 Base de datos: {db_path}")
    
    # Ejecutar migración
    success = migrate_database(db_path)
    
    if success:
        # Verificar migración
        verify_migration(db_path)
        print("\n" + "=" * 60)
        print("  ✅ MIGRACIÓN EXITOSA")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("  ❌ MIGRACIÓN FALLIDA")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
