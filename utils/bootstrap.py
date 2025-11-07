from __future__ import annotations
import os
import json
import sqlite3
import shutil
import base64
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Callable

APP_NAME = "FACOT"

# ----------------- Paths base (EXE, _internal, AppData) -----------------

def _exe_base_dir() -> Path:
    try:
        return Path(sys.argv[0]).resolve().parent  # type: ignore[name-defined]
    except Exception:
        # fallback dev: utils/.. -> raíz
        return Path(__file__).resolve().parent.parent

def _internal_base_dir() -> Path:
    # Onefile: sys._MEIPASS; Onedir: ./_internal
    try:
        import sys
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return Path(sys.argv[0]).resolve().parent / "_internal"
    except Exception:
        return Path(__file__).resolve().parent.parent / "_internal"

def user_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def ensure_dirs() -> Dict[str, Path]:
    base = user_data_dir()
    dirs = {
        "base": base,
        "templates": base / "templates",
        "data": base / "data",
        "output": base / "output",
        "logs": base / "logs",
        "import": base / "import",
        "export": base / "export",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs

def _resource_path(*parts: str) -> Path:
    # Busca en EXE, _internal y raíz del proyecto (dev)
    import sys
    here = Path(sys.argv[0]).resolve().parent
    cands = [
        here.joinpath(*parts),
        _internal_base_dir().joinpath(*parts),
        Path(__file__).resolve().parent.parent.joinpath(*parts),  # dev
    ]
    for c in cands:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return cands[0]

# ----------------- Materializar recursos del bundle junto al EXE -----------------

def _copytree_if_missing(src: Path, dst: Path, ignore: Optional[Callable[[str, list[str]], set[str]]] = None) -> bool:
    """
    Copia un árbol si el destino no existe. Devuelve True si se copió algo.
    """
    try:
        if dst.exists():
            return False
        if not src.exists():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=False, ignore=ignore)
        return True
    except FileExistsError:
        return False
    except Exception:
        return False

def materialize_bundled_resources_near_exe() -> Dict[str, bool]:
    """
    Copia desde _internal (o sys._MEIPASS) hacia la carpeta del EXE:
      - templates/ -> ./templates
      - data/ -> ./data  (ignorando *.db)
      - facot_config.json si existe y no existe en ./ 
    NO sobrescribe nada que ya exista.
    """
    copied = {"templates": False, "data": False, "config": False}
    src_root = _internal_base_dir()
    dst_root = _exe_base_dir()

    # 1) templates/
    src_tpl = (src_root / "templates")
    dst_tpl = (dst_root / "templates")
    if src_tpl.exists():
        copied["templates"] = _copytree_if_missing(src_tpl, dst_tpl)

    # 2) data/ (ignorando DBs)
    def ignore_dbs(dirpath: str, names: list[str]) -> set[str]:
        db_names = {
            "facturas_db.db", "facturacion.db", "facturas_cotizaciones.db",
        }
        # También ignora *.db en cualquier subcarpeta
        ignore_set = set()
        for n in names:
            if n.lower() in db_names or n.lower().endswith(".db"):
                ignore_set.add(n)
        return ignore_set

    src_data = (src_root / "data")
    dst_data = (dst_root / "data")
    if src_data.exists():
        copied["data"] = _copytree_if_missing(src_data, dst_data, ignore=ignore_dbs)

    # 3) facot_config.json
    src_cfg = src_root / "facot_config.json"
    dst_cfg = dst_root / "facot_config.json"
    try:
        if src_cfg.exists() and not dst_cfg.exists():
            shutil.copy2(src_cfg, dst_cfg)
            copied["config"] = True
    except Exception:
        pass

    return copied

# ----------------- Semillas, DB y defaults en AppData -----------------

def seed_company_templates_if_missing(dest_dir: Path) -> None:
    # Copia semillas company_*.json si existen en data/templates del bundle
    src_dir = _resource_path("data", "templates")
    if not src_dir.exists():
        return
    for p in src_dir.glob("company_*.json"):
        dst = dest_dir / p.name
        if not dst.exists():
            try:
                shutil.copy2(p, dst)
            except Exception:
                pass

def _call_optional_schema_initializers(db_path: str) -> None:
    # Inicializador de ítems/categorías si existe
    try:
        from items_management_window import ensure_items_schema  # type: ignore
        ensure_items_schema(db_path)
    except Exception:
        # Esquema mínimo
        try:
            with sqlite3.connect(db_path) as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        code_prefix TEXT,
                        next_seq INTEGER NOT NULL DEFAULT 1,
                        description TEXT
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_code_prefix ON categories(code_prefix);
                    CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        unit TEXT NOT NULL,
                        cost REAL NOT NULL DEFAULT 0,
                        price REAL NOT NULL DEFAULT 0,
                        category_id INTEGER,
                        description TEXT,
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_items_code ON items(code);
                    CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
                """)
                conn.commit()
        except Exception:
            pass

    # Inicializador general si existe
    try:
        import db_manager  # type: ignore
        if hasattr(db_manager, "ensure_schema"):
            db_manager.ensure_schema(db_path)  # type: ignore
    except Exception:
        pass

def ensure_database_exists() -> str:
    import facot_config  # type: ignore
    db_path = Path(facot_config.get_db_path() or "").expanduser()
    if not str(db_path):
        db_path = user_data_dir() / "facturas_db.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists() or db_path.stat().st_size == 0:
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.commit()
            _call_optional_schema_initializers(str(db_path))
        except Exception:
            db_path.touch(exist_ok=True)
    return str(db_path)

def ensure_default_config_defaults(dirs: Dict[str, Path]) -> str:
    cfg_cwd = _exe_base_dir() / "facot_config.json"
    data: Dict[str, object] = {}
    if cfg_cwd.exists():
        try:
            data = json.loads(cfg_cwd.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    # No tocar db_path si ya existe; setear solo defaults útiles
    data.setdefault("output_folder", str(dirs["output"]))
    data.setdefault("downloads_folder_path", str(dirs["import"]))
    try:
        cfg_cwd.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(cfg_cwd)
    except Exception:
        try:
            cfg_app = user_data_dir() / "facot_config.json"
            cfg_app.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return str(cfg_app)
        except Exception:
            pass
    return str(cfg_cwd)

# ----------------- Comprobador de recursos (templates + logo) -----------------

def _user_templates_dir() -> Path:
    p = user_data_dir() / "templates"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _user_data_dir() -> Path:
    p = user_data_dir() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _find_active_company_id(db_path: str) -> Optional[int]:
    # 1) Intenta por facot_config
    try:
        import facot_config  # type: ignore
        val = facot_config.get_empresa_activa()
        if str(val).strip():
            return int(val)
    except Exception:
        pass
    # 2) Detecta tabla de empresas
    table_candidates = ("companies", "empresa", "empresas", "company")
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r[0].lower() for r in cur.fetchall()}
            tbl = next((t for t in table_candidates if t in tables), None)
            if not tbl:
                tbl = next((t for t in tables if ("company" in t) or ("empresa" in t)), None)
            if not tbl:
                return None
            for col in ("id", "company_id"):
                try:
                    cur.execute(f"SELECT {col} FROM {tbl} ORDER BY {col} LIMIT 1")
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        return int(row[0])
                except Exception:
                    continue
    except Exception:
        pass
    return None

def _tiny_png_bytes() -> bytes:
    # PNG 1x1 transparente
    b64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAgMBgQW0M9kAAAAASUVORK5CYII=")
    return base64.b64decode(b64)

def _ensure_company_logo(company_id: int, parent=None) -> None:
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    candidates: Sequence[Path] = (
        _resource_path("data", f"company_{company_id}", "logo.png"),
        _resource_path("data", f"company_{company_id}", "logo.jpg"),
        _user_data_dir() / f"company_{company_id}" / "logo.png",
        _user_data_dir() / f"company_{company_id}" / "logo.jpg",
        _exe_base_dir() / "data" / f"company_{company_id}" / "logo.png",
        _exe_base_dir() / "data" / f"company_{company_id}" / "logo.jpg",
    )
    for c in candidates:
        try:
            if c.exists():
                return
        except Exception:
            continue

    # Pedir logo
    msg = (
        f"No se encontró un logo para la empresa #{company_id}.\n"
        "Selecciona una imagen (png/jpg). Si cancelas, se colocará un placeholder."
    )
    QMessageBox.information(parent, "Logo requerido", msg)
    fn, _ = QFileDialog.getOpenFileName(
        parent,
        f"Selecciona logo para empresa #{company_id}",
        "",
        "Imagen (*.png *.jpg *.jpeg);;Todos (*.*)"
    )
    # Lo instalamos también junto al EXE si es posible (para rutas relativas)
    targets = [
        _user_data_dir() / f"company_{company_id}" / "logo.png",
        _exe_base_dir() / "data" / f"company_{company_id}" / "logo.png",
    ]
    for t in targets:
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            if fn:
                shutil.copy2(fn, t)
            else:
                t.write_bytes(_tiny_png_bytes())
        except Exception:
            continue

def ensure_required_resources(required_template_names: Optional[Iterable[str]] = None, parent=None) -> None:
    """
    Verifica:
    - Templates HTML clave (por defecto: invoice_template.html, quotation_template.html).
    - Logo para la empresa activa (o detectada).
    Si falta, solicita ubicación y lo instala en AppData y, si se puede, junto al EXE.
    """
    from PyQt6.QtWidgets import QFileDialog, QMessageBox

    names = list(required_template_names or ["invoice_template.html", "quotation_template.html"])
    names = sorted(set(names))

    # ¿Están los templates visibles junto al EXE?
    missing: list[str] = []
    for name in names:
        if not (_exe_base_dir() / "templates" / name).exists():
            # Buscar en _internal o AppData
            p1 = _resource_path("templates", name)
            if not p1.exists():
                missing.append(name)

    if missing:
        QMessageBox.information(
            parent,
            "Recursos requeridos",
            "Faltan archivos de plantilla necesarios para la vista previa/impresión.\n"
            "A continuación podrás seleccionarlos para instalarlos."
        )
        # Instalamos a dos destinos: AppData y junto al EXE (si se puede)
        app_tpl = user_data_dir() / "templates"
        exe_tpl = _exe_base_dir() / "templates"
        app_tpl.mkdir(parents=True, exist_ok=True)
        try:
            exe_tpl.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        for name in missing:
            fn, _ = QFileDialog.getOpenFileName(
                parent,
                f"Selecciona el archivo para {name}",
                "",
                "HTML (*.html *.htm);;Todos (*.*)"
            )
            if not fn:
                QMessageBox.critical(
                    parent,
                    "Archivo faltante",
                    f"No seleccionaste un archivo para {name}.\n"
                    "Podrás configurarlo más tarde desde Opciones."
                )
                continue
            for dst_dir in (app_tpl, exe_tpl):
                try:
                    shutil.copy2(fn, dst_dir / name)
                except Exception:
                    continue

    # Verificar logo
    try:
        import facot_config  # type: ignore
        db_path = Path(facot_config.get_db_path() or "")
    except Exception:
        db_path = Path()
    company_id = None
    try:
        company_id = _find_active_company_id(str(db_path)) if db_path else None
    except Exception:
        company_id = None
    if company_id is not None:
        _ensure_company_logo(company_id, parent=parent)

# ----------------- Orquestador de primer inicio -----------------

def ensure_first_run() -> None:
    # 0) Materializa recursos del bundle junto al EXE (templates/data/config)
    materialize_bundled_resources_near_exe()

    # 1) AppData: carpetas de trabajo
    dirs = ensure_dirs()

    # 2) Semillas por empresa en AppData
    seed_company_templates_if_missing(dirs["templates"])

    # 3) BD existente: respetar; si falta, crear y aplicar esquema
    ensure_database_exists()

    # 4) Defaults de config (sin tocar db_path)
    ensure_default_config_defaults(dirs)

    try:
        (dirs["base"] / ".bootstrap_done").write_text("ok", encoding="utf-8")
    except Exception:
        pass