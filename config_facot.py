import json
import os

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

# --- RUTA DE BASE DE DATOS ---
def get_db_path():
    config = load_config()
    return config.get("db_path", "")

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

# --- MODO DE CONEXIÓN PREFERIDO ---
def get_connection_mode():
    """
    Obtiene el modo de conexión preferido guardado.
    
    Returns:
        str: "SQLITE", "FIREBASE", o "AUTO" (default)
    """
    config = load_config()
    return config.get("connection_mode", "AUTO")

def set_connection_mode(mode):
    """
    Guarda el modo de conexión preferido.
    
    Args:
        mode: "SQLITE", "FIREBASE", o "AUTO"
    """
    config = load_config()
    config["connection_mode"] = mode.upper()
    save_config(config)