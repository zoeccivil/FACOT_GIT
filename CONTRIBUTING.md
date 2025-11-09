# Guía de Contribución - FACOT

¡Gracias por tu interés en contribuir a FACOT! Esta guía te ayudará a comenzar.

## 📋 Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Contribuir](#cómo-contribuir)
- [Estándares de Código](#estándares-de-código)
- [Proceso de Pull Request](#proceso-de-pull-request)
- [Reportar Bugs](#reportar-bugs)
- [Sugerir Mejoras](#sugerir-mejoras)
- [Estructura del Proyecto](#estructura-del-proyecto)

## 🤝 Código de Conducta

Este proyecto se adhiere a un código de conducta. Al participar, se espera que mantengas este código. Por favor reporta comportamientos inaceptables.

### Nuestros Compromisos

- Usar un lenguaje acogedor e inclusivo
- Ser respetuoso con diferentes puntos de vista
- Aceptar críticas constructivas
- Enfocarse en lo mejor para la comunidad
- Mostrar empatía hacia otros miembros

## 🚀 Cómo Contribuir

### 1. Fork y Clone

```bash
# Fork el repositorio en GitHub
# Luego clona tu fork
git clone https://github.com/TU_USUARIO/FACOT_GIT.git
cd FACOT_GIT

# Agrega el repositorio original como upstream
git remote add upstream https://github.com/zoeccivil/FACOT_GIT.git
```

### 2. Crear una Rama

```bash
# Actualiza tu main
git checkout main
git pull upstream main

# Crea una nueva rama para tu feature
git checkout -b feature/nombre-descriptivo

# O para un bugfix
git checkout -b fix/descripcion-del-bug
```

### 3. Realizar Cambios

- Realiza tus cambios
- Sigue los [Estándares de Código](#estándares-de-código)
- Agrega pruebas si es aplicable
- Actualiza la documentación

### 4. Commit

```bash
git add .
git commit -m "Descripción clara y concisa del cambio"
```

#### Mensajes de Commit

Usa mensajes descriptivos siguiendo este formato:

```
tipo: descripción breve

Descripción más detallada si es necesaria.
Explica el QUÉ y el POR QUÉ, no el CÓMO.

Fixes #123
```

**Tipos de commit:**
- `feat`: Nueva característica
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Formato, punto y coma faltantes, etc.
- `refactor`: Refactorización de código
- `test`: Agregar o modificar tests
- `chore`: Mantenimiento, dependencias, etc.

**Ejemplos:**
```
feat: agregar soporte para múltiples listas de precios

Implementa la funcionalidad para manejar price1, price2, price3
por categoría de producto, permitiendo selección por cliente.

Fixes #45
```

```
fix: corregir cálculo de ITBIS en moneda extranjera

El ITBIS no se estaba convirtiendo correctamente cuando
la factura era en USD. Ahora aplica la tasa de cambio.

Fixes #67
```

### 5. Push y Pull Request

```bash
# Push a tu fork
git push origin feature/nombre-descriptivo

# Crea un Pull Request en GitHub
```

## 📝 Estándares de Código

### Python (PEP 8)

Seguimos las convenciones PEP 8 para código Python:

```python
# ✅ BIEN
def calcular_itbis(subtotal, tasa=0.18):
    """
    Calcula el ITBIS sobre un subtotal.
    
    Args:
        subtotal (float): El monto base
        tasa (float): Tasa de ITBIS (por defecto 18%)
    
    Returns:
        float: El monto del ITBIS
    """
    return subtotal * tasa


# ❌ MAL
def CalcularITBIS(s,t=.18):
    return s*t
```

### Documentación de Código

- Documenta todas las clases y funciones públicas
- Usa docstrings en español
- Incluye ejemplos cuando sea apropiado

```python
def agregar_factura(self, datos_factura: dict, items: list) -> int:
    """
    Agrega una nueva factura a la base de datos.
    
    Args:
        datos_factura (dict): Diccionario con los datos de la factura
            - company_id (int): ID de la empresa
            - invoice_type (str): 'emitida' o 'gasto'
            - invoice_date (str): Fecha en formato 'YYYY-MM-DD'
            - rnc (str): RNC del cliente/proveedor
            - total_amount (float): Monto total
        items (list): Lista de diccionarios con los items
            - description (str): Descripción del item
            - quantity (float): Cantidad
            - unit_price (float): Precio unitario
    
    Returns:
        int: ID de la factura creada
        
    Raises:
        IntegrityError: Si la factura ya existe (RNC + Número duplicado)
        ValueError: Si los datos son inválidos
        
    Example:
        >>> factura = {
        ...     'company_id': 1,
        ...     'invoice_type': 'emitida',
        ...     'invoice_date': '2025-01-15',
        ...     'rnc': '123456789',
        ...     'total_amount': 11800.00
        ... }
        >>> items = [{'description': 'Cemento', 'quantity': 10, 'unit_price': 1000}]
        >>> factura_id = controller.agregar_factura(factura, items)
        >>> print(f"Factura creada con ID: {factura_id}")
    """
    # Implementación...
```

### Organización de Imports

```python
# 1. Bibliotecas estándar de Python
import os
import sys
from datetime import datetime

# 2. Bibliotecas de terceros
import pandas as pd
from PyQt6.QtWidgets import QWidget
from firebase_admin import firestore

# 3. Módulos locales
from logic import LogicController
from services.company_profile_service import CompanyProfileService
```

### Nombres de Variables

```python
# ✅ BIEN - Nombres descriptivos en español
nombre_empresa = "Mi Empresa SRL"
total_factura_rd = 11800.00
lista_items = []
tasa_cambio_usd = 58.50

# ❌ MAL - Nombres poco claros o en inglés mezclado
ne = "Mi Empresa SRL"
total = 11800.00
list = []
rate = 58.50
```

## 🔍 Proceso de Pull Request

1. **Asegúrate de que tu código:**
   - Sigue los estándares de código
   - Incluye tests si aplica
   - Actualiza la documentación
   - No rompe funcionalidad existente

2. **Completa la plantilla del PR:**
   - Descripción clara de los cambios
   - Tipo de cambio (feature, fix, docs, etc.)
   - Issues relacionados
   - Capturas de pantalla si hay cambios visuales

3. **Verifica que:**
   - Todos los tests pasen
   - No hay conflictos de merge
   - El código está actualizado con main

4. **Espera la revisión:**
   - Responde a comentarios
   - Realiza cambios solicitados
   - Se paciente y respetuoso

## 🐛 Reportar Bugs

Antes de reportar un bug, verifica que no exista ya un issue similar.

### Plantilla de Bug Report

```markdown
**Descripción del Bug**
Descripción clara y concisa del bug.

**Pasos para Reproducir**
1. Ir a '...'
2. Hacer clic en '...'
3. Desplazarse hasta '...'
4. Ver error

**Comportamiento Esperado**
Qué esperabas que sucediera.

**Capturas de Pantalla**
Si aplica, agrega capturas de pantalla.

**Entorno:**
 - OS: [ej. Windows 10]
 - Python: [ej. 3.9.5]
 - Versión FACOT: [ej. 2.0]
 - Base de datos: [SQLite/Firebase]

**Contexto Adicional**
Cualquier otra información relevante.
```

## 💡 Sugerir Mejoras

### Plantilla de Feature Request

```markdown
**¿Tu solicitud está relacionada con un problema?**
Descripción clara del problema. Ej. "Me frustra cuando..."

**Describe la solución que te gustaría**
Descripción clara de lo que quieres que suceda.

**Describe alternativas consideradas**
Otras soluciones o características que consideraste.

**Contexto Adicional**
Capturas, mockups, o cualquier contexto adicional.
```

## 📁 Estructura del Proyecto

```
FACOT_GIT/
├── main.py                   # Punto de entrada
├── logic.py                  # Lógica de negocio
├── ui_mainwindow.py         # UI principal
├── config_facot.py          # Configuración
│
├── services/                # Servicios del sistema
│   ├── company_profile_service.py
│   ├── unit_resolver.py
│   └── ...
│
├── data_access/            # Acceso a datos
│   ├── sqlite_data_access.py
│   ├── firebase_data_access.py
│   └── data_access_factory.py
│
├── dialogs/                # Ventanas de diálogo
│   ├── invoice_preview_dialog.py
│   ├── quotation_preview_dialog.py
│   └── ...
│
├── widgets/                # Widgets personalizados
│   └── connection_status_bar.py
│
├── templates/              # Plantillas HTML
│   ├── invoice_template.html
│   └── quotation_template.html
│
├── firebase/               # Configuración Firebase
│   ├── firebase-credentials.json
│   └── firestore.rules
│
├── tests/                  # Tests (TODO)
│   ├── test_logic.py
│   └── test_services.py
│
└── docs/                   # Documentación
    ├── README_PR1.md
    ├── README_PR2.md
    └── ...
```

## 🧪 Tests

Aunque aún no hay un framework de tests completo, se recomienda:

```python
# TODO: Implementar tests unitarios
# Ejemplo de estructura deseada:

import unittest
from logic import LogicController

class TestLogicController(unittest.TestCase):
    def setUp(self):
        """Configuración antes de cada test"""
        self.db_path = ':memory:'  # BD en memoria para tests
        self.logic = LogicController(self.db_path)
    
    def test_agregar_factura(self):
        """Test de agregar factura"""
        factura = {...}
        items = [...]
        factura_id = self.logic.add_invoice(factura, items)
        self.assertIsNotNone(factura_id)
    
    def tearDown(self):
        """Limpieza después de cada test"""
        self.logic.close_connection()
```

## 📚 Recursos Adicionales

- [Documentación Python](https://docs.python.org/es/3/)
- [PEP 8 en Español](https://recursospython.com/pep8es.pdf)
- [Git Flow](https://www.atlassian.com/es/git/tutorials/comparing-workflows/gitflow-workflow)
- [Markdown Guide](https://www.markdownguide.org/basic-syntax/)

## ❓ Preguntas

Si tienes preguntas, puedes:
- Abrir un issue con la etiqueta `question`
- Revisar issues cerrados similares
- Consultar la documentación existente

## 🎯 Áreas que Necesitan Ayuda

Siempre buscamos ayuda en:

1. **Tests Unitarios** - Implementar suite de tests
2. **Documentación** - Mejorar guías de usuario
3. **UI/UX** - Mejorar interfaz de usuario
4. **Performance** - Optimizar consultas y procesos
5. **Traducciones** - Soporte multiidioma (próximamente)

## 📈 Hoja de Ruta

Ver [SUGERENCIAS.txt](SUGERENCIAS.txt) para características planificadas.

Próximas prioridades:
- [ ] Sistema de categorías con colores
- [ ] Múltiples listas de precios
- [ ] Sistema de auditoría completo
- [ ] Importación masiva desde CSV
- [ ] Suite de tests automatizados

---

¡Gracias por contribuir a FACOT! 🎉

Cada contribución, grande o pequeña, es valiosa y apreciada.
