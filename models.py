from dataclasses import dataclass, field
from typing import List

@dataclass
class Item:
    description: str
    quantity: float
    unit_price: float

@dataclass
class Invoice:
    company_id: int
    invoice_date: str
    invoice_number: str
    client_name: str
    client_rnc: str
    currency: str
    total_amount: float
    items: List[Item] = field(default_factory=list)

@dataclass
class Quotation:
    company_id: int
    quotation_date: str
    client_name: str
    client_rnc: str
    notes: str
    currency: str
    total_amount: float
    items: List[Item] = field(default_factory=list)