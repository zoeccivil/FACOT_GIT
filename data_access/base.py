"""
Interfaz base abstracta para acceso a datos.

Define el contrato que deben cumplir todas las implementaciones
(SQLite, Firebase, etc.)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class DataAccess(ABC):
    """
    Interfaz abstracta para acceso a datos.
    
    Todas las implementaciones (SQLite, Firebase) deben heredar
    de esta clase e implementar todos los métodos abstractos.
    """
    
    # ===== EMPRESAS (COMPANIES) =====
    
    @abstractmethod
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Obtiene todas las empresas."""
        pass
    
    @abstractmethod
    def get_company_details(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene detalles completos de una empresa."""
        pass
    
    @abstractmethod
    def add_company(self, name: str, rnc: str, address: str = "") -> int:
        """Agrega una nueva empresa. Retorna el ID."""
        pass
    
    @abstractmethod
    def update_company_fields(self, company_id: int, fields: Dict[str, Any]) -> None:
        """Actualiza campos específicos de una empresa."""
        pass
    
    # ===== ÍTEMS =====
    
    @abstractmethod
    def get_items_like(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Busca ítems por código o nombre."""
        pass
    
    @abstractmethod
    def get_item_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Obtiene un ítem por código exacto."""
        pass
    
    # ===== TERCEROS (THIRD PARTIES) =====
    
    @abstractmethod
    def get_third_party_by_rnc(self, rnc: str) -> Optional[Dict[str, Any]]:
        """Obtiene un tercero por RNC."""
        pass
    
    # ===== FACTURAS (INVOICES) =====
    
    @abstractmethod
    def add_invoice(self, invoice_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        """Agrega una nueva factura con sus ítems. Retorna el ID."""
        pass
    
    @abstractmethod
    def get_invoices(
        self, 
        company_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene facturas (opcionalmente filtradas por empresa)."""
        pass
    
    @abstractmethod
    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una factura específica con sus ítems."""
        pass
    
    # ===== COTIZACIONES (QUOTATIONS) =====
    
    @abstractmethod
    def add_quotation(self, quotation_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        """Agrega una nueva cotización con sus ítems. Retorna el ID."""
        pass
    
    @abstractmethod
    def get_quotations(
        self,
        company_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene cotizaciones (opcionalmente filtradas por empresa)."""
        pass
    
    @abstractmethod
    def get_quotation_by_id(self, quotation_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una cotización específica con sus ítems."""
        pass
    
    # ===== NCF / SECUENCIAS =====
    
    @abstractmethod
    def get_next_ncf(self, company_id: int, ncf_type: str, category: Optional[str] = None) -> str:
        """Obtiene el siguiente NCF disponible para una empresa y tipo."""
        pass

    @abstractmethod
    def mark_ncf_used(self, company_id: int, ncf: str) -> None:
        """Marca un NCF como utilizado."""
        pass

    @abstractmethod
    def reserve_ncf(self, company_id: int, ncf: str) -> None:
        """Reserva un NCF para evitar duplicados."""
        pass

    @abstractmethod
    def list_ncf_sequence_configs(self, company_id: int) -> List[Dict[str, Any]]:
        """Lista configuraciones de secuencias NCF para una empresa."""
        pass

    @abstractmethod
    def save_ncf_sequence_config(self, company_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea o actualiza una configuración de secuencia NCF."""
        pass

    @abstractmethod
    def delete_ncf_sequence_config(self, company_id: int, config_id: Any) -> None:
        """Elimina una configuración de secuencia NCF."""
        pass

    @abstractmethod
    def resolve_ncf_prefix(
        self,
        company_id: int,
        category: str,
        default_prefix: Optional[str] = None,
        reference_date: Optional[str] = None,
    ) -> str:
        """Resuelve el prefijo activo para una categoría dada."""
        pass
    
    # ===== UTILIDADES =====
    
    @abstractmethod
    def commit(self) -> None:
        """Confirma cambios pendientes (para SQLite principalmente)."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Cierra la conexión/cliente."""
        pass
