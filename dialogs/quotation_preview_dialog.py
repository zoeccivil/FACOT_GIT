from __future__ import annotations

import os
import json
import webbrowser
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox, QSizePolicy, QInputDialog
)
from PyQt6.QtCore import QUrl, QTimer, QByteArray
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Config opcional (vencimientos y logos)
try:
    import config_facot
except Exception:
    class _Cfg:
        INVOICE_DUE_DAYS = 0
        INVOICE_FIXED_DUE_DATE = ""  # "YYYY-MM-DD"
        COMPANY_LOGOS = {}  # {company_id(str/int) or name: path}
        DEFAULT_LOGO_PATH = ""
    config_facot = _Cfg()

# Inyector HTML opcional
try:
    from utils.html_injector import build_html_with_json_block
except Exception:
    build_html_with_json_block = None

# Raíz de datos para resolver rutas relativas
try:
    from utils.template_manager import get_data_root
except Exception:
    def get_data_root():
        return os.getcwd()


# =========================================================================
# HELPERS (alineados con InvoicePreviewDialog)
# =========================================================================

def _to_file_uri(path: str) -> str:
    if not path:
        return ""
    p = os.path.abspath(path)
    if os.name == "nt":
        return "file:///" + p.replace("\\", "/")
    return "file://" + p


def _resolve_logo_uri(company: Dict[str, Any], tpl_from_db: Optional[Dict[str, Any]] = None) -> str:
    """
    Igual que factura: prioridad DB -> template -> config_facot (por id/nombre) -> default.
    Devuelve file://... si existe; o http(s) si es URL; o "" si no hay nada válido.
    """
    candidates: List[str] = []
    db_logo = (company or {}).get("logo_path") or ""
    if db_logo:
        candidates.append(db_logo)
    tpl_logo = (tpl_from_db or {}).get("logo_path") or ""
    if tpl_logo:
        candidates.append(tpl_logo)

    logos = getattr(config_facot, "COMPANY_LOGOS", {}) or {}
    cid = company.get("id")
    name = (company.get("name") or "").strip()
    if cid is not None:
        key_id = str(cid)
        if key_id in logos:
            candidates.append(logos[key_id])
    if name and name in logos:
        candidates.append(logos[name])

    default_logo = getattr(config_facot, "DEFAULT_LOGO_PATH", "") or ""
    if default_logo:
        candidates.append(default_logo)

    root = get_data_root()

    print("\n[QT-LOGO] _resolve_logo_uri()")
    print(f"  company.id={cid} name='{name}'")
    print(f"  raw company.logo_path='{db_logo}'  tpl.logo_path='{tpl_logo}'")
    print(f"  data_root='{root}'")
    print(f"  candidates (ordered)={candidates}")

    for c in candidates:
        if not c:
            continue
        if isinstance(c, str) and c.startswith("file:///"):
            local = c.replace("file:///", "")
            if os.path.exists(local):
                print(f"  -> PICK file URI as-is: {c} (exists)")
                return c
            else:
                print(f"  .. skip file URI (not found): {c}")
                continue
        try:
            rel = os.path.join(root, c)
            if os.path.exists(rel):
                uri = _to_file_uri(rel)
                print(f"  -> PICK relative to data_root: '{c}' -> '{rel}' -> '{uri}'")
                return uri
            else:
                print(f"  .. not found relative: '{rel}'")
        except Exception as e:
            print(f"  .. join error relative '{c}': {e}")

        if os.path.isabs(c) and os.path.exists(c):
            uri = _to_file_uri(c)
            print(f"  -> PICK absolute path: '{c}' -> '{uri}'")
            return uri
        elif os.path.isabs(c):
            print(f"  .. absolute path not found: '{c}'")

        if c.startswith(("http://", "https://")):
            print(f"  -> PICK http(s) URL: {c}")
            return c

    print("  !! NO LOGO FOUND - returning empty string")
    return ""


def _prepare_company_data_for_preview(company_record: Dict[str, Any], tpl_from_db: Optional[Dict[str, Any]] = None, logic_controller=None) -> Dict[str, Any]:
    """
    Igual que factura: normaliza y hace fallback a BD si faltan campos.
    Resuelve logo a file:/// y refleja trazas para depurar.
    """
    company = dict(company_record or {})

    print("\n[QT-LOGO] _prepare_company_data_for_preview() - INPUTS")
    try:
        print(f"  INPUT company: id={company.get('id')} name='{company.get('name')}' logo_path='{company.get('logo_path')}'")
        print(f"  INPUT template.logo_path='{(tpl_from_db or {}).get('logo_path')}'")
    except Exception:
        pass

    if logic_controller and (not company.get("address_line1") and not company.get("signature_name")):
        try:
            cid = company.get("id")
            if cid:
                details = logic_controller.get_company_details(cid) or {}
                print(f"  [FALLBACK] get_company_details({cid}) -> {details}")
                for key in ["address_line1", "address_line2", "address", "signature_name", "logo_path", "phone", "email", "rnc"]:
                    if not company.get(key) and details.get(key):
                        company[key] = details[key]
        except Exception as e:
            print(f"  [FALLBACK ERROR] {e}")

    company["name"]  = company.get("name") or company.get("company_name") or ""
    company["rnc"]   = company.get("rnc") or company.get("rnc_number") or company.get("rnc_cliente") or ""
    company["phone"] = company.get("phone") or company.get("telefono") or ""
    company["email"] = company.get("email") or company.get("correo") or ""

    a1 = (company.get("address_line1") or company.get("address") or "").strip()
    a2 = (company.get("address_line2") or "").strip()
    company["address_line1"] = a1
    company["address_line2"] = a2
    address_full = (a1 + (" " + a2 if a2 else "")).strip() or (company.get("address") or "").strip()
    company["address"] = address_full or "Dirección no especificada"

    sig = (company.get("signature_name") or company.get("authorized_name") or "").strip()
    company["signature_name"] = sig
    company["authorized_name"] = sig

    resolved = _resolve_logo_uri(company, tpl_from_db) or company.get("logo_path") or ""
    company["logo_path"] = resolved

    print("[QT-LOGO] _prepare_company_data_for_preview() - OUTPUTS")
    try:
        print(f"  OUTPUT company.logo_path='{company.get('logo_path')}' (display-ready)")
        print(f"  OUTPUT company.name='{company.get('name')}', rnc='{company.get('rnc')}'")
        print(f"  OUTPUT company.address='{company.get('address')}'")
        print(f"  OUTPUT company.signature_name='{company.get('signature_name')}'")
    except Exception:
        pass

    return company

def _compute_due_date_if_missing(invoice: Dict[str, Any]) -> None:
    if not isinstance(invoice, dict):
        return
    if invoice.get("due_date") and invoice.get("due_date") != invoice.get("date"):
        return
    fixed = getattr(config_facot, "INVOICE_FIXED_DUE_DATE", "") or ""
    if fixed:
        invoice["due_date"] = fixed
        return
    days = int(getattr(config_facot, "INVOICE_DUE_DAYS", 0) or 0)
    inv_date = (invoice.get("date") or "").strip()
    if days > 0 and inv_date:
        try:
            d = datetime.strptime(inv_date, "%Y-%m-%d")
            new_due_date = (d + timedelta(days=days)).strftime("%Y-%m-%d")
            if new_due_date != inv_date:
                invoice["due_date"] = new_due_date
        except Exception:
            pass


def _ensure_units(invoice: Dict[str, Any], logic_controller=None) -> None:
    """
    En cada ítem, asegura que 'unit' tenga valor.
    
    Resolución de unidad por prioridad:
    1. Si el ítem ya tiene 'unit', lo usa
    2. Busca por código exacto en la BD
    3. Busca por nombre (get_items_like) con coincidencia parcial
    4. Fallback a 'UND' si no se encuentra
    
    Si logic_controller está disponible, usa el servicio UnitResolver para
    una resolución más robusta.
    """
    try:
        items = invoice.get("items") or []
        
        # Si tenemos logic_controller, usar el servicio UnitResolver
        if logic_controller:
            try:
                from services import UnitResolver
                resolver = UnitResolver(logic_controller)
                resolver.resolve_items(items)
                return
            except Exception as e:
                print(f"[ENSURE_UNITS] Could not use UnitResolver: {e}, falling back to simple method")
        
        # Fallback simple si no hay logic_controller o falla el resolver
        for it in items:
            if not (it.get("unit") or "").strip():
                it["unit"] = "UND"
    except Exception as e:
        print(f"[ENSURE_UNITS] Error: {e}")


def _local_build_html_with_json_block(template_path: str, company: Dict[str, Any], tpl: Dict[str, Any], quotation: Dict[str, Any]) -> str:
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    payload = {"COMPANY": company or {}, "TEMPLATE": tpl or {}, "QUOTATION": quotation or {}}
    js = json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")
    html = html.replace("/* INJECT_JSON_PLACEHOLDER */", js)
    return html


# =========================================================================
# CLASE PRINCIPAL
# =========================================================================

class QuotationPreviewDialog(QDialog):
    def __init__(
        self,
        company: Dict[str, Any],
        template: Dict[str, Any],
        quotation: Dict[str, Any],
        template_path: str = "quotation_template.html",  # ajustado a la ubicación real del repo
        parent=None,
        debug: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Vista previa - Cotización")
        self.resize(1000, 800)

        self.raw_company = company or {}
        self.raw_template = template or {}
        self.raw_quotation = quotation or {}

        print("\n" + "=" * 80)
        print("[QUOTATION_PREVIEW_DIALOG] PAYLOAD RECIBIDO:")
        print("=" * 80)
        try:
            import json as _json
            print("\n[RAW_COMPANY]:")
            print(_json.dumps(self.raw_company, ensure_ascii=False, indent=2))
            print("\n[RAW_TEMPLATE]:")
            print(_json.dumps(self.raw_template, ensure_ascii=False, indent=2))
            print("\n[RAW_QUOTATION]:")
            print(_json.dumps(self.raw_quotation, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[ERROR] No se pudo serializar: {e}")
            print(f"raw_company: {self.raw_company}")
            print(f"raw_template: {self.raw_template}")
            print(f"raw_quotation: {self.raw_quotation}")
        print("=" * 80 + "\n")

        self.template_path = template_path
        self.debug = bool(debug)

        self._last_payload = {}

        self._build_ui()
        self._load_html()

    def _build_ui(self):
        v = QVBoxLayout(self)
        self.view = QWebEngineView(self)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        v.addWidget(self.view)

        row = QHBoxLayout()
        self.btn_export_pdf = QPushButton("Exportar a PDF")
        # Sustituimos "Imprimir (dialog)" por "Exportar a Excel"
        self.btn_export_excel = QPushButton("Exportar a Excel")
        self.btn_save_html = QPushButton("Guardar HTML") 
        self.btn_close = QPushButton("Cerrar")
        row.addStretch(1)
        row.addWidget(self.btn_export_pdf)
        row.addWidget(self.btn_export_excel)
        row.addWidget(self.btn_save_html)
        row.addWidget(self.btn_close)
        v.addLayout(row)

        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        self.btn_export_excel.clicked.connect(self._on_export_excel)
        self.btn_save_html.clicked.connect(self._on_save_html)
        self.btn_close.clicked.connect(self.reject)

    def _load_html(self):
        try:
            if self.debug:
                q = dict(self.raw_quotation or {})
                if not q.get("client_name"):
                    txt, ok = QInputDialog.getText(self, "Cliente - Nombre", "Ingrese Nombre o Razón Social del cliente:", text="")
                    if ok and txt:
                        self.raw_quotation["client_name"] = txt.strip()
                if not q.get("client_rnc"):
                    txt2, ok2 = QInputDialog.getText(self, "Cliente - RNC/Cédula", "Ingrese RNC / Cédula del cliente:", text="")
                    if ok2 and txt2:
                        self.raw_quotation["client_rnc"] = txt2.strip()

            company, tpl, quotation = self._build_injectable_payloads()
            self._last_payload = {"COMPANY": company, "TEMPLATE": tpl, "QUOTATION": quotation}

            if build_html_with_json_block:
                html = build_html_with_json_block(self.template_path, company, tpl, quotation)
            else:
                html = _local_build_html_with_json_block(self.template_path, company, tpl, quotation)

            base = QUrl.fromLocalFile(os.path.abspath(os.path.dirname(self.template_path)) + os.sep)

            try:
                self.view.loadFinished.disconnect(self._on_loaded)
            except Exception:
                pass
            self.view.loadFinished.connect(self._on_loaded)

            self.view.setHtml(html, base)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la vista previa:\n{e}")

    def _on_loaded(self, ok: bool):
        if self.debug:
            print(f"[QuotationPreviewDialog] page.loadFinished ok={ok}")

        try:
            payload = self._last_payload or {"COMPANY": {}, "TEMPLATE": {}, "QUOTATION": {}}
            js_payload = json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")

            assign_js = f"""
(function(){{
  try {{
    var payload = {js_payload};
    window.COMPANY = payload.COMPANY || {{}};
    window.TEMPLATE = payload.TEMPLATE || {{}};
    window.QUOTATION = payload.QUOTATION || {{}};
    if (typeof renderAll === 'function') {{
      try {{ renderAll(); }} catch (e) {{ console.warn('renderAll error', e); }}
    }}
    return true;
  }} catch (e) {{
    console.error('[INJECT ERROR]', e);
    return false;
  }}
}})();
"""
            def after_assign(res):
                if self.debug:
                    print(f"[PREVIEW] assign_js ejecutado, resultado: {res}")

                # Fallback renderer (corrigiendo IDs para esta plantilla)
                fallback_js = r"""
(function(){
  try {
    var comp = window.COMPANY || {};
    var tpl  = window.TEMPLATE || {};
    var q    = window.QUOTATION || {};

    // Nombre empresa
    var nameNode = document.getElementById('company-name');
    if (nameNode) nameNode.textContent = (comp.name || '').toString().toUpperCase();

    // Meta: RNC, Dirección, Teléfono, Email (usar el id real de la plantilla)
    var metaContainer = document.getElementById('company-meta-container');
    if (metaContainer) {
      var parts = [];
      if (comp.rnc) parts.push('RNC: ' + comp.rnc);
      var address = comp.address || comp.address_line1 || 'Dirección no especificada';
      parts.push(address);
      if (comp.phone) parts.push('Teléfono: ' + comp.phone);
      if (comp.email) parts.push('Email: ' + comp.email);
      metaContainer.innerHTML = parts.map(function(x){return '<div>'+x+'</div>';}).join('');
    }

    // Firma Autorizada (usar el id real 'signature-name')
    var sigNode = document.getElementById('signature-name');
    if (sigNode) {
      var sig = comp.authorized_name || comp.signature_name || '';
      sigNode.textContent = (sig && String(sig).trim()) ? String(sig).toUpperCase() : 'NOMBRE AUTORIZADO';
    }

    // Items con unidad
    var tbody = document.getElementById('items-table-body');
    if (tbody) {
      var html = '';
      var subtotal = 0;
      (q.items || []).forEach(function(it, idx){
        var qty = Number(it.quantity) || 0;
        var up  = Number(it.unit_price) || 0;
        var line = qty * up; subtotal += line;
        var unit = (it.unit && String(it.unit).trim()) ? it.unit : 'UNID';
        html += '<tr>';
        html += '<td class="no">' + String(idx + 1).padStart(2, '0') + '</td>';
        html += '<td class="desc"><div class="code">' + (it.code || '') + '</div><div class="sub-text">' + (it.description || '') + '</div></td>';
        html += '<td class="unit">' + unit + '</td>';
        html += '<td class="unit-price">' + new Intl.NumberFormat("es-DO",{minimumFractionDigits:2,maximumFractionDigits:2}).format(up) + '</td>';
        var qfmt = (qty % 1 === 0) ? new Intl.NumberFormat("es-DO",{maximumFractionDigits:0}).format(qty) : new Intl.NumberFormat("es-DO",{minimumFractionDigits:2,maximumFractionDigits:2}).format(qty);
        html += '<td class="qty">' + qfmt + '</td>';
        html += '<td class="total">' + new Intl.NumberFormat("es-DO",{minimumFractionDigits:2,maximumFractionDigits:2}).format(line) + '</td>';
        html += '</tr>';
      });
      tbody.innerHTML = html;
    }
  } catch(e) {
    console.error('fallback renderer error', e);
  }
})();
"""
                self.view.page().runJavaScript(fallback_js)

            self.view.page().runJavaScript(assign_js, after_assign)

        except Exception as e:
            print(f"[PREVIEW] Error inyectando payload: {e}")

    def _on_save_html(self):
        try:
            company, tpl, quotation = self._build_injectable_payloads()

            if build_html_with_json_block:
                html = build_html_with_json_block(self.template_path, company, tpl, quotation)
            else:
                html = _local_build_html_with_json_block(self.template_path, company, tpl, quotation)

            fn, _ = QFileDialog.getSaveFileName(self, "Guardar HTML de Vista Previa", "quotation_preview.html", "HTML Files (*.html *.htm)")
            if not fn:
                return
            save_path = fn if fn.lower().endswith((".html", ".htm")) else fn + ".html"

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html)

            QMessageBox.information(self, "Guardar HTML", f"Archivo HTML guardado en:\n{save_path}")

            if QMessageBox.question(self, "Abrir archivo", "¿Deseas abrir el HTML en el navegador?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                try:
                    webbrowser.open(os.path.abspath(save_path))
                except Exception as e:
                    QMessageBox.warning(self, "Abrir HTML", f"No se pudo abrir el archivo en el navegador: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Guardar HTML", f"No se pudo generar/guardar el HTML:\n{e}")

    def _on_export_pdf(self):
        """
        Exporta la cotización a PDF sugiriendo automáticamente el nombre:
        COT_(No de Cotizacion)_Empresa.pdf
        Ej.: COT_COT-CON-000002_Constructora_Retro_SRL.pdf
        """
        import re

        # 1) Obtener datos actuales (usar payload si ya fue construido)
        payload = getattr(self, "_last_payload", {}) or {}
        comp = (payload.get("COMPANY") or self.raw_company or {})
        q    = (payload.get("QUOTATION") or self.raw_quotation or {})

        company_name = (comp.get("name") or "").strip() or "EMPRESA"
        display_number = (q.get("display_number") or q.get("number") or "").strip()

        # 2) Si no hay display_number, derivarlo (similar a computeQuotationNumber del template)
        if not display_number:
            name = company_name
            letters = (
                name.encode("ascii", "ignore").decode("ascii")
                if isinstance(name, str) else ""
            )
            letters = re.sub(r"[^A-Za-z]", "", letters or "")
            prefix = (letters[:3] or "EMP").upper()
            try:
                qid = int(q.get("id") or 0)
            except Exception:
                qid = 0
            display_number = f"COT-{prefix}-{qid:06d}"

        # 3) Construir nombre sugerido: COT_(No de Cotizacion)_Empresa
        base = f"COT_{display_number}_{company_name}"
        safe = re.sub(r"[^A-Za-z0-9._\-]+", "_", base).strip("_")
        suggested = f"{safe}.pdf"

        # 4) Diálogo de guardado con el nombre sugerido
        fn, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Cotización como PDF",
            suggested,
            "PDF Files (*.pdf)"
        )
        if not fn:
            return

        save_path = fn if fn.lower().endswith(".pdf") else fn + ".pdf"
        self.btn_export_pdf.setEnabled(False)

        def finish_with_message(ok: bool, msg: str = None):
            self.btn_export_pdf.setEnabled(True)
            if ok:
                QMessageBox.information(self, "PDF", f"PDF generado:\n{save_path}")
            else:
                QMessageBox.warning(self, "PDF", msg or "No se pudo generar el PDF o está vacío.")

        def on_pdf_result(result):
            try:
                if isinstance(result, QByteArray):
                    data_bytes = bytes(result)
                    with open(save_path, "wb") as f:
                        f.write(data_bytes)
                    finish_with_message(True); return
                if isinstance(result, (bytes, bytearray)):
                    with open(save_path, "wb") as f:
                        f.write(result)
                    finish_with_message(True); return
                if isinstance(result, bool) or result is None:
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        finish_with_message(True); return
                    try:
                        def cb_bytes(data):
                            try:
                                bytes_data = bytes(data) if isinstance(data, QByteArray) else data
                                if isinstance(bytes_data, (bytes, bytearray)):
                                    with open(save_path, "wb") as f:
                                        f.write(bytes_data)
                                    finish_with_message(True)
                                else:
                                    finish_with_message(False, "Fallback: printToPdf no retornó bytes.")
                            except Exception as ex:
                                finish_with_message(False, f"Error al escribir fallback PDF: {ex}")
                        self.view.page().printToPdf(cb_bytes); return
                    except Exception as e:
                        finish_with_message(False, f"No se pudo generar el PDF: {e}"); return
                finish_with_message(False, "Resultado inesperado al generar PDF.")
            finally:
                self.btn_export_pdf.setEnabled(True)

        def proceed_print():
            try:
                try:
                    self.view.page().printToPdf(on_pdf_result)
                except TypeError:
                    try:
                        self.view.page().printToPdf(save_path, on_pdf_result)
                    except Exception as ex:
                        finish_with_message(False, f"printToPdf no disponible: {ex}")
            except Exception as e:
                finish_with_message(False, f"Error al generar PDF: {e}")

        try:
            def on_ready_state(state):
                try:
                    if isinstance(state, str) and state.lower() == "complete":
                        QTimer.singleShot(150, proceed_print)
                    else:
                        QTimer.singleShot(350, proceed_print)
                except Exception:
                    proceed_print()
            self.view.page().runJavaScript("document.readyState", on_ready_state)
        except Exception:
            QTimer.singleShot(150, proceed_print)
            
    def _on_print_dialog(self):
        try:
            def cb(_):
                QMessageBox.information(self, "Imprimir", "Se generó PDF temporal para imprimir.")
            try:
                self.view.page().printToPdf(cb)
            except TypeError:
                self.view.page().printToPdf("temp_print.pdf", cb)
        except Exception as e:
            QMessageBox.critical(self, "Imprimir", f"No se pudo iniciar la impresión:\n{e}")

    def _on_export_excel(self):
        """
        Exporta la cotización a Excel usando el generador existente del proyecto:
        utils.quotation_templates.generate_quotation_excel(data, items, save_path, company_name)

        - Nombre sugerido: COT_(No de Cotización)_Empresa.xlsx
        - Incluye code y unit por renglón
        - Pasa logo_path como ruta local (convierte file:///… a path) para evitar errores en Windows
        """
        import re
        import urllib.parse

        # Payload actual mostrado en pantalla
        payload = getattr(self, "_last_payload", {}) or {}
        comp = (payload.get("COMPANY") or self.raw_company or {}) or {}
        tpl  = (payload.get("TEMPLATE") or self.raw_template or {}) or {}
        q    = (payload.get("QUOTATION") or self.raw_quotation or {}) or {}

        company_name = (comp.get("name") or "EMPRESA").strip()

        # Número visible en el template
        display_number = (q.get("display_number") or q.get("number") or "").strip()
        if not display_number:
            # Respaldo: prefijo 3 letras de la empresa + id
            letters = re.sub(r"[^A-Za-z]", "", (company_name.encode("ascii", "ignore").decode("ascii") if isinstance(company_name, str) else ""))
            prefix = (letters[:3] or "EMP").upper()
            try:
                qid = int(q.get("id") or 0)
            except Exception:
                qid = 0
            display_number = f"COT-{prefix}-{qid:06d}"

        # Nombre sugerido
        base = f"COT_{display_number}_{company_name}"
        safe = re.sub(r"[^A-Za-z0-9._\-]+", "_", base).strip("_")
        suggested = f"{safe}.xlsx"

        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como Excel", suggested, "Excel Files (*.xlsx)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".xlsx") else fn + ".xlsx"

        # Generador conocido del proyecto
        try:
            from utils.quotation_templates import generate_quotation_excel as gen_xlsx
        except Exception as e:
            QMessageBox.warning(self, "Excel", f"No se encontró el exportador Excel:\n{e}")
            return

        # Helper: convertir file:/// a ruta local
        def _file_uri_to_path(uri_or_path: str) -> str:
            s = (uri_or_path or "").strip()
            if s.lower().startswith("file:///"):
                return urllib.parse.unquote(s.replace("file:///", ""))
            return s

        try:
            items_src = q.get("items") or []
            items = []
            subtotal = 0.0

            for it in items_src:
                code = (it.get("code") or it.get("item_code") or "").strip()
                desc = (it.get("description") or "").strip()
                unit = (it.get("unit") or "").strip()
                try:
                    qty = float(it.get("quantity") or 0.0)
                except Exception:
                    qty = 0.0
                try:
                    up = float(it.get("unit_price") or 0.0)
                except Exception:
                    up = 0.0

                subtotal += qty * up
                items.append({
                    "code": code,
                    "description": desc,
                    "unit": unit,
                    "quantity": qty,
                    "unit_price": up,
                })

            itbis_rate = float(tpl.get("itbis_rate", 0.18) or 0.0)
            apply_itbis = q.get("apply_itbis")
            if apply_itbis is None:
                apply_itbis = itbis_rate > 0
            itbis_val = subtotal * itbis_rate if apply_itbis else 0.0
            total_amount = subtotal + itbis_val

            logo_local = _file_uri_to_path(comp.get("logo_path") or "")

            data = {
                "company_id": comp.get("id"),
                "quotation_date": q.get("date") or q.get("quotation_date"),
                "client_name": q.get("client_name") or q.get("third_party_name") or "",
                "client_rnc": q.get("client_rnc") or q.get("rnc") or "",
                "notes": q.get("notes") or "",
                "currency": q.get("currency") or "RD$",
                "total_amount": total_amount,
                "itbis_rate": itbis_rate,
                "apply_itbis": bool(apply_itbis),
                "logo_path": logo_local,  # el generador lo usará de forma robusta
                "excel_path": "",
                "pdf_path": "",
            }

            gen_xlsx(data, items, save_path, company_name)
            QMessageBox.information(self, "Excel", f"Archivo Excel generado:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "Excel", f"No se pudo generar el Excel:\n{e}")


    def _compute_quotation_due_date_if_missing(self, quotation: Dict[str, Any]) -> None:
        """
        Si no viene due_date, lo calcula como (quotation_date || date || created_at) + 30 días.
        Incluye trazas para depuración.
        """
        if not isinstance(quotation, dict):
            print("[QUOT-DUE] quotation no es dict")
            return

        if quotation.get("due_date"):
            print(f"[QUOT-DUE] due_date ya presente: {quotation.get('due_date')}")
            return

        base = (quotation.get("date")
                or quotation.get("quotation_date")
                or quotation.get("created_at")
                or "").strip()
        print(f"[QUOT-DUE] base='{base}'")

        if not base:
            return

        # Parse robusto de YYYY-MM-DD (y fallback ISO)
        try:
            d = datetime.strptime(base[:10], "%Y-%m-%d")
        except Exception:
            try:
                d = datetime.fromisoformat(base[:10])
            except Exception as e:
                print(f"[QUOT-DUE] no pude parsear la fecha base '{base}': {e}")
                return

        quotation["due_date"] = (d + timedelta(days=30)).strftime("%Y-%m-%d")
        print(f"[QUOT-DUE] computed due_date='{quotation['due_date']}'")

    def _build_injectable_payloads(self):
        # Obtener logic_controller del padre
        logic_ctrl = None
        try:
            if hasattr(self.parent(), 'logic'):
                logic_ctrl = self.parent().logic
        except Exception:
            pass

        company = _prepare_company_data_for_preview(self.raw_company, self.raw_template, logic_controller=logic_ctrl)
        tpl = dict(self.raw_template or {})
        quotation = dict(self.raw_quotation or {})

        tpl["itbis_rate"] = tpl.get("itbis_rate", 0.18)

        # si hay logo resuelto, asegurar show_logo True
        if company.get("logo_path"):
            if tpl.get("show_logo") is False:
                print("[QT-LOGO] tpl.show_logo estaba False, se fuerza a True porque hay logo_path.")
            tpl["show_logo"] = True

        quotation["items"] = quotation.get("items", [])

        # DEBUG antes de calcular
        print(f"[QUOT-DUE] BEFORE q.date='{quotation.get('date','')}', q.quotation_date='{quotation.get('quotation_date','')}', q.due='{quotation.get('due_date','')}'")

        # Llamar al método de instancia (firma corregida)
        self._compute_quotation_due_date_if_missing(quotation)

        # DEBUG después de calcular
        print(f"[QUOT-DUE] AFTER q.due='{quotation.get('due_date','')}'")

        _ensure_units(quotation, logic_controller=logic_ctrl)

        return company, tpl, quotation