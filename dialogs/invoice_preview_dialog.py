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
        INVOICE_FIXED_DUE_DATE = "" # "YYYY-MM-DD"
        COMPANY_LOGOS = {} # {company_id(str/int) or name: path}
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


def _to_file_uri(path: str) -> str:
    """
    Convierte una ruta local a file:// (compatible con Windows y POSIX).
    No valida existencia del archivo.
    """
    if not path:
        return ""
    p = os.path.abspath(path)
    if os.name == "nt":
        return "file:///" + p.replace("\\", "/")
    return "file://" + p


def _resolve_logo_uri(company: Dict[str, Any], tpl_from_db: Optional[Dict[str, Any]] = None) -> str:
    """
    Prioridad de logo:
    1) companies.logo_path (DB)
    2) template.logo_path (tpl_from_db)
    3) config_facot.COMPANY_LOGOS por id (str) o por nombre
    4) config_facot.DEFAULT_LOGO_PATH
    Devuelve file://... si se puede resolver a ruta existente; si no, el valor tal cual.
    """
    # 1) DB + 2) Template
    candidates: List[str] = []
    db_logo = (company or {}).get("logo_path") or ""
    if db_logo:
        candidates.append(db_logo)
    tpl_logo = (tpl_from_db or {}).get("logo_path") or ""
    if tpl_logo:
        candidates.append(tpl_logo)

    # 3) config_facot map
    logos = getattr(config_facot, "COMPANY_LOGOS", {}) or {}
    cid = company.get("id")
    name = (company.get("name") or "").strip()
    if cid is not None:
        key_id = str(cid)
        if key_id in logos:
            candidates.append(logos[key_id])
    if name and name in logos:
        candidates.append(logos[name])

    # 4) default
    default_logo = getattr(config_facot, "DEFAULT_LOGO_PATH", "") or ""
    if default_logo:
        candidates.append(default_logo)

    root = get_data_root()

    print("\n[INV-LOGO] _resolve_logo_uri()")
    print(f"  company.id={cid} name='{name}'")
    print(f"  raw company.logo_path='{db_logo}'  tpl.logo_path='{tpl_logo}'")
    print(f"  data_root='{root}'")
    print(f"  candidates (ordered)={candidates}")

    for c in candidates:
        if not c:
            continue

        # Acepta file:/// ya preparado
        if isinstance(c, str) and c.startswith("file:///"):
            local = c.replace("file:///", "")
            if os.path.exists(local):
                print(f"  -> PICK file URI as-is: {c} (exists)")
                return c
            else:
                print(f"  .. skip file URI (not found): {c}")
                continue

        # Relativa a data root
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

        # Absoluta
        if os.path.isabs(c) and os.path.exists(c):
            uri = _to_file_uri(c)
            print(f"  -> PICK absolute path: '{c}' -> '{uri}'")
            return uri
        elif os.path.isabs(c):
            print(f"  .. absolute path not found: '{c}'")

        # URL http/https
        if c.startswith(("http://", "https://")):
            print(f"  -> PICK http(s) URL: {c}")
            return c

    print("  !! NO LOGO FOUND - returning empty string")
    return ""


def _prepare_company_data_for_preview(company_record: Dict[str, Any], tpl_from_db: Optional[Dict[str, Any]] = None, logic_controller=None) -> Dict[str, Any]:
    """
    Normaliza COMPANY para la plantilla.
    - Si los campos críticos están vacíos, vuelve a consultar la BD.
    - name, rnc, phone, email
    - address_line1/address_line2 y address (línea compacta)
    - signature_name y authorized_name (alias)
    - logo_path resuelto a file:// conforme prioridad
    - invoice_due_date (FECHA FIJA DE VENCIMIENTO)  <--- NUEVO
    """
    company = dict(company_record or {})

    print("\n[INV-LOGO] _prepare_company_data_for_preview() - INPUTS")
    try:
        print(f"  INPUT company: id={company.get('id')} name='{company.get('name')}' logo_path='{company.get('logo_path')}' invoice_due_date='{company.get('invoice_due_date','')}'")
        print(f"  INPUT template.logo_path='{(tpl_from_db or {}).get('logo_path')}'")
    except Exception:
        pass

    # Fallback a BD si faltan campos
    if logic_controller and (not company.get("address_line1") and not company.get("signature_name")):
        try:
            cid = company.get("id")
            if cid:
                details = logic_controller.get_company_details(cid) or {}
                print(f"  [FALLBACK] get_company_details({cid}) -> {details}")
                for key in [
                    "address_line1", "address_line2", "address", "signature_name", "logo_path",
                    "phone", "email", "rnc", "invoice_due_date"  # <--- incluir vencimiento fijo
                ]:
                    if not company.get(key) and details.get(key):
                        company[key] = details[key]
        except Exception as e:
            print(f"  [FALLBACK ERROR] {e}")

    # Normalizar básicos
    company["name"]  = company.get("name") or company.get("company_name") or ""
    company["rnc"]   = company.get("rnc") or company.get("rnc_number") or company.get("rnc_cliente") or ""
    company["phone"] = company.get("phone") or company.get("telefono") or ""
    company["email"] = company.get("email") or company.get("correo") or ""

    # Dirección compacta
    a1 = (company.get("address_line1") or company.get("address") or "").strip()
    a2 = (company.get("address_line2") or "").strip()
    company["address_line1"] = a1
    company["address_line2"] = a2
    address_full = (a1 + (" " + a2 if a2 else "")).strip()
    if not address_full:
        address_full = (company.get("address") or "").strip()
    company["address"] = address_full or "Dirección no especificada"

    # Firma / nombre autorizado
    sig = (company.get("signature_name") or company.get("authorized_name") or "").strip()
    company["signature_name"] = sig
    company["authorized_name"] = sig

    # Logo resuelto
    resolved = _resolve_logo_uri(company, tpl_from_db) or company.get("logo_path") or ""
    company["logo_path"] = resolved

    # Vencimiento fijo por empresa (mantenerlo aunque esté vacío)
    company["invoice_due_date"] = (company.get("invoice_due_date") or "").strip()

    print("[INV-LOGO] _prepare_company_data_for_preview() - OUTPUTS")
    try:
        print(f"  OUTPUT company.logo_path='{company.get('logo_path')}' (display-ready)")
        print(f"  OUTPUT company.name='{company.get('name')}', rnc='{company.get('rnc')}'")
        print(f"  OUTPUT company.address='{company.get('address')}'")
        print(f"  OUTPUT company.signature_name='{company.get('signature_name')}'")
        print(f"  OUTPUT company.invoice_due_date='{company.get('invoice_due_date','')}'")  # <--- DEBUG
    except Exception:
        pass

    return company

# Asegura que el cálculo de vencimiento reciba company y lo use (como reflejan tus prints).
def _compute_due_date_if_missing(invoice: Dict[str, Any], company: Dict[str, Any] | None = None) -> None:
    """
    Si no viene due_date o es igual a la fecha de emisión:
    - Usa company['invoice_due_date'] (fija por empresa) si existe.
    - Luego INVOICE_FIXED_DUE_DATE o INVOICE_DUE_DAYS del config.
    """
    if not isinstance(invoice, dict):
        return

    inv_date = (invoice.get("date") or "").strip()
    due = (invoice.get("due_date") or "").strip()
    fixed_company = ((company or {}).get("invoice_due_date") or "").strip()
    print(f"[INV-DUE] INPUT inv.date='{inv_date}' inv.due='{due}' company.fixed='{fixed_company}'")

    if due and due != inv_date:
        return

    if fixed_company:
        invoice["due_date"] = fixed_company
        print(f"[INV-DUE] USING company.invoice_due_date -> {invoice['due_date']}")
        return

    fixed = getattr(config_facot, "INVOICE_FIXED_DUE_DATE", "") or ""
    if fixed:
        invoice["due_date"] = fixed
        print(f"[INV-DUE] USING config INVOICE_FIXED_DUE_DATE -> {invoice['due_date']}")
        return

    days = int(getattr(config_facot, "INVOICE_DUE_DAYS", 0) or 0)
    if days > 0 and inv_date:
        try:
            d = datetime.strptime(inv_date[:10], "%Y-%m-%d")
            new_due_date = (d + timedelta(days=days)).strftime("%Y-%m-%d")
            if new_due_date != inv_date:
                invoice["due_date"] = new_due_date
                print(f"[INV-DUE] USING config INVOICE_DUE_DAYS={days} -> {invoice['due_date']}")
        except Exception as e:
            print(f"[INV-DUE] error sumando días: {e}")

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


def _local_build_html_with_json_block(template_path: str, company: Dict[str, Any], tpl: Dict[str, Any], invoice: Dict[str, Any]) -> str:
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    payload = {"COMPANY": company or {}, "TEMPLATE": tpl or {}, "INVOICE": invoice or {}}
    js = json.dumps(payload, ensure_ascii=False)
    js = js.replace("</script>", "<\\/script>")
    html = html.replace("/* INJECT_JSON_PLACEHOLDER */", js)
    return html


class InvoicePreviewDialog(QDialog):
    def __init__(
        self,
        company: Dict[str, Any],
        template: Dict[str, Any],
        invoice: Dict[str, Any],
        template_path: str = "templates/invoice_template.html",
        parent=None,
        debug: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Vista previa - Factura")
        self.resize(1000, 800)

        self.raw_company = company or {}
        self.raw_template = template or {}
        self.raw_invoice = invoice or {}
        self.template_path = template_path
        self.debug = bool(debug)

        self._last_payload: Dict[str, Any] = {}

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

    def _build_injectable_payloads(self):
        # Intenta obtener logic_controller desde el parent (InvoiceTab)
        logic_ctrl = None
        try:
            if hasattr(self.parent(), 'logic'):
                logic_ctrl = self.parent().logic
        except Exception:
            pass
        
        company = _prepare_company_data_for_preview(self.raw_company, self.raw_template, logic_controller=logic_ctrl)
        tpl = dict(self.raw_template or {})
        tpl["itbis_rate"] = tpl.get("itbis_rate", 0.18)
        invoice = dict(self.raw_invoice or {})
        invoice["items"] = list(invoice.get("items", []))

        print(f"[INV-DUE] BEFORE company.invoice_due_date='{company.get('invoice_due_date','')}', invoice.due='{invoice.get('due_date','')}', invoice.date='{invoice.get('date','')}'")
        _compute_due_date_if_missing(invoice, company)  # <--- PASAR company
        print(f"[INV-DUE] AFTER invoice.due='{invoice.get('due_date','')}' (used company fixed if available)")

        _ensure_units(invoice, logic_controller=logic_ctrl)
        return company, tpl, invoice
        
    def _load_html(self):
        try:
            if self.debug:
                q = dict(self.raw_invoice or {})
                if not q.get("client_name"):
                    txt, ok = QInputDialog.getText(self, "Cliente - Nombre", "Ingrese Nombre o Razón Social del cliente:", text="")
                    if ok and txt:
                        self.raw_invoice["client_name"] = txt.strip()
                if not q.get("client_rnc"):
                    txt2, ok2 = QInputDialog.getText(self, "Cliente - RNC/Cédula", "Ingrese RNC / Cédula del cliente:", text="")
                    if ok2 and txt2:
                        self.raw_invoice["client_rnc"] = txt2.strip()

            company, tpl, invoice = self._build_injectable_payloads()
            self._last_payload = {"COMPANY": company, "TEMPLATE": tpl, "INVOICE": invoice}

            if build_html_with_json_block:
                html = build_html_with_json_block(self.template_path, company, tpl, invoice)
            else:
                html = _local_build_html_with_json_block(self.template_path, company, tpl, invoice)

            if self.debug:
                try:
                    debug_path = os.path.join(os.getcwd(), "debug_invoice_preview.html")
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"[InvoicePreviewDialog] Wrote debug HTML to: {debug_path}")
                except Exception:
                    pass

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
            print(f"[InvoicePreviewDialog] page.loadFinished ok={ok}")

        try:
            payload = self._last_payload or {"COMPANY": {}, "TEMPLATE": {}, "INVOICE": {}}
            js_payload = json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")
            assign_js = f"""
(function(){{
  try {{
    var payload = {js_payload};
    window.COMPANY = payload.COMPANY || {{}};
    window.TEMPLATE = payload.TEMPLATE || {{}};
    window.INVOICE = payload.INVOICE || {{}};
    if (typeof renderAll === 'function') {{
      try {{ renderAll(); }} catch (e) {{ console.warn('renderAll error', e); }}
    }}
    return true;
  }} catch (e) {{
    return false;
  }}
}})();
"""
            def after_assign(res):
                if self.debug:
                    print("[INV] assign_js executed:", res)
                try:
                    script_show = "JSON.stringify({COMPANY: window.COMPANY || null, TEMPLATE: window.TEMPLATE || null, INVOICE: window.INVOICE || null})"
                    self.view.page().runJavaScript(script_show, lambda res2: print("[DEBUG] injected objects:", res2))
                except Exception as e:
                    print("[InvoicePreviewDialog] runJavaScript error on show:", e)

                # Fallback renderer extendido: incluye due date, unidad y nombre autorizado
                try:
                    fallback_js = r"""
(function(){
  try {
    var comp = window.COMPANY || {};
    var tpl = window.TEMPLATE || {};
    var inv = window.INVOICE || {};

    // Header empresa
    if (document.getElementById('company-name'))
      document.getElementById('company-name').textContent = (comp.name||'').toString().toUpperCase();

    if (document.getElementById('company-meta')) {
      var parts=[];
      if(comp.rnc) parts.push('RNC: '+comp.rnc);
      // Usa la dirección completa calculada en Python (comp.address) o las líneas individuales
      if(comp.address) parts.push('Dirección: ' + comp.address); 
      else if(comp.address_line1) parts.push(comp.address_line1);
      
      if(comp.phone) parts.push('Teléfono: '+comp.phone);
      if(comp.email) parts.push('Email: '+comp.email);
      document.getElementById('company-meta').innerHTML = parts.join('<br/>');
    }

    if (document.getElementById('company-logo') && (comp.logo_path || tpl.logo_path)) {
      try {
        var logoSrc = comp.logo_path || tpl.logo_path || '';
        if(logoSrc){
          var img=document.createElement('img');
          img.src=logoSrc; img.style.maxWidth='100%'; img.style.maxHeight='100%';
          var cont = document.getElementById('company-logo'); cont.innerHTML=''; cont.appendChild(img);
        }
      } catch(e){}
    }

    // Datos principales de documento
    if (document.getElementById('invoice-type')) document.getElementById('invoice-type').textContent = inv.type || '';
    if (document.getElementById('invoice-number-large')) document.getElementById('invoice-number-large').textContent = inv.display_number || inv.number || '';
    if (document.getElementById('invoice-ncf')) document.getElementById('invoice-ncf').textContent = inv.ncf || '';
    if (document.getElementById('invoice-date')) document.getElementById('invoice-date').textContent = inv.date || '';
    
    // Vencimiento (muestra la fecha, o N/A si es igual a la fecha de emisión o está vacía)
    var dueDate = inv.due_date || '';
    if (document.getElementById('invoice-due-date')) document.getElementById('invoice-due-date').textContent = dueDate || 'N/A'

    // Cliente
    if (document.getElementById('client-name')) document.getElementById('client-name').textContent = inv.client_name || '';
    if (document.getElementById('client-rnc')) document.getElementById('client-rnc').textContent = inv.client_rnc || '';

    // Nombre Autorizado (Firma)
    if (document.getElementById('authorized-name')) document.getElementById('authorized-name').textContent = comp.authorized_name || comp.signature_name || '';


    // Ítems
    if (document.getElementById('items-table-body')) {
      var tbody = document.getElementById('items-table-body'); var html=''; var subtotal=0;
      (inv.items||[]).forEach(function(it){
        var qty=Number(it.quantity)||0;
        var up=Number(it.unit_price)||0;
        var line=qty*up; subtotal+=line;
        // La unidad ya fue asegurada a 'UNID' en Python, solo se muestra.
        var unit = (it.unit && String(it.unit).trim()) ? it.unit : 'UNID'; 
        
        html+='<tr>';
        html+='<td class="qty" style="text-align:center;">'+qty+'</td>';
        html+='<td><div class="code">'+(it.code||'')+'</div><div class="desc">'+(it.description||'')+'</div></td>';
        html+='<td class="unit" style="text-align:center;">'+unit+'</td>';
        html+='<td class="right" style="text-align:right;">'+new Intl.NumberFormat('es-DO',{minimumFractionDigits:2}).format(up)+'</td>';
        html+='<td class="right" style="text-align:right;">'+new Intl.NumberFormat('es-DO',{minimumFractionDigits:2}).format(line)+'</td>';
        html+='</tr>';
      });
      tbody.innerHTML = html;

      var itbis_rate = Number((tpl && tpl.itbis_rate) || 0.18);
      var itbisAmt = subtotal * itbis_rate; var total = subtotal + itbisAmt;
      if(document.getElementById('subtotal')) document.getElementById('subtotal').textContent = new Intl.NumberFormat('es-DO',{minimumFractionDigits:2}).format(subtotal);
      if(document.getElementById('itbis')) document.getElementById('itbis').textContent = new Intl.NumberFormat('es-DO',{minimumFractionDigits:2}).format(itbisAmt);
      if(document.getElementById('total')) document.getElementById('total').textContent = new Intl.NumberFormat('es-DO',{minimumFractionDigits:2}).format(total);
    }
  } catch(e) { console.error('fallback renderer error', e); }
})();
"""
                    self.view.page().runJavaScript(fallback_js)
                except Exception:
                    pass

            self.view.page().runJavaScript(assign_js, after_assign)

        except Exception as e:
            print("[InvoicePreviewDialog] Error injecting payload:", e)

    def _on_save_html(self):
        try:
            company, tpl, invoice = self._build_injectable_payloads()
            if build_html_with_json_block:
                html = build_html_with_json_block(self.template_path, company, tpl, invoice)
            else:
                html = _local_build_html_with_json_block(self.template_path, company, tpl, invoice)

            fn, _ = QFileDialog.getSaveFileName(self, "Guardar HTML de Factura", "invoice_preview.html", "HTML Files (*.html *.htm)")
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
        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como PDF", f"factura_{self._last_payload.get('INVOICE',{}).get('display_number','')}.pdf", "PDF Files (*.pdf)")
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
                    finish_with_message(True)
                    return
                if isinstance(result, (bytes, bytearray)):
                    with open(save_path, "wb") as f:
                        f.write(result)
                    finish_with_message(True)
                    return
                if isinstance(result, bool) or result is None:
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        finish_with_message(True)
                        return
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
                        self.view.page().printToPdf(cb_bytes)
                        return
                    except Exception as e:
                        finish_with_message(False, f"No se pudo generar el PDF: {e}")
                        return
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
                self.view.page().printToPdf("temp_invoice_print.pdf", cb)
        except Exception as e:
            QMessageBox.critical(self, "Imprimir", f"No se pudo iniciar la impresión:\n{e}")

    def _on_export_excel(self):
        """
        Exporta la factura a Excel usando el generador del proyecto.
        Orden de uso:
        1) utils.quotation_templates.generate_invoice_excel(invoice_data, items, save_path, company_name, template=tpl_for_excel)
        2) Fallback: utils.quotation_templates.generate_quotation_excel(data, items, save_path, company_name) con la misma info.

        - Nombre sugerido: FACT_(display_number)_Empresa.xlsx
        - Incluye code y unit en cada renglón
        - Convierte file:/// del logo a ruta local y la inserta en el template para evitar errores en Windows
        """
        import re, os, urllib.parse

        # Payload que alimenta el HTML del preview (misma data para Excel)
        payload = getattr(self, "_last_payload", {}) or {}
        comp = (payload.get("COMPANY") or self.raw_company or {}) or {}
        tpl  = (payload.get("TEMPLATE") or self.raw_template or {}) or {}
        inv  = (payload.get("INVOICE")  or self.raw_invoice  or {}) or {}

        company_name = (comp.get("name") or "EMPRESA").strip()
        display_number = (inv.get("display_number") or inv.get("number") or inv.get("ncf") or "FACT").strip()

        # Nombre sugerido
        base = f"FACT_{display_number}_{company_name}"
        safe = re.sub(r"[^A-Za-z0-9._\\-]+", "_", base).strip("_")
        suggested = f"{safe}.xlsx"

        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Factura como Excel", suggested, "Excel Files (*.xlsx)")
        if not fn:
            return
        save_path = fn if fn.lower().endswith(".xlsx") else fn + ".xlsx"

        # Generadores disponibles
        try:
            from utils.quotation_templates import generate_invoice_excel as gen_invoice_xlsx
        except Exception:
            gen_invoice_xlsx = None
        try:
            from utils.quotation_templates import generate_quotation_excel as gen_quote_xlsx
        except Exception:
            gen_quote_xlsx = None

        if not callable(gen_invoice_xlsx) and not callable(gen_quote_xlsx):
            QMessageBox.warning(self, "Excel", "No se encontró ningún exportador Excel disponible.")
            return

        # Helpers
        def _file_uri_to_path(uri_or_path: str) -> str:
            s = (uri_or_path or "").strip()
            if s.lower().startswith("file:///"):
                return urllib.parse.unquote(s.replace("file:///", ""))
            return s

        # Construir items (incluyendo code y unit)
        try:
            items_src = inv.get("items") or []
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
                disc = float(it.get("discount_pct") or 0.0)

                line_total = qty * up * (1 - disc / 100.0)
                subtotal += line_total

                items.append({
                    "code": code,
                    "description": desc,
                    "unit": unit,
                    "quantity": qty,
                    "unit_price": up,
                    "discount_pct": disc,
                })

            itbis_rate = float(tpl.get("itbis_rate", 0.18) or 0.0)
            apply_itbis = inv.get("apply_itbis")
            if apply_itbis is None:
                apply_itbis = itbis_rate > 0
            itbis_val = subtotal * itbis_rate if apply_itbis else 0.0
            total_amount = subtotal + itbis_val

            # Preparar template para Excel (inyecta logo como ruta local si viene en file:///)
            tpl_for_excel = dict(tpl or {})
            logo_local = _file_uri_to_path(comp.get("logo_path") or "")
            if logo_local:
                # El generador de invoice toma el logo de template["logo_path"]
                tpl_for_excel["logo_path"] = logo_local
                if tpl_for_excel.get("show_logo") is False:
                    tpl_for_excel["show_logo"] = True

            # Datos de factura que espera generate_invoice_excel
            invoice_data = {
                "company_id": comp.get("id"),
                "company_name": company_name,
                "invoice_date": inv.get("date"),
                "due_date": inv.get("due_date") or "",
                "ncf_type": inv.get("ncf_type") or inv.get("invoice_category") or inv.get("type") or "",
                "ncf_number": inv.get("ncf") or inv.get("number") or "",
                "invoice_type": inv.get("invoice_type") or "emitida",
                "invoice_category": inv.get("invoice_category") or inv.get("type") or "",
                "client_name": inv.get("client_name") or inv.get("third_party_name") or "",
                "client_rnc": inv.get("client_rnc") or inv.get("rnc") or "",
                "currency": inv.get("currency") or "RD$",
                "apply_itbis": bool(apply_itbis),
                "itbis_rate": itbis_rate,
                # El generador de PDF usa 'company_logo'; por compatibilidad no hace daño pasarla
                "company_logo": logo_local,
            }

            # Llamar al generador principal o al fallback
            if callable(gen_invoice_xlsx):
                gen_invoice_xlsx(invoice_data, items, save_path, company_name, template=tpl_for_excel)
            else:
                # Fallback al generador de cotización con datos equivalentes
                data_fallback = {
                    "company_id": comp.get("id"),
                    "company_name": company_name,
                    "quotation_date": inv.get("date"),
                    "client_name": invoice_data["client_name"],
                    "client_rnc": invoice_data["client_rnc"],
                    "notes": inv.get("notes") or "",
                    "currency": invoice_data["currency"],
                    "itbis_rate": itbis_rate,
                    "apply_itbis": bool(apply_itbis),
                    "total_amount": total_amount,
                    "logo_path": logo_local,
                }
                gen_quote_xlsx(data_fallback, items, save_path, company_name, template=tpl_for_excel)

            QMessageBox.information(self, "Excel", f"Archivo Excel generado:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "Excel", f"No se pudo generar el Excel:\n{e}")