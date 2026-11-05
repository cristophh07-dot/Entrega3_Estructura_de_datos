"""Pruebas de Portafolio con los mocks. Ejecutar: py -m unittest tests.test_portafolio -v"""
import unittest
from datetime import date

from mocks.portafolio_mock import PortafolioMock
from mocks.repositorio_mock import RepositorioMock
from mocks.servicio_precios_mock import ServicioPreciosMock
from motor.portafolio import Portafolio

HOY = date(2026, 11, 4)


class TestPortafolio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        repo = RepositorioMock()
        cls.p = Portafolio(repo, ServicioPreciosMock(repo), fecha_corte=HOY)

    def test_mismas_llaves_y_columnas_que_el_mock(self):
        mock = PortafolioMock()
        self.assertEqual(set(self.p.resumen()), set(mock.resumen()))
        self.assertEqual(list(self.p.posiciones().columns), list(mock.posiciones().columns))
        self.assertEqual(set(self.p.distribucion()), set(mock.distribucion()))

    def test_totales_del_ejemplo(self):
        r = self.p.resumen()
        self.assertAlmostEqual(r["total_invertido"], 47_979_000)
        self.assertAlmostEqual(r["ventas"], 3_050_000)
        self.assertAlmostEqual(r["comisiones"], 104_000)

    def test_incluye_nike_y_coca_cola(self):
        nombres = set(self.p.posiciones()["nombre"])
        self.assertIn("Nike", nombres)
        self.assertIn("Coca-Cola", nombres)

    def test_distribucion_suma_el_valor_actual(self):
        d = self.p.distribucion()
        self.assertAlmostEqual(d["renta_fija"]["valor"] + d["renta_variable"]["valor"],
                               self.p.resumen()["valor_actual"])
        self.assertAlmostEqual(d["renta_fija"]["porcentaje"]
                               + d["renta_variable"]["porcentaje"], 1.0)

    def test_ganancias_por_activo_suman_la_total(self):
        self.assertAlmostEqual(self.p.posiciones()["ganancia"].sum(),
                               self.p.resumen()["ganancia"], places=2)

    def test_serie_valor_termina_hoy(self):
        serie = self.p.serie_valor(date(2026, 10, 1))
        self.assertEqual(serie["fecha"].iloc[-1], HOY)
        self.assertTrue((serie["valor"] > 0).all())

    def test_proximos_flujos_del_bono(self):
        f = self.p.proximos_flujos(dias=30)
        self.assertEqual(list(f["nombre"]), ["Bono corporativo 2029"])
        self.assertEqual(f["fecha"].iloc[0], date(2026, 11, 15))


if __name__ == "__main__":
    unittest.main()