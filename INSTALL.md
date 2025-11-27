# Guía de Instalación - FACOT

Esta guía proporciona instrucciones detalladas para instalar y configurar FACOT en tu sistema.

## 📋 Tabla de Contenidos

1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Instalación en Windows](#instalación-en-windows)
3. [Instalación en Linux](#instalación-en-linux)
4. [Instalación en macOS](#instalación-en-macos)
5. [Configuración Inicial](#configuración-inicial)
6. [Configuración de Firebase (Opcional)](#configuración-de-firebase-opcional)
7. [Solución de Problemas](#solución-de-problemas)

## 🖥️ Requisitos del Sistema

### Mínimos
- **Sistema Operativo**: Windows 10+, Ubuntu 20.04+, macOS 10.15+
- **Python**: 3.8 o superior
- **RAM**: 4 GB
- **Disco**: 500 MB de espacio libre
- **Resolución**: 1280x720 o superior

### Recomendados
- **Python**: 3.10 o superior
- **RAM**: 8 GB o más
- **Disco**: 2 GB de espacio libre
- **Resolución**: 1920x1080 o superior

## 🪟 Instalación en Windows

### Paso 1: Instalar Python

1. Descarga Python desde [python.org](https://www.python.org/downloads/)
2. Ejecuta el instalador
3. **IMPORTANTE**: Marca la opción "Add Python to PATH"
4. Haz clic en "Install Now"

#### Verificar instalación:
```cmd
python --version
pip --version
```

### Paso 2: Descargar FACOT

**Opción A: Clonar con Git**
```cmd
git clone https://github.com/zoeccivil/FACOT_GIT.git
cd FACOT_GIT
```

**Opción B: Descargar ZIP**
1. Visita https://github.com/zoeccivil/FACOT_GIT
2. Haz clic en "Code" → "Download ZIP"
3. Extrae el archivo ZIP
4. Abre Command Prompt en la carpeta extraída

### Paso 3: Crear Entorno Virtual

```cmd
python -m venv venv
venv\Scripts\activate
```

Verás `(venv)` al inicio de la línea de comandos.

### Paso 4: Instalar Dependencias

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 5: Ejecutar FACOT

```cmd
python main.py
```

### Crear Acceso Directo (Opcional)

1. Crea un archivo `FACOT.bat` con:
```batch
@echo off
cd /d "C:\ruta\a\FACOT_GIT"
call venv\Scripts\activate
python main.py
pause
```

2. Crea un acceso directo al archivo `.bat`
3. Cambia el ícono si lo deseas

## 🐧 Instalación en Linux

### Paso 1: Instalar Python y Git

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip git
```

**Arch:**
```bash
sudo pacman -S python python-pip git
```

### Paso 2: Clonar Repositorio

```bash
git clone https://github.com/zoeccivil/FACOT_GIT.git
cd FACOT_GIT
```

### Paso 3: Crear Entorno Virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### Paso 4: Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 5: Ejecutar FACOT

```bash
python main.py
```

### Crear Lanzador de Aplicación (Opcional)

Crea `~/.local/share/applications/facot.desktop`:

```ini
[Desktop Entry]
Name=FACOT
Comment=Sistema de Gestión de Facturas
Exec=/ruta/completa/a/FACOT_GIT/venv/bin/python /ruta/completa/a/FACOT_GIT/main.py
Icon=/ruta/completa/a/FACOT_GIT/icon.png
Terminal=false
Type=Application
Categories=Office;Finance;
```

## 🍎 Instalación en macOS

### Paso 1: Instalar Homebrew (si no lo tienes)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Paso 2: Instalar Python y Git

```bash
brew install python@3.10 git
```

### Paso 3: Clonar Repositorio

```bash
git clone https://github.com/zoeccivil/FACOT_GIT.git
cd FACOT_GIT
```

### Paso 4: Crear Entorno Virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### Paso 5: Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 6: Ejecutar FACOT

```bash
python main.py
```

## ⚙️ Configuración Inicial

### Primera Ejecución

1. **Seleccionar Base de Datos**
   - Al iniciar, FACOT pedirá seleccionar un archivo `.db`
   - Opciones:
     - Crear una nueva base de datos (selecciona una ubicación y nombre)
     - Abrir una base de datos existente

2. **Agregar Primera Empresa**
   - Ir a `Configuración` → `Gestión de Empresas`
   - Hacer clic en "Agregar Empresa"
   - Llenar información:
     - Nombre de la empresa
     - RNC (Registro Nacional de Contribuyentes)
     - Dirección
   - Guardar

3. **Configurar Rutas**
   - **Plantilla de Facturas**: Archivo Excel (.xlsx) usado como plantilla
   - **Carpeta de Salida**: Donde se guardarán las facturas generadas
   - **Carpeta de Anexos**: Donde se guardarán los comprobantes escaneados

### Estructura de Carpetas Recomendada

```
Documentos/
└── FACOT/
    ├── Bases_de_Datos/
    │   ├── empresa1.db
    │   └── empresa2.db
    ├── Plantillas/
    │   ├── factura_template.xlsx
    │   └── cotizacion_template.xlsx
    ├── Facturas_Generadas/
    │   ├── Empresa1/
    │   │   ├── Facturas B01/
    │   │   └── Facturas B02/
    │   └── Empresa2/
    └── Anexos/
        ├── Empresa1/
        │   ├── 2025/
        │   │   ├── 01/
        │   │   └── 02/
        └── Empresa2/
```

## ☁️ Configuración de Firebase (Opcional)

Para habilitar la sincronización en la nube:

### 1. Crear Proyecto Firebase

1. Visita https://console.firebase.google.com/
2. Crea un nuevo proyecto
3. Habilita Firestore Database
4. Crea reglas de seguridad (ver `firebase/firestore.rules`)

### 2. Obtener Credenciales

1. Ve a Configuración del Proyecto → Cuentas de Servicio
2. Genera nueva clave privada
3. Descarga el archivo JSON
4. Renombra a `firebase-credentials.json`
5. Coloca en la carpeta `firebase/`

### 3. Configurar en FACOT

1. Abrir FACOT
2. Hacer clic en el indicador de conexión (barra inferior)
3. Seleccionar "Modo Firebase"
4. Ingresar credenciales si es necesario

### 4. Migrar Datos (Opcional)

Para migrar de SQLite a Firebase:

```bash
python migrate_sqlite_to_firebase_v2.py
```

Sigue las instrucciones en pantalla.

## 🔧 Solución de Problemas

### Error: "python no se reconoce como comando"

**Windows:**
1. Verifica que Python esté en PATH
2. Reinstala Python marcando "Add to PATH"
3. O usa `py` en lugar de `python`

**Linux/macOS:**
- Usa `python3` en lugar de `python`

### Error: "No module named 'PyQt6'"

```bash
# Asegúrate de estar en el entorno virtual
# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

# Reinstala dependencias
pip install -r requirements.txt
```

### Error: "Permission denied"

**Linux/macOS:**
```bash
chmod +x main.py
```

### La aplicación no abre o se cierra inmediatamente

1. Ejecuta desde la terminal para ver errores:
   ```bash
   python main.py
   ```

2. Verifica que todas las dependencias estén instaladas:
   ```bash
   pip install -r requirements.txt
   ```

3. Verifica la versión de Python:
   ```bash
   python --version  # Debe ser 3.8+
   ```

### Error de importación de Firebase

Si no vas a usar Firebase:
1. Comenta las importaciones de Firebase en el código
2. O instala firebase-admin:
   ```bash
   pip install firebase-admin
   ```

### Error al generar PDFs

Instala/reinstala fpdf:
```bash
pip uninstall fpdf
pip install fpdf
```

### Problemas con Excel

Verifica que openpyxl esté instalado:
```bash
pip install openpyxl
```

### Base de datos bloqueada

- Cierra todas las instancias de FACOT
- Asegúrate de que ningún otro programa esté accediendo a la BD
- En caso extremo, reinicia el sistema

### Errores de visualización en Linux

Instala bibliotecas Qt adicionales:
```bash
# Ubuntu/Debian
sudo apt install libxcb-cursor0 libxcb-xinerama0

# Fedora
sudo dnf install xcb-util-cursor
```

## 📚 Recursos Adicionales

- **Documentación Completa**: Ver [README.md](README.md)
- **Arquitectura**: Ver [ARCHITECTURE.md](ARCHITECTURE.md)
- **Contribuir**: Ver [CONTRIBUTING.md](CONTRIBUTING.md)
- **Cambios**: Ver [CHANGELOG.md](CHANGELOG.md)

## 🆘 Obtener Ayuda

Si sigues teniendo problemas:

1. **Revisa la documentación**: Lee todos los archivos .md del proyecto
2. **Issues de GitHub**: Busca issues similares en https://github.com/zoeccivil/FACOT_GIT/issues
3. **Crea un Issue**: Si no encuentras solución, abre un nuevo issue con:
   - Descripción del problema
   - Pasos para reproducir
   - Mensajes de error completos
   - Sistema operativo y versión de Python
   - Output de `pip list`

## ✅ Verificación de Instalación

Para verificar que todo está correctamente instalado:

```bash
# Activa el entorno virtual
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Verifica Python
python --version

# Verifica dependencias
pip list

# Ejecuta FACOT
python main.py
```

Si FACOT abre correctamente, ¡la instalación fue exitosa! 🎉

---

**Última Actualización:** 2025-11-09
**Versión del Documento:** 1.0
