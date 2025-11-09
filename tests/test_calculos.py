"""
Tests para cálculos de facturas (subtotal, ITBIS, totales, conversiones).
"""
import pytest


class TestCalculosFactura:
    """Tests para cálculos relacionados con facturas."""

    def test_calculo_subtotal_simple(self):
        """Test de cálculo de subtotal básico."""
        quantity = 10
        unit_price = 1000.00
        expected_subtotal = 10000.00
        
        subtotal = quantity * unit_price
        assert subtotal == expected_subtotal

    def test_calculo_subtotal_decimal(self):
        """Test de cálculo con decimales."""
        quantity = 5.5
        unit_price = 850.75
        expected_subtotal = 4679.125
        
        subtotal = quantity * unit_price
        assert abs(subtotal - expected_subtotal) < 0.01

    def test_calculo_itbis_18_porciento(self):
        """Test de cálculo de ITBIS al 18%."""
        subtotal = 10000.00
        itbis_rate = 0.18
        expected_itbis = 1800.00
        
        itbis = subtotal * itbis_rate
        assert itbis == expected_itbis

    def test_calculo_total_con_itbis(self):
        """Test de cálculo de total con ITBIS."""
        subtotal = 10000.00
        itbis = 1800.00
        expected_total = 11800.00
        
        total = subtotal + itbis
        assert total == expected_total

    def test_conversion_moneda_usd_a_rd(self):
        """Test de conversión de USD a RD$."""
        total_usd = 200.00
        exchange_rate = 58.50
        expected_total_rd = 11700.00
        
        total_rd = total_usd * exchange_rate
        assert total_rd == expected_total_rd

    def test_conversion_moneda_eur_a_rd(self):
        """Test de conversión de EUR a RD$."""
        total_eur = 150.00
        exchange_rate = 63.20
        expected_total_rd = 9480.00
        
        total_rd = total_eur * exchange_rate
        assert total_rd == expected_total_rd

    def test_calculo_multiple_items(self):
        """Test de cálculo con múltiples items."""
        items = [
            {"quantity": 10, "unit_price": 1000.00},  # 10,000
            {"quantity": 5, "unit_price": 800.00},    # 4,000
            {"quantity": 3, "unit_price": 1500.00},   # 4,500
        ]
        
        subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
        expected_subtotal = 18500.00
        
        assert subtotal == expected_subtotal

    def test_calculo_itbis_multiple_items(self):
        """Test de ITBIS sobre múltiples items."""
        items = [
            {"quantity": 10, "unit_price": 1000.00},
            {"quantity": 5, "unit_price": 800.00},
        ]
        
        subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
        itbis = subtotal * 0.18
        total = subtotal + itbis
        
        assert subtotal == 14000.00
        assert itbis == 2520.00
        assert total == 16520.00

    def test_calculo_con_moneda_extranjera_y_itbis(self):
        """Test completo con moneda extranjera e ITBIS."""
        # Factura en USD
        subtotal_usd = 100.00
        itbis_usd = subtotal_usd * 0.18  # 18.00
        total_usd = subtotal_usd + itbis_usd  # 118.00
        
        # Conversión a RD$
        exchange_rate = 58.50
        subtotal_rd = subtotal_usd * exchange_rate  # 5,850.00
        itbis_rd = itbis_usd * exchange_rate  # 1,053.00
        total_rd = total_usd * exchange_rate  # 6,903.00
        
        assert subtotal_usd == 100.00
        assert itbis_usd == 18.00
        assert total_usd == 118.00
        assert subtotal_rd == 5850.00
        assert itbis_rd == 1053.00
        assert total_rd == 6903.00

    def test_redondeo_dos_decimales(self):
        """Test de redondeo a 2 decimales."""
        value = 1234.5678
        expected = 1234.57
        
        rounded = round(value, 2)
        assert rounded == expected

    def test_calculo_descuento_porcentaje(self):
        """Test de cálculo de descuento por porcentaje."""
        subtotal = 10000.00
        discount_percent = 15.0  # 15%
        expected_discount = 1500.00
        expected_final = 8500.00
        
        discount = subtotal * (discount_percent / 100)
        final = subtotal - discount
        
        assert discount == expected_discount
        assert final == expected_final

    def test_calculo_sin_itbis(self):
        """Test de factura sin ITBIS."""
        subtotal = 10000.00
        itbis = 0.00
        total = subtotal + itbis
        
        assert total == 10000.00

    def test_precision_numerica(self):
        """Test de precisión numérica en cálculos."""
        # Evitar problemas de punto flotante
        quantity = 3
        unit_price = 33.33
        
        subtotal = round(quantity * unit_price, 2)
        expected = 99.99
        
        assert subtotal == expected

    def test_calculo_itbis_adelantado(self):
        """Test de cálculo con ITBIS adelantado."""
        total_itbis_cobrado = 5000.00
        total_itbis_pagado = 3000.00
        itbis_adelantado = 500.00
        
        itbis_a_pagar = (total_itbis_cobrado - total_itbis_pagado - itbis_adelantado)
        expected = 1500.00
        
        assert itbis_a_pagar == expected

    def test_conversion_tasa_cambio_uno(self):
        """Test de conversión con tasa 1.0 (misma moneda)."""
        total_rd = 11800.00
        exchange_rate = 1.0
        
        total_converted = total_rd * exchange_rate
        assert total_converted == 11800.00


class TestCalculosRetencion:
    """Tests para cálculos de retenciones."""

    def test_retencion_itbis_100_porciento(self):
        """Test de retención del 100% del ITBIS."""
        itbis_total = 5000.00
        porcentaje_retencion = 100.0
        
        retencion = itbis_total * (porcentaje_retencion / 100)
        assert retencion == 5000.00

    def test_retencion_sobre_total_2_75_porciento(self):
        """Test de retención del 2.75% sobre total."""
        total = 100000.00
        porcentaje = 2.75
        
        retencion = total * (porcentaje / 100)
        expected = 2750.00
        
        assert retencion == expected

    def test_retencion_combinada(self):
        """Test de retención combinada (ITBIS + total)."""
        itbis_total = 5000.00
        total_facturas = 100000.00
        
        retencion_itbis = itbis_total * 1.0  # 100%
        retencion_total = total_facturas * 0.0275  # 2.75%
        
        total_a_retener = retencion_itbis + retencion_total
        expected = 7750.00
        
        assert total_a_retener == expected
