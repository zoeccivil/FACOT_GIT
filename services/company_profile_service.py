"""
CompanyProfileService - Unified service for retrieving company profile data.

This service provides a centralized way to get company information with:
- Logo resolution (DB → config → default with file:/// conversion)
- Address normalization (line1, line2, compact address)
- Signature/authorized name handling
- In-memory LRU cache for performance

Usage:
    service = CompanyProfileService(logic_controller)
    profile = service.get_company_profile(company_id)
"""

from __future__ import annotations
import os
from typing import Dict, Any, Optional

# Config for logo paths and defaults
try:
    import config_facot
except Exception:
    class _Cfg:
        COMPANY_LOGOS = {}  # {company_id(str/int) or name: path}
        DEFAULT_LOGO_PATH = ""
    config_facot = _Cfg()

# Data root for resolving relative paths
try:
    from utils.template_manager import get_data_root
except Exception:
    def get_data_root():
        return os.getcwd()


class CompanyProfileService:
    """
    Service for retrieving and normalizing company profile data.
    
    Provides:
    - get_company_profile(company_id) → complete normalized profile
    - Logo resolution with priority: DB → config → default
    - Address normalization
    - Simple in-memory caching
    """
    
    def __init__(self, logic_controller):
        """
        Initialize the service with a logic controller.
        
        Args:
            logic_controller: Instance with get_company_details() method
        """
        self.logic = logic_controller
        self._cache = {}  # Simple dict-based cache: {company_id: profile}
        
    def get_company_profile(
        self,
        company_id: int,
        force_refresh: bool = False,
        template_logo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get complete company profile with normalized fields.
        
        Args:
            company_id: Company ID to retrieve
            force_refresh: If True, bypass cache and reload from DB
            template_logo_path: Optional template logo path for resolution priority
            
        Returns:
            Dict with keys:
                - id, name, rnc, phone, email
                - address_line1, address_line2, address (compact)
                - signature_name, authorized_name (aliases)
                - logo_uri (resolved to file:/// or empty)
                - invoice_due_date (fixed due date if set)
        """
        # Check cache unless force refresh
        if not force_refresh and company_id in self._cache:
            return dict(self._cache[company_id])  # Return copy
            
        # Get from database
        company = self.logic.get_company_details(company_id) or {}
        
        if not company:
            # Return minimal empty profile
            return {
                "id": company_id,
                "name": "",
                "rnc": "",
                "phone": "",
                "email": "",
                "address_line1": "",
                "address_line2": "",
                "address": "Dirección no especificada",
                "signature_name": "",
                "authorized_name": "",
                "logo_uri": "",
                "invoice_due_date": "",
            }
        
        # Normalize basic fields
        profile = {
            "id": company.get("id"),
            "name": company.get("name") or company.get("company_name") or "",
            "rnc": company.get("rnc") or company.get("rnc_number") or "",
            "phone": company.get("phone") or company.get("telefono") or "",
            "email": company.get("email") or company.get("correo") or "",
        }
        
        # Address handling
        a1 = (company.get("address_line1") or company.get("address") or "").strip()
        a2 = (company.get("address_line2") or "").strip()
        profile["address_line1"] = a1
        profile["address_line2"] = a2
        
        # Compact address
        address_full = (a1 + (" " + a2 if a2 else "")).strip()
        if not address_full:
            address_full = (company.get("address") or "").strip()
        profile["address"] = address_full or "Dirección no especificada"
        
        # Signature/authorized name (aliases)
        sig = (company.get("signature_name") or company.get("authorized_name") or "").strip()
        profile["signature_name"] = sig
        profile["authorized_name"] = sig
        
        # Logo resolution with priority
        logo_uri = self._resolve_logo_uri(
            company,
            template_logo_path=template_logo_path
        )
        profile["logo_uri"] = logo_uri
        
        # Fixed due date (if configured per company)
        profile["invoice_due_date"] = (company.get("invoice_due_date") or "").strip()
        
        # Cache the result
        self._cache[company_id] = dict(profile)
        
        return profile
    
    def clear_cache(self, company_id: Optional[int] = None):
        """
        Clear cache for specific company or all companies.
        
        Args:
            company_id: If provided, clear only this company. Otherwise clear all.
        """
        if company_id is not None:
            self._cache.pop(company_id, None)
        else:
            self._cache.clear()
    
    def _resolve_logo_uri(
        self,
        company: Dict[str, Any],
        template_logo_path: Optional[str] = None
    ) -> str:
        """
        Resolve logo path to file:/// URI or return empty string.
        
        Priority:
        1. company.logo_path (from DB)
        2. template_logo_path (parameter)
        3. config_facot.COMPANY_LOGOS[company_id or name]
        4. config_facot.DEFAULT_LOGO_PATH
        
        Returns:
            file:/// URI if file exists, http(s):// URL as-is, or empty string
        """
        candidates = []
        
        # 1. Database logo
        db_logo = (company or {}).get("logo_path") or ""
        if db_logo:
            candidates.append(db_logo)
            
        # 2. Template logo
        if template_logo_path:
            candidates.append(template_logo_path)
            
        # 3. Config logos by ID or name
        logos = getattr(config_facot, "COMPANY_LOGOS", {}) or {}
        cid = company.get("id")
        name = (company.get("name") or "").strip()
        
        if cid is not None:
            key_id = str(cid)
            if key_id in logos:
                candidates.append(logos[key_id])
                
        if name and name in logos:
            candidates.append(logos[name])
            
        # 4. Default logo
        default_logo = getattr(config_facot, "DEFAULT_LOGO_PATH", "") or ""
        if default_logo:
            candidates.append(default_logo)
            
        # Resolve candidates
        data_root = get_data_root()
        
        for candidate in candidates:
            if not candidate:
                continue
                
            # Already a file:/// URI
            if isinstance(candidate, str) and candidate.startswith("file:///"):
                local = candidate.replace("file:///", "")
                if os.path.exists(local):
                    return candidate
                continue
                
            # Try relative to data_root
            try:
                rel = os.path.join(data_root, candidate)
                if os.path.exists(rel):
                    return self._to_file_uri(rel)
            except Exception:
                pass
                
            # Try absolute path
            if os.path.isabs(candidate) and os.path.exists(candidate):
                return self._to_file_uri(candidate)
                
            # HTTP/HTTPS URL
            if candidate.startswith(("http://", "https://")):
                return candidate
                
        return ""
    
    @staticmethod
    def _to_file_uri(path: str) -> str:
        """
        Convert local path to file:/// URI.
        
        Args:
            path: Local file path
            
        Returns:
            file:/// URI (Windows: file:///C:/path, POSIX: file:///path)
        """
        if not path:
            return ""
        p = os.path.abspath(path)
        if os.name == "nt":
            return "file:///" + p.replace("\\", "/")
        return "file://" + p
