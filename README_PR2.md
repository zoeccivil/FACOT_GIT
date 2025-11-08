# PR2: Mejoras de UX para Tabla de Ítems - Guía de Usuario

## Descripción General

PR2 introduce mejoras significativas en la experiencia de usuario al trabajar con ítems (productos/servicios) en facturas y cotizaciones. Ahora es más rápido y eficiente agregar, editar y gestionar ítems.

## Nuevas Funcionalidades

### 1. Atajos de Teclado ⌨️

Ya no necesitas usar el mouse para todo. Usa estos atajos para trabajar más rápido:

| Atajo | Acción | Descripción |
|-------|--------|-------------|
| **Ctrl+N** | Nuevo ítem | Abre el selector para agregar un nuevo ítem |
| **Supr** | Eliminar | Elimina el ítem seleccionado (con confirmación) |
| **Ctrl+D** | Duplicar | Crea una copia del ítem seleccionado |
| **F2** | Editar | Permite editar la descripción del ítem |
| **Ctrl+V** | Pegar | Pega ítems desde Excel o CSV |

**Ejemplo de uso:**
1. Selecciona un ítem en la tabla
2. Presiona **Ctrl+D** para duplicarlo
3. Modifica la cantidad o precio si es necesario
4. ¡Listo! Mucho más rápido que agregar manualmente

### 2. Descuentos por Línea 💰

Ahora puedes aplicar descuentos individuales a cada ítem.

**Nueva Columna: Desc(%)**
- Ubicación: Entre "Precio" y "Subtotal"
- Formato: Porcentaje (0-100%)
- Cálculo automático del subtotal con descuento

**Cómo Aplicar Descuento:**

**Opción 1: Editar directamente**
1. Click en la celda de "Desc(%)" del ítem
2. Escribir el porcentaje (ej: 10 para 10%)
3. Presionar Enter
4. El subtotal se recalcula automáticamente

**Opción 2: Menú contextual**
1. Click derecho en el ítem
2. Seleccionar "💰 Aplicar descuento..."
3. Ingresar el porcentaje en el diálogo
4. Click OK

**Ejemplo de Cálculo:**
```
Ítem: Cemento
Cantidad: 10 sacos
Precio: RD$ 500.00
Descuento: 15%

Cálculo:
Subtotal bruto = 10 × 500 = RD$ 5,000.00
Descuento = 5,000 × 15% = RD$ 750.00
Subtotal neto = 5,000 - 750 = RD$ 4,250.00
```

### 3. Drag-and-Drop (Arrastrar y Soltar) 🖱️

Reordena los ítems fácilmente arrastrando las filas.

**Cómo Usar:**
1. Click y mantén presionado en cualquier celda del ítem
2. Arrastra hacia arriba o abajo
3. Suelta en la nueva posición
4. ¡La numeración se actualiza automáticamente!

**Casos de Uso:**
- Ordenar ítems por categoría
- Colocar ítems más importantes primero
- Agrupar productos relacionados

### 4. Pegar desde Excel 📋

Importa múltiples ítems desde Excel o CSV de una vez.

**Formato Requerido:**

En Excel, organiza los datos en columnas:

| Código | Descripción | Unidad | Cantidad | Precio | Descuento |
|--------|-------------|--------|----------|--------|-----------|
| CEM001 | Cemento | Saco | 10 | 500 | 5 |
| ARE002 | Arena | M3 | 5 | 800 | 0 |
| CAB003 | Cabilla | Quintal | 20 | 1200 | 10 |

**Pasos:**
1. Selecciona y copia las filas en Excel (Ctrl+C)
2. En FACOT, ve a la tabla de ítems
3. Presiona **Ctrl+V** o click derecho → "Pegar desde Excel"
4. Los ítems se agregan automáticamente

**Formatos Soportados:**
- ✅ Excel (separado por tabuladores)
- ✅ CSV (separado por comas)
- ✅ Mínimo 3 columnas (Código, Descripción, Unidad)
- ✅ Descuento es opcional

**Nota:** Si faltan columnas, se usan valores por defecto:
- Cantidad: 1.0
- Precio: 0.00
- Descuento: 0%

### 5. Menú Contextual 📑

Click derecho en cualquier ítem para ver opciones rápidas.

**Opciones Disponibles:**

```
┌─────────────────────────────────────┐
│ ➕ Nuevo ítem (Ctrl+N)             │
│────────────────────────────────────│
│ ✏️  Editar ítem (F2)                │
│ 📋 Duplicar ítem (Ctrl+D)          │
│ 🗑️  Eliminar ítem (Supr)            │
│────────────────────────────────────│
│ 💰 Aplicar descuento...            │
│────────────────────────────────────│
│ 📄 Pegar desde Excel (Ctrl+V)      │
└─────────────────────────────────────┘
```

**Ventajas:**
- Acceso rápido a funciones comunes
- Iconos visuales para identificar acciones
- Alternativa al uso de atajos de teclado

## Cambios en la Interfaz

### Antes (Versión Anterior)

```
┌────────────────────────────────────────────────────┐
│ # │ Código │ Descripción │ Unidad │ Cant │ Precio │ Subtotal │
├────────────────────────────────────────────────────┤
│ 1 │ CEM001 │ Cemento     │ Saco   │ 10   │ 500.00 │ 5,000.00 │
└────────────────────────────────────────────────────┘

Limitaciones:
- Sin descuentos por línea
- Sin atajos de teclado
- Sin drag-and-drop
- Agregar ítems uno por uno
```

### Ahora (Con PR2)

```
┌───────────────────────────────────────────────────────────────────┐
│ # │ Código │ Descripción │ Unidad │ Cant │ Precio │ Desc(%) │ Subtotal │
├───────────────────────────────────────────────────────────────────┤
│ 1 │ CEM001 │ Cemento     │ Saco   │ 10   │ 500.00 │ 15.00   │ 4,250.00 │
│ 2 │ ARE002 │ Arena       │ M3     │ 5    │ 800.00 │ 0.00    │ 4,000.00 │
└───────────────────────────────────────────────────────────────────┘

Mejoras:
✅ Descuentos individuales
✅ Atajos de teclado
✅ Drag-and-drop para reordenar
✅ Pegar múltiples ítems desde Excel
✅ Menú contextual con opciones
```

## Casos de Uso

### Caso 1: Cotización Rápida con Descuentos

**Escenario:** Preparar cotización para cliente frecuente con descuentos especiales.

**Pasos:**
1. Abrir pestaña "Cotización"
2. Presionar **Ctrl+N** para agregar primer ítem
3. Seleccionar producto del catálogo
4. Presionar **Ctrl+D** para duplicar (si necesitas cantidad adicional)
5. Click derecho → "Aplicar descuento..." → Ingresar 10%
6. Repetir para otros productos
7. ¡Cotización lista en minutos!

**Tiempo ahorrado:** ~50% comparado con método anterior

### Caso 2: Importar Lista de Precios desde Excel

**Escenario:** Tienes una lista de 20 productos en Excel que necesitas facturar.

**Pasos:**
1. Abrir archivo Excel con lista de productos
2. Copiar filas (Ctrl+C en Excel)
3. En FACOT, ir a tabla de ítems
4. Presionar **Ctrl+V**
5. Verificar que todos los ítems se agregaron
6. Ajustar cantidades/precios si es necesario
7. ¡20 ítems agregados en segundos!

**Tiempo ahorrado:** ~90% comparado con agregar uno por uno

### Caso 3: Reordenar Ítems por Categoría

**Escenario:** Organizar factura con materiales agrupados por tipo.

**Pasos:**
1. Agregar todos los ítems (de cualquier orden)
2. Arrastrar ítems de "Cemento" al inicio
3. Arrastrar ítems de "Arena" después
4. Arrastrar ítems de "Cabillas" al final
5. La numeración se actualiza automáticamente

**Beneficio:** Factura más organizada y profesional

### Caso 4: Duplicar Ítem con Modificaciones

**Escenario:** Vender mismo producto en diferentes presentaciones.

**Pasos:**
1. Agregar "Pintura Blanca - 1 Galón" @ RD$ 500
2. Seleccionar el ítem
3. Presionar **Ctrl+D**
4. Editar descripción a "Pintura Blanca - 1/2 Galón"
5. Cambiar precio a RD$ 280
6. ¡Listo! Sin volver al catálogo

**Tiempo ahorrado:** ~30 segundos por ítem duplicado

## Preguntas Frecuentes

**P: ¿Puedo usar descuentos en facturas y cotizaciones?**
R: Sí, la funcionalidad de descuentos está disponible en ambas.

**P: ¿El descuento afecta el ITBIS?**
R: Sí, el ITBIS se calcula sobre el subtotal después del descuento:
```
Subtotal con descuento = RD$ 4,250
ITBIS 18% = RD$ 765
Total = RD$ 5,015
```

**P: ¿Puedo aplicar descuento a todos los ítems a la vez?**
R: Por ahora, los descuentos se aplican individualmente. La función de descuento global vendrá en una actualización futura.

**P: ¿Qué pasa si pego mal formato desde Excel?**
R: FACOT validará el formato y te dirá cuántos ítems se pudieron importar. Los ítems con formato incorrecto se ignoran.

**P: ¿Puedo deshacer un cambio?**
R: Por ahora no hay deshacer (Ctrl+Z). Ten cuidado al eliminar ítems (siempre pide confirmación).

**P: ¿Los atajos funcionan en cualquier momento?**
R: Los atajos funcionan cuando la tabla de ítems está activa (tiene el foco).

## Solución de Problemas

### Problema: Ctrl+V no pega nada

**Causas posibles:**
1. Portapapeles vacío
2. Formato incorrecto
3. Tabla no tiene el foco

**Soluciones:**
1. Verifica que copiaste datos en Excel primero
2. Asegúrate de que los datos tienen al menos 3 columnas
3. Click en la tabla antes de pegar

### Problema: Drag-and-drop no funciona

**Causas posibles:**
1. No seleccionaste la fila completa
2. Arrastraste fuera de la tabla

**Soluciones:**
1. Click en cualquier celda de la fila y arrastra
2. Suelta dentro del área de la tabla

### Problema: Descuento no se aplica

**Causas posibles:**
1. Ingresaste valor mayor a 100
2. No presionaste Enter después de editar

**Soluciones:**
1. El descuento debe estar entre 0 y 100%
2. Siempre presiona Enter para confirmar

## Tips y Trucos

**Tip 1: Atajos en Cadena**
```
Ctrl+N (nuevo) → Seleccionar → Ctrl+D (duplicar) → F2 (editar)
Flujo rápido para agregar productos similares
```

**Tip 2: Plantilla Excel**
Crea una plantilla Excel con tus productos más usados:
```
Código | Descripción | Unidad | Cant | Precio | Desc
---------------------------------------------------
CEM001 | Cemento     | Saco   | 1    | 500    | 0
ARE002 | Arena       | M3     | 1    | 800    | 0
```
Solo copia y pega cuando necesites

**Tip 3: Descuentos Estratégicos**
- Descuento por volumen: Aplica 10-15% en cantidades grandes
- Descuento de temporada: 5% en productos de temporada baja
- Descuento por cliente: VIP 20%, Regular 10%

**Tip 4: Ordenamiento Profesional**
Ordena ítems por:
1. Categoría (materiales, mano de obra, transporte)
2. Importancia (más caros primero)
3. Orden lógico de trabajo

## Comparativa de Productividad

### Tarea: Agregar 10 ítems con descuentos

| Método | Tiempo | Clicks | Pasos |
|--------|--------|--------|-------|
| **Anterior** | ~5 min | ~80 | Abrir diálogo 10 veces, escribir datos, calcular descuentos |
| **PR2 (Excel)** | ~30 seg | ~5 | Copiar Excel, Ctrl+V, ajustar descuentos |
| **PR2 (Atajos)** | ~2 min | ~40 | Ctrl+N, seleccionar, Ctrl+D, aplicar descuentos |

**Ahorro de tiempo: 60-90%**

## Futuras Mejoras

Próximamente:
- [ ] Descuento global (aplicar % a todos los ítems)
- [ ] Deshacer/Rehacer (Ctrl+Z / Ctrl+Y)
- [ ] Buscar en tabla (Ctrl+F)
- [ ] Filtrar por categoría
- [ ] Exportar tabla a Excel
- [ ] Importar desde archivo CSV directo

---

**Versión:** 1.0  
**Fecha:** 2025-11-08  
**Estado:** ✅ Funcional
