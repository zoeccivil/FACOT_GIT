#!/usr/bin/env python3
"""
Script de migración de SQLite a Firebase.

Migra datos de la base de datos SQLite actual a Firestore,
incluyendo empresas, ítems, terceros, facturas y cotizaciones.

Uso:
    python migrate_sqlite_to_firebase.py [--db ruta/a/base.db] [--dry-run]
"""

from __future__ import annotations
import sys
import os
import argparse
from typing import Dict, Any, List
from datetime import datetime

# Agregar el directorio actual al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic import LogicController
from firebase import get_firebase_client


class SQLiteToFirebaseMigrator:
    """
    Migrador de datos SQLite a Firebase.
    
    Lee datos de SQLite y los sube a Firestore manteniendo
    la estructura y relaciones.
    """
    
    def __init__(self, db_path: str, dry_run: bool = False):
        """
        Inicializa el migrador.
        
        Args:
            db_path: Ruta a la base de datos SQLite
            dry_run: Si es True, solo muestra qué se haría sin ejecutar
        """
        self.db_path = db_path
        self.dry_run = dry_run
        
        print(f"[MIGRATOR] Inicializando...")
        print(f"  Base de datos: {db_path}")
        print(f"  Modo: {'DRY RUN (sin cambios)' if dry_run else 'REAL (migrará datos)'}")
        
        # Inicializar SQLite
        self.logic = LogicController(db_path)
        
        # Inicializar Firebase
        self.firebase_client = get_firebase_client()
        if not self.firebase_client.is_available():
            raise RuntimeError("Firebase no está disponible. Verificar configuración.")
        
        self.db = self.firebase_client.get_firestore()
        self.storage = self.firebase_client.get_storage()
        
        # Estadísticas de migración
        self.stats = {
            'companies': {'total': 0, 'migrated': 0, 'errors': 0},
            'items': {'total': 0, 'migrated': 0, 'errors': 0},
            'third_parties': {'total': 0, 'migrated': 0, 'errors': 0},
            'invoices': {'total': 0, 'migrated': 0, 'errors': 0},
            'quotations': {'total': 0, 'migrated': 0, 'errors': 0},
        }
    
    def migrate_all(self) -> None:
        """Ejecuta la migración completa."""
        print("\n" + "=" * 70)
        print("INICIANDO MIGRACIÓN SQLite → Firebase")
        print("=" * 70 + "\n")
        
        start_time = datetime.now()
        
        try:
            # Orden de migración (respetando dependencias)
            self.migrate_companies()
            self.migrate_items()
            self.migrate_third_parties()
            self.migrate_invoices()
            self.migrate_quotations()
            
            # Resumen final
            self.print_summary()
            
        except Exception as e:
            print(f"\n❌ ERROR CRÍTICO: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            elapsed = datetime.now() - start_time
            print(f"\nTiempo total: {elapsed}")
    
    def migrate_companies(self) -> None:
        """Migra empresas."""
        print("\n📊 Migrando EMPRESAS...")
        
        try:
            companies = self.logic.get_all_companies()
            self.stats['companies']['total'] = len(companies)
            
            for company in companies:
                try:
                    company_id = company['id']
                    
                    # Preparar documento
                    doc_data = {
                        'name': company.get('name', ''),
                        'rnc': company.get('rnc', ''),
                        'address': company.get('address', ''),
                        'phone': company.get('phone', ''),
                        'email': company.get('email', ''),
                        'address_line1': company.get('address_line1', ''),
                        'address_line2': company.get('address_line2', ''),
                        'signature_name': company.get('signature_name', ''),
                        'logo_path': company.get('logo_path', ''),
                        'invoice_due_date': company.get('invoice_due_date', ''),
                        'migrated_at': datetime.utcnow().isoformat(),
                        'migrated_from': 'sqlite',
                    }
                    
                    if not self.dry_run:
                        doc_ref = self.db.collection('companies').document(str(company_id))
                        doc_ref.set(doc_data)
                    
                    self.stats['companies']['migrated'] += 1
                    print(f"  ✓ Empresa {company_id}: {company.get('name', 'N/A')}")
                    
                except Exception as e:
                    self.stats['companies']['errors'] += 1
                    print(f"  ✗ Error en empresa {company.get('id', '?')}: {e}")
        
        except Exception as e:
            print(f"  ✗ Error obteniendo empresas: {e}")
    
    def migrate_items(self) -> None:
        """Migra ítems."""
        print("\n📦 Migrando ÍTEMS...")
        
        try:
            # Obtener todos los ítems (búsqueda amplia)
            items = self.logic.get_items_like('', limit=10000)
            self.stats['items']['total'] = len(items)
            
            for item in items:
                try:
                    item_id = item.get('id') or item.get('code', '')
                    
                    # Preparar documento
                    doc_data = {
                        'code': item.get('code', ''),
                        'name': item.get('name', ''),
                        'description': item.get('description', ''),
                        'unit': item.get('unit', 'UND'),
                        'price': float(item.get('price', 0.0)),
                        'cost': float(item.get('cost', 0.0)),
                        'migrated_at': datetime.utcnow().isoformat(),
                        'migrated_from': 'sqlite',
                    }
                    
                    if not self.dry_run:
                        doc_ref = self.db.collection('items').document(str(item_id))
                        doc_ref.set(doc_data)
                    
                    self.stats['items']['migrated'] += 1
                    
                    if self.stats['items']['migrated'] % 50 == 0:
                        print(f"  ... {self.stats['items']['migrated']} ítems migrados")
                    
                except Exception as e:
                    self.stats['items']['errors'] += 1
                    print(f"  ✗ Error en ítem: {e}")
            
            print(f"  ✓ Total: {self.stats['items']['migrated']} ítems")
        
        except Exception as e:
            print(f"  ✗ Error obteniendo ítems: {e}")
    
    def migrate_third_parties(self) -> None:
        """Migra terceros."""
        print("\n👥 Migrando TERCEROS...")
        print("  ℹ️ Saltando (tabla opcional no siempre presente)")
        # TODO: Implementar si la tabla third_parties existe
    
    def migrate_invoices(self) -> None:
        """Migra facturas con sus ítems."""
        print("\n🧾 Migrando FACTURAS...")
        
        try:
            # Obtener facturas (método puede variar según implementación)
            if hasattr(self.logic, 'get_all_invoices'):
                invoices = self.logic.get_all_invoices()
            elif hasattr(self.logic, 'get_invoices'):
                invoices = self.logic.get_invoices(limit=10000)
            else:
                print("  ℹ️ Método get_invoices no disponible")
                return
            
            self.stats['invoices']['total'] = len(invoices)
            
            for invoice in invoices:
                try:
                    invoice_id = invoice['id']
                    
                    # Preparar documento de factura
                    doc_data = {
                        'company_id': invoice.get('company_id'),
                        'invoice_type': invoice.get('invoice_type', 'emitida'),
                        'invoice_date': invoice.get('invoice_date', ''),
                        'invoice_number': invoice.get('invoice_number', ''),
                        'invoice_category': invoice.get('invoice_category', ''),
                        'client_name': invoice.get('client_name', ''),
                        'client_rnc': invoice.get('client_rnc', ''),
                        'currency': invoice.get('currency', 'RD$'),
                        'total_amount': float(invoice.get('total_amount', 0.0)),
                        'due_date': invoice.get('due_date', ''),
                        'migrated_at': datetime.utcnow().isoformat(),
                        'migrated_from': 'sqlite',
                    }
                    
                    if not self.dry_run:
                        # Crear documento de factura
                        invoice_ref = self.db.collection('invoices').document(str(invoice_id))
                        invoice_ref.set(doc_data)
                        
                        # Migrar ítems de la factura
                        if 'items' in invoice:
                            items_ref = invoice_ref.collection('items')
                            for idx, item in enumerate(invoice['items']):
                                item_doc = {
                                    'description': item.get('description', ''),
                                    'quantity': float(item.get('quantity', 0.0)),
                                    'unit_price': float(item.get('unit_price', 0.0)),
                                    'unit': item.get('unit', 'UND'),
                                    'code': item.get('code', ''),
                                }
                                items_ref.document(str(idx)).set(item_doc)
                    
                    self.stats['invoices']['migrated'] += 1
                    
                    if self.stats['invoices']['migrated'] % 20 == 0:
                        print(f"  ... {self.stats['invoices']['migrated']} facturas migradas")
                    
                except Exception as e:
                    self.stats['invoices']['errors'] += 1
                    print(f"  ✗ Error en factura {invoice.get('id', '?')}: {e}")
            
            print(f"  ✓ Total: {self.stats['invoices']['migrated']} facturas")
        
        except Exception as e:
            print(f"  ✗ Error obteniendo facturas: {e}")
    
    def migrate_quotations(self) -> None:
        """Migra cotizaciones con sus ítems."""
        print("\n📋 Migrando COTIZACIONES...")
        
        try:
            # Obtener cotizaciones
            if hasattr(self.logic, 'get_all_quotations'):
                quotations = self.logic.get_all_quotations()
            elif hasattr(self.logic, 'get_quotations'):
                quotations = self.logic.get_quotations(limit=10000)
            else:
                print("  ℹ️ Método get_quotations no disponible")
                return
            
            self.stats['quotations']['total'] = len(quotations)
            
            for quotation in quotations:
                try:
                    quotation_id = quotation['id']
                    
                    # Preparar documento de cotización
                    doc_data = {
                        'company_id': quotation.get('company_id'),
                        'quotation_date': quotation.get('quotation_date', ''),
                        'client_name': quotation.get('client_name', ''),
                        'client_rnc': quotation.get('client_rnc', ''),
                        'notes': quotation.get('notes', ''),
                        'currency': quotation.get('currency', 'RD$'),
                        'total_amount': float(quotation.get('total_amount', 0.0)),
                        'due_date': quotation.get('due_date', ''),
                        'migrated_at': datetime.utcnow().isoformat(),
                        'migrated_from': 'sqlite',
                    }
                    
                    if not self.dry_run:
                        # Crear documento de cotización
                        quotation_ref = self.db.collection('quotations').document(str(quotation_id))
                        quotation_ref.set(doc_data)
                        
                        # Migrar ítems de la cotización
                        if 'items' in quotation:
                            items_ref = quotation_ref.collection('items')
                            for idx, item in enumerate(quotation['items']):
                                item_doc = {
                                    'description': item.get('description', ''),
                                    'quantity': float(item.get('quantity', 0.0)),
                                    'unit_price': float(item.get('unit_price', 0.0)),
                                    'unit': item.get('unit', 'UND'),
                                    'code': item.get('code', ''),
                                }
                                items_ref.document(str(idx)).set(item_doc)
                    
                    self.stats['quotations']['migrated'] += 1
                    
                    if self.stats['quotations']['migrated'] % 20 == 0:
                        print(f"  ... {self.stats['quotations']['migrated']} cotizaciones migradas")
                    
                except Exception as e:
                    self.stats['quotations']['errors'] += 1
                    print(f"  ✗ Error en cotización {quotation.get('id', '?')}: {e}")
            
            print(f"  ✓ Total: {self.stats['quotations']['migrated']} cotizaciones")
        
        except Exception as e:
            print(f"  ✗ Error obteniendo cotizaciones: {e}")
    
    def print_summary(self) -> None:
        """Imprime resumen de la migración."""
        print("\n" + "=" * 70)
        print("RESUMEN DE MIGRACIÓN")
        print("=" * 70)
        
        total_items = sum(s['total'] for s in self.stats.values())
        total_migrated = sum(s['migrated'] for s in self.stats.values())
        total_errors = sum(s['errors'] for s in self.stats.values())
        
        print(f"\nEstadísticas por tipo:")
        for entity_type, stats in self.stats.items():
            print(f"  {entity_type.upper():20} | Total: {stats['total']:5} | Migrados: {stats['migrated']:5} | Errores: {stats['errors']:3}")
        
        print(f"\nTOTAL GENERAL:")
        print(f"  Registros procesados: {total_items}")
        print(f"  Migrados exitosamente: {total_migrated}")
        print(f"  Errores: {total_errors}")
        
        if total_errors == 0:
            print(f"\n✅ Migración completada sin errores")
        else:
            print(f"\n⚠️ Migración completada con {total_errors} errores")
        
        if self.dry_run:
            print("\n⚠️ DRY RUN - No se realizaron cambios reales")
        else:
            print("\n✅ Cambios confirmados en Firebase")


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description='Migra datos de SQLite a Firebase')
    parser.add_argument(
        '--db',
        default='facturas_cotizaciones.db',
        help='Ruta a la base de datos SQLite (default: facturas_cotizaciones.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo de prueba (no hace cambios reales)'
    )
    
    args = parser.parse_args()
    
    # Verificar que existe la base de datos
    if not os.path.exists(args.db):
        print(f"❌ Error: No se encontró la base de datos: {args.db}")
        sys.exit(1)
    
    # Confirmar antes de ejecutar (si no es dry-run)
    if not args.dry_run:
        print("\n⚠️  ADVERTENCIA: Esta operación migrará datos a Firebase.")
        print("    Los datos en SQLite NO serán modificados.")
        print("    Los datos existentes en Firebase podrían ser sobrescritos.\n")
        
        confirm = input("¿Desea continuar? (escriba 'SI' para confirmar): ")
        if confirm != 'SI':
            print("Migración cancelada.")
            sys.exit(0)
    
    # Ejecutar migración
    try:
        migrator = SQLiteToFirebaseMigrator(args.db, dry_run=args.dry_run)
        migrator.migrate_all()
    except KeyboardInterrupt:
        print("\n\n⚠️ Migración interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
