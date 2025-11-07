from __future__ import annotations
import os, sys

# Asegura que la raíz del repo esté en sys.path (carpeta padre de /scripts)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from typing import Any, Dict, List

# Ahora sí podemos importar utils
from utils.asset_paths import relativize_if_under_assets, copy_logo_to_assets, get_assets_root

def _iter_companies_from_logic(logic) -> List[Dict[str, Any]]:
    """
    Intenta obtener la lista de empresas desde diferentes métodos comunes.
    """
    for method in ("list_companies", "get_companies", "get_all_companies"):
        if hasattr(logic, method):
            companies = getattr(logic, method)()
            if companies:
                return companies
    # Si no hay un listado, intenta get_company(1..N) si existe get_company_count
    if hasattr(logic, "get_company_count") and hasattr(logic, "get_company"):
        try:
            n = int(logic.get_company_count())
            res = []
            for i in range(1, n + 1):
                c = logic.get_company(i)
                if c:
                    res.append(c)
            return res
        except Exception:
            pass
    raise RuntimeError("No pude obtener empresas del objeto 'logic'. Implementa list_companies() o get_companies().")

def migrate_company_logos_with_logic(logic):
    companies = _iter_companies_from_logic(logic)
    print(f"[migrate] Encontradas {len(companies)} empresas. assets_root={get_assets_root()}")
    for c in companies:
        cid = c.get("id")
        lp = (c.get("logo_path") or "").strip()
        if not lp:
            print(f"  - company {cid}: logo vacío. saltando.")
            continue
        rel = relativize_if_under_assets(lp)
        if rel == lp:
            # No era relativo bajo assets_root: intentar copiar
            src = lp
            if lp.lower().startswith("file:///"):
                src = lp[8:].replace("/", os.sep)
            try:
                new_rel = copy_logo_to_assets(src, cid)
                rel = new_rel
                print(f"  - company {cid}: copiado a assets ({rel})")
            except Exception as e:
                print(f"  - company {cid}: no pude copiar '{lp}': {e}")
                continue
        else:
            print(f"  - company {cid}: relativizado a {rel}")
        # Guardar de vuelta
        if hasattr(logic, "update_company"):
            try:
                logic.update_company(cid, {"logo_path": rel})
                print(f"    guardado en BD.")
            except Exception as e:
                print(f"    error guardando en BD: {e}")
        else:
            print(f"    WARNING: logic.update_company no existe; no guardé el cambio.")

if __name__ == "__main__":
    # Intenta obtener un objeto 'logic' de tu aplicación si exponen un punto de entrada.
    # Reemplaza estas líneas por la forma correcta de obtener 'logic' en tu app:
    logic = None
    try:
        # Ejemplos (ajusta a tu proyecto):
        # from app.bootstrap import get_logic
        # logic = get_logic()
        pass
    except Exception:
        pass

    if logic is None:
        print("No se encontró 'logic'. Ejecuta este script así dentro de tu app:")
        print("  from scripts.migrate_logo_paths import migrate_company_logos_with_logic")
        print("  migrate_company_logos_with_logic(window.logic)  # o tu objeto logic")
        sys.exit(0)

    migrate_company_logos_with_logic(logic)