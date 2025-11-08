# Constantes compartidas
NCF_TYPES = {
    "Crédito Fiscal (B01)": "B01",
    "Consumidor Final (B02)": "B02",
    "Gubernamental (B15)": "B15",
    "Régimen Especial (B14)": "B14",
    "Nota de Crédito (B04)": "B04",
}

# Valores por defecto del prefijo de NCF según la categoría de factura
# utilizados cuando no existe una configuración específica por empresa.
NCF_CATEGORY_DEFAULT_PREFIX = {
    "FACTURA PRIVADA": "B01",
    "FACTURA GUBERNAMENTAL": "B15",
    "FACTURA GUBERMAMENTAL": "B15",  # tolera typo histórico
    "FACTURA CONSUMIDOR FINAL": "B02",
    "FACTURA EXENTA": "B14",
    "FACTURA EXENTA (REGIMEN ESPECIAL)": "B14",
    "FACTURA EXCENTA (REGIMEN ESPECIAL)": "B14",
}
ITBIS_RATE = 0.18
DEFAULT_CURRENCY = "RD$"