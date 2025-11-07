from __future__ import annotations
import sqlite3
import argparse
import re
import os
import sys
from collections import defaultdict, Counter

# DGII (estándar en este script): 1 letra + 10 dígitos (L + TT + SSSSSSSS)
RX_FULL = re.compile(r'^[A-Z][0-9]{10}$')
RX_ANY  = re.compile(r'^([A-Za-z])(\d+)$')  # 1 letra + dígitos (longitud variable)

# Validación de nombres de tabla/columna (evita inyección)
RX_VALID_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def extract_parts(ncf: str):
    if not ncf:
        return None, None
    m = RX_ANY.match(ncf.strip())
    if not m:
        return None, None
    return m.group(1).upper(), m.group(2)


def normalize_to_11(letter: str, digits: str):
    """
    Normaliza a 11 chars: letra + 2 dígitos tipo + 8 dígitos secuencia.
    Si digits >=3: tipo=2 primeros, secuencia=resto; si <3: tipo '01', secuencia restante (0 si vacío).
    """
    if not letter or not digits:
        return None
    if len(digits) >= 3:
        tipo2 = digits[:2]
        seq = digits[2:]
    else:
        tipo2 = (digits + "01")[:2]
        seq = digits[2:] if len(digits) > 2 else ""
    try:
        seq_val = int(seq) if seq else 0
    except ValueError:
        seq_val = 0
    return f"{letter}{tipo2}{seq_val:08d}"


def qname(name: str) -> str:
    """
    Quota un nombre validado para usarlo en SQL.
    """
    if not name or not RX_VALID_NAME.match(name):
        raise ValueError(f"Nombre inválido: {name}")
    return f'"{name}"'


def next_free(conn: sqlite3.Connection, table: str, col_company: str, col_number: str, company_id: int, candidate: str):
    """
    Si candidate está en uso, busca el siguiente libre incrementando la secuencia.
    Preserva letra/tipo (primeros 3 chars).
    (Verifica colisiones contra toda la tabla, no solo emitidas, para garantizar unicidad.)
    """
    cur = conn.cursor()
    tn = qname(table); cc = qname(col_company); cn = qname(col_number)
    prefix = candidate[:3]
    try:
        seq = int(candidate[3:])
    except Exception:
        seq = 0
    for step in range(0, 100000):
        cand = f"{prefix}{(seq + step):08d}"
        cur.execute(f"SELECT 1 FROM {tn} WHERE {cc}=? AND {cn}=? LIMIT 1", (company_id, cand))
        if cur.fetchone() is None:
            return cand
    return candidate  # fallback extremo


def list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]


def get_table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({qname(table)})")
    return [row[1] for row in cur.fetchall()]  # name en índice 1


def detect_invoice_table_and_columns(conn: sqlite3.Connection, preferred_table: str | None = None):
    """
    Detecta tabla y columnas (id, company_id, invoice_number).
    Retorna (table, col_id, col_company, col_number) o (None, None, None, None) si no puede.
    """
    table_candidates = [preferred_table] if preferred_table else []
    table_candidates += ["invoices", "invoice", "facturas", "factura"]

    id_names = ["id", "invoice_id"]
    company_names = ["company_id", "empresa_id", "compania_id", "comp_id"]
    number_names = ["invoice_number", "ncf", "ncf_number", "numero", "numero_factura", "nro_factura"]

    seen = set()
    for tb in table_candidates:
        if not tb or tb in seen:
            continue
        seen.add(tb)
        try:
            cols = set(get_table_columns(conn, tb))
        except Exception:
            continue
        if not cols:
            continue

        col_id = next((c for c in id_names if c in cols), None)
        col_company = next((c for c in company_names if c in cols), None)
        col_number = next((c for c in number_names if c in cols), None)

        if col_id and col_company and col_number:
            return tb, col_id, col_company, col_number

    # Autodetección recorriendo todas las tablas
    for tb in list_tables(conn):
        try:
            cols = set(get_table_columns(conn, tb))
        except Exception:
            continue
        if not cols:
            continue
        col_id = next((c for c in id_names if c in cols), None)
        col_company = next((c for c in company_names if c in cols), None)
        col_number = next((c for c in number_names if c in cols), None)
        if col_id and col_company and col_number:
            return tb, col_id, col_company, col_number

    return None, None, None, None


def detect_type_column(conn: sqlite3.Connection, table: str) -> str | None:
    """
    Intenta detectar la columna de tipo/estado de factura (para filtrar 'emitida').
    Retorna el nombre si lo encuentra, si no, None.
    """
    candidates = ["invoice_type", "tipo", "tipo_factura", "status", "estado"]
    try:
        cols = set(get_table_columns(conn, table))
    except Exception:
        return None
    for c in candidates:
        if c in cols:
            return c
    return None


def interactive_select_table_and_columns(conn: sqlite3.Connection):
    """
    Asistente por consola para elegir tabla y mapear columnas requeridas.
    Retorna (table, col_id, col_company, col_number) o (None, None, None, None).
    """
    print("No se detectó automáticamente la tabla/columnas. Iniciando asistente interactivo.")
    tabs = list_tables(conn)
    if not tabs:
        print("La base de datos no tiene tablas.")
        return None, None, None, None

    for i, t in enumerate(tabs, 1):
        print(f"  {i}. {t}")
    try:
        idx = int(input("Seleccione el número de la tabla de facturas: ").strip())
    except Exception:
        print("Selección inválida.")
        return None, None, None, None
    if idx < 1 or idx > len(tabs):
        print("Índice fuera de rango.")
        return None, None, None, None

    table = tabs[idx - 1]
    cols = get_table_columns(conn, table)
    print(f"Columnas en {table}: {', '.join(cols)}")

    def ask_map(prompt: str, default_guess: str | None):
        if default_guess:
            ans = input(f"{prompt} [{default_guess}]: ").strip()
            return ans or default_guess
        return input(f"{prompt}: ").strip()

    def guess(names):
        for n in names:
            if n in cols:
                return n
        return None

    col_id_guess = guess(["id", "invoice_id"])
    col_company_guess = guess(["company_id", "empresa_id", "compania_id", "comp_id"])
    col_number_guess = guess(["invoice_number", "ncf", "ncf_number", "numero", "numero_factura", "nro_factura"])

    col_id = ask_map("Nombre de la columna ID", col_id_guess)
    col_company = ask_map("Nombre de la columna de compañía", col_company_guess)
    col_number = ask_map("Nombre de la columna del NCF / número de factura", col_number_guess)

    for n in (col_id, col_company, col_number):
        if n not in cols:
            print(f"La columna '{n}' no existe en la tabla {table}.")
            return None, None, None, None

    return table, col_id, col_company, col_number


def scan_stats(conn: sqlite3.Connection, table: str, col_company: str, col_number: str, col_type: str | None, only_issued: bool):
    """
    Retorna estadísticas por empresa/prefijo SOLO de emitidas si only_issued=True.
      stats[company_id][prefix] = Counter(longs del tail secuencial)
    """
    cur = conn.cursor()
    tn = qname(table); cc = qname(col_company); cn = qname(col_number)
    if only_issued and col_type:
        ct = qname(col_type)
        cur.execute(f"SELECT {cc}, {cn} FROM {tn} WHERE {ct} = 'emitida'")
    else:
        if only_issued and not col_type:
            print("Aviso: --only-issued activo pero no se encontró columna de tipo. Se procesarán todas las filas.")
        cur.execute(f"SELECT {cc}, {cn} FROM {tn}")

    stats = defaultdict(lambda: defaultdict(Counter))
    for cid, inv in cur.fetchall():
        if not inv:
            continue
        letter, digits = extract_parts(inv)
        if not letter or not digits:
            continue
        if len(digits) < 2:
            prefix = f"{letter}01"
            tail = ""
        else:
            prefix = f"{letter}{digits[:2]}"
            tail = digits[2:]
        stats[cid][prefix][len(tail)] += 1
    return stats


def normalize(conn: sqlite3.Connection, table: str, col_id: str, col_company: str, col_number: str, col_type: str | None, only_issued: bool, apply: bool):
    """
    Normaliza NCF a 11 caracteres. Si only_issued=True, solo toca facturas emitidas (si hay columna de tipo).
    Verifica colisiones contra toda la tabla para mantener unicidad por empresa+número.
    """
    cur = conn.cursor()
    tn = qname(table); cid = qname(col_id); cc = qname(col_company); cn = qname(col_number)

    if only_issued and col_type:
        ct = qname(col_type)
        cur.execute(f"SELECT {cid}, {cc}, {cn} FROM {tn} WHERE {ct} = 'emitida'")
    else:
        if only_issued and not col_type:
            print("Aviso: --only-issued activo pero no se encontró columna de tipo. Se normalizarán todas las filas.")
        cur.execute(f"SELECT {cid}, {cc}, {cn} FROM {tn}")

    rows = cur.fetchall()

    changes = []
    for inv_id, comp_id, inv in rows:
        if not inv:
            continue
        if RX_FULL.match(inv):
            continue  # ya válido 11-chars
        letter, digits = extract_parts(inv)
        if not letter or not digits:
            continue
        target = normalize_to_11(letter, digits)
        if not target:
            continue
        # Evitar colisiones (por empresa, en toda la tabla):
        cur.execute(f"SELECT 1 FROM {tn} WHERE {cc}=? AND {cn}=? LIMIT 1", (comp_id, target))
        if cur.fetchone() is not None:
            target = next_free(conn, table, col_company, col_number, comp_id, target)
        if inv != target:
            changes.append((inv_id, comp_id, inv, target))

    # Reporte
    scope = "emitidas" if (only_issued and col_type) else ("todas (sin filtro de emitidas)" if only_issued else "todas")
    print(f"Se encontraron {len(changes)} NCF para normalizar ({scope}).")
    for inv_id, comp_id, inv, target in changes[:50]:
        print(f"  - Empresa {comp_id} id={inv_id}: {inv} -> {target}")
    if len(changes) > 50:
        print(f"  ... (+{len(changes)-50} más)")

    if apply and changes:
        for inv_id, comp_id, inv, target in changes:
            cur.execute(f"UPDATE {tn} SET {cn}=? WHERE {cid}=?", (target, inv_id))
        conn.commit()
        print("Cambios aplicados.")


def _choose_db_file(initial_dir: str | None = None) -> str | None:
    """
    Abre un File Dialog para seleccionar la base de datos SQLite.
    Intenta con PyQt6; si no está disponible, prueba Tkinter; si no, usa input().
    """
    # 1) PyQt6
    try:
        from PyQt6.QtWidgets import QApplication, QFileDialog
        app = QApplication.instance()
        created = False
        if app is None:
            app = QApplication(sys.argv)
            created = True
        start_dir = initial_dir or os.getcwd()
        filter_str = "SQLite DB (*.db *.sqlite *.sqlite3);;Todos los archivos (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Seleccionar base de datos SQLite",
            start_dir,
            filter_str
        )
        if created:
            app.quit()
        return file_path or None
    except Exception:
        pass

    # 2) Tkinter
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Seleccionar base de datos SQLite",
            initialdir=initial_dir or os.getcwd(),
            filetypes=[
                ("SQLite DB", "*.db *.sqlite *.sqlite3"),
                ("Todos los archivos", "*.*"),
            ]
        )
        root.destroy()
        return file_path or None
    except Exception:
        pass

    # 3) Consola
    try:
        print("No se encontró entorno gráfico. Escriba la ruta del archivo .db y presione Enter:")
        file_path = input("> ").strip()
        return file_path or None
    except Exception:
        return None


def _print_schema(conn: sqlite3.Connection):
    print("Tablas y columnas disponibles en la base de datos:")
    try:
        tabs = list_tables(conn)
        for t in tabs:
            cols = []
            try:
                cols = get_table_columns(conn, t)
            except Exception:
                pass
            print(f"  - {t}: {', '.join(cols) if cols else '(sin columnas legibles)'}")
    except Exception as e:
        print(f"  (no se pudo listar tablas: {e})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Normaliza NCF a 11 caracteres (1 letra + 10 números) en la tabla de facturas.")
    ap.add_argument("--db", default="data/app.db", help="Ruta al archivo SQLite")
    ap.add_argument("--apply", action="store_true", help="Aplicar cambios (por defecto, solo informe)")
    ap.add_argument("--ask", action="store_true", help="Forzar diálogo para elegir la base de datos")
    ap.add_argument("--table", default="", help="Nombre exacto de la tabla de facturas (por ejemplo: invoices)")
    ap.add_argument("--col-id", default="", help="Nombre de la columna ID (default: id/invoice_id)")
    ap.add_argument("--col-company", default="", help="Nombre de la columna de compañía (default: company_id/empresa_id/...)")
    ap.add_argument("--col-number", default="", help="Nombre de la columna de número/NCF (default: invoice_number/ncf/numero/...)")
    ap.add_argument("--col-type", default="", help="Nombre de la columna de tipo/estado (se filtra por 'emitida' si se indica)")
    ap.add_argument("--only-issued", dest="only_issued", action="store_true", default=True, help="Procesar solo 'emitidas' (por defecto ON)")
    ap.add_argument("--include-all", dest="only_issued", action="store_false", help="Procesar todas (desactiva filtro 'emitida')")
    ap.add_argument("--list-tables", action="store_true", help="Listar tablas y columnas y salir")
    ap.add_argument("--no-exit", action="store_true", help="No llamar sys.exit al terminar (útil en depuradores)")
    args = ap.parse_args()

    db_path = args.db
    need_dialog = args.ask or (not db_path) or (not os.path.exists(db_path))
    if need_dialog:
        initial = None
        if db_path and db_path not in (".", "./", "data/app.db"):
            initial = os.path.dirname(os.path.abspath(db_path))
        chosen = _choose_db_file(initial_dir=initial)
        if not chosen:
            print("No se seleccionó ninguna base de datos. Saliendo.")
            return 1
        db_path = chosen

    if not os.path.exists(db_path):
        print(f"El archivo de base de datos no existe: {db_path}")
        return 1

    print(f"Usando base de datos: {db_path}")

    con = sqlite3.connect(db_path)
    try:
        if args.list_tables:
            _print_schema(con)
            return 0

        # Resolver tabla y columnas
        user_table = args.table.strip() or None
        user_col_id = args.col_id.strip() or None
        user_col_company = args.col_company.strip() or None
        user_col_number = args.col_number.strip() or None
        user_col_type = args.col_type.strip() or None

        table = col_id = col_company = col_number = None

        # 1) Si el usuario pasó tabla y columnas clave, validar
        if user_table and user_col_id and user_col_company and user_col_number:
            bad = [x for x in (user_table, user_col_id, user_col_company, user_col_number) if not RX_VALID_NAME.match(x)]
            if bad or (user_col_type and not RX_VALID_NAME.match(user_col_type)):
                print("Nombres inválidos en --table/--col-*. Solo letras, números y _; no iniciar con número.")
                _print_schema(con)
                return 2
            cols = get_table_columns(con, user_table)
            missing = [c for c in (user_col_id, user_col_company, user_col_number) if c not in cols]
            if missing:
                print(f"La tabla {user_table} no contiene columnas: {', '.join(missing)}")
                print(f"Columnas disponibles: {', '.join(cols)}")
                return 2
            table, col_id, col_company, col_number = user_table, user_col_id, user_col_company, user_col_number
            col_type = user_col_type if (user_col_type and user_col_type in cols) else None
            if args.only_issued and user_col_type and not col_type:
                print(f"Aviso: col-type '{user_col_type}' no existe en {user_table}. No se filtrará por 'emitida'.")
        else:
            # 2) Intentar detección automática
            table, col_id, col_company, col_number = detect_invoice_table_and_columns(con, preferred_table=user_table)
            if not table:
                if sys.stdin and sys.stdin.isatty():
                    _print_schema(con)
                    table, col_id, col_company, col_number = interactive_select_table_and_columns(con)
                    if not table:
                        print("No se pudo determinar tabla/columnas. Vuelva a ejecutar con --table y --col-*.") 
                        return 2
                else:
                    print("No se pudo detectar tabla/columnas y no hay entrada interactiva.")
                    print("Ejemplo de flags: --table invoices --col-id id --col-company company_id --col-number invoice_number --col-type invoice_type")
                    _print_schema(con)
                    return 2
            # Detectar columna de tipo si no la dieron
            col_type = user_col_type if user_col_type else detect_type_column(con, table)
            if args.only_issued and not col_type:
                print("Aviso: no se detectó columna de tipo. No se filtrará por 'emitida'.")

        print(f"Usando tabla: {table}  | columnas -> id: {col_id}, company: {col_company}, number: {col_number}" + (f", type: {col_type}" if col_type else ""))

        # Estadísticas útiles (solo emitidas si corresponde)
        stats = scan_stats(con, table, col_company, col_number, col_type, only_issued=args.only_issued)
        scope = "emitidas" if (args.only_issued and col_type) else ("todas (sin filtro de emitidas)" if args.only_issued else "todas")
        print(f"Distribución de longitudes (por empresa/prefijo) [{scope}]:")
        for cid, pref_map in stats.items():
            print(f"Empresa {cid}:")
            for pref, counter in pref_map.items():
                print(f"  Prefijo {pref}: {dict(counter)}  (longitudes del 'tail' secuencial)")
        print("-----")
        normalize(con, table, col_id, col_company, col_number, col_type, only_issued=args.only_issued, apply=args.apply)
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    code = main()
    # Evitar SystemExit (útil en VS Code). Si quieres comportamiento tradicional, usa: sys.exit(code)
    if code not in (None, 0):
        print(f"Finalizó con código {code}")