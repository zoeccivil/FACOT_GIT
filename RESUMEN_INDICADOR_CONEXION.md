# Indicador de Conexión - Resumen Técnico y Visual

## Vista Previa Visual

### Ventana Principal con Indicador

```
╔════════════════════════════════════════════════════════════════╗
║  FACOT - Gestión de Facturas y Cotizaciones              ▭ □ ✕ ║
╠════════════════════════════════════════════════════════════════╣
║ Archivo  Reportes  Opciones                                    ║
╠════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  Empresa: [Mi Empresa S.A.                              ▼]     ║
║                                                                 ║
║  ┌──────────────────────────────────────────────────────────┐  ║
║  │ Factura │ Cotización │ Historial Facturas │ Historial... │  ║
║  ├──────────────────────────────────────────────────────────┤  ║
║  │                                                           │  ║
║  │  [Formulario de factura/cotización]                      │  ║
║  │                                                           │  ║
║  │  Cliente: [_________________]  RNC: [___________]        │  ║
║  │                                                           │  ║
║  │  Ítems:                                                   │  ║
║  │  ┌────────────────────────────────────────────────────┐  │  ║
║  │  │ Código │ Descripción │ Cant │ Precio │ Total      │  │  ║
║  │  ├────────────────────────────────────────────────────┤  │  ║
║  │  │        │             │      │        │            │  │  ║
║  │  └────────────────────────────────────────────────────┘  │  ║
║  │                                                           │  ║
║  │                                  [Guardar] [Cancelar]    │  ║
║  └──────────────────────────────────────────────────────────┘  ║
╠════════════════════════════════════════════════════════════════╣
║  ● SQLITE  facturas_2024.db  ⚙                                 ║ ← INDICADOR
╚════════════════════════════════════════════════════════════════╝
```

### Detalle del Indicador - Estados Posibles

#### Estado 1: SQLite con Internet

```
╔════════════════════════════════════════════════╗
║  🔵 SQLITE  SQLite (Online): facturas.db  ⚙   ║
╚════════════════════════════════════════════════╝
     │        │                              │
     │        │                              └─ Botón opciones
     │        └─ Modo actual
     └─ Indicador azul (SQLite + online)
```

#### Estado 2: SQLite sin Internet

```
╔════════════════════════════════════════════════╗
║  ⚫ SQLITE  SQLite (Offline): facturas.db  ⚙  ║
╚════════════════════════════════════════════════╝
     │
     └─ Indicador gris (SQLite + offline)
```

#### Estado 3: Firebase con Internet

```
╔════════════════════════════════════════════════╗
║  🟢 FIREBASE  Conectado a Firebase  ⚙         ║
╚════════════════════════════════════════════════╝
     │
     └─ Indicador verde (Firebase + online)
```

#### Estado 4: Firebase sin Internet

```
╔════════════════════════════════════════════════╗
║  🟠 FIREBASE  Firebase (sin conexión)  ⚙      ║
╚════════════════════════════════════════════════╝
     │
     └─ Indicador naranja (Firebase + offline)
```

#### Estado 5: Modo AUTO con Internet

```
╔════════════════════════════════════════════════╗
║  🟢 AUTO  AUTO → Firebase  ⚙                   ║
╚════════════════════════════════════════════════╝
```

#### Estado 6: Modo AUTO sin Internet

```
╔════════════════════════════════════════════════╗
║  🔵 AUTO  AUTO → SQLite: facturas.db  ⚙       ║
╚════════════════════════════════════════════════╝
```

## Menú Contextual

### Desde Modo SQLite

```
Click en ⚙:

┌─────────────────────────────────────┐
│ 📂 Cambiar base de datos...        │
│ ➕ Crear nueva base de datos...    │
├─────────────────────────────────────┤
│ ☁️  Cambiar a Firebase              │
│ 🔄 Modo AUTO (Firebase/SQLite)     │
└─────────────────────────────────────┘
```

### Desde Modo Firebase

```
Click en ⚙:

┌─────────────────────────────────────┐
│ 💾 Cambiar a SQLite...              │
│ �� Modo AUTO (Firebase/SQLite)     │
└─────────────────────────────────────┘
```

### Desde Modo AUTO

```
Click en ⚙:

┌─────────────────────────────────────┐
│ 💾 Forzar SQLite...                 │
│ ☁️  Forzar Firebase                 │
└─────────────────────────────────────┘
```

## Flujo de Uso

### Escenario 1: Cambiar de Base de Datos

```
Paso 1: Usuario ve
╔═══════════════════════════════════╗
║  ● SQLITE  facturas_2024.db  ⚙   ║
╚═══════════════════════════════════╝

Paso 2: Click en ⚙ → "Cambiar base de datos..."

Paso 3: Diálogo de selección de archivo
┌─────────────────────────────────────────┐
│ Seleccionar Base de Datos SQLite        │
├─────────────────────────────────────────┤
│ 📁 Mis Documentos                       │
│   📄 facturas_2023.db                   │
│   📄 facturas_2024.db                   │
│   📄 proyecto_especial.db       [Abrir] │
└─────────────────────────────────────────┘

Paso 4: Resultado
╔════════════════════════════════════════════╗
║  ● SQLITE  proyecto_especial.db  ⚙       ║
╚════════════════════════════════════════════╝

┌─────────────────────────────────────────┐
│ Base de Datos                    ℹ      │
├─────────────────────────────────────────┤
│ Base de datos cambiada exitosamente:   │
│ proyecto_especial.db                    │
│                                         │
│                         [OK]            │
└─────────────────────────────────────────┘
```

### Escenario 2: Cambiar a Firebase

```
Paso 1: Usuario ve (con internet)
╔════════════════════════════════════╗
║  🔵 SQLITE  facturas.db  ⚙        ║
╚════════════════════════════════════╝

Paso 2: Click en ⚙ → "Cambiar a Firebase"

Paso 3: Confirmación
┌─────────────────────────────────────────┐
│ Modo de Conexión                 ℹ      │
├─────────────────────────────────────────┤
│ Modo de conexión cambiado a: FIREBASE  │
│                                         │
│ La aplicación ahora usará FIREBASE     │
│ para acceder a los datos.              │
│                                         │
│                         [OK]            │
└─────────────────────────────────────────┘

Paso 4: Resultado
╔════════════════════════════════════╗
║  🟢 FIREBASE  Conectado a Fireb... ║
╚════════════════════════════════════╝
```

### Escenario 3: Detección de Pérdida de Internet

```
Antes (con internet):
╔════════════════════════════════════╗
║  🟢 FIREBASE  Conectado a Fireb... ║
╚════════════════════════════════════╝

Después (sin internet):
╔════════════════════════════════════╗
║  🟠 FIREBASE  Firebase (sin conex  ║
╚════════════════════════════════════╝
     │
     └─ Cambio automático de color
```

## Código de Ejemplo

### Configurar el Indicador

```python
# En MainWindow.__init__()

# 1. Crear barra de estado
status_bar = QStatusBar()
self.setStatusBar(status_bar)

# 2. Crear widget de conexión
self.connection_status = ConnectionStatusBar(self)

# 3. Configurar estado inicial
db_path = facot_config.get_db_path()
self.connection_status.set_mode("SQLITE", db_path)

# 4. Agregar a barra de estado
status_bar.addPermanentWidget(self.connection_status)
```

### Manejar Cambio de Base de Datos

```python
# Conectar señal
self.connection_status.database_changed.connect(
    self._on_database_changed
)

def _on_database_changed(self, new_db_path: str):
    # Actualizar configuración
    facot_config.set_db_path(new_db_path)
    
    # Recrear LogicController
    self.logic = LogicController(new_db_path)
    
    # Actualizar toda la UI
    self._populate_companies()
    self.invoice_tab.logic = self.logic
    # ... etc
```

### Manejar Cambio de Modo

```python
# Conectar señal
self.connection_status.mode_changed.connect(
    self._on_connection_mode_changed
)

def _on_connection_mode_changed(self, new_mode: str):
    from data_access import set_data_access_mode, DataAccessMode
    
    mode_map = {
        "SQLITE": DataAccessMode.SQLITE,
        "FIREBASE": DataAccessMode.FIREBASE,
        "AUTO": DataAccessMode.AUTO
    }
    
    set_data_access_mode(mode_map[new_mode])
```

## Estructura de Archivos

```
FACOT/
├── widgets/
│   ├── __init__.py
│   └── connection_status_bar.py    # Widget del indicador
│
├── ui_mainwindow.py                 # Integración en ventana principal
│
├── INDICADOR_CONEXION.md           # Guía de usuario (español)
└── RESUMEN_INDICADOR_CONEXION.md   # Este archivo
```

## Características Técnicas

### Detección de Internet

```python
def _check_online_status(self):
    self.network_manager = QNetworkAccessManager(self)
    self.network_manager.finished.connect(
        self._on_network_check_finished
    )
    
    request = QNetworkRequest(QUrl("https://www.google.com"))
    request.setTransferTimeout(3000)  # 3 segundos
    self.network_manager.get(request)

def _on_network_check_finished(self, reply):
    is_online = (reply.error() == 0)
    self.connection_status.set_online_status(is_online)
```

### Signals/Slots

```python
class ConnectionStatusBar(QWidget):
    # Señales
    database_changed = pyqtSignal(str)  # Nueva ruta BD
    mode_changed = pyqtSignal(str)      # Nuevo modo
    
    # Métodos públicos
    def set_mode(self, mode: str, db_path: str = None)
    def set_online_status(self, is_online: bool)
```

## Beneficios

### Para el Usuario

1. **Visibilidad:** Siempre sabe dónde están sus datos
2. **Control:** Cambia fácilmente entre bases
3. **Seguridad:** Ve si está online/offline
4. **Flexibilidad:** Múltiples bases de datos sin cerrar app

### Para el Desarrollador

1. **Modular:** Widget independiente reutilizable
2. **Extensible:** Fácil agregar nuevos modos
3. **Mantenible:** Lógica centralizada
4. **Testeable:** Signals/slots bien definidos

## Próximas Mejoras

Posibles mejoras futuras:

1. **Sincronización Visual:** Mostrar progreso de sync Firebase
2. **Notificaciones:** Alertas de cambio de estado
3. **Historial:** Lista de bases recientes
4. **Favoritos:** Marcar bases frecuentes
5. **Estadísticas:** Mostrar tamaño de BD, registros, etc.

---

**Fecha:** 2025-11-08  
**Versión:** 1.0  
**Estado:** ✅ Implementado y Documentado
