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

    def test_tarifa_fija_hasta_cinco_millones(self):
        self.assertAlmostEqual(self.c.comision(300_000), 14_875)     # 12.500 + 19 % de IVA
        self.assertAlmostEqual(self.c.comision(5_000_000), 14_875)

    def test_porcentaje_por_encima_de_cinco_millones(self):
        self.assertAlmostEqual(self.c.comision(10_000_000), 10_000_000 * 0.0025 * 1.19)   # 29.750

    def test_no_salta_en_el_umbral(self):
        self.assertAlmostEqual(self.c.comision(5_000_000), self.c.comision(5_000_001), places=0)

    def test_sin_valor_no_hay_comision(self):
        self.assertEqual(self.c.comision(0), 0.0)

    def test_regla_explicada(self):
        self.assertIn("tarifa fija", self.c.regla(1_000_000))
        self.assertIn("0,25 %", self.c.regla(8_000_000))


class TestDatosDelFormulario(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        repo = RepositorioMock()
        cls.p = Portafolio(repo, ServicioPreciosMock(repo), fecha_corte=date(2026, 11, 4))

    def test_comision_sugerida(self):
        comision, regla = self.p.comision_sugerida(3 * 1_045_000)
        self.assertAlmostEqual(comision, 14_875)
        self.assertIn("tarifa fija", regla)

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
