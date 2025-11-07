#!/usr/bin/env python3
"""
Generador rápido de HTML de cotización (uso único).
Lee templates/quotation_template.html, inyecta JSON con datos de ejemplo (o carga company.json/template.json/quotation.json si existen),
genera preview_output.html en la raíz del repo y lo abre en el navegador por defecto.

Uso:
  python tools/generate_preview_html.py
"""
import json
import os
import webbrowser
from pathlib import Path

ROOT = Path.cwd()
TEMPLATE_PATH = ROOT / "templates" / "quotation_template.html"
OUT_PATH = ROOT / "preview_output.html"

# Si quieres usar archivos JSON externos, crea company.json template.json quotation.json junto a este script.
def load_if_exists(name: str):
    p = ROOT / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

company = load_if_exists("company.json") or {
    "id": 1,
    "name": "BARNHOUSE SERVICES SRL",
    "rnc": "1-32-04275-1",
    "address_line1": "Calle Ficticia #123",
    "address_line2": "Santo Domingo, R.D.",
    "phone": "809-555-1234",
    # ajusta la ruta si tu logo está en data/company_1/logo.png
    "logo_path": "file:///" + str((ROOT / 'data' / 'company_1' / 'logo.png').absolute()).replace("\\", "/")
}

tpl = load_if_exists("template.json") or {
    "show_logo": True,
    "logo_path": "company_1/logo.png",
    "primary_color": "#555502",
    "secondary_color": "#EEF8F1",
    "itbis_rate": 0.18,
    "footer_lines": ["**Condiciones:** Validez de la cotización: 30 días.", "Forma de pago: 50% Adelantado, 50% contra entrega."]
}

quotation = load_if_exists("quotation.json") or {
    "number": "QT-1-20251017-103021",
    "date": "2025-10-17",
    "client_name": "EDIC MULTISERVICES",
    "client_rnc": "132176243",
    "items": [
        {"code":"EQU0001","description":"RETROPALA 416 E","unit":"HR","quantity":15,"unit_price":2500}
    ],
    "notes": ""
}

# Build payload JSON
payload = {"COMPANY": company, "TEMPLATE": tpl, "QUOTATION": quotation}

# Read template and replace placeholder
if not TEMPLATE_PATH.exists():
    raise SystemExit(f"Template not found: {TEMPLATE_PATH}")

html = TEMPLATE_PATH.read_text(encoding="utf-8")
js = json.dumps(payload, ensure_ascii=False)
js = js.replace("</script>", "<\\/script>")
html = html.replace("/* INJECT_JSON_PLACEHOLDER */", js)

# Save output
OUT_PATH.write_text(html, encoding="utf-8")
print(f"Wrote preview HTML to: {OUT_PATH}")

# Open in default browser
webbrowser.open(OUT_PATH.as_uri())