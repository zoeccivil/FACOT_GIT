from __future__ import annotations
import sqlite3

def backfill(conn: sqlite3.Connection, table: str):
    # table: 'invoice_items' o 'quotation_items'
    cur = conn.cursor()
    # Solo filas con unit NULL o vacío y con item_code no nulo
    cur.execute(f"""
        SELECT t.id, t.item_code
        FROM {table} t
        WHERE (t.unit IS NULL OR TRIM(t.unit) = '')
          AND t.item_code IS NOT NULL AND TRIM(t.item_code) <> ''
    """)
    rows = cur.fetchall()
    print(f"[{table}] filas a completar:", len(rows))
    for row in rows:
        row_id, code = row
        cur.execute("SELECT unit FROM items WHERE code = ? LIMIT 1", (code,))
        r = cur.fetchone()
        if r and r[0]:
            cur.execute(f"UPDATE {table} SET unit=? WHERE id=?", (r[0], row_id))
    conn.commit()
    print(f"[{table}] completado.")

if __name__ == "__main__":
    conn = sqlite3.connect("data/app.db")  # ajusta la ruta a tu DB
    backfill(conn, "invoice_items")
    backfill(conn, "quotation_items")