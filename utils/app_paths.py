from __future__ import annotations
import sys
import os
from pathlib import Path
from typing import Iterable

def _user_data_root() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    p = Path(base) / "FACOT"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _user_templates_dir() -> Path:
    p = _user_data_root() / "templates"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _user_data_dir() -> Path:
    p = _user_data_root() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _base_dir() -> Path:
    # Onedir: carpeta del exe; Onefile: sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        try:
            return Path(sys._MEIPASS)  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        return Path(sys.argv[0]).resolve().parent
    except Exception:
        return Path(__file__).resolve().parent.parent

def _dev_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _candidates(parts: Iterable[str]) -> list[Path]:
    parts = list(parts)
    base = _base_dir()
    dev = _dev_root()
    user_tpl = _user_templates_dir()
    user_dat = _user_data_dir()

    # Candidatos comunes
    cands: list[Path] = [
        base.joinpath(*parts),                  # ./...
        base.joinpath("_internal", *parts),     # ./_internal/...
    ]

    # Si piden "templates/...", incluye %APPDATA%/FACOT/templates
    if parts and parts[0] == "templates":
        cands.append(user_tpl.joinpath(*parts[1:]) if len(parts) > 1 else user_tpl)

    # Si piden "data/...", incluye %APPDATA%/FACOT/data
    if parts and parts[0] == "data":
        cands.append(user_dat.joinpath(*parts[1:]) if len(parts) > 1 else user_dat)

    # Dev root al final
    cands.append(dev.joinpath(*parts))
    return cands

def resource_path(*parts: str, must_exist: bool = False) -> str:
    """
    Busca en:
    1) carpeta del exe
    2) _internal (layout PyInstaller 6.x)
    3) %APPDATA%/FACOT/templates para 'templates/...'
    4) %APPDATA%/FACOT/data para 'data/...'
    5) raíz del proyecto (desarrollo)
    """
    cands = _candidates(parts)
    for p in cands:
        try:
            if p.exists():
                return str(p)
        except Exception:
            continue
    return str(cands[0] if not must_exist else cands[-1])

# archivo: utils/app_paths.py

import os
import sys

def get_base_path() -> str:
    """
    Determina la ruta base de la aplicación.
    Si se ejecuta como EXE (PyInstaller), usa sys._MEIPASS.
    Si se ejecuta como script, usa el directorio de trabajo actual.
    """
    if getattr(sys, 'frozen', False):
        # Modo PyInstaller (EXE)
        return sys._MEIPASS
    else:
        # Modo de desarrollo (script Python). Vuelve a la raíz del proyecto.
        # Asume que utils/ está un nivel abajo.
        return os.path.abspath(os.path.dirname(__file__) + "/..")

def get_resource_path(relative_path: str) -> str:
    """
    Obtiene la ruta completa de un recurso empaquetado.
    """
    base = get_base_path()
    return os.path.join(base, relative_path)