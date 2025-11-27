"""
Configuración de pytest para FACOT.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Agregar el directorio raíz al path para imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def temp_db():
    """Crea una base de datos temporal para tests."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_invoice_data():
    """Datos de ejemplo para una factura."""
    return {
        "company_id": 1,
        "invoice_type": "emitida",
        "invoice_date": "2025-01-15",
        "imputation_date": None,
        "invoice_number": "B0100000001",
        "invoice_category": "B01",
        "rnc": "123456789",
        "third_party_name": "Cliente Ejemplo SA",
        "currency": "RD$",
        "itbis": 1800.00,
        "total_amount": 10000.00,
        "exchange_rate": 1.0,
        "total_amount_rd": 11800.00,
        "attachment_path": ""
    }


@pytest.fixture
def sample_items():
    """Items de ejemplo para una factura."""
    return [
        {
            "description": "Cemento Gris 50kg",
            "quantity": 10,
            "unit_price": 1000.00
        },
        {
            "description": "Arena Lavada m³",
            "quantity": 5,
            "unit_price": 800.00
        }
    ]
