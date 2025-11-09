# Preguntas Frecuentes (FAQ) - FACOT

## 📋 Índice

- [General](#general)
- [Instalación](#instalación)
- [Uso del Sistema](#uso-del-sistema)
- [Facturas](#facturas)
- [Firebase y Sincronización](#firebase-y-sincronización)
- [Reportes](#reportes)
- [Errores Comunes](#errores-comunes)

## 🔷 General

### ¿Qué es FACOT?

FACOT es un sistema completo de gestión de facturas y cotizaciones diseñado para empresas en República Dominicana. Permite crear, gestionar y reportar facturas cumpliendo con las normativas de la DGII.

### ¿Es gratis?

Sí, FACOT es completamente gratuito y de código abierto bajo licencia MIT.

### ¿Necesito internet para usar FACOT?

No necesariamente. FACOT funciona completamente offline con SQLite. Solo necesitas internet si decides usar Firebase para sincronización en la nube.

### ¿Cuántas empresas puedo gestionar?

Puedes gestionar múltiples empresas en una sola base de datos, o crear bases de datos separadas para cada empresa. No hay límite.

### ¿Puedo usar FACOT en varios computadores?

Sí, de dos formas:
1. **Con SQLite**: Copia el archivo `.db` entre computadores
2. **Con Firebase**: Todos los computadores se sincronizan automáticamente en la nube

## 🔷 Instalación

### ¿Qué versión de Python necesito?

Python 3.8 o superior. Se recomienda Python 3.10 o 3.11.

### ¿Funciona en Windows, Mac y Linux?

Sí, FACOT es multiplataforma y funciona en:
- Windows 10 y 11
- macOS 10.15 o superior
- Ubuntu, Debian, Fedora, Arch Linux

### ¿Puedo instalar FACOT sin conocimientos técnicos?

Sí, si sigues la [guía de instalación](INSTALL.md) paso a paso. Sin embargo, necesitarás:
- Saber abrir la terminal/consola
- Copiar y pegar comandos
- Navegar entre carpetas

### No tengo Git, ¿puedo instalar FACOT?

Sí, descarga el proyecto como ZIP desde GitHub:
1. Ve a https://github.com/zoeccivil/FACOT_GIT
2. Clic en "Code" → "Download ZIP"
3. Extrae y sigue la guía de instalación

### ¿Cuánto espacio necesito?

- **Instalación**: ~200 MB (Python + dependencias)
- **Base de datos**: Crece según uso (típicamente 1-50 MB)
- **Anexos**: Depende de cuántos comprobantes guardes

## 🔷 Uso del Sistema

### ¿Cómo empiezo a usar FACOT?

1. Instala siguiendo [INSTALL.md](INSTALL.md)
2. Ejecuta `python main.py`
3. Selecciona o crea una base de datos
4. Agrega tu primera empresa
5. Configura rutas de carpetas
6. ¡Comienza a crear facturas!

### ¿Dónde se guardan mis datos?

- **Base de datos**: En el archivo `.db` que seleccionaste al inicio
- **Facturas generadas**: En la carpeta que configuraste
- **Anexos**: En la carpeta de anexos que configuraste

### ¿Puedo cambiar de base de datos sin perder datos?

Sí, tus datos están en el archivo `.db`. Puedes:
- Hacer copias de seguridad (`Herramientas` → `Backup`)
- Cambiar de base de datos (`Archivo` → `Cambiar Base de Datos`)
- Migrar entre SQLite y Firebase

### ¿Cómo hago backup de mis datos?

1. Ve a `Herramientas` → `Copia de Seguridad`
2. Selecciona dónde guardar el backup
3. Se creará una copia del archivo `.db` con fecha y hora

**Tip**: Programa backups automáticos semanales en tu sistema operativo.

### ¿Puedo importar datos de otro sistema?

Depende del sistema. FACOT puede:
- ✅ Importar desde JSON (formato específico)
- ✅ Importar items desde Excel
- ❌ No tiene importador universal para otros sistemas

Si tienes datos en otro formato, puedes crear un script personalizado o contactar para ayuda.

## 🔷 Facturas

### ¿Qué tipos de NCF soporta?

FACOT soporta todos los NCF principales:
- **B01**: Crédito Fiscal
- **B02**: Consumidor Final
- **B04**: Nota de Crédito
- **B14**: Régimen Especial
- **B15**: Gubernamental

### ¿La numeración de NCF es automática?

Sí, FACOT genera automáticamente el siguiente número de secuencia basándose en el último NCF usado.

### ¿Puedo facturar en dólares o euros?

Sí, FACOT soporta múltiples monedas:
- RD$ (Pesos Dominicanos)
- USD (Dólares)
- EUR (Euros)
- Puedes agregar más en Configuración

El sistema convierte automáticamente a RD$ usando la tasa de cambio que ingreses.

### ¿Cómo aplico descuentos?

Hay dos formas:
1. **Por línea**: En la tabla de items (PR2), cada línea puede tener su descuento
2. **Manual**: Ajusta los precios directamente

### ¿Puedo adjuntar comprobantes a las facturas?

Sí, especialmente para facturas de gastos:
1. Al crear/editar una factura de gasto
2. Clic en "Adjuntar Comprobante"
3. Selecciona la imagen o PDF
4. Se guardará automáticamente en la estructura de carpetas

### ¿Cómo edito o elimino una factura?

**Editar:**
1. Doble clic en la factura en la lista
2. O clic derecho → "Editar"
3. Modifica y guarda

**Eliminar:**
1. Selecciona la factura
2. Presiona `Supr` o clic derecho → "Eliminar"
3. Confirma la eliminación

⚠️ **Advertencia**: La eliminación es permanente (a menos que tengas backup).

### ¿Puedo crear cotizaciones?

Sí, FACOT tiene un módulo completo de cotizaciones que te permite:
- Crear cotizaciones profesionales
- Convertirlas a facturas cuando se aprueben
- Usar plantillas personalizables

### ¿El ITBIS se calcula automáticamente?

Sí, si marcas "Aplicar ITBIS", se calcula automáticamente al 18% sobre el subtotal.

## 🔷 Firebase y Sincronización

### ¿Necesito Firebase?

No, es completamente opcional. Firebase es útil si:
- Quieres acceder desde varios computadores
- Necesitas trabajo colaborativo
- Quieres backup automático en la nube
- Trabajas remotamente

### ¿Firebase es gratis?

Firebase tiene un plan gratuito generoso que es suficiente para la mayoría de usuarios:
- **Spark Plan**: Gratis
  - 50,000 lecturas/día
  - 20,000 escrituras/día
  - 1 GB de almacenamiento

Para empresas grandes, hay planes de pago.

### ¿Cómo configuro Firebase?

Ver la [guía de instalación](INSTALL.md#configuración-de-firebase-opcional) para instrucciones detalladas.

Resumen:
1. Crea proyecto en Firebase Console
2. Descarga credenciales
3. Coloca en `firebase/firebase-credentials.json`
4. Activa modo Firebase en FACOT

### ¿Puedo migrar de SQLite a Firebase?

Sí, usa el script de migración:
```bash
python migrate_sqlite_to_firebase_v2.py
```

Sigue las instrucciones en pantalla. ⚠️ Haz backup primero.

### ¿Los datos en Firebase están seguros?

Sí, si configuras correctamente las reglas de seguridad:
- Autenticación requerida
- Acceso filtrado por empresa
- Comunicación encriptada (HTTPS)
- Backups automáticos de Google

Ver `firebase/firestore.rules` para reglas recomendadas.

## 🔷 Reportes

### ¿Qué reportes puedo generar?

FACOT ofrece varios reportes:
1. **Reporte Mensual**: PDF y Excel con todas las facturas del mes
2. **Cálculo de Retenciones**: Para declaraciones de impuestos
3. **Reporte por Tercero**: Análisis por cliente o proveedor
4. **Dashboard**: Estadísticas en tiempo real

### ¿Los reportes incluyen los comprobantes?

Sí, el reporte mensual en PDF puede incluir todos los anexos/comprobantes de las facturas de gastos automáticamente.

### ¿Puedo personalizar los reportes?

Los reportes tienen un formato estándar, pero puedes:
- Exportar a Excel y modificar allí
- Modificar el código en `report_generator.py`
- Crear tus propios reportes personalizados

### ¿Cómo envío reportes a mi contador?

Genera el reporte en PDF o Excel y envíalo por:
- Email
- WhatsApp
- Compartir en drive/dropbox
- Imprimir si lo prefieren físico

## 🔷 Errores Comunes

### Error: "No module named 'PyQt6'"

**Solución:**
```bash
pip install PyQt6 PyQt6-WebEngine
```

Asegúrate de estar en el entorno virtual activado.

### La aplicación no abre

**Diagnóstico:**
```bash
python main.py
```

Lee el mensaje de error. Comúnmente es:
- Falta una dependencia → Instala con `pip`
- Python incorrecto → Verifica versión 3.8+
- Archivo corrupto → Redownload del proyecto

### "Database is locked"

**Causa**: Otra instancia de FACOT está abierta o el archivo está en uso.

**Solución**:
1. Cierra todas las ventanas de FACOT
2. Si persiste, reinicia el computador
3. Verifica que el .db no esté en Dropbox sincronizando

### No encuentro mi base de datos

**Solución:**
1. Ve a `Archivo` → `Cambiar Base de Datos`
2. Navega a donde guardaste el archivo `.db`
3. Ábrelo

**Consejo**: Siempre guarda tus bases de datos en la misma carpeta.

### Los totales no cuadran

**Causas comunes:**
- Tasa de cambio incorrecta
- ITBIS no aplicado donde debía
- Error al ingresar números

**Solución:**
1. Edita la factura
2. Verifica cada campo
3. Recalcula manualmente
4. Compara con tu comprobante original

### Firebase no conecta

**Diagnóstico:**
1. Verifica que tienes internet
2. Revisa `firebase-credentials.json` está en lugar correcto
3. Verifica que el proyecto Firebase existe y está activo
4. Revisa las reglas de seguridad

Ver [SOLUCION_PROBLEMAS_FIREBASE.md](SOLUCION_PROBLEMAS_FIREBASE.md)

### El PDF generado está en blanco

**Posibles causas:**
- Error en la plantilla
- Datos faltantes
- Problema con fpdf

**Solución:**
```bash
pip uninstall fpdf
pip install fpdf
```

Si persiste, revisa la consola para el mensaje de error específico.

## 🆘 ¿Necesitas Más Ayuda?

### Documentación Adicional
- 📖 [README.md](README.md) - Descripción general
- 🔧 [INSTALL.md](INSTALL.md) - Instalación paso a paso
- 🏗️ [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitectura técnica
- 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) - Cómo contribuir
- 📝 [CHANGELOG.md](CHANGELOG.md) - Historial de cambios

### Soporte
1. **Busca en Issues**: https://github.com/zoeccivil/FACOT_GIT/issues
2. **Crea un Issue nuevo**: Describe tu problema detalladamente
3. **Email**: (si está disponible en el proyecto)

### Comunidad
- Comparte tu experiencia
- Ayuda a otros usuarios
- Sugiere mejoras
- Reporta bugs

---

**Última Actualización:** 2025-11-09
**¿Falta alguna pregunta?** Abre un issue sugiriendo agregarla al FAQ.
