import sqlite3
import sys

try:
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
except ImportError:
    from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

COLUMNS_TO_ADD = {
    "excel_path": "TEXT",
    "pdf_path": "TEXT"
}

def add_columns():
    app = QApplication(sys.argv)
    file_path, _ = QFileDialog.getOpenFileName(None, "Selecciona el archivo de base de datos", "", "Database Files (*.db);;Todos los archivos (*)")
    if not file_path:
        QMessageBox.warning(None, "Sin archivo", "No seleccionaste ningún archivo.")
        sys.exit(0)

    try:
        conn = sqlite3.connect(file_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(invoices)")
        columns = [col[1] for col in cur.fetchall()]
        added = []
        for col, col_type in COLUMNS_TO_ADD.items():
            if col not in columns:
                cur.execute(f"ALTER TABLE invoices ADD COLUMN {col} {col_type};")
                added.append(col)
        conn.commit()
        if added:
            msg = "Se agregaron las siguientes columnas:\n" + "\n".join(added)
        else:
            msg = "Las columnas 'excel_path' y 'pdf_path' ya existen o no son necesarias."
        QMessageBox.information(None, "Resultado", msg)
        conn.close()
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Ocurrió un error:\n{e}")

if __name__ == "__main__":
    add_columns()