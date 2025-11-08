"""
Implementación de DataAccess para Firebase (Firestore).

Proporciona acceso a datos usando Firestore como backend,
con soporte para multi-usuario y company_id scoping.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import DataAccess
from firebase import get_firebase_client


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
    
    def get_next_ncf(self, company_id: int, ncf_type: str) -> str:
        """Obtiene el siguiente NCF disponible para una empresa y tipo."""
        try:
            # Importar firestore ANTES de usarlo en el decorador
            from google.cloud import firestore
            
            # Usar transacción para asegurar atomicidad
            sequence_ref = self.db.collection('sequences').document(f"{company_id}_ncf_{ncf_type}")
            
            @firestore.transactional
            def increment_sequence(transaction):
                snapshot = sequence_ref.get(transaction=transaction)
                
                if snapshot.exists:
                    current = snapshot.get('current')
                else:
                    current = 0
                
                new_value = current + 1
                transaction.set(sequence_ref, {'current': new_value})
                
                return new_value
            
            transaction = self.db.transaction()
            seq_num = increment_sequence(transaction)
            
            # Formatear NCF
            return f"B{ncf_type}{seq_num:08d}"
        except Exception as e:
            print(f"[FIREBASE] Error getting next NCF: {e}")
            return f"B{ncf_type}00000001"
    
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
