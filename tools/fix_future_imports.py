#!/usr/bin/env python3
"""
Busca y mueve declaraciones 'from __future__ import ...' al lugar correcto
(en la parte superior de cada módulo, justo después de shebang/encoding/docstring).
Crea un backup filename.py.bak antes de sobrescribir.

Uso:
  - Modo verificación (no modifica archivos):
      python tools/fix_future_imports.py --dry
  - Ejecutar y aplicar cambios:
      python tools/fix_future_imports.py
"""
import re
import sys
from pathlib import Path

FUTURE_RE = re.compile(r'^\s*from\s+__future__\s+import\s+.+$', re.MULTILINE)
ENCODING_RE = re.compile(r'coding[:=]\s*([-\w.]+)')

def process_file(path: Path, dry_run=False):
    text = path.read_text(encoding='utf-8')
    # Find all future lines
    future_matches = list(FUTURE_RE.finditer(text))
    if not future_matches:
        return False, None

    # Collect unique future lines preserving order
    future_lines = []
    for m in future_matches:
        line = m.group(0).strip()
        if line not in future_lines:
            future_lines.append(line)

    # Remove all future lines from text
    new_text = FUTURE_RE.sub('', text)

    # Determine insertion point: after shebang, encoding comment, and optional module docstring
    lines = new_text.splitlines(keepends=True)
    insert_at = 0
    # Shebang?
    if lines and lines[0].startswith('#!'):
        insert_at = 1
    # Encoding comment on second line?
    if len(lines) > insert_at:
        first_possible = lines[insert_at]
        if 'coding' in first_possible or ENCODING_RE.search(first_possible):
            insert_at += 1
    # Skip blank lines up to possible docstring
    idx = insert_at
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    # If docstring present, skip it entirely
    if idx < len(lines) and (lines[idx].lstrip().startswith('"""') or lines[idx].lstrip().startswith("'''")):
        quote = lines[idx].lstrip()[:3]
        idx_doc = idx + 1
        while idx_doc < len(lines):
            if quote in lines[idx_doc]:
                idx_doc += 1
                break
            idx_doc += 1
        insert_at = idx_doc
    else:
        insert_at = idx

    # Build insertion text block and insert
    insert_block = '\n'.join(future_lines) + '\n\n'
    lines.insert(insert_at, insert_block)
    fixed_text = ''.join(lines)

    # Backup and write
    bak = path.with_suffix(path.suffix + '.bak')
    if not dry_run:
        # create backup safely (avoid overwriting previous .bak)
        if not bak.exists():
            path.replace(bak)
        else:
            # find a numbered backup name
            i = 1
            while True:
                alt_bak = path.with_suffix(path.suffix + f'.bak{i}')
                if not alt_bak.exists():
                    path.replace(alt_bak)
                    bak = alt_bak
                    break
                i += 1
        path.write_text(fixed_text, encoding='utf-8')
    return True, bak

def main(root: Path = Path.cwd(), dry_run=False):
    py_files = list(root.rglob('*.py'))
    changed = []
    for p in py_files:
        try:
            ok, bak = process_file(p, dry_run=dry_run)
            if ok:
                changed.append((p, bak))
                print(f"[FIXED] {p}  (backup: {bak})")
        except Exception as e:
            print(f"[ERROR] {p}: {e}")
    if not changed:
        print("No se encontró 'from __future__ import' desubicado en archivos .py")
    else:
        print(f"Total archivos modificados: {len(changed)}")
    return changed

if __name__ == '__main__':
    root = Path.cwd()
    dry = False
    if len(sys.argv) > 1 and sys.argv[1] in ('--dry', '--check'):
        dry = True
    main(root, dry_run=dry)