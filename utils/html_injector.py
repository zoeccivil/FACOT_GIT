import json, os

def safe_json_for_html(s: str) -> str:
    # evita que la secuencia "</script>" termine el script block
    return s.replace('</', '<\\/')

# utils/html_injector.py
import json
import os
from typing import Dict, Any

def build_html_with_json_block(template_path: str, company: Dict[str, Any], tpl: Dict[str, Any], quotation: Dict[str, Any]) -> str:
    """
    Lee template_path (templates/quotation_template.html) y reemplaza
    el placeholder /* INJECT_JSON_PLACEHOLDER */ por JSON seguro.

    Devuelve HTML listo para pasar a QWebEngineView.setHtml(html, baseUrl).
    """
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    payload = {
        "COMPANY": company or {},
        "TEMPLATE": tpl or {},
        "QUOTATION": quotation or {}
    }

    # Serializar JSON con ensure_ascii=False para mantener tildes/acentos
    js = json.dumps(payload, ensure_ascii=False)

    # Evitar cerrar el script accidentalmente (safety)
    js = js.replace("</script>", "<\\/script>")

    html = html.replace("/* INJECT_JSON_PLACEHOLDER */", js)
    return html