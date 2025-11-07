import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl, QEventLoop
from PyQt6.QtWebEngineWidgets import QWebEngineView
from utils.html_injector import build_html_with_json_block

def render_html_to_pdf(template_path, company, template, quotation, output_pdf_path):
    app = QApplication.instance() or QApplication(sys.argv)
    view = QWebEngineView()

    html = build_html_with_json_block(template_path, company, template, quotation)

    # loadHtml + wait loadFinished then printToPdf (async via callback)
    loop = QEventLoop()
    def on_load(ok):
        # small delay not necessary usually, but if external fonts remote, consider QTimer.singleShot(300, send_pdf)
        def on_pdf_written(success):
            loop.quit()
        # printToPdf takes a callback that receives either bytes or a boolean depending on PyQt version.
        view.page().printToPdf(output_pdf_path, lambda ok: on_pdf_written(ok))
    view.setHtml(html, QUrl.fromLocalFile(os.path.abspath(os.path.dirname(template_path))))
    view.loadFinished.connect(on_load)
    loop.exec_()
    return True

if __name__ == "__main__":
    # ejemplo de uso
    tpl_path = "templates/quotation_template.html"
    company = {"id":1, "name":"Empresa Demo S.R.L.", "rnc":"123456789", "address_line1":"C/ Ejemplo 123", "logo_path":"file:///C:/ruta/a/logo.png"}
    template = {"primary_color":"#1f7a44", "show_logo":True, "itbis_rate":0.18, "footer_lines":["Condiciones..."]}
    quotation = {"number":"10288", "date":"2025-10-16", "client_name":"Cliente X", "client_rnc":"987654321", "items":[{"code":"A001","description":"Desc A","unit":"UND","quantity":2,"unit_price":1500}], "notes":"Nota demo"}
    out_pdf = "out_quotation.pdf"
    render_html_to_pdf(tpl_path, company, template, quotation, out_pdf)
    print("PDF generado:", out_pdf)