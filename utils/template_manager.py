
from __future__ import annotations

import json
import os
import shutil
from typing import Dict, Optional
from pathlib import Path

import facot_config  # as en tu proyecto

# Estructura recomendada:
# <project_root>/data/
#    company_<id>/
#       logo.png
#    templates/
#       company_<id>.json

DEFAULT_TEMPLATE: Dict = {
    "show_logo": True,
    "logo_path": "",                # ruta relativa dentro data/ (e.g. "company_1/logo.png")
    "header_lines": ["", "", ""],
    "footer_lines": ["", ""],
    "primary_color": "#1f4e79",
    "font_name": "Arial",
    "font_size": 10,
    "logo_width_px": 180,
    "layout": "default"
}

def get_data_root() -> str:
    """
    Devuelve la carpeta raíz para data (usa facot_config.get_data_dir() si existe,
    si no, crea ./data en la raíz del proyecto).
    """
    try:
        root = facot_config.get_data_dir()
        if root:
            return str(Path(root).resolve())
    except Exception:
        pass
    # fallback: data/ en la carpeta actual (donde ejecutas main.py)
    root = Path.cwd() / "data"
    root.mkdir(parents=True, exist_ok=True)
    return str(root)

def ensure_dirs():
    root = Path(get_data_root())
    (root / "templates").mkdir(parents=True, exist_ok=True)

def template_path(company_id: int) -> Path:
    ensure_dirs()
    root = Path(get_data_root())
    return root / "templates" / f"company_{company_id}.json"

def company_dir(company_id: int) -> Path:
    root = Path(get_data_root())
    d = root / f"company_{company_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_template(company_id: int, template: Dict):
    """
    Guarda la plantilla en data/templates/company_{id}.json
    El campo logo_path debería ser relativo a data/ (ej. "company_1/logo.png")
    """
    ensure_dirs()
    p = template_path(company_id)
    # Normalizar: no guardar absolute paths for logo
    tpl = dict(DEFAULT_TEMPLATE)
    tpl.update(template or {})
    # write json with utf-8
    with open(p, "w", encoding="utf-8") as f:
        json.dump(tpl, f, ensure_ascii=False, indent=2)

def load_template(company_id: int) -> Dict:
    p = template_path(company_id)
    if not p.exists():
        return dict(DEFAULT_TEMPLATE)
    try:
        with open(p, "r", encoding="utf-8") as f:
            tpl = json.load(f)
        # merge with defaults to avoid missing keys
        merged = dict(DEFAULT_TEMPLATE)
        merged.update(tpl or {})
        return merged
    except Exception:
        return dict(DEFAULT_TEMPLATE)

def copy_logo_to_company_dir(src_path: str, company_id: int) -> Optional[str]:
    """
    Copia la imagen seleccionada al directorio data/company_{id}/ y devuelve la ruta relativa
    (relativa a data root), por ejemplo "company_1/logo.png".
    Devuelve None si falla.
    """
    try:
        src = Path(src_path)
        if not src.exists():
            return None
        dest_dir = company_dir(company_id)
        # Mantener extensión original
        ext = src.suffix.lower()
        dest_name = f"logo{ext}"
        dest_path = dest_dir / dest_name
        # Copiar (sobrescribe si existe)
        shutil.copy2(str(src), str(dest_path))
        # devolver ruta relativa a data root
        root = Path(get_data_root())
        rel = dest_path.relative_to(root)
        return str(rel).replace("\\", "/")
    except Exception:
        return None