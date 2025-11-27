# Guía del Usuario - FACOT

Bienvenido a FACOT. Esta guía te ayudará a aprovechar al máximo el sistema.

## 📋 Contenido

1. [Introducción](#introducción)
2. [Primeros Pasos](#primeros-pasos)
3. [Gestión de Empresas](#gestión-de-empresas)
4. [Trabajando con Facturas](#trabajando-con-facturas)
5. [Cotizaciones](#cotizaciones)
6. [Reportes e Impuestos](#reportes-e-impuestos)
7. [Configuración Avanzada](#configuración-avanzada)
8. [Tips y Trucos](#tips-y-trucos)

## 🎯 Introducción

### ¿Para quién es FACOT?

FACOT está diseñado para:
- Pequeñas y medianas empresas dominicanas
- Contadores y contadoras
- Freelancers y profesionales independientes
- Cualquier negocio que necesite facturar formalmente

### Lo que puedes hacer con FACOT

✅ Crear facturas con NCF válidos
✅ Gestionar múltiples empresas
✅ Llevar control de ingresos y gastos
✅ Generar reportes para DGII
✅ Calcular retenciones e impuestos
✅ Trabajar offline o en la nube
✅ Guardar comprobantes digitalmente

## 🚀 Primeros Pasos

### 1. Abrir FACOT

**Windows:**
```cmd
cd C:\ruta\a\FACOT_GIT
venv\Scripts\activate
python main.py
```

**Linux/macOS:**
```bash
cd /ruta/a/FACOT_GIT
source venv/bin/activate
python main.py
```

### 2. Seleccionar Base de Datos

Al abrir FACOT por primera vez:

1. **Crear Nueva Base de Datos:**
   - Selecciona una ubicación (ej: `Documentos/FACOT/mi_empresa.db`)
   - Dale un nombre descriptivo
   - Clic en "Guardar"

2. **Abrir Base de Datos Existente:**
   - Navega al archivo `.db`
   - Selecciónalo
   - Clic en "Abrir"

### 3. Interfaz Principal

```
┌────────────────────────────────────────────────────────┐
│  FACOT - Facturas y Cotizaciones      [Empresa: ▼]   │
├────────────────────────────────────────────────────────┤
│  📊 Dashboard  │  📄 Facturas  │  📋 Reportes  │  ⚙️  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Resumen:                    Filtros:                 │
│  Total Ingresos: RD$ XXX     [2025] [Enero ▼]       │
│  Total Gastos:   RD$ XXX     [Emitidas ▼]            │
│  ITBIS Neto:     RD$ XXX                              │
│                                                        │
├────────────────────────────────────────────────────────┤
│  Historial de Facturas                                │
│  ┌──────────────────────────────────────────────────┐ │
│  │Fecha    │NCF      │Cliente     │Monto          │ │
│  │01/01/25 │B0100001│Cliente SA  │RD$ 11,800    │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
│ ● SQLITE  mi_empresa.db  ⚙                            │
└────────────────────────────────────────────────────────┘
```

## 🏢 Gestión de Empresas

### Agregar tu Primera Empresa

1. Ve a: `Configuración` → `Gestión de Empresas`
2. Clic en `Agregar Empresa`
3. Llena el formulario:

   ```
   Nombre: Tu Empresa SRL
   RNC: 123456789
   Dirección: Calle Principal #123, Santo Domingo
   ```

4. Clic en `Guardar`

### Configurar Rutas

Después de crear la empresa, configura las rutas:

1. Selecciona la empresa
2. Clic en `Editar`
3. Configura:
   - **Plantilla de Factura**: Tu archivo Excel base
   - **Carpeta de Salida**: Donde se guardarán las facturas
   - **Logo** (opcional): Tu logo corporativo

### Gestionar Múltiples Empresas

FACOT te permite gestionar varias empresas:

1. Agrega cada empresa siguiendo los pasos anteriores
2. Cambia entre empresas con el selector superior
3. Cada empresa tiene sus propios datos y configuración

## 📄 Trabajando con Facturas

### Crear una Factura de Ingreso (Emitida)

#### Paso 1: Abrir Formulario
- Clic en `Nueva Factura` o `Ctrl+N`
- Selecciona `Factura Emitida`

#### Paso 2: Datos del Cliente
```
RNC/Cédula: 123-4567890-1
Nombre/Razón Social: Cliente Ejemplo SA

[✓] Buscar en directorio (autocompletar)
```

**Tip:** Si el cliente ya existe, se autocompletará.

#### Paso 3: Datos de la Factura
```
Tipo de NCF: [Crédito Fiscal (B01) ▼]
Número NCF: B0100000025 (automático)
Fecha: [📅 15/01/2025]
Fecha Vencimiento: [📅 15/02/2025]
Moneda: [RD$ ▼]
```

#### Paso 4: Agregar Items/Detalles

**Método 1: Manual**
1. Clic en `Agregar Item`
2. Llena:
   - Descripción: "Cemento Gris 50kg"
   - Cantidad: 100
   - Precio Unit.: 1,000.00
   - Subtotal: (se calcula auto) 100,000.00

**Método 2: Desde Excel** (Más Rápido)
1. Prepara tu Excel:
   ```
   Descripción       Cantidad  Precio
   Cemento Gris      100       1000
   Arena Lavada      50        800
   ```
2. Copia las celdas (Ctrl+C)
3. Clic en la tabla de items
4. Pega (Ctrl+V)

**Método 3: Drag and Drop** (PR2)
- Arrastra items para reordenar
- Usa `Ctrl+D` para duplicar
- Usa `Supr` para eliminar

#### Paso 5: Aplicar ITBIS
```
[✓] Aplicar ITBIS (18%)

Subtotal:     RD$ 100,000.00
ITBIS (18%):  RD$  18,000.00
─────────────────────────────
TOTAL:        RD$ 118,000.00
```

#### Paso 6: Guardar
- Clic en `Guardar` o `Ctrl+S`
- Se generará automáticamente el Excel
- Se actualizará el dashboard
- Se limpiará el formulario para la próxima

### Crear una Factura de Gasto

Similar a una factura emitida, pero:

1. Selecciona `Factura de Gasto`
2. El RNC es del proveedor (no se genera NCF)
3. **Importante:** Adjunta el comprobante

#### Adjuntar Comprobante

1. Clic en `Adjuntar Comprobante`
2. Selecciona la imagen o PDF
3. Se guardará automáticamente en:
   ```
   Anexos/
   └── Tu Empresa/
       └── 2025/
           └── 01/
               └── factura_001_proveedor.pdf
   ```

### Aplicar Descuentos (PR2)

#### Descuento por Línea
1. Selecciona un item
2. Clic derecho → `Aplicar Descuento`
3. Ingresa porcentaje (ej: 15%)
4. El subtotal se recalcula automáticamente

#### Descuento Manual
1. Ajusta el precio unitario directamente
2. O modifica el subtotal

### Editar una Factura

**Método 1: Doble Clic**
- Haz doble clic en la factura del listado

**Método 2: Menú Contextual**
- Clic derecho → `Editar`
- O selecciona y presiona `F2`

**Modificar:**
- Cambia los datos necesarios
- Agrega o quita items
- Guarda los cambios

⚠️ **Nota:** El cambio de NCF no es recomendable después de haber impreso/enviado la factura.

### Eliminar una Factura

1. Selecciona la factura
2. Presiona `Supr` o clic derecho → `Eliminar`
3. Confirma la eliminación

⚠️ **Advertencia:** La eliminación es permanente.

### Buscar Facturas

Usa los filtros en la parte superior:

**Por Fecha:**
```
Año: [2025 ▼]  Mes: [Enero ▼]
```

**Por Tipo:**
```
[Todas ▼]  [Emitidas ▼]  [Gastos ▼]
```

**Búsqueda Rápida:**
- Busca por NCF
- Busca por nombre de cliente
- Busca por RNC

## 📋 Cotizaciones

### Crear una Cotización

1. Ve a la pestaña `Cotizaciones`
2. Clic en `Nueva Cotización`
3. Llena similar a una factura:
   - Cliente
   - Items
   - Totales
4. Guarda

### Convertir Cotización a Factura

Cuando el cliente aprueba:

1. Abre la cotización
2. Clic en `Convertir a Factura`
3. Verifica/ajusta datos
4. Se genera la factura automáticamente

### Enviar Cotización

1. Genera la cotización (PDF)
2. Ubica el archivo en tu carpeta de salida
3. Envía por email/WhatsApp

## 📊 Reportes e Impuestos

### Reporte Mensual

**Para qué sirve:**
- Declaración de ITBIS mensual
- Contabilidad general
- Análisis de ingresos/gastos

**Cómo generarlo:**
1. Ve a `Reportes` → `Reporte Mensual`
2. Selecciona:
   ```
   Mes: Enero
   Año: 2025
   Formato: [PDF ▼] o [Excel ▼]
   ```
3. Marca opciones:
   - `[✓] Incluir anexos` (solo PDF)
   - `[✓] Separar por tipo`
4. Clic en `Generar`

**Contenido del Reporte:**
- Resumen de totales
- Tabla de facturas emitidas
- Tabla de facturas de gastos
- Anexos/comprobantes adjuntos (si se marcó)

### Cálculo de Retenciones

**Para qué sirve:**
- Calcular el impuesto a retener
- Declaración mensual de retenciones
- 607 y 608

**Cómo usarlo:**
1. Ve a `Herramientas` → `Calculadora de Retenciones`
2. Selecciona el período:
   ```
   Desde: 01/01/2025
   Hasta: 31/01/2025
   ```
3. Marca las facturas a incluir
4. Configura:
   ```
   % a pagar del ITBIS: 100% (normalmente)
   % a pagar del Total: 2.75% (o según aplique)
   ```
5. Clic en `Calcular`

**Resultado:**
```
Retención sobre ITBIS: RD$ XXX
Retención sobre Total: RD$ XXX
─────────────────────────────
TOTAL A RETENER:       RD$ XXX
```

6. Genera PDF para tus registros

### Reporte por Cliente/Proveedor

**Para qué sirve:**
- Ver histórico con un cliente específico
- Análisis de proveedores principales
- Cuentas por cobrar/pagar

**Cómo generarlo:**
1. Ve a `Reportes` → `Reporte por Tercero`
2. Busca el cliente/proveedor
3. Selecciona el RNC
4. Clic en `Generar`

**Muestra:**
- Todas las facturas con ese tercero
- Total de ingresos (si es cliente)
- Total de gastos (si es proveedor)
- Balance general

## ⚙️ Configuración Avanzada

### Cambiar entre SQLite y Firebase

**Ver Estado Actual:**
- Mira la barra inferior:
  ```
  ● SQLITE  mi_empresa.db
  ```

**Cambiar a Firebase:**
1. Clic en la barra de estado
2. Selecciona `Cambiar a Firebase`
3. Ingresa credenciales (si es primera vez)
4. Espera sincronización

**Cambiar a SQLite:**
1. Clic en la barra de estado
2. Selecciona `Cambiar a SQLite`
3. Selecciona el archivo .db

### Configurar Monedas

1. Ve a `Configuración` → `Monedas`
2. Agrega/edita monedas:
   ```
   RD$ (predeterminado)
   USD
   EUR
   CAD  ← Nueva
   ```

### Gestionar Directorio de Terceros

El directorio es automático, pero puedes:

1. Ver todos los terceros: `Herramientas` → `Directorio`
2. Editar nombres duplicados
3. Corregir RNCs erróneos
4. Fusionar entradas duplicadas (manualmente en BD)

### Plantillas de Factura

**Personalizar tu Plantilla:**
1. Abre tu plantilla Excel
2. Modifica:
   - Logo
   - Colores
   - Fuentes
   - Campos adicionales
3. Guarda
4. Actualiza ruta en FACOT

**Campos Dinámicos:**
FACOT reemplaza automáticamente:
- `{{company_name}}` → Nombre de empresa
- `{{client_name}}` → Nombre de cliente
- `{{ncf}}` → Número de factura
- `{{date}}` → Fecha
- `{{items}}` → Tabla de items
- `{{total}}` → Total

## 💡 Tips y Trucos

### Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+N` | Nueva factura/ítem |
| `Ctrl+S` | Guardar |
| `Ctrl+D` | Duplicar ítem |
| `Ctrl+V` | Pegar desde Excel |
| `Supr` | Eliminar ítem/factura |
| `F2` | Editar |
| `F5` | Actualizar dashboard |
| `Ctrl+F` | Buscar |
| `Esc` | Cancelar/Cerrar |

### Flujo de Trabajo Eficiente

**Para muchas facturas similares:**
1. Crea la primera factura completa
2. Para las siguientes:
   - Duplica items con `Ctrl+D`
   - Ajusta cantidades/precios
   - Cambia cliente
   - Guarda

**Para facturas recurrentes:**
1. Guarda una "plantilla" en Excel
2. Importa cada mes con `Ctrl+V`

### Organización de Archivos

**Estructura Recomendada:**
```
Documentos/
└── FACOT/
    ├── Bases_Datos/
    │   └── empresa_2025.db
    ├── Facturas/
    │   ├── 2025/
    │   │   ├── 01_Enero/
    │   │   └── 02_Febrero/
    ├── Anexos/
    │   └── (estructura automática)
    └── Backups/
        ├── empresa_2025-01-15.db
        └── empresa_2025-02-01.db
```

### Backup Automático

**Windows - Tarea Programada:**
1. Abre Programador de Tareas
2. Crea tarea básica
3. Programa: Semanal, Domingo 11 PM
4. Acción: Ejecutar script
   ```batch
   xcopy "C:\FACOT\mi_empresa.db" "C:\FACOT\Backups\mi_empresa_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db"
   ```

**Linux/macOS - Cron:**
```bash
0 23 * * 0 cp ~/FACOT/mi_empresa.db ~/FACOT/Backups/mi_empresa_$(date +\%Y\%m\%d).db
```

### Trabajo en Equipo

Si varias personas usan FACOT:

**Opción 1: Base de Datos Compartida (Dropbox/Drive)**
- ⚠️ Solo una persona a la vez
- Riesgo de corrupción si ambos abren simultáneamente

**Opción 2: Firebase (Recomendado)**
- ✅ Todos trabajan simultáneamente
- ✅ Cambios en tiempo real
- ✅ Sin conflictos

**Opción 3: Bases de Datos Separadas**
- Cada usuario su propia BD
- Consolidar manualmente al final

### Validar Datos

Antes de declarar:
1. Genera reporte mensual
2. Compara totales con tu contabilidad
3. Verifica que todos los NCF estén presentes
4. Revisa que no haya duplicados
5. Confirma que todos los anexos estén adjuntos

### Solución Rápida de Errores

**Si algo no funciona:**
1. `F5` para refrescar
2. Cierra y reabre FACOT
3. Verifica la consola por errores
4. Busca en [FAQ.md](FAQ.md)
5. Revisa [Issues](https://github.com/zoeccivil/FACOT_GIT/issues)

## 📚 Recursos Adicionales

- **[README.md](README.md)** - Descripción general
- **[INSTALL.md](INSTALL.md)** - Instalación
- **[FAQ.md](FAQ.md)** - Preguntas frecuentes
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Documentación técnica
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Cómo contribuir

## 🆘 Soporte

¿Necesitas ayuda?
1. Lee esta guía completa
2. Revisa el [FAQ](FAQ.md)
3. Busca en [Issues](https://github.com/zoeccivil/FACOT_GIT/issues)
4. Crea un nuevo issue si no encuentras solución

---

**Última Actualización:** 2025-11-09
**Versión:** 1.0
**¡Feliz facturación! 🎉**
