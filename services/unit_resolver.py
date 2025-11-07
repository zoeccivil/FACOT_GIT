"""
UnitResolver - Service for resolving item units from database.

Provides automatic unit resolution for items with missing unit information:
1. Try to resolve by item code (exact match)
2. Try to resolve by item name (fuzzy match with get_items_like)
3. Fallback to default unit ("UND")

Usage:
    resolver = UnitResolver(logic_controller)
    unit = resolver.resolve_unit(item_code, item_name, current_unit)
"""

from __future__ import annotations
from typing import Optional


class UnitResolver:
    """
    Service for resolving item units from the database.
    
    Resolution priority:
    1. Use current_unit if not empty
    2. Look up by code (exact match)
    3. Look up by name (fuzzy match)
    4. Fallback to DEFAULT_UNIT
    """
    
    DEFAULT_UNIT = "UND"
    
    def __init__(self, logic_controller):
        """
        Initialize the resolver with a logic controller.
        
        Args:
            logic_controller: Instance with get_item_by_code() and get_items_like() methods
        """
        self.logic = logic_controller
        self._cache = {}  # Cache resolved units: {(code, name): unit}
        
    def resolve_unit(
        self,
        item_code: Optional[str] = None,
        item_name: Optional[str] = None,
        current_unit: Optional[str] = None
    ) -> str:
        """
        Resolve the unit for an item.
        
        Args:
            item_code: Item code to look up
            item_name: Item name to look up (used if code fails)
            current_unit: Current unit value (returned if not empty)
            
        Returns:
            Resolved unit string (never empty - falls back to DEFAULT_UNIT)
        """
        # 1. If current_unit is already set, use it
        if current_unit and str(current_unit).strip():
            return str(current_unit).strip()
            
        # Normalize inputs
        code = (item_code or "").strip()
        name = (item_name or "").strip()
        
        # Check cache
        cache_key = (code, name)
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # 2. Try to resolve by code (exact match)
        if code:
            unit = self._resolve_by_code(code)
            if unit:
                self._cache[cache_key] = unit
                return unit
                
        # 3. Try to resolve by name (fuzzy match)
        if name:
            unit = self._resolve_by_name(name)
            if unit:
                self._cache[cache_key] = unit
                return unit
                
        # 4. Fallback to default
        self._cache[cache_key] = self.DEFAULT_UNIT
        return self.DEFAULT_UNIT
    
    def resolve_items(self, items: list) -> None:
        """
        Resolve units for a list of items in-place.
        
        Modifies each item dict to ensure it has a 'unit' field.
        
        Args:
            items: List of item dicts with 'code', 'description', and optionally 'unit'
        """
        if not items:
            return
            
        for item in items:
            if not isinstance(item, dict):
                continue
                
            # Get current values
            code = item.get("code") or item.get("item_code")
            name = item.get("description") or item.get("name")
            current_unit = item.get("unit")
            
            # Resolve and update
            item["unit"] = self.resolve_unit(code, name, current_unit)
    
    def clear_cache(self):
        """Clear the resolution cache."""
        self._cache.clear()
    
    def _resolve_by_code(self, code: str) -> Optional[str]:
        """
        Resolve unit by exact code match.
        
        Args:
            code: Item code to look up
            
        Returns:
            Unit string if found, None otherwise
        """
        try:
            item = self.logic.get_item_by_code(code)
            if item and item.get("unit"):
                unit = str(item["unit"]).strip()
                if unit:
                    return unit
        except Exception as e:
            print(f"[UnitResolver] Error resolving by code '{code}': {e}")
        return None
    
    def _resolve_by_name(self, name: str) -> Optional[str]:
        """
        Resolve unit by fuzzy name match.
        
        Uses get_items_like to find similar items and returns
        the unit from the first match.
        
        Args:
            name: Item name/description to search for
            
        Returns:
            Unit string if found, None otherwise
        """
        try:
            matches = self.logic.get_items_like(name, limit=1)
            if matches and len(matches) > 0:
                item = matches[0]
                if item.get("unit"):
                    unit = str(item["unit"]).strip()
                    if unit:
                        return unit
        except Exception as e:
            print(f"[UnitResolver] Error resolving by name '{name}': {e}")
        return None
