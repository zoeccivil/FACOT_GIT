
from __future__ import annotations

from typing import List, Dict, Optional

from utils.template_manager import load_template
from utils.invoice_templates import generate_invoice_excel, generate_invoice_pdf
from utils.quotation_templates import generate_quotation_excel, generate_quotation_pdf

def export_invoice_excel_with_template(invoice_data: Dict, items: List[Dict], save_path: str, company_name: str = "", template: Optional[Dict] = None):
    """
    Carga la plantilla de la empresa si template es None y llama a generate_invoice_excel pasando template.
    invoice_data debe contener company_id (int) para buscar la plantilla.
    """
    if template is None and invoice_data.get("company_id") is not None:
        template = load_template(int(invoice_data.get("company_id")))
    generate_invoice_excel(invoice_data, items, save_path, company_name=company_name, template=template)

def export_invoice_pdf_with_template(invoice_data: Dict, items: List[Dict], save_path: str, company_name: str = "", template: Optional[Dict] = None):
    if template is None and invoice_data.get("company_id") is not None:
        template = load_template(int(invoice_data.get("company_id")))
    generate_invoice_pdf(invoice_data, items, save_path, company_name=company_name, template=template)

def export_quotation_excel_with_template(quotation_data: Dict, items: List[Dict], save_path: str, company_name: str = "", template: Optional[Dict] = None):
    if template is None and quotation_data.get("company_id") is not None:
        template = load_template(int(quotation_data.get("company_id")))
    generate_quotation_excel(quotation_data, items, save_path, company_name=company_name, template=template)

def export_quotation_pdf_with_template(quotation_data: Dict, items: List[Dict], save_path: str, company_name: str = "", template: Optional[Dict] = None, use_html: bool = True):
    """
    Exporta la cotización a PDF. Si use_html=True intenta renderizar el HTML (templates/quotation_template.html)
    usando QWebEngine (printToPdf). Si falla o use_html=False, cae al generador PDF basado en reportlab.
    - quotation_data: dict (incluye company_id o company fields)
    - items: lista de dicts
    - save_path: ruta destino .pdf
    - company_name: opcional
    - template: template dict opcional
    """
    # Si se requiere usar HTML (WYSIWYG) y PyQt WebEngine está disponible, usarlo
    if use_html:
        try:
            # Importar aquí para evitar dependencia en tiempo de carga si no usamos HTML
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QEventLoop, QUrl, QTimer, QByteArray
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            from utils.html_injector import build_html_with_json_block

            # Preparar datos (cargar template si es None)
            tpl = template
            if tpl is None and quotation_data.get("company_id") is not None:
                tpl = load_template(int(quotation_data.get("company_id")))
            if tpl is None:
                tpl = {}

            # Prepare company info for HTML (try to include logo path)
            company = {}
            if quotation_data.get("company_id"):
                company = {
                    "id": quotation_data.get("company_id"),
                    "name": quotation_data.get("company_name") or company_name or "",
                    "rnc": quotation_data.get("company_rnc") or "",
                    "address_line1": quotation_data.get("company_address") or quotation_data.get("company_address_line1") or ""
                }
            else:
                company = {
                    "id": quotation_data.get("company_id"),
                    "name": quotation_data.get("company_name") or company_name or "",
                    "rnc": quotation_data.get("company_rnc") or "",
                    "address_line1": quotation_data.get("company_address") or quotation_data.get("company_address_line1") or ""
                }

            # Add logo path from template if present and resolve to file:/// absolute if possible
            logo_rel = tpl.get("logo_path") or quotation_data.get("company_logo") or ""
            if logo_rel:
                from utils.template_manager import get_data_root
                import os
                possible = os.path.join(get_data_root(), logo_rel)
                if os.path.exists(possible):
                    company["logo_path"] = "file:///" + os.path.abspath(possible).replace("\\", "/")
                else:
                    company["logo_path"] = logo_rel

            # Build HTML
            html = build_html_with_json_block("templates/quotation_template.html", company, tpl, {
                "number": quotation_data.get("number") or quotation_data.get("quotation_number", ""),
                "date": quotation_data.get("quotation_date") or "",
                "client_name": quotation_data.get("client_name",""),
                "client_rnc": quotation_data.get("client_rnc",""),
                "items": items,
                "notes": quotation_data.get("notes","")
            })

            # Ensure QApplication exists
            app = QApplication.instance() or QApplication([])

            # Use QWebEngineView offscreen
            view = QWebEngineView()
            loop = QEventLoop()
            success = {"done": False, "ok": False}

            def handle_pdf_result(result):
                # Handles bytes OR boolean/None OR QByteArray
                try:
                    # QByteArray -> bytes
                    if isinstance(result, QByteArray):
                        data_bytes = bytes(result)
                        with open(save_path, "wb") as f:
                            f.write(data_bytes)
                        success["done"] = True
                        success["ok"] = True
                        loop.quit()
                        return

                    if isinstance(result, (bytes, bytearray)):
                        with open(save_path, "wb") as f:
                            f.write(result)
                        success["done"] = True
                        success["ok"] = True
                        loop.quit()
                        return

                    # boolean/None: check file
                    if isinstance(result, bool) or result is None:
                        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                            success["done"] = True
                            success["ok"] = True
                            loop.quit()
                            return
                        # try bytes fallback
                        try:
                            def cb_bytes(data):
                                try:
                                    if isinstance(data, QByteArray):
                                        db = bytes(data)
                                    else:
                                        db = data
                                    if isinstance(db, (bytes, bytearray)):
                                        with open(save_path, "wb") as f:
                                            f.write(db)
                                        success["done"] = True
                                        success["ok"] = True
                                    else:
                                        success["done"] = True
                                        success["ok"] = False
                                except Exception:
                                    success["done"] = True
                                    success["ok"] = False
                                finally:
                                    loop.quit()
                            view.page().printToPdf(cb_bytes)
                            return
                        except Exception:
                            success["done"] = True
                            success["ok"] = False
                            loop.quit()
                            return

                    success["done"] = True
                    success["ok"] = False
                    loop.quit()
                except Exception:
                    success["done"] = True
                    success["ok"] = False
                    loop.quit()

            def on_load(ok):
                # Wait until the DOM reports ready, then small delay, then print
                try:
                    def on_ready(state):
                        # give small paint time
                        QTimer.singleShot(150, lambda: try_print())
                    def try_print():
                        try:
                            # prefer bytes-callback
                            try:
                                view.page().printToPdf(handle_pdf_result)
                            except TypeError:
                                view.page().printToPdf(save_path, handle_pdf_result)
                        except Exception:
                            success["done"] = True
                            success["ok"] = False
                            loop.quit()
                    view.page().runJavaScript("document.readyState", lambda st: on_ready(st))
                except Exception:
                    success["done"] = True
                    success["ok"] = False
                    loop.quit()

            view.setHtml(html, QUrl.fromLocalFile(os.path.abspath(os.path.dirname("templates/quotation_template.html"))))
            view.loadFinished.connect(on_load)
            loop.exec_()

            if success["done"] and success["ok"]:
                return True
            else:
                # fall through to reportlab fallback
                pass
        except Exception as exc:
            # cualquier error: fall back a reportlab generator abajo
            print("[template_integration] HTML->PDF path failed:", exc)
            pass

    # Fallback: llamar al generador reportlab clásico si existe
    try:
        # call the existing generate_quotation_pdf from utils.quotation_templates
        from utils.quotation_templates import generate_quotation_pdf
        # quotation_data maybe expects total; pass through
        generate_quotation_pdf(quotation_data, items, save_path, company_name=company_name, template=template)
        return True
    except Exception as e:
        # re-raise so caller sees the final failure
        raise