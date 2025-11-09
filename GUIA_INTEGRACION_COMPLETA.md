# Guía de Integración Completa - FACOT
## Para Desarrolladores Novatos - Paso a Paso

**Fecha:** 2025-11-09  
**Nivel:** Principiante/Intermedio  
**Tiempo Estimado:** 4-6 horas  
**Idioma:** Español 🇪🇸

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Preparación del Entorno](#preparación-del-entorno)
3. [Integración Backend (logic.py)](#integración-backend-logicpy)
4. [Integración UI - Tabla de Items](#integración-ui---tabla-de-items)
5. [Integración UI - Botón Email](#integración-ui---botón-email)
6. [Pruebas y Validación](#pruebas-y-validación)
7. [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Introducción

Esta guía te ayudará a integrar los nuevos servicios implementados (AuditService, NCFService, EmailService, ItemsTableModel) en la aplicación FACOT.

### ¿Qué vamos a hacer?

1. **Backend:** Integrar auditoría y NCF seguro en `logic.py`
2. **UI - Tabla:** Migrar la tabla de items a usar el nuevo modelo Qt
3. **UI - Email:** Agregar botón para enviar facturas por email

### Requisitos Previos

- Python 3.8 o superior instalado
- PyQt6 instalado
- Editor de código (VSCode, PyCharm, o similar)
- Conocimientos básicos de Python
- La aplicación FACOT funcionando

---

## 🛠️ Preparación del Entorno

### Paso 1: Verificar Instalación de Dependencias

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Instalar dependencias principales
pip install -r requirements.txt
```

### Paso 2: Hacer Backup

**IMPORTANTE:** Antes de hacer cambios, crea un backup:

```bash
# Crear carpeta de backup
mkdir -p backups

# Copiar archivos que vamos a modificar
cp logic.py backups/logic.py.backup
cp detalle_factura_items.py backups/detalle_factura_items.py.backup
cp config_facot.py backups/config_facot.py.backup
```

### Paso 3: Verificar que los Nuevos Servicios Existen

Verifica que estos archivos existen:

```bash
ls services/audit_service.py
ls services/ncf_service.py
ls utils/mail_utils.py
ls models/items_table_model.py
```

Si todos existen, ¡perfecto! Podemos continuar.

---

## 🔧 Integración Backend (logic.py)

### Objetivo

Integrar AuditService y NCFService en `logic.py` para:
- Registrar auditoría de todas las operaciones
- Generar NCF sin duplicados usando transacciones

### Paso 1: Agregar Imports

Abre el archivo `logic.py` en tu editor.

**Ubicación:** `/home/runner/work/FACOT_GIT/FACOT_GIT/logic.py`

Al inicio del archivo, después de los imports existentes, agrega:

```python
# Imports de los nuevos servicios
from services.audit_service import AuditService
from services.ncf_service import NCFService
```

**Cómo hacerlo:**
1. Abre `logic.py`
2. Busca la sección de imports (líneas 1-10 aproximadamente)
3. Agrega las dos líneas arriba al final de los imports
4. Guarda el archivo

### Paso 2: Modificar el Método `add_invoice`

Busca el método `add_invoice` en `logic.py`. Se ve algo así:

```python
def add_invoice(self, invoice_data, items):
    # código actual...
```

**ANTES del cambio:**

```python
def add_invoice(self, invoice_data, items):
    # Obtener siguiente NCF
    ncf = self.get_next_ncf(company_id, ncf_type)
    invoice_data['invoice_number'] = ncf
    
    # Insertar factura en BD
    cursor.execute("INSERT INTO invoices (...) VALUES (...)")
    invoice_id = cursor.lastrowid
    
    # Insertar items
    for item in items:
        cursor.execute("INSERT INTO invoice_items (...) VALUES (...)")
    
    return invoice_id
```

**DESPUÉS del cambio:**

```python
def add_invoice(self, invoice_data, items):
    company_id = invoice_data.get('company_id')
    ncf_type = invoice_data.get('invoice_category', 'B01')
    
    # 1. Reservar NCF de forma segura
    ncf_service = NCFService(self.db_path)
    success, ncf = ncf_service.reserve_ncf(company_id, ncf_type)
    
    if not success:
        # Si falla, retornar error
        return None, f"Error al generar NCF: {ncf}"
    
    invoice_data['invoice_number'] = ncf
    
    # 2. Insertar factura en BD (código existente)
    cursor.execute("INSERT INTO invoices (...) VALUES (...)")
    invoice_id = cursor.lastrowid
    
    # 3. Insertar items (código existente)
    for item in items:
        cursor.execute("INSERT INTO invoice_items (...) VALUES (...)")
    
    # 4. Registrar auditoría
    audit_service = AuditService(self.db_path)
    audit_service.log_invoice_create(invoice_id, invoice_data)
    audit_service.log_ncf_assignment(invoice_id, ncf, company_id)
    
    return invoice_id, None  # Sin error
```

**Instrucciones paso a paso:**

1. Busca la función `add_invoice` en `logic.py`
2. Localiza donde se genera el NCF (busca `get_next_ncf`)
3. Reemplaza esa sección con el código nuevo
4. Al final del método, ANTES del `return`, agrega el código de auditoría
5. Cambia el return para incluir el posible error: `return invoice_id, None`
6. Guarda el archivo

### Paso 3: Modificar el Método `update_invoice`

Busca el método `update_invoice`:

**DESPUÉS del cambio:**

```python
def update_invoice(self, invoice_id, invoice_data, items):
    # 1. Obtener datos ANTES de actualizar (para auditoría)
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    row = cursor.fetchone()
    
    if row:
        columns = [description[0] for description in cursor.description]
        invoice_before = dict(zip(columns, row))
    else:
        invoice_before = {}
    
    # 2. Actualizar factura (código existente)
    cursor.execute("UPDATE invoices SET ... WHERE id = ?", (..., invoice_id))
    
    # 3. Actualizar items (código existente)
    cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    for item in items:
        cursor.execute("INSERT INTO invoice_items (...) VALUES (...)")
    
    # 4. Registrar auditoría
    audit_service = AuditService(self.db_path)
    audit_service.log_invoice_update(
        invoice_id, 
        invoice_before, 
        invoice_data
    )
    
    return True
```

**Instrucciones:**

1. Busca `update_invoice` en `logic.py`
2. ANTES de hacer el UPDATE, agrega código para obtener los datos actuales
3. AL FINAL, agrega el registro de auditoría
4. Guarda

### Paso 4: Modificar el Método `delete_invoice`

**DESPUÉS del cambio:**

```python
def delete_invoice(self, invoice_id):
    # 1. Obtener datos ANTES de eliminar (para auditoría)
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    row = cursor.fetchone()
    
    if row:
        columns = [description[0] for description in cursor.description]
        invoice_data = dict(zip(columns, row))
    else:
        return False, "Factura no encontrada"
    
    # 2. Eliminar (código existente)
    cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    
    # 3. Registrar auditoría
    audit_service = AuditService(self.db_path)
    audit_service.log_invoice_delete(invoice_id, invoice_data)
    
    return True, "Factura eliminada"
```

### Paso 5: Probar la Integración Backend

Abre una terminal y ejecuta:

```bash
# Ejecutar tests
python -m pytest tests/test_db_manager.py -v

# Si falla, revisa los errores y ajusta
```

**Verificación manual:**

1. Ejecuta la aplicación: `python main.py`
2. Crea una nueva factura
3. Verifica que se crea correctamente
4. Cierra la aplicación
5. Abre la base de datos con DB Browser for SQLite
6. Verifica que existen registros en la tabla `audit_log`

---

## 🎨 Integración UI - Tabla de Items

### Objetivo

Reemplazar la tabla actual de items con el nuevo `ItemsTableModel`.

### Paso 1: Actualizar detalle_factura_items.py - Imports

Abre `detalle_factura_items.py`.

Agrega este import al inicio:

```python
from PyQt6.QtWidgets import (
    QHBoxLayout, QLineEdit, QTableView, QVBoxLayout,  # Cambiado QTableWidget por QTableView
    QPushButton, QWidget, QLabel, QHeaderView, QMessageBox
)
from models.items_table_model import ItemsTableModel
```

### Paso 2: Modificar la Clase DetalleItemsWidget

**BUSCAR:**

```python
class DetalleItemsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        # ...
```

**REEMPLAZAR con:**

```python
class DetalleItemsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Crear el modelo de items
        self.items_model = ItemsTableModel()
        
        self._build_ui()
        self.sugerencias = []
        self.seleccion_actual = None
        
        # Garantiza que existan las tablas en la BD activa
        db_path = get_db_path()
        ensure_items_schema(db_path)
```

### Paso 3: Modificar _build_ui - Reemplazar QTableWidget

**BUSCAR en _build_ui:**

```python
# --- Tabla de items de la factura ---
self.items_table = QTableWidget(0, 7)
self.items_table.setHorizontalHeaderLabels([...])
```

**REEMPLAZAR con:**

```python
# --- Tabla de items de la factura (nuevo modelo Qt) ---
self.items_table = QTableView()
self.items_table.setModel(self.items_model)
self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
self.items_table.verticalHeader().setVisible(False)
self.items_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

# Conectar señal de cambios para recalcular totales
self.items_model.dataChangedSignal.connect(self._on_items_changed)
```

### Paso 4: Agregar Método para Recalcular Totales

Agrega este método nuevo a la clase:

```python
def _on_items_changed(self):
    """Se llama cuando cambian los items para recalcular totales."""
    # Calcular total
    total = self.items_model.getTotalAmount()
    
    # Emitir señal o actualizar UI
    # (Aquí conectarías con el widget padre para actualizar totales)
    print(f"Total calculado: {total:,.2f}")
```

### Paso 5: Agregar Método para Agregar Items

**BUSCAR el botón de agregar:**

```python
self.btn_agregar.clicked.connect(self._agregar_item)
```

**Modificar el método _agregar_item:**

```python
def _agregar_item(self):
    """Agrega un item a la tabla."""
    if not self.seleccion_actual:
        QMessageBox.warning(self, "Advertencia", "Selecciona un item primero")
        return
    
    # Obtener datos del item seleccionado
    item = {
        'code': self.codigo_edit.text(),
        'description': self.nombre_edit.text(),
        'quantity': float(self.cantidad_edit.text() or 1),
        'unit': self.unidad_edit.text(),
        'unit_price': float(self.precio_edit.text() or 0),
        'discount_percent': 0.0
    }
    
    # Agregar al modelo
    self.items_model.addItem(item)
    
    # Limpiar formulario
    self.codigo_edit.clear()
    self.nombre_edit.clear()
    self.unidad_edit.clear()
    self.precio_edit.clear()
    self.cantidad_edit.clear()
    self.seleccion_actual = None
```

### Paso 6: Agregar Atajos de Teclado

Al final del método `_build_ui`, agrega:

```python
# Atajos de teclado
from PyQt6.QtGui import QShortcut, QKeySequence

# Ctrl+N: Nueva fila
shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
shortcut_new.activated.connect(lambda: self.items_model.insertRows(
    self.items_model.rowCount()
))

# Del: Eliminar fila seleccionada
shortcut_del = QShortcut(QKeySequence("Del"), self)
shortcut_del.activated.connect(self._delete_selected_row)

# Ctrl+D: Duplicar fila
shortcut_dup = QShortcut(QKeySequence("Ctrl+D"), self)
shortcut_dup.activated.connect(self._duplicate_selected_row)
```

### Paso 7: Agregar Métodos para Atajos

```python
def _delete_selected_row(self):
    """Elimina la fila seleccionada."""
    indexes = self.items_table.selectedIndexes()
    if indexes:
        row = indexes[0].row()
        self.items_model.removeRows(row, 1)

def _duplicate_selected_row(self):
    """Duplica la fila seleccionada."""
    indexes = self.items_table.selectedIndexes()
    if indexes:
        row = indexes[0].row()
        self.items_model.duplicateRow(row)
```

### Paso 8: Método para Obtener Items (Export)

Agrega o modifica:

```python
def collect_items_for_export(self):
    """Obtiene los items para exportar (compatibilidad)."""
    return self.items_model.getItems()
```

### Paso 9: Probar la Tabla de Items

1. Guarda todos los cambios
2. Ejecuta la aplicación: `python main.py`
3. Abre la vista de crear factura
4. Prueba agregar items
5. Prueba los atajos:
   - **Ctrl+N**: Debe agregar una fila vacía
   - **Del**: Debe eliminar la fila seleccionada
   - **Ctrl+D**: Debe duplicar la fila
6. Verifica que los subtotales se calculan automáticamente

---

## 📧 Integración UI - Botón Email

### Objetivo

Agregar un botón "Enviar por Email" en la vista de facturas.

### Paso 1: Configurar Email en config_facot.py

Abre `config_facot.py` y agrega al final:

```python
# --- CONFIGURACIÓN DE EMAIL ---
def get_email_config():
    """
    Obtiene configuración de email desde variables de entorno.
    
    Configura estas variables de entorno antes de usar:
    - SMTP_HOST: servidor SMTP (ej: smtp.gmail.com)
    - SMTP_PORT: puerto (ej: 587)
    - SMTP_USER: tu email
    - SMTP_PASSWORD: tu contraseña o app password
    """
    import os
    
    config = load_config()
    
    # Intentar desde config guardado, sino desde env vars
    return {
        'smtp_host': config.get('smtp_host') or os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': int(config.get('smtp_port') or os.getenv('SMTP_PORT', '587')),
        'smtp_user': config.get('smtp_user') or os.getenv('SMTP_USER', ''),
        'smtp_password': config.get('smtp_password') or os.getenv('SMTP_PASSWORD', ''),
        'use_tls': config.get('use_tls', True),
        'from_email': config.get('from_email') or os.getenv('SMTP_FROM_EMAIL', '')
    }

def save_email_config(host, port, user, password, use_tls=True, from_email=''):
    """Guarda configuración de email (sin guardar password en archivo)."""
    config = load_config()
    config['smtp_host'] = host
    config['smtp_port'] = port
    config['smtp_user'] = user
    config['use_tls'] = use_tls
    config['from_email'] = from_email
    # NO guardamos password por seguridad
    save_config(config)
```

### Paso 2: Crear Diálogo de Envío de Email

Crea un nuevo archivo: `dialogs/email_dialog.py`

```python
"""
Diálogo para enviar facturas por email.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QCheckBox,
    QMessageBox
)
from PyQt6.QtCore import Qt
import config_facot
from utils.mail_utils import EmailService


class EmailDialog(QDialog):
    """Diálogo para enviar factura por email."""
    
    def __init__(self, invoice_data, parent=None):
        super().__init__(parent)
        self.invoice_data = invoice_data
        self.setWindowTitle("Enviar Factura por Email")
        self.setMinimumWidth(500)
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Email destinatario
        layout.addWidget(QLabel("Email del destinatario:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("cliente@ejemplo.com")
        layout.addWidget(self.email_input)
        
        # Asunto
        layout.addWidget(QLabel("Asunto:"))
        self.subject_input = QLineEdit()
        default_subject = f"Factura {self.invoice_data.get('invoice_number', '')}"
        self.subject_input.setText(default_subject)
        layout.addWidget(self.subject_input)
        
        # Cuerpo del mensaje
        layout.addWidget(QLabel("Mensaje:"))
        self.body_input = QTextEdit()
        default_body = f"""
        <h2>Estimado/a Cliente</h2>
        <p>Adjunto encontrará la factura <strong>{self.invoice_data.get('invoice_number', '')}</strong></p>
        <p>Fecha: {self.invoice_data.get('invoice_date', '')}</p>
        <p>Total: {self.invoice_data.get('currency', 'RD$')} {self.invoice_data.get('total_amount', 0):,.2f}</p>
        <p>Gracias por su preferencia.</p>
        """
        self.body_input.setHtml(default_body)
        self.body_input.setMinimumHeight(200)
        layout.addWidget(self.body_input)
        
        # Checkbox para adjuntar PDF
        self.attach_pdf_checkbox = QCheckBox("Adjuntar PDF de la factura")
        self.attach_pdf_checkbox.setChecked(True)
        layout.addWidget(self.attach_pdf_checkbox)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Probar Conexión")
        self.test_btn.clicked.connect(self._test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self._send_email)
        button_layout.addWidget(self.send_btn)
        
        layout.addLayout(button_layout)
    
    def _test_connection(self):
        """Prueba la conexión SMTP."""
        email_config = config_facot.get_email_config()
        
        if not email_config['smtp_user'] or not email_config['smtp_password']:
            QMessageBox.warning(
                self,
                "Configuración Incompleta",
                "Configura las variables de entorno SMTP_USER y SMTP_PASSWORD"
            )
            return
        
        service = EmailService(email_config)
        success, message = service.test_connection()
        
        if success:
            QMessageBox.information(self, "Éxito", message)
        else:
            QMessageBox.warning(self, "Error", message)
    
    def _send_email(self):
        """Envía el email."""
        to_email = self.email_input.text().strip()
        
        if not to_email:
            QMessageBox.warning(self, "Error", "Ingresa un email destinatario")
            return
        
        if '@' not in to_email:
            QMessageBox.warning(self, "Error", "Email inválido")
            return
        
        # Obtener configuración
        email_config = config_facot.get_email_config()
        
        if not email_config['smtp_user'] or not email_config['smtp_password']:
            QMessageBox.warning(
                self,
                "Configuración Incompleta",
                "Configura las variables de entorno:\n"
                "- SMTP_USER\n"
                "- SMTP_PASSWORD\n\n"
                "En Windows: set SMTP_USER=tu@email.com\n"
                "En Linux/Mac: export SMTP_USER=tu@email.com"
            )
            return
        
        # Preparar datos
        subject = self.subject_input.text()
        body_html = self.body_input.toHtml()
        attachments = []
        
        # TODO: Agregar path del PDF si está marcado
        # if self.attach_pdf_checkbox.isChecked():
        #     pdf_path = generar_pdf_factura(self.invoice_data)
        #     attachments.append(pdf_path)
        
        # Enviar
        service = EmailService(email_config, db_path=config_facot.get_db_path())
        success, message = service.send_invoice_email(
            self.invoice_data,
            to_email,
            subject,
            body_html,
            attachments,
            invoice_id=self.invoice_data.get('id')
        )
        
        if success:
            QMessageBox.information(self, "Éxito", "Email enviado correctamente")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", f"No se pudo enviar el email:\n{message}")
```

### Paso 3: Agregar Botón en la Vista de Facturas

Si estás usando `ui_mainwindow-2.py` o similar, busca donde se muestran las facturas.

Agrega un botón:

```python
# En el método donde construyes la UI de facturas
self.send_email_btn = QPushButton("📧 Enviar por Email")
self.send_email_btn.clicked.connect(self._on_send_email_clicked)
# Agregar el botón al layout correspondiente
```

Agrega el método handler:

```python
def _on_send_email_clicked(self):
    """Abre diálogo para enviar factura por email."""
    # Obtener factura seleccionada
    selected_invoice = self._get_selected_invoice()
    
    if not selected_invoice:
        QMessageBox.warning(self, "Advertencia", "Selecciona una factura primero")
        return
    
    # Abrir diálogo
    from dialogs.email_dialog import EmailDialog
    dialog = EmailDialog(selected_invoice, self)
    dialog.exec()
```

### Paso 4: Configurar Variables de Entorno

Antes de usar el email, configura las variables de entorno:

**En Windows (CMD):**

```cmd
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USER=tu_email@gmail.com
set SMTP_PASSWORD=tu_password_o_app_password
```

**En Linux/Mac:**

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=tu_email@gmail.com
export SMTP_PASSWORD=tu_password_o_app_password
```

**Nota para Gmail:**
Si usas Gmail, necesitas crear una "App Password":
1. Ve a tu cuenta de Google
2. Seguridad → Verificación en 2 pasos
3. Contraseñas de aplicaciones
4. Genera una contraseña para "Correo"
5. Usa esa contraseña en SMTP_PASSWORD

### Paso 5: Probar el Email

1. Configura las variables de entorno
2. Ejecuta la aplicación
3. Abre una factura
4. Click en "Enviar por Email"
5. Click en "Probar Conexión" primero
6. Si funciona, ingresa un email y envía

---

## ✅ Pruebas y Validación

### Lista de Verificación

Marca cada item cuando lo compruebes:

#### Backend
- [ ] Se crean registros en `audit_log` al crear facturas
- [ ] Se crean registros en `audit_log` al editar facturas
- [ ] Se crean registros en `audit_log` al eliminar facturas
- [ ] Los NCF no se duplican (crear 5 facturas seguidas y verificar)
- [ ] Los NCF son secuenciales (B0100000001, B0100000002, etc.)

#### Tabla de Items
- [ ] Se pueden agregar items a la tabla
- [ ] Los subtotales se calculan automáticamente
- [ ] Los descuentos funcionan correctamente
- [ ] Ctrl+N agrega una fila vacía
- [ ] Del elimina la fila seleccionada
- [ ] Ctrl+D duplica la fila seleccionada
- [ ] Los totales se actualizan al editar

#### Email
- [ ] "Probar Conexión" funciona
- [ ] Se puede enviar un email de prueba
- [ ] El email se recibe correctamente
- [ ] Se registra en `email_logs`

### Pruebas Manuales Detalladas

#### Prueba 1: Crear Factura con Auditoría

1. Abre la aplicación
2. Crea una nueva factura
3. Llena todos los campos
4. Guarda la factura
5. Cierra la aplicación
6. Abre la base de datos con "DB Browser for SQLite"
7. Ve a la tabla `audit_log`
8. Verifica que hay 2 registros nuevos:
   - Uno con `action='create'` y `entity_type='invoice'`
   - Uno con `action='assign'` y `entity_type='ncf'`

#### Prueba 2: NCF Sin Duplicados

1. Crea 5 facturas seguidas rápidamente
2. Anota los números de NCF generados
3. Verifica que son secuenciales:
   - B0100000001
   - B0100000002
   - B0100000003
   - B0100000004
   - B0100000005
4. Abre la BD y cuenta cuántos NCF B01 hay
5. El número debe coincidir con las facturas creadas

#### Prueba 3: Tabla de Items

1. Abre crear factura
2. Agrega 3 items diferentes
3. Edita la cantidad de uno (debe recalcular)
4. Edita el precio de otro (debe recalcular)
5. Agrega un descuento del 10% (debe recalcular)
6. Selecciona una fila y presiona Ctrl+D (debe duplicarse)
7. Selecciona una fila y presiona Del (debe eliminarse)
8. Presiona Ctrl+N (debe agregar fila vacía)
9. Verifica que el total general es correcto

#### Prueba 4: Enviar Email

1. Configura las variables de entorno de email
2. Abre una factura existente
3. Click en "Enviar por Email"
4. Click en "Probar Conexión"
5. Si dice "Conexión exitosa", continúa
6. Ingresa tu propio email
7. Click en "Enviar"
8. Revisa tu bandeja de entrada
9. Verifica que llegó el email
10. Abre la BD y verifica registro en `email_logs`

---

## 🚨 Solución de Problemas

### Problema: ImportError al importar servicios

**Error:**
```
ImportError: cannot import name 'AuditService' from 'services.audit_service'
```

**Solución:**
1. Verifica que el archivo existe: `ls services/audit_service.py`
2. Verifica que services tiene `__init__.py`: `ls services/__init__.py`
3. Si no existe, créalo: `touch services/__init__.py`

### Problema: ModuleNotFoundError: No module named 'PyQt6'

**Solución:**
```bash
pip install PyQt6
```

### Problema: Email no se envía (Gmail)

**Error:**
```
Error de autenticación SMTP
```

**Solución:**
1. Activa verificación en 2 pasos en Google
2. Genera una "App Password"
3. Usa esa password en SMTP_PASSWORD
4. NO uses tu contraseña normal de Gmail

### Problema: La tabla no muestra los items

**Solución:**
1. Verifica que creaste el modelo: `self.items_model = ItemsTableModel()`
2. Verifica que lo conectaste a la vista: `self.items_table.setModel(self.items_model)`
3. Revisa la consola por errores

### Problema: NCF duplicados

**Posible causa:** No se está usando NCFService

**Solución:**
1. Verifica que modificaste `add_invoice` en `logic.py`
2. Verifica que se llama a `NCFService.reserve_ncf()`
3. Verifica que no quedó código antiguo de `get_next_ncf()`

### Problema: Los atajos de teclado no funcionan

**Solución:**
1. Verifica que agregaste los QShortcut
2. Verifica que el foco está en la ventana correcta
3. Prueba con la tabla seleccionada

---

## 📚 Recursos Adicionales

### Documentación de Referencia

- **AuditService:** Ver `services/audit_service.py`
- **NCFService:** Ver `services/ncf_service.py`
- **EmailService:** Ver `utils/mail_utils.py`
- **ItemsTableModel:** Ver `models/items_table_model.py`

### Tests de Ejemplo

- `tests/test_audit_log.py` - Ejemplos de cómo usar AuditService
- `tests/test_ncf_reservation.py` - Ejemplos de cómo usar NCFService
- `tests/test_mail_utils.py` - Ejemplos de cómo usar EmailService
- `tests/test_items_model.py` - Ejemplos de cómo usar ItemsTableModel

### Comandos Útiles

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Ejecutar un test específico
python -m pytest tests/test_audit_log.py -v

# Ver la base de datos
sqlite3 facot.db
.tables
SELECT * FROM audit_log LIMIT 5;
.quit

# Ver logs de email
sqlite3 facot.db
SELECT * FROM email_logs;
.quit
```

---

## ✨ Resumen

### Lo que Logramos

1. ✅ **Backend integrado** - AuditService y NCFService en logic.py
2. ✅ **Tabla moderna** - ItemsTableModel con validación automática
3. ✅ **Email funcional** - Botón para enviar facturas
4. ✅ **Atajos de teclado** - Ctrl+N, Del, Ctrl+D
5. ✅ **Auditoría completa** - Registro de todas las operaciones
6. ✅ **NCF seguro** - Sin duplicados garantizado

### Próximos Pasos

- Generar PDFs de las facturas para adjuntar en emails
- Agregar más validaciones en la UI
- Implementar reportes de auditoría
- Agregar filtros en la búsqueda de facturas

---

## 🆘 ¿Necesitas Ayuda?

Si tienes problemas:

1. Revisa la sección "Solución de Problemas"
2. Verifica los logs en la consola
3. Revisa los tests para ver ejemplos de uso
4. Consulta la documentación en los archivos .py

---

**¡Éxito con la integración!** 🎉

**Creado por:** GitHub Copilot Agent  
**Versión:** 1.0  
**Fecha:** 2025-11-09
