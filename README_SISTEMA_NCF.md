# 🔢 Sistema de Gestión de Secuencias NCF

**Documentación Completa del Sistema de Números de Comprobante Fiscal (NCF)**

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Características Principales](#características-principales)
3. [Acceso al Sistema](#acceso-al-sistema)
4. [Configuración de Secuencias](#configuración-de-secuencias)
5. [Gestión de Cambio 2026](#gestión-de-cambio-2026)
6. [Formatos NCF Soportados](#formatos-ncf-soportados)
7. [Ejemplos de Uso](#ejemplos-de-uso)
8. [Solución de Problemas](#solución-de-problemas)
9. [Referencia Técnica](#referencia-técnica)

---

## Introducción

El Sistema de Gestión de Secuencias NCF es una herramienta completa para manejar los Números de Comprobante Fiscal según la normativa de la DGII (Dirección General de Impuestos Internos) de República Dominicana.

### ¿Qué es un NCF?

Un NCF (Número de Comprobante Fiscal) es un identificador único requerido por la DGII para todas las facturas emitidas en República Dominicana. Tiene un formato específico que incluye:
- Letra identificadora (ej: B, E)
- Tipo de comprobante (2 dígitos: 01, 02, 15, etc.)
- Número secuencial (8 u 11 dígitos según el tipo)

**Ejemplo:** `B0100000125`
- `B` = Letra identificadora
- `01` = Tipo de comprobante (Crédito Fiscal)
- `00000125` = Secuencia (factura número 125)

---

## Características Principales

### ✅ 1. Gestión Completa de Secuencias

- **Por Empresa:** Cada empresa tiene sus propias secuencias independientes
- **Por Tipo de Comprobante:** Control individual para cada tipo (Privada, Gubernamental, etc.)
- **Configuración Manual:** Permite establecer la última secuencia utilizada
- **Reseteo de Secuencias:** Útil para cambio de año fiscal

### ✅ 2. Formatos DGII Soportados

#### Formato Estándar (11 caracteres)
- Letra + Tipo (2 dígitos) + Secuencia (8 dígitos)
- Ejemplo: `B0100000001`
- Tipos: B01, B02, B14, B15, B16, etc.

#### Formato E-CF Electrónico (14 caracteres)
- E + Tipo (2 dígitos) + Secuencia (11 dígitos)
- Ejemplo: `E3100000000001`
- Tipos: E31, E32, E33, E34, E41, E43, E44, E45

### ✅ 3. Gestión de Cambio 2026

A mediados de 2026, los prefijos NCF cambiarán según nueva normativa DGII:
- `B01` → `F01` (Crédito Fiscal)
- `B02` → `F02` (Consumidor Final)
- `B15` → `F15` (Gubernamental)
- Y otros...

El sistema permite:
- Configurar con anticipación los nuevos prefijos
- Establecer fecha de activación por empresa y tipo
- Cambio automático cuando llega la fecha configurada

---

## Acceso al Sistema

### Opción 1: Desde el Menú Principal

```
Herramientas → Configurar Secuencias NCF
```

### Opción 2: Atajo de Teclado

```
Ctrl + Shift + N
```

---

## Configuración de Secuencias

### Interfaz del Diálogo

Al abrir el diálogo de configuración, verás:

```
╔══════════════════════════════════════════════════════╗
║  Configuración de Secuencias NCF                     ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  Empresa: [ZOE CONSTRUCTORA ▼]                      ║
║                                                      ║
║  ┌────────────────────────────────────────────────┐ ║
║  │ Tipo Comprobante   │ Prefijo │ Última Sec.    │ ║
║  ├────────────────────┼─────────┼────────────────┤ ║
║  │ PRIVADA            │ B01     │ 00000125       │ ║
║  │ GUBERNAMENTAL      │ B15     │ 00000043       │ ║
║  │ CONSUMIDOR FINAL   │ B02     │ 00001250       │ ║
║  │ EXENTA             │ B14     │ 00000012       │ ║
║  │ E-CF (Electrónica) │ E31     │ 00000000025    │ ║
║  └────────────────────┴─────────┴────────────────┘ ║
║                                                      ║
║  [Editar Secuencia]  [Resetear a Cero]              ║
╚══════════════════════════════════════════════════════╝
```

### Pasos para Configurar

#### 1. Seleccionar Empresa

- Usa el desplegable superior para elegir la empresa
- Las secuencias son independientes por empresa

#### 2. Ver Secuencias Actuales

- La tabla muestra todos los tipos de comprobante disponibles
- Columna "Última Sec." indica el último número usado

#### 3. Editar una Secuencia

**Pasos:**
1. Hacer click en la fila del tipo deseado
2. Hacer click en botón "Editar Secuencia"
3. Ingresar el nuevo número secuencial
4. Hacer click en "Aceptar"

**Ejemplo:**
```
Si la última factura B01 fue 00000125
Y quieres que la próxima sea 00000200
Ingresa: 199 (el sistema generará la 200 como siguiente)
```

#### 4. Resetear Secuencias

**Útil para cambio de año fiscal**

**Pasos:**
1. Seleccionar el tipo de comprobante
2. Click en "Resetear a Cero"
3. Confirmar la acción
4. La secuencia vuelve a 00000000

**⚠️ Advertencia:** Esta acción no se puede deshacer. Asegúrate de hacerlo solo cuando cambies de año fiscal.

---

## Gestión de Cambio 2026

### Interfaz de Configuración 2026

En la parte inferior del diálogo encontrarás:

```
══════════════════════════════════════════════════  
CONFIGURACIÓN CAMBIO 2026                           
══════════════════════════════════════════════════  

A partir de mediados de 2026, los prefijos NCF     
cambiarán según normativa DGII.                    

┌────────────────────────────────────────────────┐ 
│ Tipo        │ Actual │ Nuevo 2026 │ Fecha Act.│ 
├─────────────┼────────┼────────────┼───────────┤ 
│ PRIVADA     │ B01    │ F01  [✓]   │ 01/07/2026│ 
│ GUBERNAMEN. │ B15    │ F15  [✓]   │ 01/07/2026│ 
│ CONS. FINAL │ B02    │ F02  [✓]   │ 01/07/2026│ 
│ EXENTA      │ B14    │ F14  [✓]   │ 01/07/2026│ 
└─────────────┴────────┴────────────┴───────────┘ 

☑ Activar automáticamente en fecha configurada     
```

### Pasos para Configurar Cambio 2026

#### 1. Habilitar Tipo de Comprobante

- Marca el checkbox [✓] en la columna "Nuevo 2026"
- Esto indica que este tipo cambiará de prefijo

#### 2. Configurar Nuevo Prefijo

- El nuevo prefijo se muestra automáticamente según mapeo DGII
- Ejemplo: B01 → F01

#### 3. Establecer Fecha de Activación

- Click en la celda "Fecha Act."
- Selecciona la fecha cuando entrará en vigor
- Por defecto: 01/07/2026 (estimado)

#### 4. Activar Cambio Automático

- Marca checkbox: "☑ Activar automáticamente en fecha configurada"
- El sistema cambiará automáticamente cuando llegue la fecha

### Comportamiento del Sistema

**Antes de la fecha de activación:**
```python
# Genera NCF con prefijo actual
ncf = "B0100000126"  # Usando B01
```

**Después de la fecha de activación:**
```python
# Genera NCF con nuevo prefijo
ncf = "F0100000001"  # Usando F01
# La secuencia comienza desde 1 con el nuevo prefijo
```

**Logs del Sistema:**
```
[NCF] 2026-07-01: Activando nuevo prefijo F01 para empresa ZOE (antes: B01)
[NCF] Última secuencia B01: 00000125
[NCF] Primera secuencia F01: 00000001
```

---

## Formatos NCF Soportados

### Tipos de Comprobante Estándar

| Prefijo | Descripción | Formato | Ejemplo |
|---------|-------------|---------|---------|
| B01 | Crédito Fiscal | B01 + 8 dígitos | B0100000001 |
| B02 | Consumidor Final | B02 + 8 dígitos | B0200000001 |
| B14 | Regímenes Especiales | B14 + 8 dígitos | B1400000001 |
| B15 | Gubernamental | B15 + 8 dígitos | B1500000001 |
| B16 | Exportaciones | B16 + 8 dígitos | B1600000001 |

### Tipos de Comprobante E-CF (Electrónico)

| Prefijo | Descripción | Formato | Ejemplo |
|---------|-------------|---------|---------|
| E31 | Consumidor Final E-CF | E31 + 11 dígitos | E3100000000001 |
| E32 | Crédito Fiscal E-CF | E32 + 11 dígitos | E3200000000001 |
| E33 | Nota de Débito E-CF | E33 + 11 dígitos | E3300000000001 |
| E34 | Nota de Crédito E-CF | E34 + 11 dígitos | E3400000000001 |
| E41 | Compras E-CF | E41 + 11 dígitos | E4100000000001 |
| E43 | Gastos Menores E-CF | E43 + 11 dígitos | E4300000000001 |
| E44 | Regímenes Especiales E-CF | E44 + 11 dígitos | E4400000000001 |
| E45 | Gubernamental E-CF | E45 + 11 dígitos | E4500000000001 |

### Mapeo de Cambio 2026

| Prefijo Actual | Prefijo 2026 | Tipo |
|----------------|--------------|------|
| B01 | F01 | Crédito Fiscal |
| B02 | F02 | Consumidor Final |
| B14 | F14 | Regímenes Especiales |
| B15 | F15 | Gubernamental |
| B16 | F16 | Exportaciones |

---

## Ejemplos de Uso

### Ejemplo 1: Configurar Nueva Secuencia

**Escenario:** Has recibido autorización de DGII para usar NCF desde B0100000500

**Pasos:**
1. Menú: Herramientas → Configurar Secuencias NCF
2. Seleccionar empresa
3. Click en fila "PRIVADA (B01)"
4. Click botón "Editar Secuencia"
5. Ingresar: `499`
6. Click "Aceptar"
7. Click "Guardar"

**Resultado:**
- La próxima factura usará: `B0100000500`

### Ejemplo 2: Resetear Secuencias para Nuevo Año Fiscal

**Escenario:** Es 1 de enero y necesitas resetear todas las secuencias

**Pasos:**
1. Abrir configuración de secuencias
2. Seleccionar primer tipo (PRIVADA)
3. Click "Resetear a Cero"
4. Confirmar
5. Repetir para cada tipo necesario
6. Click "Guardar"

**Resultado:**
- Todas las secuencias comienzan desde 00000001

### Ejemplo 3: Configurar Cambio 2026

**Escenario:** Preparar sistema para cambio de prefijos en julio 2026

**Pasos:**
1. Abrir configuración de secuencias
2. Scroll hacia abajo hasta "CONFIGURACIÓN CAMBIO 2026"
3. Marcar checkbox en cada tipo que cambiará (B01, B02, B15, etc.)
4. Verificar fechas de activación (01/07/2026)
5. Marcar "☑ Activar automáticamente en fecha configurada"
6. Click "Guardar"

**Resultado:**
- Sistema cambiará automáticamente el 1 de julio de 2026
- B01 → F01, B02 → F02, etc.

---

## Solución de Problemas

### Problema 1: No puedo ver el menú de configuración NCF

**Solución:**
- Verifica que tengas permisos de administrador
- Actualiza la aplicación a la última versión
- Reinicia la aplicación

### Problema 2: Las secuencias no se guardan

**Posibles causas:**
1. **Firebase sin conexión:**
   - Verifica conexión a internet
   - Widget debe mostrar: 🟢 FIREBASE Conectado

2. **Base de datos SQLite bloqueada:**
   - Cierra otras instancias de la aplicación
   - Verifica permisos de escritura en la base de datos

### Problema 3: NCF generado tiene formato incorrecto

**Verificación:**
- Formato estándar debe tener 11 caracteres (ej: B0100000001)
- Formato E-CF debe tener 14 caracteres (ej: E3100000000001)
- Si el formato es incorrecto, resetea la secuencia y vuelve a configurar

### Problema 4: El sistema no cambia a prefijo 2026 en la fecha configurada

**Verificación:**
1. Confirma que checkbox "Activar automáticamente" está marcado
2. Verifica que la fecha de activación sea correcta
3. Revisa logs del sistema para mensajes de error
4. Reinicia la aplicación si es necesario

---

## Referencia Técnica

### Archivos del Sistema

| Archivo | Descripción |
|---------|-------------|
| `dialogs/ncf_config_dialog.py` | Diálogo de configuración (520 líneas) |
| `utils/ncf_manager.py` | Gestor de lógica NCF (180 líneas) |
| `data_access/firebase_data_access.py` | Métodos NCF para Firebase |
| `data_access/sqlite_data_access.py` | Métodos NCF para SQLite |
| `ui_mainwindow.py` | Integración en menú principal |

### Métodos Principales

#### get_next_ncf(company_id, prefix3)
```python
"""
Genera el siguiente NCF para empresa y prefijo dado.

Args:
    company_id (int): ID de la empresa
    prefix3 (str): Prefijo de 3 caracteres (ej: "B01", "E31")

Returns:
    str: NCF generado (ej: "B0100000126")
"""
```

#### validate_ncf(ncf)
```python
"""
Valida formato de NCF según regex DGII.

Args:
    ncf (str): NCF a validar

Returns:
    bool: True si es válido, False si no
"""
```

### Collection Firebase

**ncf_config:**
```json
{
  "company_id": 1,
  "ncf_type": "B01",
  "current_seq": 125,
  "new_prefix_2026": "F01",
  "activation_date": "2026-07-01",
  "auto_switch_enabled": true
}
```

### Tabla SQLite

**ncf_sequences:**
```sql
CREATE TABLE ncf_sequences (
    id INTEGER PRIMARY KEY,
    company_id INTEGER,
    ncf_type TEXT,
    current_seq INTEGER,
    new_prefix_2026 TEXT,
    activation_date TEXT,
    auto_switch_enabled INTEGER
);
```

---

## Validación y Seguridad

### Validación de Formato

El sistema valida automáticamente:
- ✅ Longitud correcta (11 o 14 caracteres)
- ✅ Formato según regex DGII
- ✅ Prefijo válido
- ✅ Secuencia numérica válida

### Transacciones Atómicas

En Firebase, el sistema usa transacciones para garantizar:
- No se generen NCF duplicados
- Las secuencias sean consecutivas
- Los cambios sean atómicos

### Logs y Auditoría

Todos los cambios se registran:
```
[NCF] 2025-11-08 14:30: Secuencia B01 actualizada: 125 → 200 (Empresa: ZOE)
[NCF] 2026-07-01 00:00: Activado prefijo F01 (antes: B01)
```

---

## Soporte y Contacto

Para más información sobre el sistema NCF:
- Consulta la documentación de DGII: https://www.dgii.gov.do
- Revisa el código fuente en GitHub
- Contacta al administrador del sistema

---

**Última actualización:** Noviembre 2025  
**Versión del Sistema:** 1.0  
**Compatibilidad:** Firebase + SQLite

