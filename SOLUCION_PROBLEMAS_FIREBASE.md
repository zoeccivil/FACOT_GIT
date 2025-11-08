# Solución de Problemas: Conexión a Firebase

**Versión:** 1.0  
**Última actualización:** 2025-11-08

Este documento explica cómo diagnosticar y solucionar problemas comunes de conexión a Firebase en FACOT.

---

## 📋 Índice

1. [Problemas Comunes](#problemas-comunes)
2. [Diagnóstico Paso a Paso](#diagnóstico-paso-a-paso)
3. [Verificación de Configuración](#verificación-de-configuración)
4. [Logs y Mensajes de Error](#logs-y-mensajes-de-error)
5. [Soluciones Específicas](#soluciones-específicas)

---

## 🔧 Problemas Comunes

### Problema 1: Widget Muestra "Sin Conexión" Pero Firebase Está Conectado

**Síntomas:**
- Widget en barra de estado muestra "sin conexión" o modo incorrecto
- Firebase está configurado y funcional
- Logs muestran "Firebase inicializado correctamente"

**Causa:**
El widget no detectaba correctamente el estado de Firebase.

**Solución (IMPLEMENTADA en commit d575e61):**
✅ El widget ahora verifica automáticamente el estado de Firebase
✅ Método `_verify_firebase_connection()` agregado
✅ Detección automática al cambiar de modo

**Verificación:**
```
1. Iniciar aplicación
2. Revisar consola - debe mostrar:
   [MAIN] Detected Firebase mode - updating status bar
   [CONNECTION_STATUS] Firebase is available
3. Widget debe mostrar: 🟢 FIREBASE  Conectado a Firebase
```

---

### Problema 2: Solo Carga Empresas, No Otros Datos

**Síntomas:**
- El dropdown de empresas se llena correctamente
- No se cargan ítems, facturas u otros datos
- Error al intentar crear factura o cotización

**Causa:**
El código usaba `self.logic` directamente en lugar de `self.data_access`.

**Solución (IMPLEMENTADA en commit d575e61):**
✅ `MainWindow` ahora usa `self.data_access` consistentemente
✅ Método `_populate_companies()` actualizado
✅ Cambio de modo recrea `data_access` correctamente

**Verificación:**
```python
# En la consola Python:
from ui_mainwindow import MainWindow
window = MainWindow()
print(window.data_access)  # Debe mostrar FirebaseDataAccess o SQLiteDataAccess
```

---

### Problema 3: Estado Inconsistente al Cambiar Modos

**Síntomas:**
- Cambiar de SQLite a Firebase no surte efecto
- Widget muestra un modo pero usa otro
- Datos no se recargan después de cambiar

**Causa:**
No se recreaba la instancia de `data_access` al cambiar modos.

**Solución (IMPLEMENTADA en commit d575e61):**
✅ `_on_connection_mode_changed()` recrea `data_access`
✅ Recarga empresas automáticamente
✅ Actualiza widget de estado

**Verificación:**
```
1. Click en ⚙ → "Cambiar a Firebase"
2. Debe aparecer mensaje: "Modo de conexión cambiado a: FIREBASE"
3. Widget debe actualizarse inmediatamente
4. Dropdown de empresas debe recargarse
```

---

## 🔍 Diagnóstico Paso a Paso

### Paso 1: Verificar Instalación de Firebase Admin

```bash
# En terminal/consola:
pip show firebase-admin

# Debe mostrar:
# Name: firebase-admin
# Version: 6.x.x o superior
```

**Si no está instalado:**
```bash
pip install firebase-admin
```

---

### Paso 2: Verificar Archivo de Credenciales

**Ubicaciones buscadas (en orden):**
1. Variable `FIREBASE_CREDENTIALS_PATH`
2. Variable `GOOGLE_APPLICATION_CREDENTIALS`
3. `firebase-credentials.json` en directorio actual
4. `firebase-credentials.json` en `%APPDATA%\FACOT\`

**Verificar manualmente:**
```python
import os

# Método 1: Variable de entorno
print(os.getenv("FIREBASE_CREDENTIALS_PATH"))

# Método 2: Archivo local
print(os.path.exists("firebase-credentials.json"))

# Método 3: APPDATA
appdata = os.getenv("APPDATA")
facot_cred = os.path.join(appdata, "FACOT", "firebase-credentials.json")
print(os.path.exists(facot_cred))
```

**Contenido esperado del archivo:**
```json
{
  "type": "service_account",
  "project_id": "tu-proyecto-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "...",
  "client_id": "...",
  ...
}
```

---

### Paso 3: Verificar Inicialización de Firebase

**Ejecutar en consola Python:**
```python
from firebase import get_firebase_client

client = get_firebase_client()
print(client.is_available())  # Debe ser True

db = client.get_firestore()
print(db)  # Debe mostrar <google.cloud.firestore_v1.client.Client object>
```

**Logs esperados:**
```
[FIREBASE] ✓ Inicializado correctamente
[FIREBASE]   Credenciales: C:\path\to\firebase-credentials.json
[FIREBASE]   Storage Bucket: tu-proyecto.appspot.com
```

---

### Paso 4: Verificar Conexión a Firestore

**Probar lectura de colección:**
```python
from firebase import get_firebase_client

client = get_firebase_client()
db = client.get_firestore()

# Intentar leer companies
companies_ref = db.collection('companies')
docs = companies_ref.limit(5).stream()

for doc in docs:
    print(f"Company: {doc.id} - {doc.to_dict()}")
```

**Si falla:**
- Verificar reglas de seguridad en Firebase Console
- Verificar que la colección `companies` existe
- Verificar permisos de la cuenta de servicio

---

### Paso 5: Verificar Modo en Aplicación

**En la aplicación FACOT:**
```
1. Iniciar aplicación
2. Revisar widget en barra de estado (esquina inferior)
3. Debe mostrar uno de:
   🟢 FIREBASE  Conectado a Firebase
   🔵 SQLITE  SQLite (Online): archivo.db
   🔄 AUTO → Firebase
```

**Si muestra modo incorrecto:**
```python
# En consola Python con app abierta:
from data_access import get_current_mode
print(get_current_mode())  # SQLITE, FIREBASE o AUTO
```

---

## ⚙️ Verificación de Configuración

### Checklist Completo

- [ ] **Firebase Admin instalado**
  ```bash
  pip show firebase-admin
  ```

- [ ] **Archivo de credenciales existe**
  ```bash
  # Windows
  dir firebase-credentials.json
  
  # Linux/Mac
  ls firebase-credentials.json
  ```

- [ ] **Credenciales válidas**
  ```python
  import json
  with open('firebase-credentials.json') as f:
      cred = json.load(f)
      print(cred.get('project_id'))  # Debe mostrar tu proyecto
  ```

- [ ] **Firebase inicializado**
  ```python
  from firebase import get_firebase_client
  client = get_firebase_client()
  print(client.is_available())  # True
  ```

- [ ] **Firestore accesible**
  ```python
  db = client.get_firestore()
  print(db.collection('companies').limit(1).get())
  ```

- [ ] **Reglas de seguridad configuradas**
  - Ir a Firebase Console → Firestore → Rules
  - Verificar que permiten acceso a companies

- [ ] **Widget muestra estado correcto**
  - Iniciar FACOT
  - Verificar barra de estado inferior

---

## 📝 Logs y Mensajes de Error

### Logs Normales (Todo Funciona)

```
[FIREBASE] ✓ Inicializado correctamente
[FIREBASE]   Credenciales: C:\Users\...\firebase-credentials.json
[FIREBASE]   Storage Bucket: facot-project.appspot.com
[DATA_ACCESS] Usando Firebase
[MAIN] Detected Firebase mode - updating status bar
[CONNECTION_STATUS] Firebase is available
```

### Logs de Problemas

**Problema: Firebase no inicializado**
```
[FIREBASE] ⚠️ No se encontró archivo de credenciales Firebase
[FIREBASE] Configurar FIREBASE_CREDENTIALS_PATH o colocar firebase-credentials.json
```

**Solución:**
- Colocar `firebase-credentials.json` en directorio de la app
- O configurar variable de entorno `FIREBASE_CREDENTIALS_PATH`

---

**Problema: Firebase no disponible**
```
[FIREBASE] Firebase no disponible
[DATA_ACCESS] AUTO: Firebase no disponible (...)
[DATA_ACCESS] AUTO: Usando SQLite (fallback)
```

**Solución:**
- Verificar que firebase-admin está instalado
- Verificar archivo de credenciales
- Revisar logs de inicialización

---

**Problema: Error al leer Firestore**
```
[FIREBASE] Error getting companies: [PERMISSION_DENIED] ...
```

**Solución:**
- Verificar reglas de seguridad en Firebase Console
- Verificar que cuenta de servicio tiene permisos
- Verificar que colección 'companies' existe

---

## 🔨 Soluciones Específicas

### Solución 1: Reinstalar Firebase Admin

```bash
pip uninstall firebase-admin
pip install firebase-admin --upgrade
```

### Solución 2: Regenerar Credenciales

1. Ir a Firebase Console
2. Project Settings → Service Accounts
3. Generate New Private Key
4. Descargar archivo JSON
5. Renombrar a `firebase-credentials.json`
6. Colocar en directorio de FACOT

### Solución 3: Verificar Reglas de Firestore

En Firebase Console → Firestore → Rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Permitir lectura de companies (temporalmente)
    match /companies/{companyId} {
      allow read: if true;  // SOLO PARA PRUEBAS
      allow write: if request.auth != null;
    }
  }
}
```

**⚠️ IMPORTANTE:** Esto es solo para pruebas. En producción, usar reglas más restrictivas.

### Solución 4: Modo de Depuración Extendido

**Activar logs detallados:**

Editar `firebase/firebase_client.py`:
```python
# Al inicio del archivo
import logging
logging.basicConfig(level=logging.DEBUG)
```

Esto mostrará TODOS los logs de Firebase, incluidos requests HTTP.

### Solución 5: Forzar Reinicialización

```python
# En consola Python:
import firebase_admin

# Ver apps inicializadas
apps = firebase_admin._apps
print(apps)

# Si es necesario, eliminar app y reinicializar
if apps:
    firebase_admin.delete_app(firebase_admin.get_app())
    
# Luego reiniciar aplicación FACOT
```

---

## 💡 Tips de Diagnóstico

### Tip 1: Revisar Consola Siempre

Al iniciar FACOT, revisar la consola/terminal para ver logs de:
- Inicialización de Firebase
- Modo de data_access usado
- Errores de conexión

### Tip 2: Usar Modo AUTO Primero

Si tienes dudas, usar modo AUTO:
```
1. Click en ⚙ → "Modo AUTO (Firebase/SQLite)"
2. Si Firebase funciona, usará Firebase
3. Si no, usará SQLite automáticamente
```

### Tip 3: Probar con Firebase Console

Antes de usar en FACOT:
1. Ir a Firebase Console
2. Abrir Firestore
3. Ver si colecciones existen
4. Intentar agregar documento manualmente

Si falla en Console, no funcionará en FACOT.

### Tip 4: Comparar con SQLite

Para verificar que Firebase tiene los mismos datos:
```python
# SQLite
from logic import LogicController
logic = LogicController("facturas.db")
sqlite_companies = logic.get_all_companies()
print(f"SQLite: {len(sqlite_companies)} empresas")

# Firebase
from data_access import get_data_access, DataAccessMode
fb_access = get_data_access(mode=DataAccessMode.FIREBASE)
fb_companies = fb_access.get_all_companies()
print(f"Firebase: {len(fb_companies)} empresas")
```

---

## 📞 Contacto de Soporte

Si después de seguir esta guía el problema persiste:

1. Copiar TODOS los logs de la consola
2. Tomar captura del widget de estado
3. Verificar versión de firebase-admin: `pip show firebase-admin`
4. Reportar con toda esta información

---

**Documento actualizado:** 2025-11-08  
**Commit:** d575e61  
**Estado:** ✅ Problemas comunes solucionados
