import sqlite3
import os
import json
import datetime
import re

import config_facot
from typing import Any, Dict, List, Optional, Tuple

# Importar servicios de auditoría y NCF
from services.audit_service import AuditService
from services.ncf_service import NCFService

# NCF válido:
# - Estándar (no E): 1 letra distinta de E + 10 dígitos
# - e-CF (E): 'E' + 13 dígitos (2 de tipo + 11 de secuencia)
NCF_REGEX_STD = re.compile(r'^(?!E)[A-Z][0-9]{10}$')
NCF_REGEX_E = re.compile(r'^E[0-9]{13}$')

# Tipo por defecto cuando no se pueda inferir
DEFAULT_TYPE_STD = "01"
DEFAULT_TYPE_E = "31"

class LogicController:
    """
    Lógica de negocio y BD.
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        print(f"[DEBUG-LOGIC] Path de la BD: {self.db_path}")
        self._connect()
        self._initialize_db()
        
        # Inicializar servicios de auditoría y NCF
        self.audit_service = AuditService(db_path)
        self.ncf_service = NCFService(db_path)

    # -------------------------
    # Bootstrap / DB
    # -------------------------
    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _initialize_db(self):
        cur = self.conn.cursor()

        # --- Empresas ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                rnc TEXT UNIQUE NOT NULL,
                address TEXT,
                invoice_template_path TEXT,
                invoice_output_base_path TEXT,
                itbis_adelantado REAL DEFAULT 0.0,
                legacy_filename TEXT
            )
        """)
        self._ensure_company_extra_columns()

        # --- Facturas ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                invoice_type TEXT,
                invoice_date TEXT NOT NULL,
                imputation_date TEXT,
                invoice_number TEXT NOT NULL,
                invoice_category TEXT,
                rnc TEXT,
                third_party_name TEXT,
                client_name TEXT,
                client_rnc TEXT,
                currency TEXT NOT NULL,
                itbis REAL DEFAULT 0.0,
                total_amount REAL NOT NULL DEFAULT 0.0,
                exchange_rate REAL NOT NULL DEFAULT 1.0,
                total_amount_rd REAL NOT NULL DEFAULT 0.0,
                excel_path TEXT,
                pdf_path TEXT,
                attachment_path TEXT,
                due_date TEXT,
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
                item_code TEXT,
                unit TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
        """)

        # --- Cotizaciones ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                quotation_date TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_rnc TEXT,
                notes TEXT,
                currency TEXT NOT NULL,
                total_amount REAL NOT NULL DEFAULT 0.0,
                excel_path TEXT,
                pdf_path TEXT,
                due_date TEXT,
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
                item_code TEXT,
                unit TEXT,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
            )
        """)

        # --- Terceros ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS third_parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rnc TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL
            )
        """)

        # NUEVO: Tabla de secuencias NCF persistentes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ncf_sequences (
                company_id INTEGER NOT NULL,
                prefix3 TEXT NOT NULL,
                last_seq INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (company_id, prefix3),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)

        # Columnas adicionales/vencimientos
        self._ensure_line_item_columns()
        self._ensure_due_date_columns()
        self.conn.commit()

    def _ensure_company_extra_columns(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(companies)")
        existing = {row["name"] for row in cur.fetchall()}
        needed = [
            ("address_line1", "TEXT", "''"),
            ("address_line2", "TEXT", "''"),
            ("phone", "TEXT", "''"),
            ("email", "TEXT", "''"),
            ("signature_name", "TEXT", "''"),
            ("logo_path", "TEXT", "''"),
            ("address", "TEXT", "''"),
            ("invoice_template_path", "TEXT", "''"),
            ("invoice_output_base_path", "TEXT", "''"),
            ("invoice_due_date", "TEXT", "''"),
        ]
        for col, typ, default in needed:
            if col not in existing:
                print(f"[DEBUG-LOGIC] Añadiendo columna {col} a companies.")
                cur.execute(f"ALTER TABLE companies ADD COLUMN {col} {typ} DEFAULT {default}")
        self.conn.commit()

    def _ensure_line_item_columns(self):
        cur = self.conn.cursor()
        for table in ("invoice_items", "quotation_items"):
            cur.execute(f"PRAGMA table_info({table})")
            existing = {row["name"] for row in cur.fetchall()}
            if "item_code" not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN item_code TEXT")
            if "unit" not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN unit TEXT")
        self.conn.commit()

    # -------------------------
    # Maestro de Ítems
    # -------------------------
    def _lookup_item_by_code(self, code: str):
        if not code:
            return None
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT code, name, unit, price, cost, description FROM items WHERE code = ? LIMIT 1",
                (code,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"[DEBUG-LOGIC] Error al buscar ítem por código '{code}': {e}")
            return None

    def get_item_by_code(self, code: str):
        return self._lookup_item_by_code(code)

    def get_items_like(self, query: str, limit: int = 20):
        if not query or len(query.strip()) < 1:
            return []
        q = f"%{query.strip()}%"
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT code, name, unit, price, cost, description FROM items "
                "WHERE code LIKE ? OR name LIKE ? ORDER BY code LIMIT ?",
                (q, q, int(limit))
            )
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"[DEBUG-LOGIC] Error al buscar ítems: {e}")
            return []

    def search_items_by_code_or_name(self, query: str, limit: int = 20):
        return self.get_items_like(query, limit)

    # -------------------------
    # Empresas
    # -------------------------
    def get_all_companies(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, rnc, phone, email FROM companies ORDER BY name ASC")
        return [dict(row) for row in cur.fetchall()]

    def add_company(self, name, rnc, address=""):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO companies (name, rnc, address) VALUES (?, ?, ?)", (name, rnc, address))
        self.conn.commit()
        return cur.lastrowid

    def update_company(self, company_id, name, rnc, address, template_path, output_path):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE companies
               SET name = ?, rnc = ?, address = ?, invoice_template_path = ?, invoice_output_base_path = ?
             WHERE id = ?
        """, (name, rnc, address, template_path, output_path, company_id))
        self.conn.commit()

    def update_company_fields(self, company_id: int, payload: Dict[str, Any]):
        allowed = {
            "address_line1", "address_line2", "phone", "email", "signature_name",
            "logo_path", "address", "invoice_template_path", "invoice_output_base_path",
            "invoice_due_date"
        }
        data = {k: v for k, v in (payload or {}).items() if k in allowed}
        if not data:
            return
        sets = ", ".join([f"{k} = ?" for k in data.keys()])
        vals = list(data.values()) + [int(company_id)]
        sql = f"UPDATE companies SET {sets} WHERE id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, vals)
        self.conn.commit()

    def set_company_field(self, company_id: int, key: str, value: Any):
        allowed = {
            "address_line1", "address_line2", "phone", "email", "signature_name",
            "logo_path", "address", "invoice_template_path", "invoice_output_base_path",
            "invoice_due_date"
        }
        if key not in allowed:
            raise ValueError(f"Campo no permitido: {key}")
        cur = self.conn.cursor()
        cur.execute(f"UPDATE companies SET {key} = ? WHERE id = ?", (value, int(company_id)))
        self.conn.commit()

    def commit(self):
        try:
            self.conn.commit()
        except Exception:
            pass

    def get_company_details(self, company_id):
        cur = self.conn.cursor()
        try:
            cur.execute("""
                SELECT 
                    id, name, rnc, address, invoice_template_path, 
                    invoice_output_base_path, itbis_adelantado, legacy_filename,
                    address_line1, address_line2, phone, email, 
                    signature_name, logo_path,
                    invoice_due_date
                FROM companies 
                WHERE id = ?
            """, (company_id,))
            row = cur.fetchone()
            details = dict(row) if row else None
            print(f"[DEBUG-LOGIC] Detalles recuperados para ID {company_id}: {details}")
            return details
        except Exception as e:
            print(f"[DEBUG-LOGIC] ERROR CRÍTICO en get_company_details para ID {company_id}: {e}")
            return None

    # -------------------------
    # NCF: helpers y secuencias persistentes
    # -------------------------
    NCF_REGEX_STD = re.compile(r'^(?!E)[A-Z][0-9]{10}$')
    NCF_REGEX_E = re.compile(r'^E[0-9]{13}$')
    DEFAULT_TYPE_STD = "01"
    DEFAULT_TYPE_E = "31"

    @staticmethod
    def validate_ncf(ncf: str) -> bool:
        s = (ncf or "").strip().upper()
        return bool(LogicController.NCF_REGEX_STD.match(s) or LogicController.NCF_REGEX_E.match(s))

    @staticmethod
    def split_ncf(ncf: str):
        n = (ncf or "").strip().upper()
        if NCF_REGEX_E.match(n):
            letter = "E"; tipo2 = n[1:3]; sec = n[3:]
            return letter, tipo2, sec
        if NCF_REGEX_STD.match(n):
            letter = n[0]; tipo2 = n[1:3]; sec = n[3:]
            return letter, tipo2, sec
        return None, None, None

    @staticmethod
    def _pad_len_for_letter(letter: str) -> int:
        return 11 if (letter or "").upper() == "E" else 8

    # Máximo observado en facturas (compat)
    def _max_seq_for_prefix(self, company_id: int, prefix3: str, issued_only: bool = True) -> int:
        if not prefix3 or len(prefix3) != 3:
            return 0
        exp_len = 1 + 2 + self._pad_len_for_letter(prefix3[0])
        cur = self.conn.cursor()
        if issued_only:
            cur.execute("""
                SELECT invoice_number FROM invoices
                WHERE company_id = ?
                  AND invoice_type = 'emitida'
                  AND invoice_number LIKE ?
                  AND LENGTH(invoice_number) = ?
            """, (company_id, f"{prefix3.upper()}%", exp_len))
        else:
            cur.execute("""
                SELECT invoice_number FROM invoices
                WHERE company_id = ?
                  AND invoice_number LIKE ?
                  AND LENGTH(invoice_number) = ?
            """, (company_id, f"{prefix3.upper()}%", exp_len))

        mx = 0
        for (inv,) in cur.fetchall():
            inv = (inv or "").upper()
            if not inv.startswith(prefix3.upper()):
                continue
            try:
                val = int(inv[3:])
                if val > mx: mx = val
            except Exception:
                pass
        return mx

    # Compat histórica (no persiste consumo)
    def get_next_ncf(self, company_id: int, prefix3: str) -> str:
        if not prefix3 or len(prefix3) != 3 or not prefix3[0].isalpha() or not prefix3[1:].isdigit():
            prefix3 = "B01"
        prefix3 = prefix3.upper()
        pad = self._pad_len_for_letter(prefix3[0])
        max_seq = self._max_seq_for_prefix(company_id, prefix3, issued_only=True)
        return f"{prefix3}{(max_seq + 1):0{pad}d}"

    # NUEVO: persistencia de secuencias
    def ensure_ncf_sequence_row(self, company_id: int, prefix3: str) -> int:
        """
        Garantiza fila en ncf_sequences. Si no existe, la crea con el máximo histórico en facturas.
        Devuelve last_seq actual.
        """
        prefix3 = (prefix3 or "B01").upper()
        cur = self.conn.cursor()
        cur.execute("SELECT last_seq FROM ncf_sequences WHERE company_id=? AND prefix3=?", (company_id, prefix3))
        row = cur.fetchone()
        if row:
            return int(row["last_seq"])
        # sembrar con máximo histórico
        pad = self._pad_len_for_letter(prefix3[0])
        exp_len = 1 + 2 + pad
        cur.execute("""
            SELECT invoice_number FROM invoices
             WHERE company_id=? AND invoice_type='emitida'
               AND invoice_number LIKE ? AND LENGTH(invoice_number)=?
        """, (company_id, f"{prefix3}%", exp_len))
        mx = 0
        for (inv,) in cur.fetchall():
            inv = (inv or "").upper()
            if inv.startswith(prefix3) and len(inv) == exp_len:
                try:
                    val = int(inv[3:])
                    if val > mx: mx = val
                except Exception:
                    pass
        cur.execute("""
            INSERT INTO ncf_sequences(company_id,prefix3,last_seq,updated_at)
            VALUES (?,?,?,datetime('now'))
        """, (company_id, prefix3, mx))
        self.conn.commit()
        return mx

    def get_ncf_last_seq(self, company_id: int, prefix3: str) -> int:
        return self.ensure_ncf_sequence_row(company_id, prefix3)

    def set_ncf_last_seq(self, company_id: int, prefix3: str, last_seq: int):
        prefix3 = (prefix3 or "B01").upper()
        _ = self.ensure_ncf_sequence_row(company_id, prefix3)
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE ncf_sequences SET last_seq=?, updated_at=datetime('now')
             WHERE company_id=? AND prefix3=?
        """, (int(last_seq), company_id, prefix3))
        self.conn.commit()

    def get_ncf_preview(self, company_id: int, prefix3: str) -> str:
        prefix3 = (prefix3 or "B01").upper()
        last_seq = self.ensure_ncf_sequence_row(company_id, prefix3)
        pad = self._pad_len_for_letter(prefix3[0])
        return f"{prefix3}{(last_seq + 1):0{pad}d}"

    def allocate_next_ncf(self, company_id: int, prefix3: str) -> str:
        """
        Consume/asigna el siguiente NCF: incrementa last_seq y retorna el NCF listo.
        """
        prefix3 = (prefix3 or "B01").upper()
        last_seq = self.ensure_ncf_sequence_row(company_id, prefix3)
        new_seq = last_seq + 1
        pad = self._pad_len_for_letter(prefix3[0])
        ncf = f"{prefix3}{new_seq:0{pad}d}"
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE ncf_sequences SET last_seq=?, updated_at=datetime('now')
             WHERE company_id=? AND prefix3=?
        """, (new_seq, company_id, prefix3))
        self.conn.commit()
        return ncf

    def find_next_free_ncf(self, company_id: int, prefix3: str, start_seq: int) -> str:
        cur = self.conn.cursor()
        p3 = (prefix3 or "B01").upper()
        pad = self._pad_len_for_letter(p3[0])
        for step in range(0, 10000):
            cand = f"{p3}{(start_seq + step):0{pad}d}"
            cur.execute("SELECT 1 FROM invoices WHERE company_id=? AND invoice_number=? LIMIT 1", (company_id, cand))
            if cur.fetchone() is None and self.validate_ncf(cand):
                return cand
        return f"{p3}{start_seq:0{pad}d}"

    def update_invoice_number(self, invoice_id: int, company_id: int, rnc: str, new_ncf: str):
        """
        Actualiza el número de NCF de una factura.
        
        INTEGRACIÓN: Registra el cambio en auditoría.
        """
        n = (new_ncf or "").strip().upper()
        if not self.validate_ncf(n):
            return False, "NCF inválido. Formatos válidos: E + 13 dígitos, o letra≠E + 10 dígitos.", n

        cur = self.conn.cursor()
        
        # NUEVO: Obtener NCF anterior para auditoría
        try:
            cur.execute("SELECT invoice_number FROM invoices WHERE id = ?", (invoice_id,))
            old_row = cur.fetchone()
            old_ncf = old_row['invoice_number'] if old_row else None
        except Exception:
            old_ncf = None
        
        cur.execute("SELECT id FROM invoices WHERE company_id=? AND invoice_number=? LIMIT 1", (company_id, n))
        row = cur.fetchone()
        if row and row["id"] != invoice_id:
            prefix3 = n[:3]
            try:
                seq = int(n[3:])
            except Exception:
                seq = 1
            suggestion = self.find_next_free_ncf(company_id, prefix3, seq + 1)
            return False, f"NCF en uso. Sugerencia: {suggestion}", suggestion

        cur.execute("UPDATE invoices SET invoice_number=? WHERE id=?", (n, invoice_id))
        self.conn.commit()
        
        # NUEVO: Registrar cambio de NCF en auditoría
        try:
            if old_ncf and old_ncf != n:
                self.audit_service.log_action(
                    entity_type='invoice',
                    entity_id=invoice_id,
                    action='update',
                    payload_before={'invoice_number': old_ncf},
                    payload_after={'invoice_number': n},
                    user=os.getenv('USER', 'system')
                )
        except Exception as e:
            print(f"[DEBUG-LOGIC] Error al registrar auditoría de NCF: {e}")
        
        return True, "NCF actualizado.", n

    @staticmethod
    def _normalize_free_form_to_valid(ncf: str) -> str | None:
        s = (ncf or "").strip().upper()
        m = re.match(r'^([A-Z])(\\d+)$', s)
        if not m:
            return None
        letter = m.group(1)
        digits = m.group(2)
        if letter == "E":
            tipo2 = digits[:2] if len(digits) >= 2 else LogicController.DEFAULT_TYPE_E
            seq = digits[2:] if len(digits) > 2 else ""
            try:
                seq_val = int(seq) if seq else 0
            except Exception:
                seq_val = 0
            return f"E{tipo2}{seq_val:011d}"
        else:
            tipo2 = digits[:2] if len(digits) >= 2 else LogicController.DEFAULT_TYPE_STD
            seq = digits[2:] if len(digits) > 2 else ""
            try:
                seq_val = int(seq) if seq else 0
            except Exception:
                seq_val = 0
            return f"{letter}{tipo2}{seq_val:08d}"

    # -------------------------
    # Facturas
    # -------------------------
    def add_invoice(self, invoice_data, items):
        """
        Inserta la factura y sus renglones.
        - due_date:
          1) invoice_data['due_date'] si viene
          2) companies.invoice_due_date
          3) ''
        
        INTEGRACIÓN: Usa NCFService para reservar NCF de forma segura
        y AuditService para registrar la creación.
        """
        cur = self.conn.cursor()
        inv_type = (invoice_data.get('invoice_type') or 'emitida')
        company_id = int(invoice_data.get('company_id'))

        # Resolver due_date
        due_date = (invoice_data.get('due_date') or "").strip()
        if not due_date:
            due_date = self.get_company_invoice_due_date(company_id) or ""

        # NUEVO: Reservar NCF de forma segura si es factura emitida y no tiene NCF asignado
        invoice_number = invoice_data.get('invoice_number', '').strip()
        if inv_type == 'emitida' and not invoice_number:
            invoice_category = invoice_data.get('invoice_category', 'B01')
            success, result = self.ncf_service.reserve_ncf(company_id, invoice_category)
            if not success:
                # Error al reservar NCF
                raise Exception(f"Error al reservar NCF: {result}")
            invoice_number = result
            print(f"[DEBUG-LOGIC] NCF reservado: {invoice_number}")
        
        # Actualizar invoice_data con el NCF reservado
        invoice_data_copy = invoice_data.copy()
        if invoice_number:
            invoice_data_copy['invoice_number'] = invoice_number

        # Cabecera
        cur.execute("""
            INSERT INTO invoices (company_id, invoice_type, invoice_date, imputation_date, invoice_number,
                                  invoice_category, rnc, third_party_name, client_name, client_rnc, currency, itbis,
                                  total_amount, exchange_rate, total_amount_rd, excel_path, pdf_path, attachment_path, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            inv_type,
            invoice_data_copy.get('invoice_date'),
            invoice_data_copy.get('imputation_date'),
            invoice_data_copy.get('invoice_number'),
            invoice_data_copy.get('invoice_category'),
            invoice_data_copy.get('rnc'),
            invoice_data_copy.get('third_party_name'),
            invoice_data_copy.get('client_name'),
            invoice_data_copy.get('client_rnc'),
            invoice_data_copy.get('currency'),
            float(invoice_data_copy.get('itbis', 0.0) or 0.0),
            float(invoice_data_copy.get('total_amount', 0.0) or 0.0),
            float(invoice_data_copy.get('exchange_rate', 1.0) or 1.0),
            float(invoice_data_copy.get('total_amount_rd', 0.0) or 0.0),
            invoice_data_copy.get('excel_path', ''),
            invoice_data_copy.get('pdf_path', ''),
            invoice_data_copy.get('attachment_path', ''),
            due_date or None
        ))
        invoice_id = cur.lastrowid

        # Detalle (unidad desde items.unit)
        for it in items or []:
            code = (it.get('code') or it.get('item_code') or '').strip()
            desc = (it.get('description') or '').strip()
            qty = float(it.get('quantity', 0.0) or 0.0)
            up  = float(it.get('unit_price', 0.0) or 0.0)
            unit_from_master = self._get_unit_from_items(code, desc) or None

            cur.execute("""
                INSERT INTO invoice_items (invoice_id, item_code, description, quantity, unit_price, unit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (invoice_id, code, desc, qty, up, unit_from_master))

        self.conn.commit()
        
        # NUEVO: Registrar en auditoría
        try:
            self.audit_service.log_invoice_create(
                invoice_id, 
                invoice_data_copy,
                user=os.getenv('USER', 'system')
            )
            
            # Registrar asignación de NCF si aplica
            if inv_type == 'emitida' and invoice_number:
                self.audit_service.log_ncf_assignment(
                    invoice_id,
                    invoice_number,
                    company_id,
                    user=os.getenv('USER', 'system')
                )
        except Exception as e:
            print(f"[DEBUG-LOGIC] Error al registrar auditoría: {e}")
        
        return invoice_id

    def update_invoice(self, invoice_id: int, invoice_data: Dict[str, Any], items: List[Dict[str, Any]]):
        """
        Actualiza una factura existente y sus items.
        
        INTEGRACIÓN: Registra los cambios en auditoría antes de actualizar.
        """
        cur = self.conn.cursor()
        
        # NUEVO: Obtener datos anteriores para auditoría
        payload_before = None
        try:
            cur.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            row = cur.fetchone()
            if row:
                payload_before = dict(row)
        except Exception as e:
            print(f"[DEBUG-LOGIC] Error al obtener invoice anterior: {e}")
        
        # Resolver due_date
        company_id = int(invoice_data.get('company_id', payload_before.get('company_id', 0)))
        due_date = (invoice_data.get('due_date') or "").strip()
        if not due_date and payload_before:
            due_date = payload_before.get('due_date', '')
        if not due_date:
            due_date = self.get_company_invoice_due_date(company_id) or ""
        
        # Actualizar cabecera de factura
        cur.execute("""
            UPDATE invoices SET
                company_id = ?,
                invoice_type = ?,
                invoice_date = ?,
                imputation_date = ?,
                invoice_number = ?,
                invoice_category = ?,
                rnc = ?,
                third_party_name = ?,
                client_name = ?,
                client_rnc = ?,
                currency = ?,
                itbis = ?,
                total_amount = ?,
                exchange_rate = ?,
                total_amount_rd = ?,
                excel_path = ?,
                pdf_path = ?,
                attachment_path = ?,
                due_date = ?
            WHERE id = ?
        """, (
            company_id,
            invoice_data.get('invoice_type', 'emitida'),
            invoice_data.get('invoice_date'),
            invoice_data.get('imputation_date'),
            invoice_data.get('invoice_number'),
            invoice_data.get('invoice_category'),
            invoice_data.get('rnc'),
            invoice_data.get('third_party_name'),
            invoice_data.get('client_name'),
            invoice_data.get('client_rnc'),
            invoice_data.get('currency'),
            float(invoice_data.get('itbis', 0.0) or 0.0),
            float(invoice_data.get('total_amount', 0.0) or 0.0),
            float(invoice_data.get('exchange_rate', 1.0) or 1.0),
            float(invoice_data.get('total_amount_rd', 0.0) or 0.0),
            invoice_data.get('excel_path', ''),
            invoice_data.get('pdf_path', ''),
            invoice_data.get('attachment_path', ''),
            due_date or None,
            invoice_id
        ))
        
        # Eliminar items anteriores y crear nuevos
        cur.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        
        for it in items or []:
            code = (it.get('code') or it.get('item_code') or '').strip()
            desc = (it.get('description') or '').strip()
            qty = float(it.get('quantity', 0.0) or 0.0)
            up = float(it.get('unit_price', 0.0) or 0.0)
            unit_from_master = self._get_unit_from_items(code, desc) or None
            
            cur.execute("""
                INSERT INTO invoice_items (invoice_id, item_code, description, quantity, unit_price, unit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (invoice_id, code, desc, qty, up, unit_from_master))
        
        self.conn.commit()
        
        # NUEVO: Registrar en auditoría
        try:
            self.audit_service.log_invoice_update(
                invoice_id,
                payload_before or {},
                invoice_data,
                user=os.getenv('USER', 'system')
            )
        except Exception as e:
            print(f"[DEBUG-LOGIC] Error al registrar auditoría de actualización: {e}")
        
        return invoice_id

    def get_facturas(self, company_id, only_issued: bool = True):
        cur = self.conn.cursor()
        if only_issued:
            cur.execute("""
                SELECT * FROM invoices
                 WHERE company_id = ? AND invoice_type = 'emitida'
                 ORDER BY invoice_date DESC
            """, (company_id,))
        else:
            cur.execute("""
                SELECT * FROM invoices
                 WHERE company_id = ?
                 ORDER BY invoice_date DESC
            """, (company_id,))
        return [dict(row) for row in cur.fetchall()]

    def get_invoice_items(self, invoice_id):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, invoice_id, item_code, description, quantity, unit_price, unit
              FROM invoice_items WHERE invoice_id = ?
            ORDER BY id ASC
        """, (invoice_id,))
        rows = [dict(r) for r in cur.fetchall()]
        out = []
        for r in rows:
            code = r.get('item_code') or ''
            unit = self._get_unit_from_items(code, r.get('description', '')) or ''
            out.append({
                "id": r.get("id"),
                "invoice_id": r.get("invoice_id"),
                "code": code,
                "description": r.get("description", ""),
                "quantity": float(r.get('quantity') or 0.0),
                "unit_price": float(r.get('unit_price') or 0.0),
                "unit": unit,
            })
        return out

    def delete_factura(self, factura_id):
        """
        Elimina una factura y sus items.
        
        INTEGRACIÓN: Registra la eliminación en auditoría antes de borrar.
        """
        cur = self.conn.cursor()
        
        # NUEVO: Obtener datos de la factura antes de eliminar para auditoría
        try:
            cur.execute("SELECT * FROM invoices WHERE id = ?", (factura_id,))
            invoice_row = cur.fetchone()
            if invoice_row:
                invoice_data = dict(invoice_row)
                # Registrar eliminación en auditoría
                self.audit_service.log_invoice_delete(
                    factura_id,
                    invoice_data,
                    user=os.getenv('USER', 'system')
                )
        except Exception as e:
            print(f"[DEBUG-LOGIC] Error al registrar auditoría de eliminación: {e}")
        
        # Eliminar factura e items
        cur.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (factura_id,))
        cur.execute("DELETE FROM invoices WHERE id = ?", (factura_id,))
        self.conn.commit()

    # -------------------------
    # Cotizaciones
    # -------------------------
    def add_quotation(self, quotation_data, items):
        cur = self.conn.cursor()
        qdate = quotation_data.get('quotation_date')
        due_date = self.compute_quotation_due_date(qdate)
        cur.execute("""
            INSERT INTO quotations (company_id, quotation_date, client_name, client_rnc, notes, currency, total_amount, excel_path, pdf_path, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            quotation_data['company_id'], qdate, quotation_data['client_name'],
            quotation_data.get('client_rnc', ''), quotation_data.get('notes', ''),
            quotation_data['currency'], float(quotation_data.get('total_amount', 0.0) or 0.0),
            quotation_data.get('excel_path', ''), quotation_data.get('pdf_path', ''), due_date or None
        ))
        quotation_id = cur.lastrowid

        for it in items or []:
            code = (it.get('code') or it.get('item_code') or '').strip()
            desc = (it.get('description') or '').strip()
            qty = float(it.get('quantity', 0.0) or 0.0)
            up  = float(it.get('unit_price', 0.0) or 0.0)
            unit_from_master = self._get_unit_from_items(code, desc) or None

            cur.execute("""
                INSERT INTO quotation_items (quotation_id, item_code, description, quantity, unit_price, unit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (quotation_id, code, desc, qty, up, unit_from_master))

        self.conn.commit()
        return quotation_id

    def get_quotations(self, company_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM quotations WHERE company_id = ? ORDER BY quotation_date DESC", (company_id,))
        return [dict(row) for row in cur.fetchall()]

    def get_quotation_items(self, quotation_id):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, quotation_id, item_code, description, quantity, unit_price, unit
              FROM quotation_items WHERE quotation_id = ?
            ORDER BY id ASC
        """, (quotation_id,))
        rows = [dict(r) for r in cur.fetchall()]
        out = []
        for r in rows:
            code = r.get('item_code') or ''
            unit = self._get_unit_from_items(code, r.get('description', '')) or ''
            out.append({
                "id": r.get("id"),
                "quotation_id": r.get("quotation_id"),
                "code": code,
                "description": r.get("description", ""),
                "quantity": float(r.get('quantity') or 0.0),
                "unit_price": float(r.get('unit_price') or 0.0),
                "unit": unit,
            })
        return out

    def update_quotation(self, quotation_id, quotation_data, items):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE quotations SET quotation_date=?, client_name=?, client_rnc=?, notes=?, currency=?, total_amount=?, excel_path=?, pdf_path=?
             WHERE id=?
        """, (
            quotation_data['quotation_date'], quotation_data['client_name'], quotation_data['client_rnc'],
            quotation_data.get('notes', ''), quotation_data['currency'], quotation_data['total_amount'],
            quotation_data.get('excel_path', ''), quotation_data.get('pdf_path', ''), quotation_id
        ))
        cur.execute("DELETE FROM quotation_items WHERE quotation_id=?", (quotation_id,))
        for it in items or []:
            code = it.get('code') or it.get('item_code') or ''
            unit = it.get('unit') or ''
            if (not unit) and code:
                master = self._lookup_item_by_code(code)
                unit = (master or {}).get('unit', '') or unit
            cur.execute("""
                INSERT INTO quotation_items (quotation_id, item_code, description, quantity, unit_price, unit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                quotation_id, code, it.get('description', ''), float(it.get('quantity', 0.0) or 0.0),
                float(it.get('unit_price', 0.0) or 0.0), unit or None
            ))
        self.conn.commit()

    def delete_quotation(self, quotation_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM quotation_items WHERE quotation_id=?", (quotation_id,))
        cur.execute("DELETE FROM quotations WHERE id=?", (quotation_id,))
        self.conn.commit()

    # -------------------------
    # Terceros
    # -------------------------
    def search_third_parties(self, query, search_by='name'):
        if not self.conn or len(query) < 2:
            return []
        cur = self.conn.cursor()
        column = 'name' if search_by == 'name' else 'rnc'
        sql_query = f"SELECT rnc, name FROM third_parties WHERE {column} LIKE ? LIMIT 10"
        cur.execute(sql_query, (f"{query}%",))
        return [dict(row) for row in cur.fetchall()]

    def add_or_update_third_party(self, rnc, name):
        if not self.conn or not rnc or not name:
            return
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO third_parties (rnc, name) VALUES (?, ?)
            ON CONFLICT(rnc) DO UPDATE SET name=excluded.name
        """, (rnc.strip(), name.strip()))
        self.conn.commit()

    # -------------------------
    # Utilidades
    # -------------------------
    def close(self):
        if self.conn:
            self.conn.close()

    def _get_unit_from_items(self, code: str = "", name: str = "") -> str:
        try:
            if code:
                m = self._lookup_item_by_code(code)
                u = (m or {}).get('unit', '') or ''
                if u:
                    return u.strip()
            if name:
                try:
                    cur = self.conn.cursor()
                    cur.execute("SELECT unit FROM items WHERE name = ? LIMIT 1", (name.strip(),))
                    row = cur.fetchone()
                    if row and (row["unit"] or "").strip():
                        return row["unit"].strip()
                except Exception as e:
                    print(f"[DEBUG-LOGIC] Error lookup unit by name='{name}': {e}")
        except Exception as e:
            print(f"[DEBUG-LOGIC] _get_unit_from_items error: {e}")
        return ""

    def _ensure_due_date_columns(self):
        cur = self.conn.cursor()
        # companies.invoice_due_date
        cur.execute("PRAGMA table_info(companies)")
        cols = {r["name"] for r in cur.fetchall()}
        if "invoice_due_date" not in cols:
            cur.execute("ALTER TABLE companies ADD COLUMN invoice_due_date TEXT DEFAULT ''")

        # invoices.due_date
        cur.execute("PRAGMA table_info(invoices)")
        cols = {r["name"] for r in cur.fetchall()}
        if "due_date" not in cols:
            cur.execute("ALTER TABLE invoices ADD COLUMN due_date TEXT")

        # quotations.due_date
        cur.execute("PRAGMA table_info(quotations)")
        cols = {r["name"] for r in cur.fetchall()}
        if "due_date" not in cols:
            cur.execute("ALTER TABLE quotations ADD COLUMN due_date TEXT")

        self.conn.commit()

    def compute_quotation_due_date(self, quotation_date: str | None) -> str:
        if not quotation_date:
            return ""
        from datetime import datetime, timedelta
        try:
            d = datetime.strptime(quotation_date[:10], "%Y-%m-%d")
            return (d + timedelta(days=30)).strftime("%Y-%m-%d")
        except Exception:
            return ""

    def get_company_invoice_due_date(self, company_id: int) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT invoice_due_date FROM companies WHERE id = ?", (company_id,))
        row = cur.fetchone()
        if not row:
            return ""
        try:
            return (row["invoice_due_date"] or "").strip()
        except Exception:
            return (row[0] or "").strip()