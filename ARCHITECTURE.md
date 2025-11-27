# Arquitectura del Sistema FACOT

## 📐 Visión General

FACOT es una aplicación de escritorio construida en Python que utiliza una arquitectura en capas con soporte para múltiples backends de datos (SQLite local y Firebase cloud).

## 🏗️ Arquitectura en Capas

```
┌─────────────────────────────────────────────────────┐
│              CAPA DE PRESENTACIÓN (UI)              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ MainWindow   │  │   Dialogs    │  │  Widgets  │ │
│  │ (PyQt6/Tk)   │  │  (Ventanas)  │  │  (Custom) │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│            CAPA DE LÓGICA DE NEGOCIO                │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │    Logic     │  │   Services   │  │ Utilities │ │
│  │ Controller   │  │  (Business)  │  │  (Helpers)│ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│          CAPA DE ACCESO A DATOS (DAL)               │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   SQLite     │  │   Firebase   │  │  Factory  │ │
│  │ DataAccess   │  │ DataAccess   │  │  (Pattern)│ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              CAPA DE PERSISTENCIA                   │
│  ┌──────────────┐              ┌──────────────────┐ │
│  │   SQLite DB  │              │  Firebase Cloud  │ │
│  │  (Local)     │              │  (Firestore)     │ │
│  └──────────────┘              └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 📦 Componentes Principales

### 1. Capa de Presentación (UI)

#### main.py
- **Responsabilidad**: Punto de entrada de la aplicación
- **Funciones clave**:
  - Inicialización de la aplicación
  - Selección de base de datos
  - Configuración del tema visual

#### ui_mainwindow.py
- **Responsabilidad**: Ventana principal de la aplicación
- **Componentes**:
  - Dashboard con estadísticas
  - Selector de empresa
  - Filtros de fecha y tipo
  - Árbol de facturas (Treeview)
  - Panel de resumen
  - Menús y toolbar

#### dialogs/
Ventanas de diálogo especializadas:

```
dialogs/
├── invoice_preview_dialog.py      # Vista previa de facturas
├── quotation_preview_dialog.py    # Vista previa de cotizaciones
├── add_invoice_window.py          # Crear/editar facturas
├── report_window.py               # Generación de reportes
├── tax_calculation_window.py      # Cálculo de impuestos
└── attachment_editor_window.py    # Editor de anexos
```

#### widgets/
Componentes UI reutilizables:

```
widgets/
├── connection_status_bar.py       # Barra de estado de conexión
├── enhanced_items_table.py        # Tabla mejorada de items
└── mini_calculator.py             # Calculadora integrada
```

### 2. Capa de Lógica de Negocio

#### logic.py (LogicController)
**El cerebro de la aplicación**

```python
class LogicController:
    """
    Controlador principal que maneja toda la lógica de negocio.
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._initialize_db()
    
    # Métodos principales:
    # - Gestión de empresas
    # - CRUD de facturas
    # - Cálculos de impuestos
    # - Generación de reportes
    # - Gestión de configuración
```

**Responsabilidades**:
- Gestión de conexión a BD
- Operaciones CRUD (Create, Read, Update, Delete)
- Validaciones de negocio
- Cálculos de impuestos y totales
- Migración de datos

#### services/
Servicios especializados del sistema:

##### company_profile_service.py
```python
class CompanyProfileService:
    """
    Servicio centralizado para gestión de datos de empresa.
    """
    # Funcionalidades:
    # - Resolución de logos con fallback
    # - Normalización de direcciones
    # - Gestión de firmas autorizadas
    # - Caché en memoria
```

##### unit_resolver.py
```python
class UnitResolver:
    """
    Resolución inteligente de unidades para items.
    """
    # Prioridad:
    # 1. Valor existente
    # 2. Búsqueda por código
    # 3. Búsqueda por nombre (fuzzy)
    # 4. Fallback a "UND"
```

### 3. Capa de Acceso a Datos

#### Patrón Factory

```python
# data_access/data_access_factory.py
def get_data_access(logic=None, mode=DataAccessMode.AUTO, user_id=None):
    """
    Factory que retorna la implementación apropiada de data access.
    
    Modos:
    - AUTO: Intenta Firebase, fallback a SQLite
    - SQLITE: Fuerza uso de SQLite
    - FIREBASE: Fuerza uso de Firebase
    """
    if mode == DataAccessMode.FIREBASE:
        return FirebaseDataAccess(user_id)
    elif mode == DataAccessMode.SQLITE:
        return SQLiteDataAccess(logic)
    else:  # AUTO
        try:
            return FirebaseDataAccess(user_id)
        except:
            return SQLiteDataAccess(logic)
```

#### SQLiteDataAccess
```python
class SQLiteDataAccess:
    """
    Implementación de acceso a datos usando SQLite local.
    """
    # Ventajas:
    # - Trabajo offline
    # - No requiere internet
    # - Rápido para operaciones locales
    # - Archivo único portátil
```

#### FirebaseDataAccess
```python
class FirebaseDataAccess:
    """
    Implementación de acceso a datos usando Firebase Firestore.
    """
    # Ventajas:
    # - Trabajo en la nube
    # - Multi-usuario
    # - Sincronización automática
    # - Backup automático
    # - Acceso desde cualquier lugar
```

## 🗄️ Modelo de Datos

### Esquema de Base de Datos

#### Tabla: companies
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    rnc TEXT UNIQUE NOT NULL,
    address TEXT,
    invoice_template_path TEXT,
    invoice_output_base_path TEXT,
    itbis_adelantado REAL DEFAULT 0.0,
    legacy_filename TEXT
);
```

#### Tabla: invoices
```sql
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    invoice_type TEXT NOT NULL,  -- 'emitida' o 'gasto'
    invoice_date TEXT NOT NULL,
    imputation_date TEXT,
    invoice_number TEXT NOT NULL,
    invoice_category TEXT,  -- B01, B02, etc.
    rnc TEXT NOT NULL,
    third_party_name TEXT NOT NULL,
    currency TEXT NOT NULL,  -- RD$, USD, EUR
    itbis REAL NOT NULL DEFAULT 0.0,
    total_amount REAL NOT NULL DEFAULT 0.0,
    exchange_rate REAL NOT NULL DEFAULT 1.0,
    total_amount_rd REAL NOT NULL DEFAULT 0.0,
    attachment_path TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX idx_unique_invoice 
ON invoices (company_id, rnc, invoice_number);
```

#### Tabla: invoice_items
```sql
CREATE TABLE invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0.0,
    unit_price REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
```

#### Tabla: third_parties (Directorio)
```sql
CREATE TABLE third_parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rnc TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);
```

#### Tabla: tax_calculations
```sql
CREATE TABLE tax_calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    percent_to_pay REAL NOT NULL,
    notes TEXT,
    start_date TEXT,
    end_date TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
```

### Relaciones

```
companies (1) ──────< (N) invoices
                        │
                        └──────< (N) invoice_items

companies (1) ──────< (N) tax_calculations
                        │
                        └──────< (N) tax_calculation_details
                                  │
                                  └─────> (1) invoices
```

## 🔄 Flujo de Datos

### Ejemplo: Crear una Factura

```
1. Usuario ingresa datos en AddInvoiceWindow
                ↓
2. Valida datos en el frontend
                ↓
3. Envía a LogicController.add_invoice()
                ↓
4. LogicController valida negocio
                ↓
5. Inicia transacción en BD
                ↓
6. Inserta en tabla invoices
                ↓
7. Inserta items en invoice_items
                ↓
8. Commit de transacción
                ↓
9. Retorna ID de factura
                ↓
10. UI actualiza dashboard
```

### Ejemplo: Generar Reporte PDF

```
1. Usuario selecciona mes/año en ReportWindow
                ↓
2. Llama a LogicController.get_monthly_report_data()
                ↓
3. LogicController consulta BD
                ↓
4. Retorna datos agrupados y totalizados
                ↓
5. ReportWindow llama a report_generator.generate_professional_pdf()
                ↓
6. report_generator:
   - Crea PDF con FPDF
   - Agrega resumen
   - Agrega tablas de facturas
   - Adjunta comprobantes (si existen)
                ↓
7. Guarda PDF en disco
                ↓
8. Abre PDF con visor predeterminado
```

## 🎨 Patrones de Diseño Utilizados

### 1. Singleton
- **config_manager.py**: Configuración global única

### 2. Factory
- **data_access_factory.py**: Creación de objetos DataAccess

### 3. Service Layer
- **services/**: Lógica de negocio encapsulada

### 4. Repository (implícito)
- **LogicController**: Abstrae acceso a datos

### 5. Observer (implícito)
- **UI**: Escucha cambios y actualiza

## 🔐 Seguridad

### Validaciones

```python
# 1. Validación de entrada
def add_invoice(self, invoice_data, items_data):
    # Valida RNC
    if not invoice_data.get("rnc"):
        raise ValueError("RNC es requerido")
    
    # Valida montos
    if invoice_data.get("total_amount", 0) < 0:
        raise ValueError("Monto no puede ser negativo")
```

### Integridad Referencial

```sql
-- Constraints en BD
FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE

-- Índices únicos
CREATE UNIQUE INDEX idx_unique_invoice 
ON invoices (company_id, rnc, invoice_number);
```

### Firebase Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Autenticación requerida
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
    
    // Filtrado por company_id
    match /invoices/{invoice} {
      allow read: if request.auth != null 
        && resource.data.company_id == request.auth.uid;
    }
  }
}
```

## 📊 Rendimiento

### Optimizaciones Implementadas

1. **Índices en BD**
```sql
CREATE INDEX idx_invoices_company_date ON invoices(company_id, invoice_date);
CREATE INDEX idx_invoices_rnc ON invoices(rnc);
CREATE INDEX idx_items_invoice ON invoice_items(invoice_id);
```

2. **Caché en Memoria**
```python
# CompanyProfileService
self._cache = {}  # Caché de perfiles de empresa

# UnitResolver
self._unit_cache = {}  # Caché de unidades
```

3. **Batch Operations**
```python
# Inserción masiva de items
cursor.executemany("""
    INSERT INTO invoice_items (invoice_id, description, quantity, unit_price)
    VALUES (?, ?, ?, ?)
""", items_batch)
```

## 🧩 Extensibilidad

### Agregar un Nuevo Tipo de Reporte

```python
# 1. Crear función en report_generator.py
def generate_custom_report(data, save_path):
    # Lógica del reporte
    pass

# 2. Agregar opción en ReportWindow
def _on_generate_custom(self):
    data = self.controller.get_custom_data()
    success, msg = generate_custom_report(data, path)
```

### Agregar un Nuevo Backend de Datos

```python
# 1. Crear clase en data_access/
class MongoDBDataAccess(AbstractDataAccess):
    def get_invoices(self, company_id, filters):
        # Implementación específica de MongoDB
        pass

# 2. Registrar en factory
def get_data_access(mode):
    if mode == DataAccessMode.MONGODB:
        return MongoDBDataAccess()
```

## 🔧 Configuración

### config_facot.py
```python
# Configuración global centralizada
CONFIG = {
    'database_path': '',
    'carpeta_destino': '',
    'downloads_folder_path': '',
    'invoice_output_base_path': '',
    'empresas': {
        'RNC123': {
            'nombre': 'Empresa Ejemplo',
            'ruta_plantilla': '',
            'carpeta_salida': ''
        }
    }
}
```

## 📈 Métricas del Sistema

```
Líneas de Código:
- logic.py:              ~1,200 líneas
- ui_mainwindow.py:      ~3,600 líneas
- services/:             ~500 líneas
- data_access/:          ~1,400 líneas
- dialogs/:              ~2,000 líneas

Archivos Totales:        32+ archivos
Complejidad:             Media-Alta
Mantenibilidad:          Alta (arquitectura en capas)
```

## 🚀 Próximas Mejoras Arquitectónicas

1. **Separación UI/Logic más estricta**
   - Implementar patrón MVP/MVVM
   - Eliminar dependencias directas de UI en Logic

2. **Event Bus**
   - Sistema de eventos desacoplado
   - Comunicación asíncrona entre componentes

3. **Dependency Injection**
   - Inyección de dependencias formal
   - Mejor testabilidad

4. **Async/Await**
   - Operaciones asíncronas para Firebase
   - UI más responsiva

5. **Tests Unitarios**
   - Suite completa de tests
   - Integración continua (CI/CD)

---

**Última Actualización:** 2025-11-09
**Versión:** 2.0
