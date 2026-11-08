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

    def test_ganancia_se_separa_en_tres_partes(self):
        for moneda in ("COP", "USD"):
            r = self.p.resumen(moneda)
            partes = r["ganancia_no_realizada"] + r["ganancia_realizada"] + r["ingresos"]
            self.assertAlmostEqual(partes, r["ganancia"], places=4)
        # Apple: vendió 3 a 1.020.000 (−10.000 comisión); costaban 951.500 c/u
        self.assertAlmostEqual(self.p.resumen()["ganancia_realizada"], 3_050_000 - 2_854_500)

    def test_mock_tambien_separa_la_ganancia(self):
        r = PortafolioMock().resumen()
        partes = r["ganancia_no_realizada"] + r["ganancia_realizada"] + r["ingresos"]
        self.assertAlmostEqual(partes, r["ganancia"], places=4)

    def test_precio_sugerido(self):
        activos = {a.nombre: a for a in self.p.repositorio.listar_activos()}
        self.assertAlmostEqual(self.p.precio_sugerido(activos["Nike"]), 278_800)
        pasado = self.p.precio_sugerido(activos["Coca-Cola"], date(2026, 10, 3))   # sábado
        viernes = self.p.precio_sugerido(activos["Coca-Cola"], date(2026, 10, 2))
        self.assertIsNotNone(viernes)
        self.assertEqual(pasado, viernes)
        cdt = self.p.precio_sugerido(activos["CDT Banco 360 días"], date(2026, 8, 3))
        self.assertAlmostEqual(cdt, 5_000_000 * 1.105 ** (182 / 365))
        self.assertIsNone(self.p.precio_sugerido(activos["CDT Banco 360 días"], date(2027, 3, 1)))

    def test_mock_sugiere_precio(self):
        m = PortafolioMock()
        nike = [a for a in self.p.repositorio.listar_activos() if a.nombre == "Nike"][0]
        self.assertEqual(m.precio_sugerido(nike), 278_800)
        
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