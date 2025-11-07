"""
Configuración de FACOT: resolución de ruta de BD y parámetros opcionales.
- Permite configurar una ruta explícita vía:
  1) Variable de entorno FACOT_DB_PATH
  2) Archivo facot_config.json (clave: "db_path")
  3) Fallback automático: copia semilla data/facturas_db.db a %APPDATA%\\FACOT\\facturas_db.db
"""
from __future__ import annotations

import json
import os
import json, os
from pathlib import Path
from typing import Optional

try:
    from utils.runtime_init import resolve_or_copy_db
except Exception:
    def resolve_or_copy_db(explicit_path: Optional[str]) -> str:
        # Fallback ultra-simple si faltan utilidades
        p = Path(explicit_path or "").expanduser()
        if explicit_path and p.parent.exists():
            try:
                p.touch(exist_ok=True)
                return str(p)
            except Exception:
                pass
        appdata = os.environ.get("APPDATA") or str(Path.home())
        dst = Path(appdata) / "FACOT" / "facturas_db.db"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            dst.touch()
        return str(dst)

CONFIG_FILE = "facot_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

_DB_PATH: Optional[str] = None

def _read_json_config() -> Optional[str]:
    """
    Lee facot_config.json si existe junto al ejecutable (dist/FACOT) o en raíz del proyecto en desarrollo.
    Espera: {"db_path": "C:/ruta/a/mi_db.db"}
    """
    # 1) junto al ejecutable o en sys._MEIPASS (PyInstaller coloca el JSON al lado del exe por --add-data)
    candidates = [
        Path(os.getcwd()) / "facot_config.json",
        Path(__file__).resolve().parent / "facot_config.json",
    ]
    for c in candidates:
        try:
            if c.exists():
                data = json.loads(c.read_text(encoding="utf-8"))
                dbp = (data.get("db_path") or "").strip()
                if dbp:
                    return dbp
        except Exception:
            continue
    return None

def get_db_path() -> str:
    """
    Devuelve la ruta de BD para el runtime. Prioridad:
    - ENV FACOT_DB_PATH
    - facot_config.json (db_path)
    - Fallback: %APPDATA%\\FACOT\\facturas_db.db (copiando semilla si está incluida)
    """
    global _DB_PATH
    if _DB_PATH:
        return _DB_PATH

    env_path = (os.environ.get("FACOT_DB_PATH") or "").strip() or None
    json_path = _read_json_config()

    _DB_PATH = resolve_or_copy_db(env_path or json_path)
    return _DB_PATH

def set_db_path(path):
    config = load_config()
    config["db_path"] = path
    save_config(config)

# --- RUTA DE PLANTILLA DE FACTURA ---
def get_template_path():
    config = load_config()
    return config.get("template_path", "")

def set_template_path(path):
    config = load_config()
    config["template_path"] = path
    save_config(config)

# --- CARPETA DE SALIDA DE FACTURAS Y COTIZACIONES ---
def get_output_folder():
    config = load_config()
    return config.get("output_folder", "")

def set_output_folder(path):
    config = load_config()
    config["output_folder"] = path
    save_config(config)

# --- EMPRESA ACTIVA ---
def get_empresa_activa():
    config = load_config()
    return config.get("empresa_activa", "")

def set_empresa_activa(company_id):
    config = load_config()
    config["empresa_activa"] = company_id
    save_config(config)

# --- CONFIGURACIÓN POR EMPRESA ---
def get_empresa_config(company_id):
    config = load_config()
    empresas = config.get("empresas", {})
    return empresas.get(str(company_id), {})

def set_empresa_config(company_id, empresa_cfg):
    config = load_config()
    if "empresas" not in config:
        config["empresas"] = {}
    config["empresas"][str(company_id)] = empresa_cfg
    save_config(config)

# --- CARPETA DE DESCARGAS/ORIGEN ---
def get_downloads_folder_path():
    config = load_config()
    empresa_id = get_empresa_activa()
    empresa_cfg = get_empresa_config(empresa_id)
    # Prioridad: empresa > global
    return empresa_cfg.get("carpeta_origen") or config.get("downloads_folder_path", "")

def set_downloads_folder_path(path):
    config = load_config()
    empresa_id = get_empresa_activa()
    empresa_cfg = get_empresa_config(empresa_id)
    empresa_cfg["carpeta_origen"] = path
    config["downloads_folder_path"] = path
    set_empresa_config(empresa_id, empresa_cfg)
    save_config(config)