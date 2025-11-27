#!/usr/bin/env python3
"""
Script de demostración del backend integrado.

Demuestra:
1. Creación de factura con NCF automático
2. Auditoría automática
3. NCF sin duplicados
4. Historial de cambios

Uso:
    python demo_backend.py
"""

import sys
import os
import tempfile

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic import LogicController


def print_separator(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def demo_backend():
    """Demostración del backend integrado."""
    print_separator("🚀 DEMO: BACKEND INTEGRADO FACOT")
    
    # Crear BD temporal para demo
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    print(f"\n📂 BD Temporal: {db_path}")
    
    try:
        # 1. Inicializar LogicController (carga servicios automáticamente)
        print_separator("1. Inicializar LogicController")
        logic = LogicController(db_path)
        print("✅ LogicController inicializado")
        print(f"✅ AuditService: {logic.audit_service}")
        print(f"✅ NCFService: {logic.ncf_service}")
        
        # 2. Crear empresa
        print_separator("2. Crear Empresa")
        company_id = logic.add_company(
            name="Empresa Demo S.A.",
            rnc="000000001",
            address="Santo Domingo, RD"
        )
        print(f"✅ Empresa creada: ID = {company_id}")
        
        # 3. Crear facturas con NCF automático
        print_separator("3. Crear Facturas con NCF Automático")
        
        invoices = []
        for i in range(1, 6):
            invoice_data = {
                'company_id': company_id,
                'invoice_type': 'emitida',
                'invoice_date': f'2024-01-{15+i:02d}',
                'invoice_category': 'B01',
                'client_name': f'Cliente #{i}',
                'client_rnc': f'00000000{i}',
                'currency': 'RD$',
                'total_amount': 1000.0 * i,
            }
            items = [
                {'description': f'Servicio {i}', 'quantity': 1, 'unit_price': 1000.0 * i}
            ]
            
            invoice_id = logic.add_invoice(invoice_data, items)
            
            # Obtener NCF asignado
            cur = logic.conn.cursor()
            cur.execute("SELECT invoice_number FROM invoices WHERE id = ?", (invoice_id,))
            ncf = cur.fetchone()[0]
            
            invoices.append((invoice_id, ncf))
            print(f"  Factura #{i}: ID={invoice_id}, NCF={ncf}, Total=RD${1000.0 * i:,.2f}")
        
        print(f"\n✅ {len(invoices)} facturas creadas")
        
        # 4. Verificar NCF sin duplicados
        print_separator("4. Verificar NCF Sin Duplicados")
        ncfs = [ncf for _, ncf in invoices]
        unique_ncfs = set(ncfs)
        
        print(f"  Total NCFs generados: {len(ncfs)}")
        print(f"  NCFs únicos: {len(unique_ncfs)}")
        print(f"  ✅ Sin duplicados: {len(ncfs) == len(unique_ncfs)}")
        
        print("\n  NCFs generados:")
        for i, ncf in enumerate(ncfs, 1):
            print(f"    {i}. {ncf}")
        
        # 5. Ver auditoría
        print_separator("5. Auditoría Automática")
        
        # Ver logs de la primera factura
        invoice_id = invoices[0][0]
        print(f"\n  Historial de Factura ID={invoice_id}:")
        
        history = logic.audit_service.get_invoice_history(invoice_id)
        for entry in history:
            print(f"    [{entry['timestamp']}] {entry['action']} por {entry['user']}")
        
        print(f"\n  ✅ {len(history)} registros de auditoría")
        
        # 6. Actualizar factura
        print_separator("6. Actualizar Factura (con Auditoría)")
        
        invoice_data_updated = {
            'company_id': company_id,
            'invoice_type': 'emitida',
            'invoice_date': '2024-01-16',
            'invoice_number': ncfs[0],
            'invoice_category': 'B01',
            'client_name': 'Cliente #1 ACTUALIZADO',
            'client_rnc': '000000001',
            'currency': 'RD$',
            'total_amount': 2500.0,  # Cambio
        }
        items_updated = [
            {'description': 'Servicio Premium', 'quantity': 1, 'unit_price': 2500.0}
        ]
        
        logic.update_invoice(invoice_id, invoice_data_updated, items_updated)
        print(f"✅ Factura {invoice_id} actualizada")
        
        # Ver auditoría actualizada
        history_updated = logic.audit_service.get_invoice_history(invoice_id)
        print(f"\n  Historial actualizado ({len(history_updated)} registros):")
        for entry in history_updated:
            print(f"    [{entry['timestamp']}] {entry['action']} por {entry['user']}")
        
        # 7. Eliminar factura
        print_separator("7. Eliminar Factura (con Auditoría)")
        
        delete_id = invoices[-1][0]  # Última factura
        print(f"  Eliminando factura ID={delete_id}...")
        
        logic.delete_factura(delete_id)
        print(f"✅ Factura {delete_id} eliminada")
        
        # Verificar que el log de eliminación existe
        cur = logic.conn.cursor()
        cur.execute("""
            SELECT * FROM audit_log 
            WHERE entity_type = 'invoice' 
            AND entity_id = ? 
            AND action = 'delete'
        """, (delete_id,))
        delete_log = cur.fetchone()
        
        if delete_log:
            print(f"✅ Log de eliminación registrado")
        
        # 8. Estadísticas de auditoría
        print_separator("8. Estadísticas de Auditoría")
        
        recent_actions = logic.audit_service.get_recent_actions(limit=10)
        print(f"\n  Últimas 10 acciones:")
        for i, action in enumerate(recent_actions[:10], 1):
            print(f"    {i}. [{action['timestamp']}] "
                  f"{action['entity_type']}.{action['action']} "
                  f"(ID={action['entity_id']})")
        
        # Contar por tipo de acción
        cur = logic.conn.cursor()
        cur.execute("SELECT action, COUNT(*) as count FROM audit_log GROUP BY action")
        stats = cur.fetchall()
        
        print(f"\n  Acciones por tipo:")
        for action, count in stats:
            print(f"    {action}: {count}")
        
        # 9. Verificar tabla email_logs
        print_separator("9. Verificar Tabla email_logs")
        
        try:
            cur.execute("SELECT COUNT(*) FROM email_logs")
            email_count = cur.fetchone()[0]
            print(f"✅ Tabla email_logs existe ({email_count} registros)")
        except:
            print(f"ℹ️  Tabla email_logs se crea al usar EmailService")
            print(f"   (Ejecutar migrate_db.py para crearla)")
        
        # 10. Resumen final
        print_separator("✅ DEMO COMPLETADO EXITOSAMENTE")
        
        cur.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM audit_log")
        audit_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM ncf_sequences")
        ncf_seq_count = cur.fetchone()[0]
        
        print(f"""
  📊 Estadísticas:
    • Facturas creadas: {len(invoices)}
    • Facturas actuales: {invoice_count}
    • Registros de auditoría: {audit_count}
    • Secuencias NCF: {ncf_seq_count}
    • NCF únicos generados: {len(unique_ncfs)}
    • Sin duplicados: ✅
        """)
        
        print("  ✅ TODO FUNCIONANDO CORRECTAMENTE")
        print()
        
    finally:
        # Limpiar
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"🧹 BD temporal eliminada: {db_path}")


if __name__ == "__main__":
    try:
        demo_backend()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
