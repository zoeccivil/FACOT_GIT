# Re-exports para utils: expone funciones de invoice_templates y quotation_templates
# Esto permite usar "from utils import generate_invoice_pdf, generate_quotation_excel, ..." como antes.
__all__ = []

# Prioriza funciones específicas de facturas si existe utils/invoice_templates.py
try:
    from .invoice_templates import generate_invoice_template, generate_invoice_excel, generate_invoice_pdf  # type: ignore
    __all__.extend(["generate_invoice_template", "generate_invoice_excel", "generate_invoice_pdf"])
except Exception:
    # Si no existe invoice_templates, mapea funciones de quotation_templates para compatibilidad
    try:
        from .quotation_templates import (
            generate_quotation_template,
            generate_quotation_excel,
            generate_quotation_pdf,
        )  # type: ignore
        # alias para compatibilidad con código que esperaba nombres de "invoice"
        generate_invoice_template = generate_quotation_template
        generate_invoice_excel = generate_quotation_excel
        generate_invoice_pdf = generate_quotation_pdf
        __all__.extend([
            "generate_invoice_template",
            "generate_invoice_excel",
            "generate_invoice_pdf",
            "generate_quotation_template",
            "generate_quotation_excel",
            "generate_quotation_pdf",
        ])
    except Exception:
        # No hay plantillas disponibles; no romper la importación ahora.
        pass

# Además, si existen las funciones de cotización, expónlas también
try:
    from .quotation_templates import generate_quotation_template, generate_quotation_excel, generate_quotation_pdf  # type: ignore
    for name in ("generate_quotation_template", "generate_quotation_excel", "generate_quotation_pdf"):
        if name not in __all__:
            __all__.append(name)
except Exception:
    pass