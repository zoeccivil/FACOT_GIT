#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Directorios/archivos a ignorar en el árbol
IGNORE_DIRS = {
    ".git", ".github", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "__pycache__", "venv", ".venv", "env", ".idea", ".vscode", "dist", "build"
}
IGNORE_FILES_ENDSWITH = {
    ".pyc", ".pyo", ".pyd", ".log", ".tmp", ".DS_Store", "Thumbs.db"
}

ROOT = Path(__file__).resolve().parent.parent  # carpeta raíz del proyecto
OUTPUT = ROOT / "PROJECT_MAP.md"

def is_ignored(path: Path) -> bool:
    """
    Devuelve True si el path debe ser ignorado.
    - Compara los nombres de todos los componentes del path contra IGNORE_DIRS.
    - Ignora archivos por sufijo según IGNORE_FILES_ENDSWITH.
    """
    p = Path(path)
    # parts es una tupla de str; normalizamos a minúsculas para comparar
    try:
        parts_lower = {part.lower() for part in p.resolve().parts}
    except Exception:
        # Si resolve falla (permisos/symlink), usamos parts “tal cual”
        parts_lower = {part.lower() for part in p.parts}

    if any(d.lower() in parts_lower for d in IGNORE_DIRS):
        return True

    name = p.name
    for suf in IGNORE_FILES_ENDSWITH:
        if name.endswith(suf):
            return True
    return False

def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")

def build_tree() -> tuple[str, dict[str, int]]:
    lines = []
    counts = defaultdict(int)
    sizes = defaultdict(int)

    def walk(dir_path: Path, prefix: str = ""):
        try:
            raw_entries = list(dir_path.iterdir())
        except Exception:
            return  # sin permisos o no accesible

        # Filtra ignorados y ordena: directorios primero, luego archivos, por nombre
        entries = [p for p in raw_entries if not is_ignored(p)]
        entries.sort(key=lambda x: (x.is_file(), x.name.lower()))

        for i, p in enumerate(entries):
            is_last = (i == len(entries)-1)
            connector = "└── " if is_last else "├── "
            line = f"{prefix}{connector}{p.name}"
            if p.is_dir():
                lines.append(line + "/")
                walk(p, prefix + ("    " if is_last else "│   "))
            else:
                lines.append(line)
                ext = p.suffix.lower() or "<no_ext>"
                counts[ext] += 1
                try:
                    sizes[ext] += p.stat().st_size
                except Exception:
                    pass

    lines.append(f"# Project Map for {ROOT.name}")
    lines.append(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
    lines.append("```\n" + rel(ROOT) + "/")
    walk(ROOT)
    lines.append("```")

    # Resumen por extensión
    lines.append("\n## File Type Summary")
    lines.append("| Extension | Count | Size (KB) |")
    lines.append("|-----------|-------:|----------:|")
    for ext, cnt in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        size_kb = sizes[ext] / 1024
        lines.append(f"| {ext} | {cnt} | {size_kb:,.1f} |")

    return "\n".join(lines), counts

def main():
    content, _ = build_tree()
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Map written to: {OUTPUT}")

if __name__ == "__main__":
    sys.exit(main())