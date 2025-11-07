from __future__ import annotations
import os, shutil
from pathlib import Path
from typing import Optional

def user_data_dir(app_name: str = "FACOT") -> Path:
    """
    Carpeta de datos del usuario:
    - Windows: %APPDATA%\FACOT
    - Otros: ~\FACOT
    """
    base = os.environ.get("APPDATA") or str(Path.home())
    p = Path(base) / app_name
    p.mkdir(parents=True, exist_ok=True)
    return p

def ensure_db(initial_db_rel: str = "data/facturas_db.db", target_name: str = "facturas_db.db") -> str:
    """
    Garantiza una BD escribible en %APPDATA%\FACOT copiando la semilla incluida en el paquete si fuese necesario.
    Devuelve la ruta de trabajo (writable).
    """
    from utils.app_paths import resource_path
    dst = user_data_dir() / target_name
    if not dst.exists():
        src = Path(resource_path(*initial_db_rel.replace("\\", "/").split("/")))
        try:
            if src.exists():
                shutil.copy2(src, dst)
            else:
                dst.touch()
        except Exception:
            dst.touch()
    return str(dst)

def resolve_or_copy_db(explicit_path: Optional[str]) -> str:
    """
    Si viene una ruta explícita válida, la devuelve.
    En caso contrario, usa ensure_db() para crear/copiar la BD en AppData.
    """
    if explicit_path:
        p = Path(explicit_path)
        try:
            if p.exists():
                return str(p)
            # Si la carpeta existe pero no el archivo, créalo
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch(exist_ok=True)
            return str(p)
        except Exception:
            pass
    return ensure_db()