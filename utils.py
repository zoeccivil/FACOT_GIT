import os
import pandas as pd
from fpdf import FPDF

# ====== PDF Utility ======
class PDF(FPDF):
    def __init__(self, title="Documento", company_name="", extra_info=""):
        super().__init__()
        self.title = title
        self.company_name = company_name
        self.extra_info = extra_info
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, self.title, 0, 1, 'C')
        self.set_font('Arial', 'I', 11)
        self.cell(0, 8, f'Empresa: {self.company_name}', 0, 1, 'C')
        if self.extra_info:
            self.cell(0, 6, self.extra_info, 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_invoice_pdf(invoice_data, items, save_path, company_name=""):
    pdf = PDF(title="Factura", company_name=company_name, extra_info=f"Cliente: {invoice_data.get('client_name','')}")
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"NCF: {invoice_data.get('invoice_number','')}", 0, 1)
    pdf.cell(0, 8, f"Fecha: {invoice_data.get('invoice_date','')}", 0, 1)
    pdf.cell(0, 8, f"Moneda: {invoice_data.get('currency','')}", 0, 1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "Detalles de la Factura", 0, 1)
    pdf.set_font('Arial', '', 10)
    # Tabla
    pdf.cell(80, 8, "Descripción", 1)
    pdf.cell(30, 8, "Cantidad", 1)
    pdf.cell(40, 8, "Precio Unitario", 1)
    pdf.cell(40, 8, "Subtotal", 1, 1)
    pdf.set_font('Arial', '', 9)
    for item in items:
        pdf.cell(80, 6, item['description'], 1)
        pdf.cell(30, 6, f"{item['quantity']:.2f}", 1)
        pdf.cell(40, 6, f"{item['unit_price']:.2f}", 1)
        subtotal = item['quantity'] * item['unit_price']
        pdf.cell(40, 6, f"{subtotal:.2f}", 1, 1)
    pdf.ln(5)
    subtotal = sum(i['quantity']*i['unit_price'] for i in items)
    itbis = subtotal * 0.18
    total = subtotal + itbis
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"Subtotal: {invoice_data.get('currency','RD$')} {subtotal:,.2f}", 0, 1, 'R')
    pdf.cell(0, 8, f"ITBIS (18%): {invoice_data.get('currency','RD$')} {itbis:,.2f}", 0, 1, 'R')
    pdf.cell(0, 10, f"Total: {invoice_data.get('currency','RD$')} {total:,.2f}", 0, 1, 'R')
    pdf.output(save_path)
    return save_path

def generate_quotation_pdf(quotation_data, items, save_path, company_name=""):
    pdf = PDF(title="Cotización", company_name=company_name, extra_info=f"Cliente: {quotation_data.get('client_name','')}")
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"Fecha: {quotation_data.get('quotation_date','')}", 0, 1)
    pdf.cell(0, 8, f"Moneda: {quotation_data.get('currency','')}", 0, 1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "Detalles de la Cotización", 0, 1)
    pdf.set_font('Arial', '', 10)
    # Tabla
    pdf.cell(80, 8, "Descripción", 1)
    pdf.cell(30, 8, "Cantidad", 1)
    pdf.cell(40, 8, "Precio Unitario", 1)
    pdf.cell(40, 8, "Subtotal", 1, 1)
    pdf.set_font('Arial', '', 9)
    for item in items:
        pdf.cell(80, 6, item['description'], 1)
        pdf.cell(30, 6, f"{item['quantity']:.2f}", 1)
        pdf.cell(40, 6, f"{item['unit_price']:.2f}", 1)
        subtotal = item['quantity'] * item['unit_price']
        pdf.cell(40, 6, f"{subtotal:.2f}", 1, 1)
    pdf.ln(5)
    total = sum(i['quantity']*i['unit_price'] for i in items)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"Total: {quotation_data.get('currency','RD$')} {total:,.2f}", 0, 1, 'R')
    pdf.output(save_path)
    return save_path

# ====== Excel Utility ======
def generate_invoice_excel(invoice_data, items, save_path, company_name=""):
    df_items = pd.DataFrame(items)
    # Crea hoja resumen
    resumen = {
        "Campo": ["Empresa", "Cliente", "NCF", "Fecha", "Moneda", "Subtotal", "ITBIS", "Total"],
        "Valor": [
            company_name,
            invoice_data.get('client_name',''),
            invoice_data.get('invoice_number',''),
            invoice_data.get('invoice_date',''),
            invoice_data.get('currency','RD$'),
            sum(i['quantity']*i['unit_price'] for i in items),
            sum(i['quantity']*i['unit_price'] for i in items)*0.18,
            sum(i['quantity']*i['unit_price'] for i in items)*1.18,
        ]
    }
    df_resumen = pd.DataFrame(resumen)
    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
        df_items.to_excel(writer, sheet_name='Detalle', index=False)
    return save_path

def generate_quotation_excel(quotation_data, items, save_path, company_name=""):
    df_items = pd.DataFrame(items)
    resumen = {
        "Campo": ["Empresa", "Cliente", "Fecha", "Moneda", "Total"],
        "Valor": [
            company_name,
            quotation_data.get('client_name',''),
            quotation_data.get('quotation_date',''),
            quotation_data.get('currency','RD$'),
            sum(i['quantity']*i['unit_price'] for i in items),
        ]
    }
    df_resumen = pd.DataFrame(resumen)
    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
        df_items.to_excel(writer, sheet_name='Detalle', index=False)
    return save_path