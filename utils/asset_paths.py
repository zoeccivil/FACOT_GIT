from __future__ import annotations
import os
import json
import shutil
from typing import Optional

_CONFIG_CACHE: Optional[dict] = None

def _load_config() -> dict:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    cfg_path = os.path.join(os.getcwd(), "config", "app_config.json")
    data = {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    _CONFIG_CACHE = data
    return data

def get_assets_root() -> str:
    cfg = _load_config()
    root = cfg.get("assets_root") or os.path.join(os.getcwd(), "data")
    root = os.path.abspath(os.path.normpath(root))
    os.makedirs(root, exist_ok=True)
    return root

def resolve_logo_uri(path_or_uri: str | None) -> str:
    """
    Devuelve un file:/// URI resolviendo:
    - Si ya viene file:/// -> se devuelve tal cual.
    - Si es ruta absoluta -> se convierte a file:/// si existe.
    - Si es relativa -> se resuelve contra assets_root.
    - Si no existe, retorna ''.
    """
    if not path_or_uri:
        return ""
    txt = str(path_or_uri).strip()
    if not txt:
        return ""
    low = txt.lower()
    if low.startswith("file:///"):
        return txt
    p = os.path.normpath(txt)
    # Absoluta
    if os.path.isabs(p):
        abspath = os.path.abspath(p)
        if os.path.exists(abspath):
            return "file:///" + abspath.replace("\\", "/")
        return ""
    # Relativa a assets_root
    root = get_assets_root()
    abs_candidate = os.path.abspath(os.path.join(root, p))
    if os.path.exists(abs_candidate):
        return "file:///" + abs_candidate.replace("\\", "/")
    return ""

def copy_logo_to_assets(src_path: str, company_id: int) -> str:
    """
    Copia el archivo al directorio assets_root/company_{id}/logo.ext
    Retorna ruta relativa: 'company_{id}/logo.png'
    """
    if not src_path:
        raise ValueError("src_path vacío")
    src_abs = os.path.abspath(src_path)
    if not os.path.exists(src_abs):
        raise FileNotFoundError(src_abs)
    root = get_assets_root()
    ext = os.path.splitext(src_abs)[1].lower() or ".png"
    rel_dir = f"company_{company_id}"
    rel_path = os.path.join(rel_dir, f"logo{ext}").replace("\\", "/")
    dest_dir = os.path.join(root, rel_dir)
    os.makedirs(dest_dir, exist_ok=True)
    dest_abs = os.path.join(dest_dir, f"logo{ext}")
    shutil.copyfile(src_abs, dest_abs)
    return rel_path

def relativize_if_under_assets(path_or_uri: str) -> str:
    """
    Si path_or_uri apunta dentro de assets_root, devuelve ruta relativa.
    Si es file:/// que apunta dentro, convierte a relativo.
    En otro caso, retorna el valor original.
    """
    if not path_or_uri:
        return ""
    root = get_assets_root()
    root_norm = os.path.abspath(root)
    txt = path_or_uri.strip()
    low = txt.lower()
    # file:///
    if low.startswith("file:///"):
        abs_from_uri = txt[8:].replace("/", os.sep)
        abs_from_uri = os.path.abspath(abs_from_uri)
        if abs_from_uri.startswith(root_norm):
            rel = os.path.relpath(abs_from_uri, root_norm).replace("\\", "/")
            return rel
        return txt
    # absoluta
    p = os.path.abspath(txt)
    if os.path.isabs(p) and p.startswith(root_norm):
        rel = os.path.relpath(p, root_norm).replace("\\", "/")
        return rel
    return txt