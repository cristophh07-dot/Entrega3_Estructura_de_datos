"""Pruebas de la comisión estándar y de los datos que usa el formulario de operaciones.
Ejecutar: py -m unittest tests.test_comision_broker -v"""
import unittest
from datetime import date

from mocks.portafolio_mock import PortafolioMock
from mocks.repositorio_mock import RepositorioMock
from mocks.servicio_precios_mock import ServicioPreciosMock
from motor.comision_broker import ComisionBroker
from motor.portafolio import Portafolio


class TestComisionBroker(unittest.TestCase):

    def setUp(self):
        self.c = ComisionBroker()

    def test_cero_coma_dos_por_ciento(self):
        # Compra del Excel: 20 acciones de Nike a 577.659,5 COP → 0,2 % de 11.553.190
        self.assertAlmostEqual(self.c.comision(20 * 577_659.5), 23_106.38)

    def test_igual_al_vender(self):
        # Venta del Excel: 20 acciones a 436.851,8 COP → 0,2 % de 8.737.036
        self.assertAlmostEqual(self.c.comision(20 * 436_851.8), 17_474.07)

    def test_sin_valor_no_hay_comision(self):
        self.assertEqual(self.c.comision(0), 0.0)

    def test_regla_explicada(self):
        self.assertIn("0,2 %", self.c.regla())


class TestDatosDelFormulario(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        repo = RepositorioMock()
        cls.p = Portafolio(repo, ServicioPreciosMock(repo), fecha_corte=date(2026, 11, 4))

    def test_comision_sugerida(self):
        comision, regla = self.p.comision_sugerida(3 * 1_045_000)
        self.assertAlmostEqual(comision, 6_270)
        self.assertIn("0,2 %", regla)

    def test_cantidad_disponible_antes_y_despues_de_vender(self):
        # Apple (id 1): compró 10 el 15-ene y vendió 3 el 20-ago
        self.assertEqual(self.p.cantidad_disponible(1, date(2026, 8, 19)), 10)
        self.assertEqual(self.p.cantidad_disponible(1, date(2026, 8, 20)), 7)
        self.assertEqual(self.p.cantidad_disponible(1), 7)
        self.assertEqual(self.p.cantidad_disponible(1, date(2026, 1, 1)), 0)

    def test_mock_da_lo_mismo(self):
        m = PortafolioMock()
        for valor in (300_000, 5_000_000, 12_000_000):
            self.assertAlmostEqual(m.comision_sugerida(valor)[0], self.p.comision_sugerida(valor)[0])
        self.assertEqual(m.cantidad_disponible(1), 7)


if __name__ == "__main__":
    unittest.main()
