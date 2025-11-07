# PR1: Motor de Documentos Unificado - Resumen de Implementación

## Descripción General
Este PR implementa la base para la refactorización del motor de documentos unificado, proporcionando servicios reutilizables y corrigiendo problemas críticos en el sistema de facturas/cotizaciones de FACOT.

## Elementos Completados ✅

### 1. CompanyProfileService
**Ubicación:** `services/company_profile_service.py`

Un servicio centralizado para recuperar y normalizar datos del perfil de empresa.

**Características:**
- **Resolución de Logo** con cadena de prioridad:
  1. Campo `logo_path` de la base de datos
  2. `logo_path` de plantilla (pasado como parámetro)
  3. `config_facot.COMPANY_LOGOS` (por ID de empresa o nombre)
  4. `config_facot.DEFAULT_LOGO_PATH`
- **Conversión Automática de URI:** Convierte rutas locales a URIs `file:///` (multiplataforma)
- **Normalización de Dirección:** Maneja `address_line1`, `address_line2`, y campo compacto `address`
- **Manejo de Firma:** Aliases `signature_name` y `authorized_name`
- **Caché:** Caché simple en memoria basado en diccionario para rendimiento
- **Fechas de Vencimiento Fijas:** Soporta `invoice_due_date` por empresa

**Uso:**
```python
from services import CompanyProfileService

service = CompanyProfileService(logic_controller)
profile = service.get_company_profile(company_id)

# Retorna: {
#   id, name, rnc, phone, email,
#   address_line1, address_line2, address,
#   signature_name, authorized_name,
#   logo_uri, invoice_due_date
# }
```

### 2. Servicio UnitResolver
**Ubicación:** `services/unit_resolver.py`

Resolución inteligente de unidades para ítems que carecen de información de unidad.

**Prioridad de Resolución:**
1. Usar `unit` existente si ya está presente y no está vacío
2. Buscar por `code` (coincidencia exacta en tabla de ítems)
3. Buscar por `name`/`description` (coincidencia difusa vía `get_items_like`)
4. Retroceder a `"UND"` como predeterminado

**Características:**
- **Resolución Inteligente:** Verifica tanto campos de código como nombre
- **Caché:** Caché en memoria con `(code, name)` como clave
- **Procesamiento por Lotes:** `resolve_items(items_list)` para procesar múltiples ítems
- **Degradación Elegante:** Retrocede a predeterminado si BD no disponible

**Uso:**
```python
from services import UnitResolver

resolver = UnitResolver(logic_controller)

# Ítem individual
unit = resolver.resolve_unit(
    item_code="ITEM001",
    item_name="Cemento",
    current_unit=""  # Se resolverá desde BD
)

# Procesamiento por lotes (modifica ítems en el lugar)
resolver.resolve_items(items_list)
```

**Integración:**
- Actualizado `invoice_preview_dialog.py`: `_ensure_units()` ahora usa UnitResolver
- Actualizado `quotation_preview_dialog.py`: `_ensure_units()` ahora usa UnitResolver
- Ambos diálogos retroceden elegantemente a asignación simple "UND" si servicio no disponible

### 3. Corrección de Variables CSS
**Ubicación:** `templates/quotation_template.html`

**Problema:** 
La función `setColorVariables()` estaba usando `sheet.insertRule()` para inyectar CSS dinámicamente, lo que causaba `DOMException` en ciertos navegadores y contextos (especialmente QtWebEngine).

**Solución:**
Se eliminó completamente la llamada a `insertRule()`. El CSS ya usa `var(--primary)` para fondos de encabezados de tabla, así que el JavaScript solo necesita establecer la variable CSS:

```javascript
// Antes (causaba DOMException):
sheet.insertRule('table thead th { background: ' + p + ' !important; }', ...);

// Después (limpio y confiable):
document.documentElement.style.setProperty('--primary', p);
```

El CSS existente aplica automáticamente la variable:
```css
table thead th {
  background: var(--primary);
  /* ... */
}
```

### 4. Higiene del Proyecto
**Archivos Nuevos:**
- `.gitignore` - Gitignore completo para proyecto Python
  - Excluye `__pycache__/`, `*.pyc`, artefactos de construcción
  - Excluye configuración específica de usuario (`facot_config.json`)
  - Excluye PDFs/Excel generados (excepto archivo de plantilla)
  - Excluye archivos HTML de depuración

**Limpieza:**
- Eliminados todos los directorios `__pycache__` del repositorio
- Todos los archivos Python validados sintácticamente con `py_compile`

## Arquitectura

### Patrón de Servicios
El nuevo paquete `services/` sigue una separación limpia de responsabilidades:

```
services/
├── __init__.py               # Exportaciones del paquete
├── company_profile_service.py # Gestión de datos de empresa
└── unit_resolver.py          # Resolución de unidades de ítems
```

**Beneficios:**
- **Reutilizable:** Los servicios pueden ser usados por cualquier componente (pestañas, diálogos, reportes)
- **Testeable:** Lógica de negocio separada de UI
- **Cacheable:** Caché incorporado para rendimiento
- **Mantenible:** Fuente única de verdad para datos de empresa/ítems

### Puntos de Integración

**Integración Actual:**
- `InvoicePreviewDialog._build_injectable_payloads()` → Usa `UnitResolver`
- `QuotationPreviewDialog._build_injectable_payloads()` → Usa `UnitResolver`

**Integración Futura (PR2+):**
- Reemplazar `_prepare_company_data_for_preview()` en línea con `CompanyProfileService`
- Usar `CompanyProfileService` en pestañas de factura/cotización
- Agregar `UnitResolver` a ventanas de gestión de ítems

## Pruebas

Todos los cambios han sido validados sintácticamente:
```bash
python3 -m py_compile dialogs/invoice_preview_dialog.py
python3 -m py_compile dialogs/quotation_preview_dialog.py  
python3 -m py_compile services/company_profile_service.py
python3 -m py_compile services/unit_resolver.py
```

**Prueba de Importación:**
```bash
python3 -c "from services import CompanyProfileService, UnitResolver"
# ✓ Exitoso
```

## Compatibilidad Hacia Atrás

Todos los cambios son **compatibles hacia atrás**:
- El código existente continúa funcionando sin cambios
- Los servicios son opcionales (retroceso a lógica simple si no disponible)
- Sin cambios de esquema de base de datos
- Sin cambios de API que rompan compatibilidad

## Archivos Modificados

```
Modificados:
  dialogs/invoice_preview_dialog.py       (+27, -7)
  dialogs/quotation_preview_dialog.py     (+27, -7)
  templates/quotation_template.html       (+1, -4)

Nuevos:
  .gitignore                              (+64)
  services/__init__.py                    (+8)
  services/company_profile_service.py     (+251)
  services/unit_resolver.py               (+159)
```

## Próximos Pasos (PRs Futuros)

### PR2: Mejoras de UX
- Atajos de teclado para tabla de ítems (Ctrl+N, Supr, Ctrl+D, F2)
- Descuentos por línea de ítem y descuentos globales
- Reordenamiento por arrastrar y soltar
- Pegar desde Excel/portapapeles

### PR3: Estados de Cotización
- Estados: Borrador, Enviada, Aceptada, Rechazada, Vencida
- Seguimiento de fecha de vencimiento con `QUOTATION_DUE_DAYS`
- Funcionalidad "Convertir a Factura"

### PR4: Funcionalidad de Email
- Configuración SMTP por empresa
- Plantillas de email con variables
- Adjuntos PDF
- Seguimiento de registro de envíos

### PR5-9: 
Ver lista de verificación del proyecto principal para fases restantes (Auditoría, Firebase, Reportes, Empaquetado, Documentación)

## Notas para Usuarios No Técnicos

**Qué Cambió:**
1. **Mejor Manejo de Logos:** El sistema ahora encuentra logos de empresa de manera más confiable, verificando la base de datos, archivos de configuración y valores predeterminados
2. **Unidades Más Inteligentes:** Cuando agregas ítems sin unidades, el sistema ahora los busca en la base de datos en lugar de usar siempre "UNID"
3. **Error de Impresión Corregido:** Las cotizaciones ya no fallan al intentar aplicar colores personalizados
4. **Código Más Limpio:** Agregada organización para mantenimiento futuro más fácil

**Qué Notarás:**
- Las unidades deberían llenarse automáticamente cuando seleccionas ítems de la base de datos
- Los logos de empresa deberían aparecer más consistentemente en vistas previas y PDFs
- No más errores al generar cotizaciones con colores de marca personalizados

**Sin Cambios que Rompan Funcionalidad:**
¡Todo funciona exactamente como antes, pero más inteligente y confiable!
