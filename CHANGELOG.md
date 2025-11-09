# Registro de Cambios - FACOT

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [No Publicado]

### Planificado
- Sistema de categorías con colores personalizables
- Múltiples listas de precios (price1, price2, price3)
- Sistema completo de auditoría (created_at, updated_at, created_by)
- Importación masiva desde CSV
- Suite de tests automatizados
- Documentación de API completa

## [2.0.0] - 2025-11-09

### Agregado
- **Documentación Completa en Español**
  - README.md principal con descripción completa del proyecto
  - CONTRIBUTING.md con guía de contribución
  - ARCHITECTURE.md con documentación de arquitectura
  - CHANGELOG.md para registro de cambios

### Mejorado
- Organización de la documentación del proyecto
- Accesibilidad de la información para nuevos contribuidores

## [1.6.0] - PR6 - Migración a Firebase

### Agregado
- **Arquitectura Dual: SQLite + Firebase**
  - Implementación de FirebaseDataAccess (283 líneas)
  - Capa de abstracción DataAccess (752 líneas)
  - Factory pattern para selección de backend
  - Modo AUTO con fallback automático

- **Script de Migración**
  - Herramienta completa de migración SQLite → Firebase (425 líneas)
  - Migración de empresas, facturas, items, terceros
  - Validación de datos migrados
  - Rollback en caso de error

- **Reglas de Seguridad Firebase**
  - Autenticación requerida (85 líneas)
  - Filtrado por company_id
  - Validación de esquemas
  - Logs inmutables

### Documentación
- README_PR6.md - Guía de usuario Firebase
- PR6_RESUMEN_COMPLETO.md - Documentación técnica

### Impacto
- Trabajo multi-usuario posible
- Sincronización en tiempo real
- Backup automático en la nube
- Acceso desde cualquier lugar

## [1.5.0] - PR2 - Mejoras de UX

### Agregado
- **Tabla de Items Mejorada**
  - EnhancedItemsTable con drag-and-drop (450 líneas)
  - Descuentos por línea con porcentaje
  - Importación desde Excel/CSV
  - Atajos de teclado completos

- **Atajos de Teclado**
  - Ctrl+N: Nuevo item
  - Ctrl+D: Duplicar item
  - Ctrl+V: Pegar desde Excel
  - Supr: Eliminar item
  - F2: Editar item

- **Funcionalidades Avanzadas**
  - Reordenamiento con drag-and-drop
  - Diálogo rápido de descuentos
  - Validación automática al pegar
  - Cálculo automático de subtotales

### Documentación
- README_PR2.md (330 líneas)

### Impacto
- 60-90% de ahorro de tiempo en ingreso de datos
- Flujos de trabajo optimizados
- Menos errores de digitación

## [1.4.0] - Indicador de Conexión

### Agregado
- **Barra de Estado Visual**
  - ConnectionStatusBar widget (250 líneas)
  - Indicador de tipo de BD (SQLite/Firebase)
  - Selector de modo de conexión
  - Menú contextual con opciones

- **Estados Visuales**
  - 🟢 Verde: Firebase online
  - 🔵 Azul: SQLite online
  - 🟠 Naranja: Firebase offline
  - ⚫ Gris: SQLite offline

- **Integración MainWindow**
  - Barra integrada en ventana principal (144 líneas)
  - Detección automática de estado
  - Actualización en tiempo real
  - Cambio de BD sin reiniciar

### Documentación
- INDICADOR_CONEXION.md (266 líneas)
- RESUMEN_INDICADOR_CONEXION.md (370 líneas)

### Impacto
- Visibilidad total del estado de conexión
- Cambio fácil entre bases de datos
- Experiencia de usuario mejorada

## [1.3.0] - PR1 - Motor de Documentos Unificado

### Agregado
- **CompanyProfileService**
  - Servicio centralizado de empresa (250 líneas)
  - Resolución de logos con 4 niveles de fallback
  - Normalización de direcciones
  - Caché en memoria

- **UnitResolver**
  - Resolución inteligente de unidades (160 líneas)
  - Búsqueda por código y nombre
  - Matching difuso (fuzzy)
  - Procesamiento por lotes

- **Corrección CSS**
  - Fix de DOMException en plantillas
  - Uso de variables CSS en lugar de insertRule()

- **Integración Dialogs**
  - UnitResolver integrado en preview dialogs
  - Unidades automáticas desde BD

### Mejorado
- **.gitignore**
  - Exclusiones completas para Python
  - Limpieza de __pycache__
  
### Documentación
- README_PR1.md
- PR1_RESUMEN.md
- IMPLEMENTACION_COMPLETA.md

### Impacto
- Logos más confiables
- Unidades automáticas correctas
- Sin crashes en cotizaciones

## [1.2.0] - Sistema NCF

### Agregado
- **Comprobantes Fiscales**
  - Soporte completo para NCF dominicanos
  - B01: Crédito Fiscal
  - B02: Consumidor Final
  - B04: Nota de Crédito
  - B14: Régimen Especial
  - B15: Gubernamental

- **Numeración Automática**
  - Generación secuencial de NCF
  - Formato: Prefijo + 8 dígitos
  - Validación de unicidad
  - Búsqueda del último número usado

### Documentación
- README_SISTEMA_NCF.md (14,366 líneas)

### Impacto
- Cumplimiento con DGII
- Numeración automática confiable
- Reducción de errores de digitación

## [1.1.0] - Reportes Avanzados

### Agregado
- **Generación de Reportes**
  - Reportes mensuales en PDF
  - Exportación a Excel
  - Inclusión de anexos en PDF
  - Tablas profesionales

- **Cálculo de Retenciones**
  - Calculadora de impuestos
  - Soporte para múltiples monedas
  - Conversión a RD$
  - Reporte detallado en PDF

- **Reportes por Terceros**
  - Análisis por cliente/proveedor
  - Totales de ingresos y gastos
  - Histórico completo

### Archivos Nuevos
- report_generator.py
- dialogs/report_window.py
- dialogs/tax_calculation_window.py
- dialogs/third_party_report_window.py

### Impacto
- Reportes profesionales para contabilidad
- Cálculos precisos de impuestos
- Análisis detallado de clientes

## [1.0.0] - Versión Inicial

### Agregado
- **Sistema Base**
  - Gestión de empresas múltiples
  - Facturas emitidas (ingresos)
  - Facturas de gastos
  - Base de datos SQLite

- **Interfaz Principal**
  - Dashboard con estadísticas
  - Filtros por fecha y tipo
  - Tabla de facturas
  - Panel de resumen con totales

- **Gestión de Facturas**
  - CRUD completo de facturas
  - Soporte para items/detalles
  - Cálculo automático de ITBIS
  - Validación de RNC

- **Monedas Múltiples**
  - RD$ (Pesos Dominicanos)
  - USD (Dólares)
  - Tasa de cambio manual
  - Conversión automática a RD$

- **Gestión de Anexos**
  - Carga de comprobantes
  - Organización automática por carpetas
  - Estructura: Empresa/Año/Mes
  - Soporte para PDF e imágenes

- **Directorio de Terceros**
  - Base de datos de clientes/proveedores
  - Búsqueda por RNC o nombre
  - Autocompletado en formularios

- **Configuración**
  - Gestión de empresas
  - Configuración de rutas
  - Plantillas de factura
  - Carpetas de salida

### Archivos Base
- main.py - Punto de entrada
- logic.py - Lógica de negocio
- ui_mainwindow.py - Interfaz principal
- config_facot.py - Configuración
- db_manager.py - Gestión de BD

## Tipos de Cambios

- **Agregado**: Para nuevas características
- **Cambiado**: Para cambios en funcionalidad existente
- **Obsoleto**: Para características que serán removidas
- **Removido**: Para características removidas
- **Corregido**: Para corrección de bugs
- **Seguridad**: Para vulnerabilidades

## Formato de Versiones

**[MAJOR.MINOR.PATCH]**
- **MAJOR**: Cambios incompatibles en API
- **MINOR**: Nuevas características compatibles
- **PATCH**: Correcciones de bugs compatibles

---

**Mantenido por:** Equipo FACOT
**Última Actualización:** 2025-11-09
