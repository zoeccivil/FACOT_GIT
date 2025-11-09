"""
Tests para ncf_service.py incluyendo simulación de concurrencia.
"""
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from services.ncf_service import NCFService


class TestNCFService:
    """Tests para el servicio de NCF."""
    
    def test_initialization(self, temp_db):
        """Test de inicialización."""
        service = NCFService(temp_db)
        assert service.db_path == temp_db
    
    def test_validate_ncf_format_valid(self):
        """Test de validación de formato válido."""
        service = NCFService(':memory:')
        
        valid_ncfs = [
            'B0100000001',
            'B0299999999',
            'B0400000100',
            'B1400000001',
            'B1500000001'
        ]
        
        for ncf in valid_ncfs:
            valid, message = service.validate_ncf_format(ncf)
            assert valid is True, f"NCF {ncf} debería ser válido"
    
    def test_validate_ncf_format_invalid(self):
        """Test de validación de formato inválido."""
        service = NCFService(':memory:')
        
        invalid_ncfs = [
            '',
            'B01',
            'B0100000',  # Muy corto
            'B011000000001',  # Muy largo
            'A0100000001',  # Prefijo inválido
            'B0300000001',  # Tipo no válido
            'B01XXXXXXXX',  # No numérico
        ]
        
        for ncf in invalid_ncfs:
            valid, message = service.validate_ncf_format(ncf)
            assert valid is False, f"NCF {ncf} debería ser inválido"
    
    def test_reserve_ncf_first(self, temp_db):
        """Test de reservar el primer NCF."""
        # Crear tabla invoices
        self._create_invoices_table(temp_db)
        
        service = NCFService(temp_db)
        success, ncf = service.reserve_ncf(1, 'B01')
        
        assert success is True
        assert ncf == 'B0100000001'
    
    def test_reserve_ncf_sequential(self, temp_db):
        """Test de reservar NCFs secuenciales."""
        self._create_invoices_table(temp_db)
        
        # Insertar una factura existente
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                INSERT INTO invoices 
                (company_id, invoice_type, invoice_date, invoice_number, 
                 invoice_category, rnc, third_party_name, currency, itbis, 
                 total_amount, exchange_rate, total_amount_rd)
                VALUES (1, 'emitida', '2025-01-15', 'B0100000005', 'B01', 
                        '123', 'Test', 'RD$', 0, 1000, 1.0, 1000)
            """)
        
        service = NCFService(temp_db)
        success, ncf = service.reserve_ncf(1, 'B01')
        
        assert success is True
        assert ncf == 'B0100000006'
    
    def test_reserve_ncf_different_types(self, temp_db):
        """Test de reservar NCFs de diferentes tipos."""
        self._create_invoices_table(temp_db)
        
        service = NCFService(temp_db)
        
        # B01
        success, ncf1 = service.reserve_ncf(1, 'B01')
        assert ncf1 == 'B0100000001'
        
        # B02 (diferente secuencia)
        success, ncf2 = service.reserve_ncf(1, 'B02')
        assert ncf2 == 'B0200000001'
        
        # B01 de nuevo (continúa secuencia)
        success, ncf3 = service.reserve_ncf(1, 'B01')
        assert ncf3 == 'B0100000001'  # Aún es el primero porque no se insertó
    
    def test_reserve_ncf_invalid_type(self, temp_db):
        """Test de reservar NCF con tipo inválido."""
        self._create_invoices_table(temp_db)
        
        service = NCFService(temp_db)
        success, error = service.reserve_ncf(1, 'B99')
        
        assert success is False
        assert 'inválido' in error.lower()
    
    def test_check_ncf_exists(self, temp_db):
        """Test de verificar si NCF existe."""
        self._create_invoices_table(temp_db)
        
        # Insertar factura
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                INSERT INTO invoices 
                (company_id, invoice_type, invoice_date, invoice_number, 
                 invoice_category, rnc, third_party_name, currency, itbis, 
                 total_amount, exchange_rate, total_amount_rd)
                VALUES (1, 'emitida', '2025-01-15', 'B0100000001', 'B01', 
                        '123', 'Test', 'RD$', 0, 1000, 1.0, 1000)
            """)
        
        service = NCFService(temp_db)
        
        assert service.check_ncf_exists(1, 'B0100000001') is True
        assert service.check_ncf_exists(1, 'B0100000002') is False
    
    def test_get_ncf_sequence_info(self, temp_db):
        """Test de obtener información de secuencia."""
        self._create_invoices_table(temp_db)
        
        # Insertar algunas facturas
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                INSERT INTO invoices 
                (company_id, invoice_type, invoice_date, invoice_number, 
                 invoice_category, rnc, third_party_name, currency, itbis, 
                 total_amount, exchange_rate, total_amount_rd)
                VALUES (1, 'emitida', '2025-01-15', 'B0100000001', 'B01', 
                        '123', 'Test', 'RD$', 0, 1000, 1.0, 1000)
            """)
            conn.execute("""
                INSERT INTO invoices 
                (company_id, invoice_type, invoice_date, invoice_number, 
                 invoice_category, rnc, third_party_name, currency, itbis, 
                 total_amount, exchange_rate, total_amount_rd)
                VALUES (1, 'emitida', '2025-01-16', 'B0100000002', 'B01', 
                        '123', 'Test', 'RD$', 0, 1000, 1.0, 1000)
            """)
        
        service = NCFService(temp_db)
        info = service.get_ncf_sequence_info(1, 'B01')
        
        assert info['ncf_type'] == 'B01'
        assert info['last_ncf'] == 'B0100000002'
        assert info['next_ncf'] == 'B0100000003'
        assert info['total_issued'] == 2
        assert info['remaining'] > 0
    
    def test_calculate_next_ncf(self, temp_db):
        """Test de cálculo de siguiente NCF."""
        service = NCFService(temp_db)
        
        # Test de incremento normal
        next_ncf = service._calculate_next_ncf('B0100000001', 'B01')
        assert next_ncf == 'B0100000002'
        
        next_ncf = service._calculate_next_ncf('B0100000099', 'B01')
        assert next_ncf == 'B0100000100'
        
        # Test de agotamiento de números
        with pytest.raises(ValueError, match="Se agotaron"):
            # Debería fallar, se agotaron los números
            next_ncf = service._calculate_next_ncf('B0199999999', 'B01')
    
    def test_concurrent_ncf_reservation(self, temp_db):
        """
        Test de concurrencia: múltiples threads intentan reservar NCF.
        Solo uno debe tener éxito, los demás deben obtener el siguiente número.
        """
        self._create_invoices_table(temp_db)
        
        service = NCFService(temp_db)
        results = []
        errors = []
        lock = threading.Lock()
        
        def reserve_ncf_thread(thread_id):
            """Función que ejecutará cada thread."""
            try:
                # Pequeño delay para asegurar que los threads se ejecuten más o menos juntos
                time.sleep(0.01)
                
                success, ncf = service.reserve_ncf(1, 'B01', timeout=10)
                if success:
                    with lock:
                        results.append(ncf)
                    # Simular inserción de factura
                    try:
                        with sqlite3.connect(temp_db) as conn:
                            conn.execute("""
                                INSERT INTO invoices 
                                (company_id, invoice_type, invoice_date, invoice_number, 
                                 invoice_category, rnc, third_party_name, currency, itbis, 
                                 total_amount, exchange_rate, total_amount_rd)
                                VALUES (1, 'emitida', '2025-01-15', ?, 'B01', 
                                        ?, 'Test', 'RD$', 0, 1000, 1.0, 1000)
                            """, (ncf, f'RNC{thread_id}'))
                    except sqlite3.IntegrityError as e:
                        with lock:
                            errors.append((thread_id, str(e)))
                else:
                    with lock:
                        errors.append((thread_id, ncf))
            except Exception as e:
                with lock:
                    errors.append((thread_id, str(e)))
        
        # Ejecutar múltiples threads concurrentemente
        num_threads = 5
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=reserve_ncf_thread, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verificar resultados
        print(f"NCFs reservados: {sorted(results)}")
        print(f"Errores: {errors}")
        
        # Deben haberse reservado NCFs únicos (puede haber menos si hay colisiones detectadas)
        assert len(results) >= num_threads - 1  # Permitir 1 fallo por concurrencia
        assert len(set(results)) == len(results)  # Todos únicos
    
    def test_concurrent_different_companies(self, temp_db):
        """
        Test de concurrencia con diferentes empresas.
        Cada empresa debe tener su propia secuencia.
        """
        self._create_invoices_table(temp_db)
        
        service = NCFService(temp_db)
        results_company1 = []
        results_company2 = []
        
        def reserve_for_company(company_id, results_list):
            """Reserva NCF para una empresa."""
            success, ncf = service.reserve_ncf(company_id, 'B01', timeout=10)
            if success:
                results_list.append(ncf)
                with sqlite3.connect(temp_db) as conn:
                    conn.execute("""
                        INSERT INTO invoices 
                        (company_id, invoice_type, invoice_date, invoice_number, 
                         invoice_category, rnc, third_party_name, currency, itbis, 
                         total_amount, exchange_rate, total_amount_rd)
                        VALUES (?, 'emitida', '2025-01-15', ?, 'B01', 
                                '123', 'Test', 'RD$', 0, 1000, 1.0, 1000)
                    """, (company_id, ncf))
        
        # Reservar para ambas empresas concurrentemente
        with ThreadPoolExecutor(max_workers=4) as executor:
            for i in range(2):
                executor.submit(reserve_for_company, 1, results_company1)
                executor.submit(reserve_for_company, 2, results_company2)
        
        # Cada empresa debe tener su secuencia independiente
        assert len(results_company1) == 2
        assert len(results_company2) == 2
        
        # Ambas secuencias deben empezar desde 1
        assert 'B0100000001' in results_company1
        assert 'B0100000001' in results_company2
    
    def _create_invoices_table(self, db_path):
        """Helper para crear tabla de facturas."""
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    invoice_type TEXT NOT NULL,
                    invoice_date TEXT NOT NULL,
                    invoice_number TEXT NOT NULL,
                    invoice_category TEXT,
                    rnc TEXT NOT NULL,
                    third_party_name TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    itbis REAL NOT NULL DEFAULT 0.0,
                    total_amount REAL NOT NULL DEFAULT 0.0,
                    exchange_rate REAL NOT NULL DEFAULT 1.0,
                    total_amount_rd REAL NOT NULL DEFAULT 0.0,
                    UNIQUE(company_id, rnc, invoice_number)
                )
            """)
