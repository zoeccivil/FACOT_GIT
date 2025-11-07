class ItemsLookupMixin:
    def _normalize_name(self, s: str) -> str:
        try:
            if hasattr(self, "_dbg_origin"):
                self._dbg_origin(self._normalize_name, "normalize_name")
        except Exception:
            pass
        print("[HIT] _normalize_name (Mixin)")
        s = (s or "").strip().upper()
        return " ".join(s.split())

    def _lookup_unit_by_code_or_name(self, code: str, name: str) -> str:
        try:
            if hasattr(self, "_dbg_origin"):
                self._dbg_origin(self._lookup_unit_by_code_or_name, "lookup_unit")
        except Exception:
            pass
        print(f"[HIT] _lookup_unit_by_code_or_name (Mixin) code='{code}' name='{name}'")

        # 1) por código
        if code and hasattr(self, "logic") and hasattr(self.logic, "get_item_by_code"):
            try:
                found = self.logic.get_item_by_code(code) or {}
                u = (found.get("unit") or "").strip()
                print("[HIT] get_item_by_code ->", found)
                if u:
                    return u
            except Exception as e:
                print("[ItemsLookupMixin] get_item_by_code error:", e)

        # 2) por nombre normalizado
        if name and hasattr(self, "logic") and hasattr(self.logic, "get_items_like"):
            try:
                target = self._normalize_name(name)
                cands = self.logic.get_items_like(name, limit=25) or []
                print(f"[HIT] get_items_like count={len(cands)} first5={[c.get('name') for c in cands[:5]]}")
                for c in cands:
                    if self._normalize_name(c.get("name")) == target:
                        u = (c.get("unit") or "").strip()
                        if u:
                            return u
            except Exception as e:
                print("[ItemsLookupMixin] get_items_like error:", e)

        return ""
