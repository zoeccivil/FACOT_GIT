import sqlite3
import os

class DBManager:
    def __init__(self, db_path="facturas_cotizaciones.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._initialize_tables()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _initialize_tables(self):
        cur = self.conn.cursor()
        # Empresas (igual que tu modelo)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                rnc TEXT UNIQUE NOT NULL,
                address TEXT,
                invoice_template_path TEXT
            )
        """)
        # Facturas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                invoice_date TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_rnc TEXT,
                currency TEXT NOT NULL,
                total_amount REAL NOT NULL,
                excel_path TEXT,
                pdf_path TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0.0,
                unit_price REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
        """)
        # Cotizaciones
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                quotation_date TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_rnc TEXT,
                notes TEXT,
                currency TEXT NOT NULL,
                total_amount REAL NOT NULL,
                excel_path TEXT,
                pdf_path TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotation_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0.0,
                unit_price REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    # --- Métodos CRUD para empresas, facturas y cotizaciones ---
    def get_companies(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, rnc FROM companies ORDER BY name ASC")
        return cur.fetchall()

    # Facturas
    def add_invoice(self, invoice_data, items):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO invoices (company_id, invoice_date, invoice_number, client_name, client_rnc, currency, total_amount, excel_path, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_data['company_id'], invoice_data['invoice_date'], invoice_data['invoice_number'],
            invoice_data['client_name'], invoice_data['client_rnc'], invoice_data['currency'],
            invoice_data['total_amount'], invoice_data.get('excel_path', ''), invoice_data.get('pdf_path', '')
        ))
        invoice_id = cur.lastrowid
        for item in items:
            cur.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (invoice_id, item['description'], item['quantity'], item['unit_price']))
        self.conn.commit()
        return invoice_id

    # Cotizaciones
    def add_quotation(self, quotation_data, items):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO quotations (company_id, quotation_date, client_name, client_rnc, notes, currency, total_amount, excel_path, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            quotation_data['company_id'], quotation_data['quotation_date'],
            quotation_data['client_name'], quotation_data['client_rnc'],
            quotation_data['notes'], quotation_data['currency'],
            quotation_data['total_amount'], quotation_data.get('excel_path', ''), quotation_data.get('pdf_path', '')
        ))
        quotation_id = cur.lastrowid
        for item in items:
            cur.execute("""
                INSERT INTO quotation_items (quotation_id, description, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (quotation_id, item['description'], item['quantity'], item['unit_price']))
        self.conn.commit()
        return quotation_id

    def get_quotations(self, company_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM quotations WHERE company_id = ? ORDER BY quotation_date DESC", (company_id,))
        return cur.fetchall()

    def get_quotation_items(self, quotation_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM quotation_items WHERE quotation_id = ?", (quotation_id,))
        return cur.fetchall()

    def update_quotation(self, quotation_id, quotation_data, items):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE quotations SET quotation_date=?, client_name=?, client_rnc=?, notes=?, currency=?, total_amount=?, excel_path=?, pdf_path=?
            WHERE id=?
        """, (
            quotation_data['quotation_date'], quotation_data['client_name'], quotation_data['client_rnc'],
            quotation_data['notes'], quotation_data['currency'], quotation_data['total_amount'],
            quotation_data.get('excel_path', ''), quotation_data.get('pdf_path', ''),
            quotation_id
        ))
        cur.execute("DELETE FROM quotation_items WHERE quotation_id=?", (quotation_id,))
        for item in items:
            cur.execute("""
                INSERT INTO quotation_items (quotation_id, description, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (quotation_id, item['description'], item['quantity'], item['unit_price']))
        self.conn.commit()

    def delete_quotation(self, quotation_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM quotation_items WHERE quotation_id=?", (quotation_id,))
        cur.execute("DELETE FROM quotations WHERE id=?", (quotation_id,))
        self.conn.commit()


    def get_facturas(self, company_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM invoices WHERE company_id = ? ORDER BY invoice_date DESC", (company_id,))
        return cur.fetchall()

    def delete_factura(self, factura_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (factura_id,))
        cur.execute("DELETE FROM invoices WHERE id = ?", (factura_id,))
        self.conn.commit()
    # --- Otros métodos CRUD a agregar según necesidad ---


    def get_facturas(self, company_id):
        """
        Devuelve todas las facturas (emitidas y gastos) de una empresa por su ID, ordenadas por fecha descendente.
        """
        if not self.conn or not company_id:
            return []
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM invoices WHERE company_id = ? ORDER BY invoice_date DESC", (company_id,))
        return [dict(row) for row in cur.fetchall()]

    def close(self):
        if self.conn:
            self.conn.close()