# Roadmap de Modernización FACOT

## Estado Actual

### ✅ Completado: PR1 - Calidad (Commit 0529704)

**Implementado:**
- ✅ GitHub Actions CI (.github/workflows/ci.yml)
  - Soporte para Python 3.8, 3.9, 3.10, 3.11
  - Linting con ruff
  - Formateo con black
  - Type checking con mypy
  - Cobertura de código con pytest-cov
  
- ✅ Pre-commit hooks (.pre-commit-config.yaml)
  - Formateo automático
  - Linting automático
  - Validación de YAML/JSON
  - Control de archivos grandes
  
- ✅ Suite de Tests (tests/)
  - 18 tests de cálculos (100% pasando)
  - Tests de LogicController
  - Fixtures compartidos
  - Configuración pytest.ini
  
- ✅ Dependencias de desarrollo (requirements-dev.txt)

**Criterios de Aceptación:**
- ✅ Workflow de GitHub Actions configurado
- ✅ Tests de ejemplo pasando localmente
- ✅ Pre-commit ejecutable

---

## 📋 Pendiente: PR2 - UX: Mejora de Tabla de Ítems

### Objetivo
Modernizar la tabla de items de facturas/cotizaciones usando el patrón Model-View de Qt.

### Tareas

#### 1. Crear ItemsTableModel
**Archivo:** `models/items_table_model.py`

```python
class ItemsTableModel(QAbstractTableModel):
    """
    Modelo Qt para la tabla de items de factura/cotización.
    
    Columnas:
    - Código
    - Descripción
    - Cantidad
    - Unidad
    - Precio Unit.
    - Descuento (%)
    - Subtotal
    """
    
    # Métodos a implementar:
    - rowCount()
    - columnCount()
    - data()
    - setData()
    - flags()
    - headerData()
    - insertRows()
    - removeRows()
    
    # Funcionalidad adicional:
    - Recálculo automático de subtotales
    - Validación de datos (cantidad >= 0, precio >= 0)
    - Signals para cambios
```

#### 2. Migrar detalle_factura_items.py
**Cambios:**
- Reemplazar QTableWidget por QTableView
- Conectar ItemsTableModel
- Mantener compatibilidad con `collect_items_for_export()`
- Integrar autocompletar de items desde BD

#### 3. Atajos de Teclado
- `Ctrl+N`: Insertar nueva fila
- `Del`: Eliminar fila seleccionada
- `Ctrl+D`: Duplicar fila
- `F2`: Editar celda
- `Tab/Shift+Tab`: Navegar entre celdas

#### 4. Autocompletar
- Integrar con `ensure_items_schema()` existente
- QCompleter en columna de código/descripción
- Autorellenar precio y unidad al seleccionar item

#### 5. Tests
**Archivo:** `tests/test_items_model.py`

```python
class TestItemsTableModel:
    def test_add_row()
    def test_remove_row()
    def test_edit_cell()
    def test_calculate_subtotal()
    def test_validation_quantity()
    def test_validation_price()
    def test_discount_calculation()
```

### Criterios de Aceptación
- [ ] Ediciones inline funcionando
- [ ] Recálculo automático de subtotales
- [ ] Autocompletar de items
- [ ] Atajos de teclado funcionando
- [ ] No romper funcionalidad de guardado/export
- [ ] Tests unitarios del modelo

---

## 📧 Pendiente: PR4 - Email

### Objetivo
Permitir enviar facturas/cotizaciones por email directamente desde la aplicación.

### Tareas

#### 1. Crear utils/mail_utils.py
```python
class EmailService:
    """
    Servicio de envío de emails.
    Soporta SMTP y SendGrid.
    """
    
    def __init__(self, config):
        # Leer config de email desde config_facot.py
        pass
    
    def send_invoice_email(
        invoice_payload: dict,
        to_email: str,
        subject: str,
        body_html: str,
        attachments: list = []
    ) -> bool:
        """
        Envía factura por email.
        Registra en email_logs.
        """
        pass
    
    def test_connection(self) -> bool:
        """Prueba la conexión SMTP."""
        pass
```

#### 2. Tabla email_logs
**SQL:**
```sql
CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    status TEXT NOT NULL, -- 'sent', 'failed', 'pending'
    error_message TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
```

#### 3. Configuración de Email
**Agregar a config_facot.py:**
```python
def get_email_config():
    """
    Retorna configuración de email.
    Usar variables de entorno para credenciales.
    """
    return {
        'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', 587)),
        'smtp_user': os.getenv('SMTP_USER', ''),
        'smtp_password': os.getenv('SMTP_PASSWORD', ''),
        'use_tls': True,
        'sendgrid_api_key': os.getenv('SENDGRID_API_KEY', '')
    }
```

#### 4. UI: Botón "Enviar por Email"
**Ubicación:** `tabs/invoice_tab.py` o `ui_mainwindow-2.py`

**Diálogo:**
- Campo: Email destinatario
- Vista previa del email
- Checkbox: Adjuntar PDF de factura
- Botón: Enviar

#### 5. Tests
**Archivo:** `tests/test_mail_utils.py`

```python
class TestEmailService:
    def test_smtp_connection_mock()
    def test_send_email_success()
    def test_send_email_failure()
    def test_email_log_created()
    def test_attachment_included()
```

### Criterios de Aceptación
- [ ] Envío simulado exitoso con mock
- [ ] UI dispara el envío
- [ ] Log registrado en email_logs
- [ ] Configuración desde variables de entorno
- [ ] Tests con mocking de SMTP

---

## 🔒 Pendiente: PR5 - Auditoría y NCF Robusto

### Objetivo
Implementar auditoría completa y asegurar generación de NCF sin duplicados.

### Tareas

#### 1. Tabla audit_log
**SQL:**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,  -- 'invoice', 'company', 'ncf'
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,  -- 'create', 'update', 'delete'
    user TEXT,  -- username o host
    timestamp TEXT NOT NULL,
    payload_before TEXT,  -- JSON
    payload_after TEXT,   -- JSON
    ip_address TEXT,
    user_agent TEXT
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

#### 2. Servicio de Auditoría
**Archivo:** `services/audit_service.py`

```python
class AuditService:
    """Servicio centralizado de auditoría."""
    
    def log_action(
        entity_type: str,
        entity_id: int,
        action: str,
        payload_before: dict = None,
        payload_after: dict = None,
        user: str = None
    ):
        """Registra una acción en audit_log."""
        pass
    
    def get_audit_trail(entity_type: str, entity_id: int):
        """Obtiene el historial de auditoría de una entidad."""
        pass
```

#### 3. Integrar Auditoría
**Puntos de integración:**
- `logic.py::add_invoice()` → log create
- `logic.py::update_invoice()` → log update con before/after
- `logic.py::delete_invoice()` → log delete
- `logic.py::reserve_ncf()` → log NCF assignment

#### 4. NCF Seguro con Transacciones
**Archivo:** `services/ncf_service.py`

```python
class NCFService:
    """Servicio de gestión de NCF con transacciones."""
    
    def reserve_ncf(
        db_connection,
        company_id: int,
        ncf_type: str
    ) -> str:
        """
        Reserva un NCF de forma segura.
        Usa BEGIN EXCLUSIVE para evitar race conditions.
        """
        try:
            db_connection.execute("BEGIN EXCLUSIVE")
            
            # Buscar último NCF
            last_ncf = get_last_ncf(company_id, ncf_type)
            
            # Calcular siguiente
            next_ncf = calculate_next_ncf(last_ncf, ncf_type)
            
            # Marcar como usado (insertar en tabla temporal)
            mark_ncf_as_used(next_ncf)
            
            db_connection.commit()
            return next_ncf
        except:
            db_connection.rollback()
            raise
```

#### 5. Tests
**Archivos:**
- `tests/test_audit_log.py`
- `tests/test_ncf_reservation.py`

```python
class TestAuditLog:
    def test_log_invoice_creation()
    def test_log_invoice_update()
    def test_log_invoice_deletion()
    def test_audit_trail_retrieval()

class TestNCFReservation:
    def test_reserve_ncf_sequential()
    def test_reserve_ncf_concurrent()  # Simular concurrencia
    def test_no_duplicate_ncf()
    def test_transaction_rollback()
```

### Criterios de Aceptación
- [ ] Audit logs generados para operaciones críticas
- [ ] NCF reservado sin duplicados
- [ ] Simulación de concurrencia sin colisiones
- [ ] Tests de transacciones pasando

---

## 📝 Notas de Implementación

### Prioridades
1. **PR1** ✅ - Ya completado
2. **PR2** - Alta prioridad (mejora UX)
3. **PR5** - Alta prioridad (seguridad NCF)
4. **PR4** - Media prioridad (feature adicional)

### Estilo y Calidad
- ✅ Usar typing en todas las funciones nuevas
- ✅ Mantener compatibilidad retroactiva
- ✅ Incluir migraciones de BD cuando sea necesario
- ✅ Documentar cambios en cada PR

### Variables de Entorno
No almacenar credenciales en código:
```bash
# .env (NO commitear)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_password
SENDGRID_API_KEY=SG.xxxxx
```

### Migraciones de BD
Para cada cambio de esquema, crear script en `scripts/migrations/`:
```python
# scripts/migrations/001_add_audit_log.py
def upgrade(conn):
    conn.execute("""CREATE TABLE audit_log ...""")

def downgrade(conn):
    conn.execute("""DROP TABLE audit_log""")
```

---

## 🎯 Entregables por PR

Cada PR debe incluir:
1. ✅ Código funcional
2. ✅ Tests unitarios (>70% cobertura del código nuevo)
3. ✅ Documentación en el PR
4. ✅ Instrucciones de prueba manual
5. ✅ Checklist de aceptación
6. ✅ Update a CHANGELOG.md

---

**Última Actualización:** 2025-11-09  
**Estado:** PR1 Completado, PR2/PR4/PR5 En Progreso
