# Indicador de Estado de Conexión - Guía de Usuario

## Descripción General

La barra de estado de conexión es una nueva funcionalidad en FACOT que te permite:
- **Ver** a qué base de datos estás conectado (SQLite o Firebase)
- **Cambiar** fácilmente entre bases de datos SQLite
- **Seleccionar** el modo de conexión (local o en la nube)
- **Monitorear** si tienes conexión a internet

## Ubicación

La barra de estado está ubicada en la **parte inferior** de la ventana principal:

```
┌──────────────────────────────────────────────────────┐
│  FACOT - Gestión de Facturas y Cotizaciones          │
├──────────────────────────────────────────────────────┤
│  Empresa: [Mi Empresa S.A.            ▼]             │
│  ┌────────────────────────────────────────────────┐  │
│  │ Factura │ Cotización │ Historial │ ...        │  │
│  │                                                 │  │
│  │  [Contenido del tab actual]                    │  │
│  │                                                 │  │
│  └────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────┤
│  ● SQLITE  facturas_2024.db  ⚙                       │ ← BARRA DE ESTADO
└──────────────────────────────────────────────────────┘
```

## Componentes de la Barra

### 1. Indicador de Estado (●)

El círculo de color indica el tipo y estado de la conexión:

| Color | Significado |
|-------|-------------|
| 🟢 **Verde** | Conectado a Firebase con internet |
| 🔵 **Azul** | Conectado a SQLite con internet |
| 🟠 **Naranja** | Modo Firebase sin conexión a internet |
| ⚫ **Gris** | Modo SQLite sin conexión a internet |

### 2. Etiqueta de Modo

Muestra el modo actual de conexión:
- **SQLITE** - Usando base de datos local solamente
- **FIREBASE** - Usando base de datos en la nube solamente
- **AUTO** - Automático (intenta Firebase, si no hay internet usa SQLite)

### 3. Información de Base de Datos

- En modo **SQLITE**: Muestra el nombre del archivo de base de datos
  - Ejemplo: `facturas_2024.db`
  - Ejemplo: `SQLite (Online): mi_base.db`

- En modo **FIREBASE**: Muestra el estado de Firebase
  - Ejemplo: `Conectado a Firebase`
  - Ejemplo: `Firebase (sin conexión)`

- En modo **AUTO**: Muestra qué backend se está usando
  - Ejemplo: `AUTO → Firebase`
  - Ejemplo: `AUTO → SQLite: facturas.db`

### 4. Botón de Opciones (⚙)

Click en este botón para abrir el menú de opciones.

## Usando la Barra de Estado

### Cambiar de Base de Datos SQLite

1. Click en el botón **⚙** (engranaje)
2. Seleccionar **"📂 Cambiar base de datos..."**
3. Buscar y seleccionar el archivo `.db` deseado
4. La aplicación recargará automáticamente con la nueva base

### Crear Nueva Base de Datos

1. Click en el botón **⚙**
2. Seleccionar **"➕ Crear nueva base de datos..."**
3. Elegir ubicación y nombre para la nueva base
4. La aplicación creará la base y la abrirá automáticamente

### Cambiar Modo de Conexión

#### Cambiar de SQLite a Firebase

1. Asegúrate de tener conexión a internet
2. Click en el botón **⚙**
3. Seleccionar **"☁️ Cambiar a Firebase"**
4. La aplicación cambiará a modo Firebase

**Requisitos:**
- Conexión a internet activa
- Firebase configurado correctamente
- Credenciales de Firebase válidas

#### Cambiar de Firebase a SQLite

1. Click en el botón **⚙**
2. Seleccionar **"💾 Cambiar a SQLite..."**
3. Si no tienes una base SQLite seleccionada, te pedirá que elijas una
4. La aplicación cambiará a modo SQLite local

#### Usar Modo AUTO

1. Click en el botón **⚙**
2. Seleccionar **"🔄 Modo AUTO (Firebase/SQLite)"**
3. La aplicación:
   - **Con internet:** Usará Firebase automáticamente
   - **Sin internet:** Usará SQLite automáticamente

Este modo es ideal si trabajas a veces con y sin internet.

## Casos de Uso

### Caso 1: Trabajando en la Oficina (con Internet)

```
Estado: ● FIREBASE  Conectado a Firebase  ⚙
```

- Todos tus datos están en la nube
- Puedes acceder desde cualquier computadora
- Cambios se sincronizan automáticamente
- Otros usuarios pueden trabajar simultáneamente

### Caso 2: Trabajando sin Internet

```
Estado: ● SQLITE  SQLite (Offline): facturas.db  ⚙
```

- Trabajas con tu base de datos local
- No necesitas conexión a internet
- Ideal para trabajo en campo o áreas sin cobertura
- Puedes sincronizar después cuando tengas internet

### Caso 3: Modo Automático

```
Con Internet:    ● AUTO → Firebase  ⚙
Sin Internet:    ● AUTO → SQLite: facturas.db  ⚙
```

- No te preocupas por el estado de conexión
- La app cambia automáticamente según disponibilidad
- Siempre puedes trabajar, con o sin internet

### Caso 4: Cambiando entre Proyectos

```
Proyecto A: ● SQLITE  proyecto_a.db  ⚙
Proyecto B: ● SQLITE  proyecto_b.db  ⚙
```

- Usa el botón ⚙ → "Cambiar base de datos..."
- Selecciona la base del proyecto deseado
- Cambio instantáneo sin cerrar la aplicación

## Solución de Problemas

### El indicador está gris

**Causa:** No hay conexión a internet

**Solución:** 
- Verifica tu conexión WiFi/Ethernet
- Si trabajas en modo SQLite, puedes continuar normalmente
- Si necesitas Firebase, restaura tu conexión a internet

### No puedo cambiar a Firebase

**Posibles causas:**
1. No hay conexión a internet
2. Firebase no está configurado
3. Credenciales de Firebase inválidas

**Soluciones:**
1. Verifica tu conexión a internet
2. Asegúrate de tener el archivo `firebase-credentials.json` configurado
3. Verifica que `pip install firebase-admin` esté instalado
4. Consulta la documentación en `README_PR6.md`

### La base de datos no cambia

**Causa:** El archivo seleccionado no es una base de datos válida

**Solución:**
- Asegúrate de seleccionar un archivo `.db` válido
- Verifica que el archivo no esté corrupto
- Intenta crear una nueva base de datos

### Dice "AUTO → Firebase" pero quiero usar SQLite

**Solución:**
1. Click en ⚙
2. Selecciona "💾 Forzar SQLite..."
3. Elige tu base de datos local
4. Ahora usará SQLite exclusivamente

## Preguntas Frecuentes

**¿Qué pasa con mis datos si cambio de SQLite a Firebase?**
- Tus datos en SQLite permanecen intactos
- Firebase es una base separada
- Usa el script de migración para copiar datos de SQLite a Firebase

**¿Puedo usar SQLite y Firebase al mismo tiempo?**
- No simultáneamente
- Pero puedes cambiar entre ellos usando el botón ⚙
- Usa el modo AUTO para cambio automático

**¿El indicador afecta el rendimiento?**
- No, es muy ligero
- Solo hace una verificación de internet al iniciar
- No hace consultas constantes

**¿Puedo ocultar la barra de estado?**
- Por ahora no, está siempre visible
- Ocupa muy poco espacio (una línea)
- Proporciona información importante

**¿Qué significa "Online" vs "Offline"?**
- **Online:** Tienes conexión a internet activa
- **Offline:** No hay conexión a internet
- En modo SQLite, puedes trabajar en ambos casos
- En modo Firebase, necesitas estar Online

## Atajos y Tips

**Tip 1: Acceso Rápido al Menú**
- Click en cualquier parte de la barra de estado para más opciones
- El botón ⚙ siempre está disponible

**Tip 2: Monitoreo Visual**
- El color del indicador te dice todo de un vistazo
- Verde = Todo bien en la nube
- Azul = Todo bien localmente

**Tip 3: Bases de Datos por Proyecto**
- Crea una base `.db` por proyecto o año
- Ejemplo: `facturas_2023.db`, `facturas_2024.db`
- Cambia fácilmente entre ellas con el botón ⚙

**Tip 4: Respaldo Antes de Cambiar**
- Haz backup de tu base actual antes de cambiar
- Usa: Menú Archivo → Hacer Backup...
- Así puedes volver si algo sale mal

## Integración con Firebase

Si tienes Firebase configurado:

1. La barra mostrará cuando estás conectado a Firebase
2. Puedes ver el estado de sincronización
3. Si pierdes internet, el indicador cambiará a naranja
4. Cuando recuperes internet, volverá a verde

Ver `README_PR6.md` para más información sobre Firebase.

---

**Última actualización:** 2025-11-08  
**Versión:** 1.0
