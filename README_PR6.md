# FACOT - PR6: Migración a Firebase

## Descripción General

Este PR implementa la migración completa de FACOT de SQLite a Firebase, proporcionando una arquitectura moderna, escalable y multi-usuario.

## ¿Qué es Firebase?

Firebase es una plataforma de Google que proporciona:
- **Firestore**: Base de datos en la nube (NoSQL)
- **Storage**: Almacenamiento de archivos (logos, PDFs, etc.)
- **Auth**: Autenticación de usuarios

## Características Principales

### 1. Capa de Abstracción de Datos

**Problema anterior:** Código acoplado directamente a SQLite

**Solución:** Interfaz `DataAccess` con dos implementaciones:
- `SQLiteDataAccess` - Mantiene compatibilidad con BD actual
- `FirebaseDataAccess` - Nueva implementación en la nube

### 2. Modo Dual (SQLite + Firebase)

La aplicación puede funcionar con:
- **Solo SQLite** (actual, sin cambios)
- **Solo Firebase** (nuevo, en la nube)
- **AUTO** (intenta Firebase, fallback a SQLite)

### 3. Multi-Usuario

Firebase permite múltiples usuarios trabajando simultáneamente:
- Autenticación con email/password
- Datos separados por empresa (`company_id`)
- Auditoría de cambios (quién y cuándo)

## Instalación

### Requisitos

```bash
pip install firebase-admin
```

### Configuración Firebase

1. **Crear proyecto en Firebase Console:**
   - Ir a https://console.firebase.google.com
   - Crear nuevo proyecto "FACOT"
   - Activar Firestore y Storage

2. **Obtener credenciales:**
   - En Configuración del Proyecto → Cuentas de servicio
   - Generar nueva clave privada
   - Descargar archivo JSON

3. **Colocar credenciales:**
   - Opción A: Guardar como `firebase-credentials.json` en directorio de FACOT
   - Opción B: Definir variable de entorno `FIREBASE_CREDENTIALS_PATH`
   - Opción C: Guardar en `%APPDATA%\FACOT\firebase-credentials.json`

### Configuración de Reglas de Seguridad

Subir el archivo `firestore.rules` a Firebase Console:
1. Firestore Database → Reglas
2. Copiar contenido de `firestore.rules`
3. Publicar

## Uso

### Modo Básico (AUTO)

```python
from data_access import get_data_access

# Intenta Firebase, si no disponible usa SQLite
data_access = get_data_access(logic_controller=logic)

# Usar normalmente
companies = data_access.get_all_companies()
data_access.add_invoice(invoice_data, items)
```

### Forzar SQLite

```python
from data_access import get_data_access, DataAccessMode

data_access = get_data_access(
    logic_controller=logic,
    mode=DataAccessMode.SQLITE
)
```

### Forzar Firebase

```python
from data_access import get_data_access, DataAccessMode

data_access = get_data_access(
    user_id="usuario@example.com",
    mode=DataAccessMode.FIREBASE
)
```

### Configurar Modo Global

```python
from data_access import set_data_access_mode, DataAccessMode

# Toda la aplicación usará Firebase
set_data_access_mode(DataAccessMode.FIREBASE)
```

## Migración de Datos

### Migrar SQLite → Firebase

```bash
# Modo de prueba (sin cambios reales)
python migrate_sqlite_to_firebase.py --dry-run

# Migración real
python migrate_sqlite_to_firebase.py --db ruta/a/tu/base.db
```

El script migra:
- ✓ Empresas (companies)
- ✓ Ítems (items)
- ✓ Facturas con ítems (invoices + items)
- ✓ Cotizaciones con ítems (quotations + items)

### Verificación Post-Migración

1. Abrir Firebase Console
2. Ir a Firestore Database
3. Verificar que existen las colecciones:
   - `companies`
   - `items`
   - `invoices`
   - `quotations`

## Estructura de Datos en Firestore

```
companies/{company_id}
  - name, rnc, address, phone, email, etc.

items/{item_id}
  - code, name, unit, price, cost

invoices/{invoice_id}
  - company_id, invoice_date, client_name, total_amount, etc.
  /items/{item_index}
    - description, quantity, unit_price, unit

quotations/{quotation_id}
  - company_id, quotation_date, client_name, total_amount, etc.
  /items/{item_index}
    - description, quantity, unit_price, unit

sequences/{company_id}_ncf_{ncf_type}
  - current (contador para NCF)

audit_logs/{log_id}
  - user_id, action, timestamp, document_id, before, after
```

## Ventajas de Firebase

### 1. Acceso Desde Cualquier Lugar
- Los datos están en la nube
- Acceso desde múltiples dispositivos
- Sincronización automática

### 2. Backup Automático
- Google maneja los respaldos
- Alta disponibilidad
- Recuperación ante desastres

### 3. Multi-Usuario
- Varios usuarios simultáneamente
- Auditoría de cambios
- Control de permisos

### 4. Escalabilidad
- Soporta millones de documentos
- Sin límites de almacenamiento
- Rendimiento constante

## Comparación SQLite vs Firebase

| Característica | SQLite | Firebase |
|----------------|--------|----------|
| Ubicación | Local (archivo .db) | Nube (Google) |
| Multi-usuario | No | Sí |
| Acceso remoto | No | Sí |
| Backup | Manual | Automático |
| Escalabilidad | Limitada | Ilimitada |
| Costo | Gratis | Gratis hasta 1GB |

## Seguridad

### Reglas de Firestore

Las reglas en `firestore.rules` garantizan:
- Solo usuarios autenticados pueden acceder
- Datos filtrados por `company_id`
- Logs de auditoría inmutables
- Lectura pública solo para ítems

### Autenticación

Firebase Auth proporciona:
- Email/Password
- Google Sign-In (opcional)
- Tokens seguros
- Sesiones gestionadas

## Preguntas Frecuentes

**¿Puedo seguir usando SQLite?**
Sí, la aplicación funciona con SQLite sin cambios.

**¿Se borran mis datos de SQLite?**
No, SQLite queda intacto. La migración solo COPIA a Firebase.

**¿Qué pasa si no tengo internet?**
En modo AUTO, la app usará SQLite automáticamente.

**¿Cuánto cuesta Firebase?**
- Gratis hasta 1GB de datos
- Gratis hasta 20,000 escrituras/día
- Suficiente para la mayoría de usuarios

**¿Puedo volver a SQLite después?**
Sí, solo cambia el modo a `SQLITE`.

## Solución de Problemas

### Error: "Firebase no está disponible"
- Verificar que `pip install firebase-admin` fue ejecutado
- Verificar que archivo de credenciales existe
- Verificar variable de entorno `FIREBASE_CREDENTIALS_PATH`

### Error: "Permission denied"
- Verificar reglas de seguridad en Firebase Console
- Verificar que usuario está autenticado
- Revisar `firestore.rules`

### Migración falla
- Ejecutar con `--dry-run` primero
- Verificar conexión a internet
- Revisar logs para detalles del error

## Próximos Pasos

Después de PR6:
- PR7: Reportes y utilidades
- PR8: Empaquetado e instalador
- PR9: Documentación de usuario final

## Soporte

Para dudas o problemas:
1. Revisar esta documentación
2. Ejecutar migración en modo `--dry-run`
3. Verificar configuración de Firebase
4. Revisar logs de la aplicación

---

**Última actualización:** 2025-11-08
**Versión:** 1.0
