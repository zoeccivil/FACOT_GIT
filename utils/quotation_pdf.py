"""
Generador PDF para cotizaciones usando reportlab.

Uso:
    from utils.quotation_pdf import generate_quotation_pdf
    generate_quotation_pdf(quotation_data, items, save_path, company_name=..., template=...)

- quotation_data: dict con campos típicos:
    company_id, quotation_date, number, client_name, client_rnc, currency, apply_itbis, itbis_rate, notes
- items: lista de dicts con keys: code, description, unit, quantity, unit_price
- template: dict opcional (se carga automáticamente si es None cuando se usa template_integration)
    keys relevantes: primary_color (hex), show_logo (bool), logo_path (relativa a data root), footer_lines, itbis_rate
"""
from __future__ import annotations


import os
import datetime
from typing import List, Dict, Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image as RLImage,
        PageBreak,
    )
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# Optional Pillow to compute image aspect ratio
try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

from utils.template_manager import get_data_root, load_template


def _resolve_template(data: Dict, template: Optional[Dict]) -> Dict:
    tpl = template
    if tpl is None and data.get("company_id") is not None:
        tpl = load_template(int(data.get("company_id")))
    if tpl is None:
        tpl = {}
    defaults = {
        "primary_color": "#1f7a44",
        "show_logo": True,
        "logo_path": "",
        "footer_lines": [],
        "itbis_rate": 0.18,
        "font_name": "Helvetica",
    }
    out = dict(defaults)
    out.update(tpl)
    return out


def _resolve_logo_path_rel_to_abs(logo_rel: str) -> Optional[str]:
    if not logo_rel:
        return None
    if os.path.isabs(logo_rel) and os.path.exists(logo_rel):
        return logo_rel
    data_root = get_data_root()
    abs_path = os.path.join(data_root, logo_rel)
    if os.path.exists(abs_path):
        return abs_path
    # try relative to cwd
    if os.path.exists(logo_rel):
        return os.path.abspath(logo_rel)
    return None


def _hex_to_rgb_tuple(hex_color: str):
    if not hex_color:
        return colors.HexColor("#1f7a44")
    try:
        if hex_color.startswith("#"):
            hex_color = hex_color[1:]
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return colors.Color(r, g, b)
    except Exception:
        return colors.HexColor("#1f7a44")


def generate_quotation_pdf(quotation_data: Dict, items: List[Dict], save_path: str, company_name: str = "", template: Dict = None):
    """
    Genera un PDF de la cotización aplicando el template (logo, color, footer lines).
    - quotation_data: puede incluir company_id para cargar template automáticamente.
    - items: lista de dicts: code, description, unit, quantity, unit_price
    - save_path: ruta destino .pdf
    - company_name: nombre para mostrar (override)
    - template: dict opcional con configuraciones visuales
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab no está instalado. Instala con: pip install reportlab")

    tpl = _resolve_template(quotation_data or {}, template)
    primary_color = _hex_to_rgb_tuple(tpl.get("primary_color", "#1f7a44"))
    itbis_rate = float(tpl.get("itbis_rate", quotation_data.get("itbis_rate", 0.18) or 0.18))

    # Document setup
    doc = SimpleDocTemplate(save_path, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=18*mm, bottomMargin=18*mm)

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = tpl.get("font_name", "Helvetica")
    normal.fontSize = 9
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName=tpl.get("font_name", "Helvetica"),
                        fontSize=16, leading=18, textColor=primary_color)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=tpl.get("font_name", "Helvetica"),
                        fontSize=12, leading=14, textColor=primary_color)
    meta_style = ParagraphStyle("meta", parent=normal, alignment=TA_RIGHT, fontSize=9)
    muted = ParagraphStyle("muted", parent=normal, textColor=colors.HexColor("#6b7280"))

    elements = []

    # Header: left = company info & logo, right = quotation meta
    # Prepare left block content
    comp = {
        "name": quotation_data.get("company_name") or company_name or "",
        "rnc": quotation_data.get("company_rnc") or "",
        "address_line1": quotation_data.get("company_address") or quotation_data.get("company_address_line1") or "",
        "address_line2": quotation_data.get("company_address_line2") or "",
    }

    # Logo
    logo_src = (quotation_data.get("company_logo") or tpl.get("logo_path") or "")
    logo_abs = _resolve_logo_path_rel_to_abs(logo_src) if logo_src else None
    logo_flowable = None
    if logo_abs:
        try:
            # determine size keeping aspect ratio
            max_w = 160  # px aprox
            max_h = 60
            if PILImage is not None:
                with PILImage.open(logo_abs) as im:
                    w, h = im.size
                    ratio = h / w if w else 1
                    desired_w = max_w
                    desired_h = int(desired_w * ratio)
                    if desired_h > max_h:
                        desired_h = max_h
                        desired_w = int(desired_h / ratio) if ratio else desired_w
            else:
                desired_w = max_w
                desired_h = max_h
            # reportlab uses points; assume px approximates pts at 1:1 for typical logos
            logo_flowable = RLImage(logo_abs, width=desired_w, height=desired_h)
        except Exception:
            logo_flowable = None

    # Build header table (2 columns)
    left_lines = []
    if comp.get("name"):
        left_lines.append(Paragraph(f"<b>{comp['name']}</b>", normal))
    if comp.get("address_line1"):
        left_lines.append(Paragraph(comp.get("address_line1"), muted))
    if comp.get("address_line2"):
        left_lines.append(Paragraph(comp.get("address_line2"), muted))
    if comp.get("rnc"):
        left_lines.append(Paragraph(f"RNC: {comp.get('rnc')}", muted))

    # Right meta
    qnum = quotation_data.get("number") or quotation_data.get("quotation_number") or ""
    qdate = quotation_data.get("quotation_date") or quotation_data.get("date") or datetime.date.today().isoformat()
    right_lines = [
        Paragraph(f"<para align=right><font size=14 color='{primary_color.hex}'>COTIZACIÓN N°: {qnum}</font></para>", normal),
        Spacer(1, 4),
        Paragraph(f"<para alignment=right>FECHA: {qdate}</para>", meta_style)
    ]

    # Create a two-column table: left = logo+company, right = meta
    header_data = [
        [
            # left cell: stack logo over company text
            (logo_flowable, left_lines),
            right_lines
        ]
    ]

    # We need to create a custom cell content: a list of flowables for left cell
    left_cell_flowables = []
    if logo_flowable:
        left_cell_flowables.append(logo_flowable)
        left_cell_flowables.append(Spacer(1, 6))
    left_cell_flowables.extend(left_lines)

    header_table = Table([[left_cell_flowables, right_lines]], colWidths=[doc.width * 0.6, doc.width * 0.4])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8))

    # Client box
    client_box_data = [
        [Paragraph("<b>DATOS DEL CLIENTE</b>", h2), ""],
        [Paragraph(f"<b>Nombre:</b> {quotation_data.get('client_name','')}", normal), ""],
        [Paragraph(f"<b>RNC:</b> {quotation_data.get('client_rnc','')}", normal), ""],
    ]
    # simple single-column presentation
    elements.append(Spacer(1, 6))

    # Items table: headers + rows. Keep columns: Código, Descripción, Unidad, Cantidad, Precio Unit., Subtotal
    table_data = []
    headers = ["Código", "Descripción", "Unidad", "Cantidad", "Precio Unit.", "Subtotal"]
    header_row = []
    for h in headers:
        header_row.append(Paragraph(f"<b>{h}</b>", ParagraphStyle("hdr", backColor=primary_color, textColor=colors.white, alignment=TA_LEFT, fontName=tpl.get("font_name","Helvetica"), fontSize=9)))
    table_data.append(header_row)

    # Rows
    subtotal = 0.0
    for it in items:
        code = it.get("code","")
        desc = it.get("description","")
        unit = it.get("unit","")
        qty = float(it.get("quantity", it.get("cantidad", 0)) or 0)
        up = float(it.get("unit_price", it.get("precio", 0)) or 0)
        line_total = qty * up
        subtotal += line_total
        row = [
            Paragraph(escape_for_para(code), normal),
            Paragraph(escape_for_para(desc), normal),
            Paragraph(escape_for_para(unit), normal),
            Paragraph(f"{qty:.2f}", normal),
            Paragraph(f"{up:,.2f}", normal),
            Paragraph(f"{line_total:,.2f}", normal),
        ]
        table_data.append(row)

    # Table styling
    col_widths = [50, None, 50, 60, 80, 80]  # last columns narrower/wider in pts
    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table_style = TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#e6eaea")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BACKGROUND", (0,0), (-1,0), primary_color),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (-2,1), (-1,-1), "RIGHT"),
        ("ALIGN", (3,1), (3,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ])
    items_table.setStyle(items_table_style)
    elements.append(items_table)
    elements.append(Spacer(1, 12))

    # Totals
    itbis_amount = subtotal * itbis_rate if quotation_data.get("apply_itbis") or tpl.get("itbis_rate") else subtotal * itbis_rate
    total = subtotal + itbis_amount
    totals_data = [
        ["Subtotal:", f"{subtotal:,.2f}"],
        [f"ITBIS ({itbis_rate*100:.0f}%):", f"{itbis_amount:,.2f}"],
        ["Total:", f"{total:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[doc.width - 120, 120])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("FONTNAME", (0,0), (-1,-1), tpl.get("font_name","Helvetica")),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 12))

    # Notes / footer lines
    notes = quotation_data.get("notes", "")
    if notes:
        elements.append(Paragraph("<b>Notas:</b>", normal))
        elements.append(Paragraph(escape_for_para(notes), muted))
        elements.append(Spacer(1, 8))

    footer_lines = tpl.get("footer_lines", [])
    for line in footer_lines:
        elements.append(Paragraph(line, ParagraphStyle("footer", parent=muted, alignment=TA_LEFT)))

    # Signature placeholder
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("<para alignment=center><u>Firma Autorizada</u></para>", muted))
    elements.append(Spacer(1, 6))

    # Build document
    doc.build(elements)


def escape_for_para(text: str) -> str:
    if not text:
        return ""
    # minimal escaping for XML used by reportlab Paragraph
    s = str(text)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace('"', "&quot;").replace("'", "&#039;")
    return s