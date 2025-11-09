"""
Implementación de DataAccess para SQLite.

Envuelve el LogicController existente para cumplir con la interfaz DataAccess.
Mantiene compatibilidad total con el código existente.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

from .base import DataAccess


class SQLiteDataAccess(DataAccess):
    """
    Adaptador de DataAccess para SQLite (LogicController).
    
    Envuelve el LogicController existente manteniendo toda la lógica
    SQLite actual, pero exponiendo la interfaz DataAccess estándar.
    """
    
    def __init__(self, logic_controller):
        """
        Inicializa con un LogicController existente.
        
        Args:
            logic_controller: Instancia de LogicController
        """
        self.logic = logic_controller
    
    # ===== EMPRESAS (COMPANIES) =====
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Obtiene todas las empresas."""
        return self.logic.get_all_companies()
    
    def get_company_details(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene detalles completos de una empresa."""
        return self.logic.get_company_details(company_id)
    
    def add_company(self, name: str, rnc: str, address: str = "") -> int:
        """Agrega una nueva empresa. Retorna el ID."""
        return self.logic.add_company(name, rnc, address)
    
    def update_company_fields(self, company_id: int, fields: Dict[str, Any]) -> None:
        """Actualiza campos específicos de una empresa."""
        self.logic.update_company_fields(company_id, fields)
    
    # ===== ÍTEMS =====
    
    def get_items_like(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Busca ítems por código o nombre."""
        return self.logic.get_items_like(query, limit)
    
    def get_item_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Obtiene un ítem por código exacto."""
        return self.logic.get_item_by_code(code)
    
    # ===== TERCEROS (THIRD PARTIES) =====
    
    def get_third_party_by_rnc(self, rnc: str) -> Optional[Dict[str, Any]]:
        """Obtiene un tercero por RNC."""
        try:
            return self.logic.get_third_party_by_rnc(rnc)
        except AttributeError:
            # Si el método no existe en logic, retornar None
            return None
    
    # ===== FACTURAS (INVOICES) =====
    
    def add_invoice(self, invoice_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        """Agrega una nueva factura con sus ítems. Retorna el ID."""
        return self.logic.add_invoice(invoice_data, items)
    
    def get_invoices(
        self, 
        company_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene facturas (opcionalmente filtradas por empresa)."""
        try:
            return self.logic.get_invoices(company_id, limit, offset)
        except (AttributeError, TypeError):
            # Fallback si el método tiene firma diferente
            if hasattr(self.logic, 'get_all_invoices'):
                all_invoices = self.logic.get_all_invoices()
                if company_id:
                    all_invoices = [inv for inv in all_invoices if inv.get('company_id') == company_id]
                return all_invoices[offset:offset+limit]
            return []
    
    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una factura específica con sus ítems."""
        try:
            return self.logic.get_invoice_by_id(invoice_id)
        except AttributeError:
            return None
    
    # ===== COTIZACIONES (QUOTATIONS) =====
    
    def add_quotation(self, quotation_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        """Agrega una nueva cotización con sus ítems. Retorna el ID."""
        return self.logic.add_quotation(quotation_data, items)
    
    def get_quotations(
        self,
        company_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene cotizaciones (opcionalmente filtradas por empresa)."""
        try:
            return self.logic.get_quotations(company_id, limit, offset)
        except (AttributeError, TypeError):
            # Fallback si el método tiene firma diferente
            if hasattr(self.logic, 'get_all_quotations'):
                all_quotes = self.logic.get_all_quotations()
                if company_id:
                    all_quotes = [q for q in all_quotes if q.get('company_id') == company_id]
                return all_quotes[offset:offset+limit]
            return []
    
    def get_quotation_by_id(self, quotation_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una cotización específica con sus ítems."""
        try:
            return self.logic.get_quotation_by_id(quotation_id)
        except AttributeError:
            return None
    
    # ===== NCF / SECUENCIAS =====
    
    def get_next_ncf(self, company_id: int, ncf_type: str) -> str:
        """Obtiene el siguiente NCF disponible para una empresa y tipo."""
        try:
            return self.logic.get_next_ncf(company_id, ncf_type)
        except AttributeError:
            # Fallback básico si no existe el método
            return f"B{ncf_type}0000000001"
    
    # ===== MÉTODOS ADICIONALES PARA COMPATIBILIDAD =====
    
    def get_invoice_items(self, invoice_id: int) -> List[Dict[str, Any]]:
        """Obtiene los ítems de una factura específica."""
        try:
            return self.logic.get_invoice_items(invoice_id)
        except AttributeError:
            return []
    
    def get_quotation_items(self, quotation_id: int) -> List[Dict[str, Any]]:
        """Obtiene los ítems de una cotización específica."""
        try:
            return self.logic.get_quotation_items(quotation_id)
        except AttributeError:
            return []
    
    def search_third_parties(self, query: str, search_by: str = 'name') -> List[Dict[str, Any]]:
        """Busca terceros por nombre o RNC."""
        try:
            return self.logic.search_third_parties(query, search_by=search_by)
        except AttributeError:
            return []
    
    def add_or_update_third_party(self, rnc: str, name: str) -> None:
        """Agrega o actualiza un tercero por RNC."""
        try:
            self.logic.add_or_update_third_party(rnc, name)
        except AttributeError:
            pass
    
    def validate_ncf(self, ncf: str) -> bool:
        """Valida formato de NCF."""
        try:
            return self.logic.validate_ncf(ncf)
        except AttributeError:
            # Fallback básico
            return bool(ncf and len(ncf) >= 11)
    
    def get_facturas(self, company_id: int, only_issued: bool = True) -> List[Dict[str, Any]]:
        """Alias de get_invoices para compatibilidad."""
        try:
            return self.logic.get_facturas(company_id, only_issued=only_issued)
        except AttributeError:
            return self.get_invoices(company_id=company_id)
    
    def delete_factura(self, factura_id: int) -> None:
        """Elimina una factura."""
        try:
            self.logic.delete_factura(factura_id)
        except AttributeError:
            pass
    
    def delete_quotation(self, quotation_id: int) -> None:
        """Elimina una cotización."""
        try:
            self.logic.delete_quotation(quotation_id)
        except AttributeError:
            pass
    
    def update_quotation(self, quotation_id: int, quotation_data: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
        """Actualiza una cotización."""
        try:
            self.logic.update_quotation(quotation_id, quotation_data, items)
        except AttributeError:
            pass
    
    # ===== UTILIDADES =====
    
    def commit(self) -> None:
        """Confirma cambios pendientes."""
        if hasattr(self.logic, 'commit'):
            self.logic.commit()
        elif hasattr(self.logic, 'conn'):
            self.logic.conn.commit()
    
    def close(self) -> None:
        """Cierra la conexión."""
        if hasattr(self.logic, 'close'):
            self.logic.close()
        elif hasattr(self.logic, 'conn'):
            self.logic.conn.close()
