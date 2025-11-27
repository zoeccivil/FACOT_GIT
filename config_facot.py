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

# --- CONFIGURACIÓN DE EMAIL (SMTP) ---
def get_email_config():
    """
    Obtiene la configuración de email.
    Prioriza variables de entorno sobre config guardado.
    
    Returns:
        dict: Configuración de email con claves:
            - smtp_host
            - smtp_port
            - smtp_user
            - smtp_password
            - smtp_use_tls
            - smtp_from_email
    """
    # Priorizar variables de entorno (más seguro)
    env_config = {
        'smtp_host': os.getenv('SMTP_HOST'),
        'smtp_port': int(os.getenv('SMTP_PORT', 587)),
        'smtp_user': os.getenv('SMTP_USER'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'smtp_use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
        'smtp_from_email': os.getenv('SMTP_FROM_EMAIL'),
    }
    
    # Si hay variables de entorno configuradas, usarlas
    if env_config['smtp_host'] and env_config['smtp_user']:
        return env_config
    
    # Fallback a configuración guardada (menos seguro)
    config = load_config()
    saved_config = config.get('email_config', {})
    
    return {
        'smtp_host': saved_config.get('smtp_host', ''),
        'smtp_port': saved_config.get('smtp_port', 587),
        'smtp_user': saved_config.get('smtp_user', ''),
        'smtp_password': saved_config.get('smtp_password', ''),  # NO RECOMENDADO
        'smtp_use_tls': saved_config.get('smtp_use_tls', True),
        'smtp_from_email': saved_config.get('smtp_from_email', ''),
    }

def set_email_config(email_cfg):
    """
    Guarda configuración de email en archivo.
    
    NOTA: No se recomienda guardar contraseñas en archivos.
    Use variables de entorno en su lugar.
    
    Args:
        email_cfg: dict con configuración de email
    """
    config = load_config()
    config['email_config'] = email_cfg
    save_config(config)

def clear_email_password():
    """
    Elimina la contraseña guardada de la configuración.
    """
    config = load_config()
    if 'email_config' in config and 'smtp_password' in config['email_config']:
        del config['email_config']['smtp_password']
        save_config(config)