import sqlite3
import os
import json
import datetime
import re

import config_facot
# Cerca del inicio del archivo, junto con tus otros imports
from typing import Any, Dict, List, Optional

from constants import NCF_CATEGORY_DEFAULT_PREFIX


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
        
        print(f"[DEBUG-LOGIC] Path de la BD: {self.db_path}") # Debug 1: ¿Ruta correcta?
        
        self._connect()
        self._initialize_db()

    # -------------------------
    # Bootstrap / DB
    # -------------------------
    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row # CRÍTICO: Permite acceder a columnas por nombre


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
                due_date TEXT,                          -- NUEVO
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
                due_date TEXT,                          -- NUEVO
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

        # --- Terceros ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS third_parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rnc TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL
            )
        """)

        # Columnas nuevas en ítems (unidad/código, etc.)
        self._ensure_line_item_columns()

        # NUEVO: asegurar columnas de vencimiento
        self._ensure_due_date_columns()

        # Configuración de secuencias NCF por empresa
        self._ensure_ncf_sequence_tables()

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
            ("invoice_due_date", "TEXT", "''"),  # NUEVO: fecha fija de vencimiento para facturas
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
    # Maestro de Items (id, code, name, unit, cost, price, category_id, description)
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
            # Captura errores si la tabla 'items' no existe (solución pendiente)
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
            # Captura errores si la tabla 'items' no existe
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
        """
        Actualiza múltiples columnas de companies de forma segura.
        Incluye invoice_due_date entre las columnas permitidas.
        """
        allowed = {
            "address_line1", "address_line2", "phone", "email", "signature_name",
            "logo_path", "address", "invoice_template_path", "invoice_output_base_path",
            "invoice_due_date"  # <---- permitir este campo
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
        """
        Fallback para actualizar un único campo permitido.
        """
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
        # CORRECCIÓN/DEPURACIÓN: Listado explícito de TODAS las columnas para forzar la recuperación
        cur = self.conn.cursor()
        try:
            cur.execute("""
                SELECT 
                    id, name, rnc, address, invoice_template_path, 
                    invoice_output_base_path, itbis_adelantado, legacy_filename,
                    address_line1, address_line2, phone, email, 
                    signature_name, logo_path,
                    invoice_due_date     -- Asegúrate de incluir esta columna
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
    # NCF (DGII) helpers: 1 letra + 10 dígitos (TT + SSSSSSSS)
    # -------------------------
    # === NCF (DGII) helpers: estándar y e-CF ===
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
        """
        Retorna (letter, tipo2, sec_str) si el NCF es válido; de lo contrario (None, None, None).
        - Estándar: total 11 -> tipo2 + 8 de secuencia
        - E (e-CF): total 14 -> tipo2 + 11 de secuencia
        """
        n = (ncf or "").strip().upper()
        if NCF_REGEX_E.match(n):
            letter = "E"
            tipo2 = n[1:3]
            sec = n[3:] # 11 dígitos
            return letter, tipo2, sec
        if NCF_REGEX_STD.match(n):
            letter = n[0]
            tipo2 = n[1:3]
            sec = n[3:] # 8 dígitos
            return letter, tipo2, sec
        return None, None, None

    @staticmethod
    def _pad_len_for_letter(letter: str) -> int:
        return 11 if (letter or "").upper() == "E" else 8

    def _max_seq_for_prefix(self, company_id: int, prefix3: str, issued_only: bool = True) -> int:
        """
        Prefijo 3 chars (letra + tipo2). Devuelve el máximo secuencial (int) observado
        para ese prefijo en la empresa. Si issued_only=True, solo toma invoice_type='emitida'.
        Respeta largo total: E=14, resto=11.
        """
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
                if val > mx:
                    mx = val
            except Exception:
                pass
        return mx

    def get_next_ncf(self, company_id: int, prefix3: str, category: str | None = None) -> str:
        """
        Obtiene el siguiente NCF considerando la configuración de secuencias.

        Si existe una configuración específica por empresa/categoría, usa el prefijo
        y correlativo definidos allí. En caso contrario recurre al máximo registrado
        en facturas emitidas.
        """
        if not prefix3 or len(prefix3) != 3 or not prefix3[0].isalpha() or not prefix3[1:].isdigit():
            prefix3 = "B01"
        prefix3 = prefix3.upper()
        category_upper = (category or "").strip().upper() or None
        today = datetime.date.today().isoformat()

        config = None
        if category_upper:
            config = self._select_ncf_sequence_config(company_id, category_upper, None, today)
        if not config:
            config = self._select_ncf_sequence_config(company_id, None, prefix3, today)

        if config:
            cfg_prefix = (config.get("prefix") or prefix3).upper()
            next_seq = int(config.get("next_sequence") or 1)
            if next_seq <= 0:
                next_seq = 1
            pad = self._pad_len_for_letter(cfg_prefix[0])
            return f"{cfg_prefix}{next_seq:0{pad}d}"

        resolved_prefix = self.resolve_ncf_prefix(
            company_id,
            category_upper or "",
            default_prefix=prefix3,
            reference_date=today,
        )
        pad = self._pad_len_for_letter(resolved_prefix[0])
        max_seq = self._max_seq_for_prefix(company_id, resolved_prefix, issued_only=True)
        return f"{resolved_prefix}{(max_seq + 1):0{pad}d}"

    def find_next_free_ncf(self, company_id: int, prefix3: str, start_seq: int) -> str:
        """
        Busca el siguiente NCF libre preservando el prefijo. Considera padding de E (11) vs estándar (8).
        """
        cur = self.conn.cursor()
        p3 = (prefix3 or "B01").upper()
        pad = self._pad_len_for_letter(p3[0])
        for step in range(0, 10000):
            cand = f"{p3}{(start_seq + step):0{pad}d}"
            cur.execute("""
                SELECT 1 FROM invoices
                WHERE company_id=? AND invoice_number=? LIMIT 1
            """, (company_id, cand))
            if cur.fetchone() is None and self.validate_ncf(cand):
                return cand
        return f"{p3}{start_seq:0{pad}d}"

    def update_invoice_number(self, invoice_id: int, company_id: int, rnc: str, new_ncf: str):
        n = (new_ncf or "").strip().upper()
        if not self.validate_ncf(n):
            return False, "NCF inválido. Formatos válidos: E + 13 dígitos, o letra≠E + 10 dígitos.", n

        cur = self.conn.cursor()
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
        return True, "NCF actualizado.", n

    @staticmethod
    def _normalize_free_form_to_valid(ncf: str) -> str | None:
        s = (ncf or "").strip().upper()
        m = re.match(r'^([A-Z])(\d+)$', s)
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

    @staticmethod
    def _normalize_iso_date(value: str | None) -> str:
        if not value:
            return "1900-01-01"
        try:
            return datetime.date.fromisoformat(value[:10]).isoformat()
        except Exception:
            return "1900-01-01"

    def _format_ncf(self, prefix3: str, seq_value: int | None) -> str:
        if not prefix3 or seq_value is None or seq_value <= 0:
            return ""
        pad = self._pad_len_for_letter(prefix3[0])
        return f"{prefix3.upper()}{seq_value:0{pad}d}"

    @staticmethod
    def _sequence_from_ncf(ncf: str | None) -> int | None:
        s = (ncf or "").strip().upper()
        if len(s) < 4 or not s[3:].isdigit():
            return None
        try:
            return int(s[3:])
        except Exception:
            return None

    @staticmethod
    def _category_for_prefix(prefix3: str) -> str | None:
        pfx = (prefix3 or "").upper()
        for category, default_prefix in NCF_CATEGORY_DEFAULT_PREFIX.items():
            if (default_prefix or "").upper() == pfx:
                return category.upper()
        return None

    def _select_ncf_sequence_config(
        self,
        company_id: int,
        category: str | None,
        prefix: str | None,
        reference_date: str | None = None,
    ) -> Dict[str, Any] | None:
        cur = self.conn.cursor()
        params: List[Any] = [int(company_id)]
        sql = """
            SELECT id, company_id, category, prefix, next_sequence, last_assigned,
                   effective_from, notes, updated_at
            FROM ncf_sequence_configs
            WHERE company_id = ?
        """
        if category:
            sql += " AND UPPER(category) = ?"
            params.append(category.upper())
        if prefix:
            sql += " AND UPPER(prefix) = ?"
            params.append(prefix.upper())
        sql += " ORDER BY effective_from ASC, id ASC"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        if not rows:
            return None
        ref = self._normalize_iso_date(reference_date)
        active: Dict[str, Any] | None = None
        future: Dict[str, Any] | None = None
        for row in rows:
            eff = self._normalize_iso_date(row.get("effective_from"))
            row["effective_from"] = eff
            if eff <= ref:
                if (not active) or eff >= active.get("effective_from", "1900-01-01"):
                    active = row
            elif future is None:
                future = row
        return active or future or rows[-1]

    def _enrich_sequence_row(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(raw)
        prefix = (data.get("prefix") or "").upper()
        data["prefix"] = prefix
        next_sequence = int(data.get("next_sequence") or 1)
        if next_sequence <= 0:
            next_sequence = 1
        data["next_sequence"] = next_sequence
        last_assigned = (data.get("last_assigned") or "").upper()
        if not last_assigned and next_sequence > 1:
            last_assigned = self._format_ncf(prefix, next_sequence - 1)
        data["last_assigned"] = last_assigned
        data["next_ncf"] = self._format_ncf(prefix, next_sequence)
        data["category"] = (data.get("category") or "").upper()
        data["effective_from"] = self._normalize_iso_date(data.get("effective_from"))
        data["notes"] = data.get("notes") or ""
        return data

    def _get_ncf_sequence_config_by_id(self, config_id: Any) -> Dict[str, Any] | None:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, company_id, category, prefix, next_sequence, last_assigned,
                   effective_from, notes, updated_at
            FROM ncf_sequence_configs
            WHERE id = ?
            """,
            (config_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._enrich_sequence_row(dict(row))

    def list_ncf_sequence_configs(self, company_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, company_id, category, prefix, next_sequence, last_assigned,
                   effective_from, notes, updated_at
            FROM ncf_sequence_configs
            WHERE company_id = ?
            ORDER BY UPPER(category) ASC, effective_from ASC, id ASC
            """,
            (int(company_id),),
        )
        rows = [self._enrich_sequence_row(dict(r)) for r in cur.fetchall()]
        reference_date = datetime.date.today().isoformat()
        active_per_category: Dict[str, tuple[int, str]] = {}
        for row in rows:
            cat = row.get("category", "")
            eff = row.get("effective_from") or "1900-01-01"
            try:
                row_id = int(row.get("id"))
            except Exception:
                continue
            if eff <= reference_date:
                current = active_per_category.get(cat)
                if (not current) or eff >= current[1]:
                    active_per_category[cat] = (row_id, eff)
        for row in rows:
            cat = row.get("category", "")
            row_id = None
            try:
                row_id = int(row.get("id"))
            except Exception:
                pass
            active = active_per_category.get(cat)
            row["is_active"] = bool(active and active[0] == row_id)
        return rows

    def save_ncf_sequence_config(self, company_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        category = (data.get("category") or "").strip().upper()
        if not category:
            raise ValueError("La categoría/tipo de comprobante es obligatoria.")
        prefix = (data.get("prefix") or "").strip().upper()
        if len(prefix) != 3 or not prefix[0].isalpha() or not prefix[1:].isdigit():
            raise ValueError("El prefijo debe tener formato LETRA + 2 dígitos (ej. B01, E31).")

        effective_from = self._normalize_iso_date(data.get("effective_from"))
        notes = (data.get("notes") or "").strip()

        last_assigned = (data.get("last_assigned") or "").strip().upper()
        if last_assigned:
            if not self.validate_ncf(last_assigned):
                raise ValueError("El último NCF indicado no es válido.")
            if not last_assigned.startswith(prefix):
                raise ValueError("El último NCF debe iniciar con el prefijo configurado.")

        next_sequence = data.get("next_sequence")
        seq_value = None
        if isinstance(next_sequence, str):
            next_sequence = int(next_sequence) if next_sequence.isdigit() else None
        if isinstance(next_sequence, int):
            if next_sequence <= 0:
                raise ValueError("El siguiente correlativo debe ser mayor que cero.")
            seq_value = max(next_sequence, 1)
        if seq_value is None:
            last_seq = self._sequence_from_ncf(last_assigned)
            if last_seq is not None:
                seq_value = last_seq + 1
        if seq_value is None:
            seq_value = self._max_seq_for_prefix(company_id, prefix, issued_only=True) + 1
        if seq_value <= 0:
            seq_value = 1

        last_value = last_assigned
        if not last_value and seq_value > 1:
            last_value = self._format_ncf(prefix, seq_value - 1)

        config_id = data.get("id")
        timestamp = datetime.datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        if config_id:
            cur.execute(
                """
                UPDATE ncf_sequence_configs
                   SET category = ?, prefix = ?, next_sequence = ?, last_assigned = ?,
                       effective_from = ?, notes = ?, updated_at = ?
                 WHERE id = ? AND company_id = ?
                """,
                (
                    category,
                    prefix,
                    int(seq_value),
                    last_value,
                    effective_from,
                    notes,
                    timestamp,
                    int(config_id),
                    int(company_id),
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO ncf_sequence_configs (
                    company_id, category, prefix, next_sequence, last_assigned,
                    effective_from, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(company_id),
                    category,
                    prefix,
                    int(seq_value),
                    last_value,
                    effective_from,
                    notes,
                    timestamp,
                ),
            )
            config_id = cur.lastrowid
        self.conn.commit()
        saved = self._get_ncf_sequence_config_by_id(config_id)
        return saved or {}

    def delete_ncf_sequence_config(self, company_id: int, config_id: Any) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM ncf_sequence_configs WHERE id = ? AND company_id = ?",
            (config_id, int(company_id)),
        )
        self.conn.commit()

    def resolve_ncf_prefix(
        self,
        company_id: int,
        category: str,
        default_prefix: str | None = None,
        reference_date: str | None = None,
    ) -> str:
        default = (default_prefix or "B01").upper()
        category_upper = (category or "").strip().upper()
        config = None
        if category_upper:
            config = self._select_ncf_sequence_config(company_id, category_upper, None, reference_date)
        if config and config.get("prefix"):
            return str(config.get("prefix")).upper()
        return default

    def _apply_sequence_usage(self, company_id: int, prefix3: str, seq_value: int, ncf_str: str) -> bool:
        today = datetime.date.today().isoformat()
        config = self._select_ncf_sequence_config(company_id, None, prefix3, today)
        if not config:
            category = self._category_for_prefix(prefix3)
            if category:
                config = self._select_ncf_sequence_config(company_id, category, None, today)
        if not config:
            return False
        new_next = seq_value + 1
        current_next = int(config.get("next_sequence") or 1)
        if current_next > new_next:
            new_next = current_next
        timestamp = datetime.datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE ncf_sequence_configs
               SET next_sequence = ?, last_assigned = ?, updated_at = ?
             WHERE id = ?
            """,
            (
                int(new_next),
                ncf_str,
                timestamp,
                int(config.get("id")),
            ),
        )
        self.conn.commit()
        return True

    def mark_ncf_used(self, company_id: int, ncf: str) -> None:
        letter, tipo2, seq_str = self.split_ncf(ncf)
        if not letter or not tipo2 or not seq_str or not seq_str.isdigit():
            raise ValueError("NCF inválido para marcar como usado.")
        prefix3 = f"{letter}{tipo2}".upper()
        seq_value = int(seq_str)
        ncf_upper = (ncf or "").strip().upper()
        if self._apply_sequence_usage(company_id, prefix3, seq_value, ncf_upper):
            return
        category = self._category_for_prefix(prefix3) or prefix3
        payload = {
            "category": category,
            "prefix": prefix3,
            "last_assigned": ncf_upper,
            "next_sequence": seq_value + 1,
            "effective_from": datetime.date.today().isoformat(),
        }
        self.save_ncf_sequence_config(company_id, payload)

    def reserve_ncf(self, company_id: int, ncf: str) -> None:
        # Para evitar duplicados, usamos la misma lógica que mark_ncf_used.
        self.mark_ncf_used(company_id, ncf)

    # -------------------------
    # Facturas
    # -------------------------
    # --- Guardado de factura: por defecto 'emitida' ---

    def add_invoice(self, invoice_data, items):
        """
        Inserta la factura y sus renglones.
        - La unidad SIEMPRE viene del maestro (ya implementado).
        - El vencimiento (due_date) se resuelve así:
        1) invoice_data['due_date'] si viene
        2) companies.invoice_due_date (fija por empresa)
        3) '' (sin vencimiento)
        """
        cur = self.conn.cursor()
        inv_type = (invoice_data.get('invoice_type') or 'emitida')
        company_id = int(invoice_data.get('company_id'))

        # Resolver due_date
        due_date = (invoice_data.get('due_date') or "").strip()
        if not due_date:
            due_date = self.get_company_invoice_due_date(company_id) or ""

        # Cabecera
        cur.execute("""
            INSERT INTO invoices (company_id, invoice_type, invoice_date, imputation_date, invoice_number,
                                invoice_category, rnc, third_party_name, client_name, client_rnc, currency, itbis,
                                total_amount, exchange_rate, total_amount_rd, excel_path, pdf_path, attachment_path, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            inv_type,
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
            # SIEMPRE desde items.unit (por code; si no hay, por nombre exacto)
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
        cur = self.conn.cursor()
        cur.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (factura_id,))
        cur.execute("DELETE FROM invoices WHERE id = ?", (factura_id,))
        self.conn.commit()

    # -------------------------
    # Cotizaciones
    # -------------------------

    def add_quotation(self, quotation_data, items):
        """
        Inserta la cotización y sus renglones.
        - La unidad SIEMPRE viene del maestro.
        - due_date = quotation_date + 30 días (automático).
        """
        cur = self.conn.cursor()

        qdate = quotation_data.get('quotation_date')
        due_date = self.compute_quotation_due_date(qdate)

        # Cabecera
        cur.execute("""
            INSERT INTO quotations (company_id, quotation_date, client_name, client_rnc, notes, currency, total_amount, excel_path, pdf_path, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            quotation_data['company_id'],
            qdate,
            quotation_data['client_name'],
            quotation_data.get('client_rnc', ''),
            quotation_data.get('notes', ''),
            quotation_data['currency'],
            float(quotation_data.get('total_amount', 0.0) or 0.0),
            quotation_data.get('excel_path', ''),
            quotation_data.get('pdf_path', ''),
            due_date or None
        ))
        quotation_id = cur.lastrowid

        # Detalle
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
            # SIEMPRE desde items.unit
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
            quotation_data.get('excel_path', ''), quotation_data.get('pdf_path', ''),
            quotation_id
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
                quotation_id,
                code,
                it.get('description', ''),
                float(it.get('quantity', 0.0) or 0.0),
                float(it.get('unit_price', 0.0) or 0.0),
                unit or None
            ))
        self.conn.commit()

    def delete_quotation(self, quotation_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM quotation_items WHERE quotation_id=?", (quotation_id,))
        cur.execute("DELETE FROM quotations WHERE id=?", (quotation_id,))
        self.conn.commit()

    # -------------------------
    # Terceros / Clientes / Proveedores
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
    # Utilidades varias
    # -------------------------
    def close(self):
        if self.conn:
            self.conn.close()

    def _get_unit_from_items(self, code: str = "", name: str = "") -> str:
        """
        Devuelve SIEMPRE la unidad desde el maestro items.unit.
        - Primero intenta por code.
        - Si no hay code, intenta por nombre exacto (name = description).
        """
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
    
# --- NUEVO/ACTUALIZADO: helpers y migraciones de vencimiento ---

    def _ensure_due_date_columns(self):
        """
        Asegura columnas due_date en invoices y quotations y la fija por empresa en companies.
        Se puede llamar en cada inicio sin efectos adversos.
        """
        cur = self.conn.cursor()

        # companies.invoice_due_date (fecha fija para facturas de esta empresa)
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


    def _ensure_ncf_sequence_tables(self) -> None:
        """Crea tablas auxiliares para administrar secuencias de NCF."""
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ncf_sequence_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                prefix TEXT NOT NULL,
                next_sequence INTEGER NOT NULL DEFAULT 1,
                last_assigned TEXT,
                effective_from TEXT NOT NULL DEFAULT '1900-01-01',
                notes TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                UNIQUE(company_id, category, effective_from)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ncf_seq_company
                ON ncf_sequence_configs(company_id)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ncf_seq_category
                ON ncf_sequence_configs(company_id, category)
            """
        )
        self.conn.commit()


    def compute_quotation_due_date(self, quotation_date: str | None) -> str:
        """
        Retorna quotation_date + 30 días en formato YYYY-MM-DD.
        Si no se puede parsear, retorna ''.
        """
        if not quotation_date:
            return ""
        from datetime import datetime, timedelta
        try:
            d = datetime.strptime(quotation_date[:10], "%Y-%m-%d")
            return (d + timedelta(days=30)).strftime("%Y-%m-%d")
        except Exception:
            return ""


    def get_company_invoice_due_date(self, company_id: int) -> str:
        """
        Retorna companies.invoice_due_date para la empresa, o '' si no está definido.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT invoice_due_date FROM companies WHERE id = ?", (company_id,))
        row = cur.fetchone()
        if not row:
            return ""
        # sqlite3.Row: puede acceder por índice o nombre
        try:
            return (row["invoice_due_date"] or "").strip()
        except Exception:
            return (row[0] or "").strip()