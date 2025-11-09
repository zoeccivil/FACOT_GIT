# FACOT - Sistema de Gestión de Facturas y Cotizaciones

![Versión](https://img.shields.io/badge/versión-2.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Licencia](https://img.shields.io/badge/licencia-MIT-orange.svg)
![Tests](https://img.shields.io/badge/tests-79%20passing-brightgreen.svg)

## 📋 Descripción

FACOT es un sistema completo de gestión de facturas y cotizaciones diseñado para empresas en República Dominicana. El sistema ofrece una solución robusta para la administración de documentos fiscales, cumpliendo con las normativas de la DGII (Dirección General de Impuestos Internos).

### 🆕 Novedades v2.1

✨ **Sistema de Auditoría Completo**
- Registro automático de todas las operaciones críticas
- Historial completo de cambios en facturas
- Trazabilidad total de NCF asignados

✨ **NCF Sin Duplicados**
- Transacciones BEGIN EXCLUSIVE (SQLite)
- Validado con tests de concurrencia
- Imposible generar NCF duplicados

✨ **Sistema de Email Profesional**
- Envío de facturas por email con adjuntos
- Soporte SMTP/TLS y SendGrid
- Registro de todos los envíos
- Vista previa de emails

✨ **79 Tests Automatizados**
- Cobertura completa del backend
- Tests de integración
- Tests de concurrencia
- CI/CD con GitHub Actions

### Características Principales

✅ **Gestión de Facturas**
- Facturas emitidas (ingresos)
- Facturas de gastos
- Soporte para múltiples monedas (RD$, USD, EUR)
- Cálculo automático de ITBIS (18%)
- Conversión automática a pesos dominicanos
- **🆕 NCF automático al crear facturas**
- **🆕 Auditoría automática de cambios**

✅ **Gestión de Cotizaciones**
- Creación de cotizaciones profesionales
- Conversión de cotizaciones a facturas
- Plantillas personalizables

✅ **Comprobantes Fiscales (NCF)**
- B01 - Crédito Fiscal
- B02 - Consumidor Final
- B04 - Nota de Crédito
- B14 - Régimen Especial
- B15 - Gubernamental
- **🆕 Numeración segura sin duplicados (BEGIN EXCLUSIVE)**
- **🆕 Tabla de secuencias persistente**

✅ **Arquitectura Dual: SQLite + Firebase**
- **SQLite Local**: Para trabajo offline
- **Firebase Cloud**: Para sincronización y trabajo multi-usuario
- Cambio automático entre modos
- Migración de datos facilitada

✅ **Reportes y Análisis**
- Reportes mensuales en PDF y Excel
- Cálculo de retenciones e impuestos
- Análisis por terceros (clientes/proveedores)
- Estadísticas del dashboard en tiempo real

✅ **Gestión de Anexos**
- Carga y organización automática de comprobantes
- Editor de imágenes integrado
- Visualización de PDFs
- Estructura de carpetas automatizada

✅ **Interfaz de Usuario Mejorada**
- Indicador de conexión visual
- Atajos de teclado (Ctrl+N, Ctrl+D, Supr, F2)
- Importación desde Excel/CSV
- Drag-and-drop para reordenar items
- Descuentos por línea

## 🚀 Inicio Rápido

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Sistema operativo: Windows, Linux o macOS

### Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/zoeccivil/FACOT_GIT.git
cd FACOT_GIT
```

2. **Crear entorno virtual (recomendado)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Migrar base de datos (NUEVO - v2.1)**
```bash
python scripts/migrate_db.py facturas_cotizaciones.db
```

5. **Ejecutar la aplicación**
```bash
python main.py
```

### 🚀 Inicio Rápido - Demo del Backend

Prueba las nuevas funcionalidades de auditoría y NCF:

```bash
# Ver demo completo del backend
python demo_backend.py
```

**Salida esperada:**
```
✅ 5 facturas creadas con NCF automático
✅ Sin duplicados: True
✅ 12 registros de auditoría
✅ TODO FUNCIONANDO CORRECTAMENTE
```

## 📚 Documentación

### Documentación Técnica Nueva (v2.1)

- **[Implementación Backend Completa](IMPLEMENTACION_BACKEND_COMPLETA.md)** - Resumen técnico completo
- **[Guía de Integración Completa](GUIA_INTEGRACION_COMPLETA.md)** - Paso a paso para desarrolladores
- **[Resumen de Implementación](RESUMEN_IMPLEMENTACION_FINAL.md)** - Detalles de PRs
- **[Roadmap de Modernización](ROADMAP_MODERNIZACION.md)** - Plan de mejoras

### Documentación por Fases

- **[PR1: Motor de Documentos Unificado](README_PR1.md)** - Servicios base y arquitectura
- **[PR2: Mejoras de UX](README_PR2.md)** - Tabla mejorada y atajos de teclado
- **[PR6: Migración a Firebase](README_PR6.md)** - Arquitectura cloud y sincronización
- **[Sistema NCF](README_SISTEMA_NCF.md)** - Comprobantes fiscales dominicanos
- **[Indicador de Conexión](INDICADOR_CONEXION.md)** - Barra de estado visual

### Documentación Técnica

- **[Implementación Completa PR1](IMPLEMENTACION_COMPLETA.md)** - Detalles técnicos PR1
- **[Resumen PR6](PR6_RESUMEN_COMPLETO.md)** - Detalles técnicos Firebase
- **[Resumen Completo](RESUMEN_COMPLETO_PR1_PR6_INDICADOR_PR2.md)** - Todas las fases

### Guías de Solución de Problemas

- **[Solución de Problemas Firebase](SOLUCION_PROBLEMAS_FIREBASE.md)**
- **[Correcciones Firebase](RESUMEN_CORRECCIONES_FIREBASE.md)**

## 🏗️ Arquitectura del Sistema

```
FACOT/
├── main.py                    # Punto de entrada principal
├── logic.py                   # Lógica de negocio y BD
├── ui_mainwindow.py          # Interfaz principal
├── config_facot.py           # Configuración
├── services/                  # Servicios del sistema
│   ├── company_profile_service.py
│   ├── unit_resolver.py
│   └── ...
├── data_access/              # Capa de acceso a datos
│   ├── sqlite_data_access.py
│   ├── firebase_data_access.py
│   └── data_access_factory.py
├── dialogs/                  # Ventanas de diálogo
│   ├── invoice_preview_dialog.py
│   ├── quotation_preview_dialog.py
│   └── ...
├── widgets/                  # Componentes UI personalizados
│   └── connection_status_bar.py
├── templates/                # Plantillas HTML para documentos
│   ├── invoice_template.html
│   └── quotation_template.html
└── firebase/                 # Configuración Firebase
    ├── firebase-credentials.json
    └── firestore.rules
```

## 💻 Uso del Sistema

### Configuración Inicial

1. **Seleccionar Base de Datos**
   - Al iniciar, el sistema pedirá seleccionar un archivo `.db`
   - Puede crear una nueva base de datos o usar una existente

2. **Configurar Empresa**
   - Ir a `Configuración` → `Gestión de Empresas`
   - Agregar información de la empresa (nombre, RNC, dirección)
   - Configurar rutas de plantillas y carpetas de salida

3. **Configurar Firebase (Opcional)**
   - Para trabajo en la nube, configurar credenciales Firebase
   - Ver [README_PR6.md](README_PR6.md) para detalles

### Operaciones Comunes

#### Crear una Factura

1. Seleccionar la empresa activa
2. Clic en `Nueva Factura` o presionar `Ctrl+N`
3. Seleccionar tipo de factura (Emitida o Gasto)
4. Llenar datos del cliente
5. Agregar items/detalles
6. Guardar

#### Generar Reportes

1. Ir a `Reportes` → `Reporte Mensual`
2. Seleccionar mes y año
3. Elegir formato (PDF o Excel)
4. Generar y guardar

#### Calcular Retenciones

1. Ir a `Herramientas` → `Calculadora de Retenciones`
2. Seleccionar período
3. Marcar facturas a incluir
4. Calcular y generar reporte

### Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+N` | Nueva factura/ítem |
| `Ctrl+S` | Guardar |
| `Ctrl+D` | Duplicar ítem |
| `Ctrl+V` | Pegar desde Excel |
| `Supr` | Eliminar ítem |
| `F2` | Editar ítem |
| `F5` | Actualizar dashboard |

## 🔄 Mejoras Pendientes

Según el archivo [SUGERENCIAS.txt](SUGERENCIAS.txt), las siguientes características están planificadas:

### Gestión de Categorías
- [ ] Colores/etiquetas por categoría
- [ ] Impuesto por categoría (ITBIS configurable)
- [ ] Márgenes por categoría (cálculo automático de precio de venta)
- [ ] Unidades favoritas por categoría

### Sistema de Precios
- [ ] Múltiples listas de precios (price1, price2, price3)
- [ ] Selección de lista de precios por cliente
- [ ] Selección de lista de precios por documento

### Importación/Exportación
- [x] Exportación a Excel (implementado)
- [x] Exportación a PDF (implementado)
- [ ] Importación masiva desde CSV
- [ ] Importación de items desde Excel

### Auditoría
- [ ] Campos `created_at` en todas las entidades
- [ ] Campos `updated_at` en todas las entidades
- [ ] Campo `created_by` para multi-usuario
- [ ] Historial de cambios

### Validaciones Mejoradas
- [x] Validación de cliente y RNC (implementado)
- [x] Validación de items (implementado)
- [x] Validación de importes (implementado)
- [x] Cálculo automático de montos (implementado)

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

### Estándares de Código

- Seguir PEP 8 para Python
- Documentar funciones y clases
- Agregar pruebas para nuevas características
- Mantener la documentación actualizada

## 📊 Estadísticas del Proyecto

```
Total de Entregas:     4 fases completadas
Total de Commits:      19+ commits
Total de Archivos:     32+ archivos

Código de Producción:  2,664+ líneas
Documentación:         2,502+ líneas
Gran Total:            5,166+ líneas

Seguridad:             0 vulnerabilidades (CodeQL)
Compatibilidad:        100% hacia atrás
Idioma:                100% español
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Contacto

**Proyecto FACOT**
- GitHub: [@zoeccivil](https://github.com/zoeccivil)
- Repositorio: [FACOT_GIT](https://github.com/zoeccivil/FACOT_GIT)

## 🙏 Agradecimientos

- Comunidad de desarrolladores Python
- Usuarios y testers del sistema FACOT
- Contribuidores del proyecto

---

**Última Actualización:** 2025-11-09
**Versión:** 2.0
**Estado:** ✅ ACTIVO Y EN DESARROLLO
