"""
Implementación de DataAccess para Firebase (Firestore).

Proporciona acceso a datos usando Firestore como backend,
con soporte para multi-usuario y company_id scoping.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from .base import DataAccess
from firebase import get_firebase_client
from constants import NCF_CATEGORY_DEFAULT_PREFIX

NCF_REGEX_STD = re.compile(r'^(?!E)[A-Z][0-9]{10}$')
NCF_REGEX_E = re.compile(r'^E[0-9]{13}$')


class FirebaseDataAccess(DataAccess):
    """
    Implementación de DataAccess usando Firebase Firestore.
    
    Estructura de colecciones:
    - companies/{company_id}
    - items/{item_id}
    - third_parties/{third_party_id}
    - invoices/{invoice_id} con subcol items
    - quotations/{quotation_id} con subcol items
    - sequences/{company_id}_ncf/{ncf_type}
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Inicializa con cliente Firebase.
        
        Args:
            user_id: ID del usuario actual (para created_by/updated_by)
        """
        self.client = get_firebase_client()
        self.db = self.client.get_firestore()
        self.storage = self.client.get_storage()
        self.user_id = user_id or "system"
        
        if not self.db:
            raise RuntimeError("Firestore no está disponible. Verificar configuración de Firebase.")
    
    def _add_metadata(self, data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """Agrega metadatos de auditoría a un documento."""
        now = datetime.utcnow().isoformat()

        if not is_update:
            data['created_at'] = now
            data['created_by'] = self.user_id

        data['updated_at'] = now
        data['updated_by'] = self.user_id

        return data

    # ------------------------------------------------------------------
    # Helpers NCF
    # ------------------------------------------------------------------
    @staticmethod
    def _pad_len_for_prefix(prefix: str) -> int:
        return 11 if (prefix or "").upper().startswith("E") else 8

    def _format_ncf(self, prefix: str, seq: int) -> str:
        if not prefix or seq <= 0:
            return ""
        pad = self._pad_len_for_prefix(prefix)
        return f"{prefix.upper()}{seq:0{pad}d}"

    @staticmethod
    def _normalize_iso_date(value: Optional[str]) -> str:
        if not value:
            return "1900-01-01"
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except Exception:
            return "1900-01-01"

    @staticmethod
    def _sequence_from_ncf(ncf: Optional[str]) -> Optional[int]:
        s = (ncf or "").strip().upper()
        if len(s) < 4 or not s[3:].isdigit():
            return None
        try:
            return int(s[3:])
        except Exception:
            return None

    @staticmethod
    def _validate_ncf(ncf: str) -> bool:
        value = (ncf or "").strip().upper()
        return bool(NCF_REGEX_STD.match(value) or NCF_REGEX_E.match(value))

    @staticmethod
    def _split_ncf(ncf: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        value = (ncf or "").strip().upper()
        if NCF_REGEX_E.match(value):
            return "E", value[1:3], value[3:]
        if NCF_REGEX_STD.match(value):
            return value[0], value[1:3], value[3:]
        return None, None, None

    def _fetch_sequence_configs(self, company_id: int) -> List[Dict[str, Any]]:
        configs: List[Dict[str, Any]] = []
        try:
            query = (
                self.db.collection('ncf_sequence_configs')
                .where('company_id', '==', int(company_id))
            )
            for doc in query.stream():
                data = doc.to_dict() or {}
                data['id'] = doc.id
                configs.append(self._enrich_config(data))
        except Exception as exc:
            print(f"[FIREBASE] Error fetching NCF sequence configs: {exc}")
            return []

        configs.sort(
            key=lambda item: (
                str(item.get('category') or ''),
                str(item.get('effective_from') or ''),
                str(item.get('id') or ''),
            )
        )
        return configs

    def _enrich_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        prefix = (data.get('prefix') or '').upper()
        next_seq = int(data.get('next_sequence') or 1)
        if next_seq <= 0:
            next_seq = 1
        last_assigned = (data.get('last_assigned') or '').upper()
        if not last_assigned and next_seq > 1:
            last_assigned = self._format_ncf(prefix, next_seq - 1)
        enriched = dict(data)
        enriched['prefix'] = prefix
        enriched['next_sequence'] = next_seq
        enriched['last_assigned'] = last_assigned
        enriched['next_ncf'] = self._format_ncf(prefix, next_seq)
        enriched['category'] = str(data.get('category') or '').upper()
        enriched['effective_from'] = self._normalize_iso_date(data.get('effective_from'))
        enriched['notes'] = data.get('notes') or ''
        return enriched

    def _choose_config(
        self,
        configs: List[Dict[str, Any]],
        category: Optional[str],
        prefix: Optional[str],
        reference_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not configs:
            return None
        category_upper = (category or '').strip().upper() or None
        prefix_upper = (prefix or '').strip().upper() or None
        filtered = [cfg for cfg in configs if cfg]
        if category_upper:
            filtered = [cfg for cfg in filtered if cfg.get('category') == category_upper]
        if prefix_upper and filtered:
            filtered = [cfg for cfg in filtered if cfg.get('prefix') == prefix_upper] or filtered

        if not filtered:
            filtered = configs

        ref = self._normalize_iso_date(reference_date)
        active = None
        future = None
        for cfg in filtered:
            eff = cfg.get('effective_from') or '1900-01-01'
            if eff <= ref:
                if (not active) or eff >= (active.get('effective_from') or '1900-01-01'):
                    active = cfg
            elif future is None:
                future = cfg
        return active or future or filtered[-1]

    def _get_config_by_id(self, company_id: int, config_id: Any) -> Optional[Dict[str, Any]]:
        try:
            doc = (
                self.db.collection('ncf_sequence_configs')
                .document(str(config_id))
                .get()
            )
            if not doc.exists:
                return None
            data = doc.to_dict() or {}
            if int(data.get('company_id', company_id)) != int(company_id):
                return None
            data['id'] = doc.id
            return self._enrich_config(data)
        except Exception as exc:
            print(f"[FIREBASE] Error reading NCF config {config_id}: {exc}")
            return None

    def _legacy_sequence_doc(self, company_id: int, prefix: str):
        return self.db.collection('sequences').document(f"{company_id}_ncf_{prefix}")

    def _get_next_ncf_legacy(self, company_id: int, prefix: str) -> str:
        try:
            sequence_ref = self._legacy_sequence_doc(company_id, prefix)
            snapshot = sequence_ref.get()
            current = snapshot.get('current') if snapshot.exists else 0
            return self._format_ncf(prefix, int(current) + 1)
        except Exception as exc:
            print(f"[FIREBASE] Error leyendo secuencia legacy: {exc}")
            return self._format_ncf(prefix, 1)

    def _update_legacy_sequence(self, company_id: int, prefix: str, seq_value: int) -> None:
        try:
            sequence_ref = self._legacy_sequence_doc(company_id, prefix)
            sequence_ref.set({'current': int(seq_value)}, merge=True)
        except Exception as exc:
            print(f"[FIREBASE] Error actualizando secuencia legacy: {exc}")
    
    # ===== EMPRESAS (COMPANIES) =====
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Obtiene todas las empresas."""
        try:
            companies_ref = self.db.collection('companies')
            docs = companies_ref.stream()
            
            companies = []
            for doc in docs:
                company_data = doc.to_dict()
                company_data['id'] = int(doc.id) if doc.id.isdigit() else doc.id
                companies.append(company_data)
            
            return companies
        except Exception as e:
            print(f"[FIREBASE] Error getting companies: {e}")
            return []
    
    def get_company_details(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene detalles completos de una empresa."""
        try:
            doc_ref = self.db.collection('companies').document(str(company_id))
            doc = doc_ref.get()
            
            if doc.exists:
                company_data = doc.to_dict()
                company_data['id'] = company_id
                return company_data
            
            return None
        except Exception as e:
            print(f"[FIREBASE] Error getting company {company_id}: {e}")
            return None
    
    def add_company(self, name: str, rnc: str, address: str = "") -> int:
        """Agrega una nueva empresa. Retorna el ID."""
        try:
            # Generar ID auto-incrementable
            # En Firestore, usamos timestamp + random para evitar colisiones
            import time
            company_id = int(time.time() * 1000) % 1000000
            
            company_data = {
                'name': name,
                'rnc': rnc,
                'address': address,
            }
            company_data = self._add_metadata(company_data)
            
            doc_ref = self.db.collection('companies').document(str(company_id))
            doc_ref.set(company_data)
            
            return company_id
        except Exception as e:
            print(f"[FIREBASE] Error adding company: {e}")
            raise
    
    def update_company_fields(self, company_id: int, fields: Dict[str, Any]) -> None:
        """Actualiza campos específicos de una empresa."""
        try:
            fields = self._add_metadata(fields, is_update=True)
            
            doc_ref = self.db.collection('companies').document(str(company_id))
            doc_ref.update(fields)
        except Exception as e:
            print(f"[FIREBASE] Error updating company {company_id}: {e}")
            raise
    
    # ===== ÍTEMS =====
    
    def get_items_like(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Busca ítems por código o nombre."""
        try:
            items_ref = self.db.collection('items')
            
            # Firestore no soporta LIKE, así que filtramos en cliente
            # Para mejor rendimiento, usar índices y queries específicas
            all_items = []
            
            for doc in items_ref.limit(100).stream():
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                
                # Filtrar por código o nombre
                code = str(item_data.get('code', '')).lower()
                name = str(item_data.get('name', '')).lower()
                query_lower = query.lower()
                
                if query_lower in code or query_lower in name:
                    all_items.append(item_data)
                    
                    if len(all_items) >= limit:
                        break
            
            return all_items
        except Exception as e:
            print(f"[FIREBASE] Error searching items: {e}")
            return []
    
    def get_item_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Obtiene un ítem por código exacto."""
        try:
            items_ref = self.db.collection('items')
            query = items_ref.where('code', '==', code).limit(1)
            
            docs = list(query.stream())
            if docs:
                item_data = docs[0].to_dict()
                item_data['id'] = docs[0].id
                return item_data
            
            return None
        except Exception as e:
            print(f"[FIREBASE] Error getting item by code {code}: {e}")
            return None
    
    # ===== TERCEROS (THIRD PARTIES) =====
    
    def get_third_party_by_rnc(self, rnc: str) -> Optional[Dict[str, Any]]:
        """Obtiene un tercero por RNC."""
        try:
            parties_ref = self.db.collection('third_parties')
            query = parties_ref.where('rnc', '==', rnc).limit(1)
            
            docs = list(query.stream())
            if docs:
                party_data = docs[0].to_dict()
                party_data['id'] = docs[0].id
                return party_data
            
            return None
        except Exception as e:
            print(f"[FIREBASE] Error getting third party by RNC {rnc}: {e}")
            return None
    
    # ===== FACTURAS (INVOICES) =====
    
    def add_invoice(self, invoice_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        """Agrega una nueva factura con sus ítems. Retorna el ID."""
        try:
            import time
            invoice_id = int(time.time() * 1000) % 1000000
            
            # Preparar datos de factura
            invoice_doc = dict(invoice_data)
            invoice_doc = self._add_metadata(invoice_doc)
            
            # Crear documento de factura
            invoice_ref = self.db.collection('invoices').document(str(invoice_id))
            invoice_ref.set(invoice_doc)
            
            # Agregar ítems como subcolección
            items_ref = invoice_ref.collection('items')
            for idx, item in enumerate(items):
                item_doc = self._add_metadata(dict(item))
                items_ref.document(str(idx)).set(item_doc)
            
            return invoice_id
        except Exception as e:
            print(f"[FIREBASE] Error adding invoice: {e}")
            raise
    
    def get_invoices(
        self, 
        company_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene facturas (opcionalmente filtradas por empresa)."""
        try:
            invoices_ref = self.db.collection('invoices')
            
            if company_id:
                query = invoices_ref.where('company_id', '==', company_id)
            else:
                query = invoices_ref
            
            query = query.limit(limit).offset(offset)
            
            invoices = []
            for doc in query.stream():
                invoice_data = doc.to_dict()
                invoice_data['id'] = int(doc.id) if doc.id.isdigit() else doc.id
                invoices.append(invoice_data)
            
            return invoices
        except Exception as e:
            print(f"[FIREBASE] Error getting invoices: {e}")
            return []
    
    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una factura específica con sus ítems."""
        try:
            invoice_ref = self.db.collection('invoices').document(str(invoice_id))
            doc = invoice_ref.get()
            
            if not doc.exists:
                return None
            
            invoice_data = doc.to_dict()
            invoice_data['id'] = invoice_id
            
            # Obtener ítems de la subcolección
            items_ref = invoice_ref.collection('items')
            items = []
            for item_doc in items_ref.stream():
                item_data = item_doc.to_dict()
                items.append(item_data)
            
            invoice_data['items'] = items
            
            return invoice_data
        except Exception as e:
            print(f"[FIREBASE] Error getting invoice {invoice_id}: {e}")
            return None
    
    # ===== COTIZACIONES (QUOTATIONS) =====
    
    def add_quotation(self, quotation_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        """Agrega una nueva cotización con sus ítems. Retorna el ID."""
        try:
            import time
            quotation_id = int(time.time() * 1000) % 1000000
            
            # Preparar datos de cotización
            quotation_doc = dict(quotation_data)
            quotation_doc = self._add_metadata(quotation_doc)
            
            # Crear documento de cotización
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            quotation_ref.set(quotation_doc)
            
            # Agregar ítems como subcolección
            items_ref = quotation_ref.collection('items')
            for idx, item in enumerate(items):
                item_doc = self._add_metadata(dict(item))
                items_ref.document(str(idx)).set(item_doc)
            
            return quotation_id
        except Exception as e:
            print(f"[FIREBASE] Error adding quotation: {e}")
            raise
    
    def get_quotations(
        self,
        company_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene cotizaciones (opcionalmente filtradas por empresa)."""
        try:
            quotations_ref = self.db.collection('quotations')
            
            if company_id:
                query = quotations_ref.where('company_id', '==', company_id)
            else:
                query = quotations_ref
            
            query = query.limit(limit).offset(offset)
            
            quotations = []
            for doc in query.stream():
                quotation_data = doc.to_dict()
                quotation_data['id'] = int(doc.id) if doc.id.isdigit() else doc.id
                quotations.append(quotation_data)
            
            return quotations
        except Exception as e:
            print(f"[FIREBASE] Error getting quotations: {e}")
            return []
    
    def get_quotation_by_id(self, quotation_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una cotización específica con sus ítems."""
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            doc = quotation_ref.get()
            
            if not doc.exists:
                return None
            
            quotation_data = doc.to_dict()
            quotation_data['id'] = quotation_id
            
            # Obtener ítems de la subcolección
            items_ref = quotation_ref.collection('items')
            items = []
            for item_doc in items_ref.stream():
                item_data = item_doc.to_dict()
                items.append(item_data)
            
            quotation_data['items'] = items
            
            return quotation_data
        except Exception as e:
            print(f"[FIREBASE] Error getting quotation {quotation_id}: {e}")
            return None
    
    # ===== NCF / SECUENCIAS =====

    def get_next_ncf(self, company_id: int, ncf_type: str, category: Optional[str] = None) -> str:
        """Obtiene el siguiente NCF disponible para una empresa y tipo."""
        try:
            prefix = (ncf_type or "B01").upper()
            configs = self._fetch_sequence_configs(company_id)
            reference_date = date.today().isoformat()
            config = self._choose_config(configs, category, prefix, reference_date)
            if config:
                cfg_prefix = (config.get('prefix') or prefix).upper()
                seq = int(config.get('next_sequence') or 1)
                if seq <= 0:
                    seq = 1
                return self._format_ncf(cfg_prefix, seq)
            return self._get_next_ncf_legacy(company_id, prefix)
        except Exception as e:
            print(f"[FIREBASE] Error getting next NCF: {e}")
            return self._format_ncf((ncf_type or 'B01').upper(), 1)

    def mark_ncf_used(self, company_id: int, ncf: str) -> None:
        letter, tipo2, seq_str = self._split_ncf(ncf)
        if not letter or not tipo2 or not seq_str or not seq_str.isdigit():
            raise ValueError("NCF inválido para registrar en Firebase")
        prefix = f"{letter}{tipo2}".upper()
        seq_val = int(seq_str)
        configs = self._fetch_sequence_configs(company_id)
        reference_date = date.today().isoformat()
        config = self._choose_config(configs, None, prefix, reference_date)
        ncf_upper = (ncf or "").strip().upper()

        if config and config.get('id'):
            new_next = max(seq_val + 1, int(config.get('next_sequence') or 1))
            try:
                self.db.collection('ncf_sequence_configs').document(str(config['id'])).update({
                    'next_sequence': int(new_next),
                    'last_assigned': ncf_upper,
                    'updated_at': datetime.utcnow().isoformat(),
                    'updated_by': self.user_id,
                })
            except Exception as exc:
                print(f"[FIREBASE] Error actualizando secuencia NCF: {exc}")
        else:
            category = None
            for cat, default_prefix in NCF_CATEGORY_DEFAULT_PREFIX.items():
                if (default_prefix or '').upper() == prefix.upper():
                    category = cat.upper()
                    break
            payload = {
                'category': category or prefix,
                'prefix': prefix,
                'last_assigned': ncf_upper,
                'next_sequence': seq_val + 1,
                'effective_from': reference_date,
            }
            try:
                self.save_ncf_sequence_config(company_id, payload)
            except Exception as exc:
                print(f"[FIREBASE] Error creando secuencia NCF: {exc}")

        self._update_legacy_sequence(company_id, prefix, seq_val)

    def reserve_ncf(self, company_id: int, ncf: str) -> None:
        self.mark_ncf_used(company_id, ncf)

    def list_ncf_sequence_configs(self, company_id: int) -> List[Dict[str, Any]]:
        configs = self._fetch_sequence_configs(company_id)
        reference_date = date.today().isoformat()
        active_per_cat: Dict[str, tuple[str, str]] = {}
        for cfg in configs:
            cat = cfg.get('category', '')
            eff = cfg.get('effective_from') or '1900-01-01'
            cfg_id = str(cfg.get('id'))
            if eff <= reference_date:
                current = active_per_cat.get(cat)
                if (not current) or eff >= current[1]:
                    active_per_cat[cat] = (cfg_id, eff)
        for cfg in configs:
            cat = cfg.get('category', '')
            cfg_id = str(cfg.get('id'))
            active = active_per_cat.get(cat)
            cfg['is_active'] = bool(active and active[0] == cfg_id)
        return configs

    def save_ncf_sequence_config(self, company_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        category = (data.get('category') or '').strip().upper()
        if not category:
            raise ValueError("Debe especificar la categoría del comprobante.")
        prefix = (data.get('prefix') or '').strip().upper()
        if len(prefix) != 3 or not prefix[0].isalpha() or not prefix[1:].isdigit():
            raise ValueError("El prefijo debe tener formato LETRA + 2 dígitos (ej. B01, E31).")

        effective_from = self._normalize_iso_date(data.get('effective_from'))
        notes = (data.get('notes') or '').strip()

        last_assigned = (data.get('last_assigned') or '').strip().upper()
        if last_assigned:
            if not self._validate_ncf(last_assigned):
                raise ValueError("El último NCF indicado no es válido.")
            if not last_assigned.startswith(prefix):
                raise ValueError("El último NCF debe coincidir con el prefijo configurado.")

        next_sequence = data.get('next_sequence')
        if isinstance(next_sequence, str):
            next_sequence = int(next_sequence) if next_sequence.isdigit() else None
        if isinstance(next_sequence, int) and next_sequence <= 0:
            raise ValueError("El próximo correlativo debe ser mayor que cero.")

        seq_value: Optional[int] = next_sequence if isinstance(next_sequence, int) else None
        if seq_value is None:
            last_seq = self._sequence_from_ncf(last_assigned)
            if last_seq is not None:
                seq_value = last_seq + 1
        if seq_value is None or seq_value <= 0:
            seq_value = 1

        last_value = last_assigned if last_assigned else (
            self._format_ncf(prefix, seq_value - 1) if seq_value > 1 else ''
        )

        payload = {
            'company_id': int(company_id),
            'category': category,
            'prefix': prefix,
            'next_sequence': int(seq_value),
            'last_assigned': last_value,
            'effective_from': effective_from,
            'notes': notes,
            'updated_at': datetime.utcnow().isoformat(),
            'updated_by': self.user_id,
        }

        config_id = data.get('id')
        try:
            configs_ref = self.db.collection('ncf_sequence_configs')
            if config_id:
                configs_ref.document(str(config_id)).set(payload, merge=True)
            else:
                payload['created_at'] = datetime.utcnow().isoformat()
                payload['created_by'] = self.user_id
                doc_ref = configs_ref.document()
                doc_ref.set(payload)
                config_id = doc_ref.id
        except Exception as exc:
            print(f"[FIREBASE] Error guardando configuración NCF: {exc}")
            raise

        return self._get_config_by_id(company_id, config_id) or {}

    def delete_ncf_sequence_config(self, company_id: int, config_id: Any) -> None:
        try:
            self.db.collection('ncf_sequence_configs').document(str(config_id)).delete()
        except Exception as exc:
            print(f"[FIREBASE] Error eliminando configuración NCF: {exc}")

    def resolve_ncf_prefix(
        self,
        company_id: int,
        category: str,
        default_prefix: Optional[str] = None,
        reference_date: Optional[str] = None,
    ) -> str:
        prefix = (default_prefix or 'B01').upper()
        configs = self._fetch_sequence_configs(company_id)
        config = self._choose_config(configs, category, None, reference_date)
        if config and config.get('prefix'):
            return str(config.get('prefix')).upper()
        return prefix

    # ===== MÉTODOS ADICIONALES PARA COMPATIBILIDAD =====

    def get_invoice_items(self, invoice_id: int) -> List[Dict[str, Any]]:
        """Obtiene los ítems de una factura específica."""
        try:
            invoice_ref = self.db.collection('invoices').document(str(invoice_id))
            items_ref = invoice_ref.collection('items')
            
            items = []
            for doc in items_ref.stream():
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                items.append(item_data)
            
            return items
        except Exception as e:
            print(f"[FIREBASE] Error getting invoice items for {invoice_id}: {e}")
            return []
    
    def get_quotation_items(self, quotation_id: int) -> List[Dict[str, Any]]:
        """Obtiene los ítems de una cotización específica."""
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            items_ref = quotation_ref.collection('items')
            
            items = []
            for doc in items_ref.stream():
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                items.append(item_data)
            
            return items
        except Exception as e:
            print(f"[FIREBASE] Error getting quotation items for {quotation_id}: {e}")
            return []
    
    def search_third_parties(self, query: str, search_by: str = 'name') -> List[Dict[str, Any]]:
        """Busca terceros por nombre o RNC."""
        try:
            parties_ref = self.db.collection('third_parties')
            
            # Firestore no soporta LIKE, filtrar en cliente
            all_parties = []
            for doc in parties_ref.limit(100).stream():
                party_data = doc.to_dict()
                party_data['id'] = doc.id
                
                if search_by == 'name':
                    if query.lower() in str(party_data.get('name', '')).lower():
                        all_parties.append(party_data)
                elif search_by == 'rnc':
                    if query in str(party_data.get('rnc', '')):
                        all_parties.append(party_data)
                
                if len(all_parties) >= 20:
                    break
            
            return all_parties
        except Exception as e:
            print(f"[FIREBASE] Error searching third parties: {e}")
            return []
    
    def add_or_update_third_party(self, rnc: str, name: str) -> None:
        """Agrega o actualiza un tercero por RNC."""
        try:
            parties_ref = self.db.collection('third_parties')
            query = parties_ref.where('rnc', '==', rnc).limit(1)
            
            docs = list(query.stream())
            
            party_data = {
                'rnc': rnc,
                'name': name,
            }
            party_data = self._add_metadata(party_data, is_update=len(docs) > 0)
            
            if docs:
                # Actualizar existente
                docs[0].reference.update(party_data)
            else:
                # Crear nuevo
                parties_ref.add(party_data)
                
        except Exception as e:
            print(f"[FIREBASE] Error adding/updating third party: {e}")
            raise
    
    def validate_ncf(self, ncf: str) -> bool:
        """Valida formato de NCF."""
        if not ncf:
            return False
        
        # Validación básica de formato
        import re
        # NCF estándar: letra + 10 dígitos
        if re.match(r'^[A-Z][0-9]{10}$', ncf):
            return True
        # e-CF: E + 13 dígitos
        if re.match(r'^E[0-9]{13}$', ncf):
            return True
        
        return False
    
    def get_facturas(self, company_id: int, only_issued: bool = True) -> List[Dict[str, Any]]:
        """Alias de get_invoices para compatibilidad con LogicController."""
        return self.get_invoices(company_id=company_id)
    
    def delete_factura(self, factura_id: int) -> None:
        """Elimina una factura y sus ítems."""
        try:
            invoice_ref = self.db.collection('invoices').document(str(factura_id))
            
            # Eliminar ítems primero
            items_ref = invoice_ref.collection('items')
            for item_doc in items_ref.stream():
                item_doc.reference.delete()
            
            # Eliminar factura
            invoice_ref.delete()
            
        except Exception as e:
            print(f"[FIREBASE] Error deleting invoice {factura_id}: {e}")
            raise
    
    def delete_quotation(self, quotation_id: int) -> None:
        """Elimina una cotización y sus ítems."""
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            
            # Eliminar ítems primero
            items_ref = quotation_ref.collection('items')
            for item_doc in items_ref.stream():
                item_doc.reference.delete()
            
            # Eliminar cotización
            quotation_ref.delete()
            
        except Exception as e:
            print(f"[FIREBASE] Error deleting quotation {quotation_id}: {e}")
            raise
    
    def update_quotation(self, quotation_id: int, quotation_data: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
        """Actualiza una cotización con sus ítems."""
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            
            # Actualizar datos de cotización
            quotation_doc = dict(quotation_data)
            quotation_doc = self._add_metadata(quotation_doc, is_update=True)
            quotation_ref.update(quotation_doc)
            
            # Eliminar ítems antiguos
            items_ref = quotation_ref.collection('items')
            for item_doc in items_ref.stream():
                item_doc.reference.delete()
            
            # Agregar nuevos ítems
            for idx, item in enumerate(items):
                item_doc = self._add_metadata(dict(item))
                items_ref.document(str(idx)).set(item_doc)
                
        except Exception as e:
            print(f"[FIREBASE] Error updating quotation {quotation_id}: {e}")
            raise
    
    # ===== UTILIDADES =====
    
    def commit(self) -> None:
        """No-op para Firestore (commits automáticos)."""
        pass
    
    def close(self) -> None:
        """No-op para Firestore (no necesita cierre explícito)."""
        pass
