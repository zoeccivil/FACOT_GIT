"""
Gestor centralizado de lógica NCF (Número de Comprobante Fiscal)
según normativa DGII de República Dominicana.

Maneja:
- Formatos estándar vs E-CF
- Configuración por empresa y tipo
- Cambio de nomenclatura 2026
"""

import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple


class NCFManager:
    """
    Gestor de NCF con soporte para:
    - Formato estándar DGII (11 caracteres)
    - Formato E-CF electrónico (14 caracteres)
    - Configuración de secuencias por empresa/tipo
    - Cambio de prefijos 2026
    """
    
    # Regex para validación NCF según DGII
    NCF_STANDARD_PATTERN = re.compile(r'^(?!E)[A-Z][0-9]{10}$')  # No E, letra + 10 dígitos
    NCF_ECF_PATTERN = re.compile(r'^E[0-9]{13}$')  # E + 13 dígitos
    
    # Mapeo de tipos NCF actuales (hasta 2026)
    NCF_TYPES_CURRENT = {
        'B01': 'Crédito Fiscal',
        'B02': 'Consumidor Final',
        'B14': 'Regímenes Especiales',
        'B15': 'Gubernamental',
        'B16': 'Exportaciones',
        'E31': 'Consumidor Final E-CF',
        'E32': 'Crédito Fiscal E-CF',
        'E33': 'Nota de Débito E-CF',
        'E34': 'Nota de Crédito E-CF',
        'E41': 'Compras E-CF',
        'E43': 'Gastos Menores E-CF',
        'E44': 'Regímenes Especiales E-CF',
        'E45': 'Gubernamental E-CF',
    }
    
    # Mapeo de cambio 2026 (ejemplo)
    NCF_TYPES_2026 = {
        'B01': 'F01',  # Crédito Fiscal
        'B02': 'F02',  # Consumidor Final
        'B14': 'F14',  # Regímenes Especiales
        'B15': 'F15',  # Gubernamental
        'B16': 'F16',  # Exportaciones
    }
    
    @staticmethod
    def pad_length_for_prefix(prefix: str) -> int:
        """
        Retorna longitud de padding según tipo de NCF.
        
        Args:
            prefix: Prefijo de 3 caracteres (ej: "B01", "E31")
            
        Returns:
            11 para E-CF, 8 para estándar
        """
        if not prefix or len(prefix) < 1:
            return 8
        return 11 if prefix[0].upper() == 'E' else 8
    
    @staticmethod
    def validate_ncf(ncf: str) -> bool:
        """
        Valida formato de NCF según DGII.
        
        Args:
            ncf: NCF a validar
            
        Returns:
            True si es válido, False si no
        """
        if not ncf:
            return False
            
        ncf = ncf.strip().upper()
        
        # Validar E-CF (14 caracteres)
        if ncf.startswith('E'):
            return bool(NCFManager.NCF_ECF_PATTERN.match(ncf))
        
        # Validar estándar (11 caracteres)
        return bool(NCFManager.NCF_STANDARD_PATTERN.match(ncf))
    
    @staticmethod
    def format_ncf(prefix: str, sequence: int) -> str:
        """
        Formatea NCF con prefijo y secuencia.
        
        Args:
            prefix: Prefijo de 3 caracteres (ej: "B01")
            sequence: Número de secuencia
            
        Returns:
            NCF formateado (ej: "B0100000001" o "E3100000000001")
        """
        if not prefix or len(prefix) != 3:
            prefix = "B01"  # Default
        
        pad_len = NCFManager.pad_length_for_prefix(prefix)
        return f"{prefix.upper()}{sequence:0{pad_len}d}"
    
    @staticmethod
    def parse_ncf(ncf: str) -> Optional[Tuple[str, int]]:
        """
        Parsea NCF extrayendo prefijo y secuencia.
        
        Args:
            ncf: NCF a parsear
            
        Returns:
            Tuple (prefijo, secuencia) o None si inválido
        """
        if not NCFManager.validate_ncf(ncf):
            return None
        
        ncf = ncf.strip().upper()
        prefix = ncf[:3]
        
        try:
            sequence = int(ncf[3:])
            return (prefix, sequence)
        except ValueError:
            return None
    
    @staticmethod
    def get_active_prefix(
        current_prefix: str,
        new_prefix: str,
        activation_date: Optional[date],
        auto_switch: bool,
        current_date: Optional[date] = None
    ) -> str:
        """
        Determina qué prefijo usar según fecha de activación.
        
        Args:
            current_prefix: Prefijo actual (ej: "B01")
            new_prefix: Nuevo prefijo 2026 (ej: "F01")
            activation_date: Fecha de cambio automático
            auto_switch: Si auto-cambio está habilitado
            current_date: Fecha actual (None = hoy)
            
        Returns:
            Prefijo a usar
        """
        if not auto_switch or not activation_date or not new_prefix:
            return current_prefix
        
        if current_date is None:
            current_date = date.today()
        
        if current_date >= activation_date:
            return new_prefix
        
        return current_prefix
    
    @staticmethod
    def get_ncf_type_name(prefix: str) -> str:
        """
        Obtiene nombre descriptivo del tipo de NCF.
        
        Args:
            prefix: Prefijo de 3 caracteres
            
        Returns:
            Nombre del tipo o "Desconocido"
        """
        return NCFManager.NCF_TYPES_CURRENT.get(prefix, "Desconocido")
    
    @staticmethod
    def get_2026_prefix(current_prefix: str) -> Optional[str]:
        """
        Obtiene el prefijo 2026 correspondiente al actual.
        
        Args:
            current_prefix: Prefijo actual (ej: "B01")
            
        Returns:
            Nuevo prefijo o None si no hay mapeo
        """
        return NCFManager.NCF_TYPES_2026.get(current_prefix)
