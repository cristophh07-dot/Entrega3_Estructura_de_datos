"""Pruebas de HistorialAccion y Portafolio.grafica_accion. Ejecutar: py -m unittest tests.test_historial_accion -v"""
import unittest
from datetime import date, timedelta
from types import SimpleNamespace

import pandas as pd

from mocks.portafolio_mock import PortafolioMock
from mocks.repositorio_mock import RepositorioMock
from mocks.servicio_precios_mock import ServicioPreciosMock
from mocks.servicio_velas_mock import ServicioVelasMock
from motor.historial_accion import HistorialAccion
from motor.portafolio import Portafolio

LUNES = date(2026, 3, 2)
HOY = date(2026, 11, 4)


class VelasFijas:
    """Dos semanas de velas en USD: cada día apertura = n, cierre = n + 1, máx n + 2, mín n − 1."""

    def velas(self, ticker, desde):
        dias = [LUNES + timedelta(days=i) for i in range(12) if (LUNES + timedelta(days=i)).weekday() < 5]
        filas = [{"fecha": d, "apertura": 100.0 + i, "maximo": 102.0 + i,
                  "minimo": 99.0 + i, "cierre": 101.0 + i} for i, d in enumerate(dias)]
        df = pd.DataFrame(filas)
        return df[df["fecha"] >= desde].reset_index(drop=True)

    def limpiar_cache(self):
        pass


class ConversorFijo:
    """TRM 4.000 la primera semana y 3.000 la segunda."""

    def trm_en(self, fecha):
        return 4_000.0 if fecha < LUNES + timedelta(days=7) else 3_000.0

    def a_usd(self, valor_cop, fecha=None):
        return valor_cop / self.trm_en(fecha)


KO = SimpleNamespace(id=7, nombre="Coca-Cola", tipo="ACCION", ticker="KO", moneda="USD",
                     es_renta_fija=lambda: False)


class TestHistorialAccion(unittest.TestCase):

    def setUp(self):
        self.h = HistorialAccion(VelasFijas(), ConversorFijo())

    def test_en_moneda_original_no_cambia(self):
        v = self.h.velas(KO, LUNES, "USD")
        self.assertEqual(len(v), 10)
        self.assertEqual(v["apertura"].iloc[0], 100.0)

    def test_a_pesos_usa_la_trm_de_cada_dia(self):
        v = self.h.velas(KO, LUNES, "COP")
        self.assertAlmostEqual(v["cierre"].iloc[0], 101.0 * 4_000)    # primera semana
        self.assertAlmostEqual(v["cierre"].iloc[-1], 110.0 * 3_000)   # segunda semana

    def test_agrupar_por_semana(self):
        semanas = HistorialAccion.por_semana(self.h.velas(KO, LUNES, "USD"))
        self.assertEqual(len(semanas), 2)
        primera = semanas.iloc[0]
        self.assertEqual(primera["apertura"], 100.0)   # apertura del lunes
        self.assertEqual(primera["cierre"], 105.0)     # cierre del viernes
        self.assertEqual(primera["maximo"], 106.0)     # máximo de la semana
        self.assertEqual(primera["minimo"], 99.0)      # mínimo de la semana

    def test_resumen_del_periodo(self):
        r = HistorialAccion.resumen(self.h.velas(KO, LUNES, "USD"))
        self.assertEqual(r["precio_inicio"], 100.0)
        self.assertEqual(r["ultimo_cierre"], 110.0)
        self.assertAlmostEqual(r["variacion"], 0.10)
        self.assertEqual(r["maximo"], 111.0)
        self.assertEqual(r["minimo"], 99.0)

    def test_operaciones_y_costo_promedio_en_dolares(self):
        compra = SimpleNamespace(activo_id=7, tipo="COMPRA", fecha=LUNES, cantidad=10,
                                 precio=400_000.0, comision=40_000.0)   # USD 100 + USD 10 de comisión
        ops = self.h.operaciones(KO, [compra], LUNES, HOY, "USD")
        self.assertAlmostEqual(ops["precio"].iloc[0], 100.0)
        self.assertAlmostEqual(self.h.costo_promedio(KO, [compra], HOY, "USD"), 101.0)
        self.assertAlmostEqual(self.h.costo_promedio(KO, [compra], HOY, "COP"), 404_000.0)

    def test_periodo_largo_se_agrupa_por_semana(self):
        h = HistorialAccion(ServicioVelasMock(hoy=HOY), ConversorFijo())
        g = h.grafica(KO, [], date(2025, 11, 4), HOY, "USD")
        self.assertEqual(g["agrupacion"], "semana")
        g = h.grafica(KO, [], date(2026, 8, 4), HOY, "USD")
        self.assertEqual(g["agrupacion"], "dia")


class TestGraficaAccionEnPortafolio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        repo = RepositorioMock()
        cls.p = Portafolio(repo, ServicioPreciosMock(repo), fecha_corte=HOY,
                           servicio_velas=ServicioVelasMock(hoy=HOY))

    def test_coca_cola_con_su_compra(self):
        g = self.p.grafica_accion(7, date(2026, 1, 1), "USD")
        self.assertFalse(g["velas"].empty)
        self.assertEqual(list(g["operaciones"]["tipo"]), ["COMPRA"])
        self.assertAlmostEqual(g["costo_promedio"], (30 * 287_000 + 12_000) / 30 / 4_100)

    def test_renta_fija_no_tiene_velas(self):
        with self.assertRaises(ValueError):
            self.p.grafica_accion(3, date(2026, 1, 1))   # el CDT

    def test_sin_servicio_de_velas_viene_vacio(self):
        repo = RepositorioMock()
        p = Portafolio(repo, ServicioPreciosMock(repo), fecha_corte=HOY)
        self.assertTrue(p.grafica_accion(7, date(2026, 1, 1))["velas"].empty)

    def test_mock_tiene_la_misma_forma(self):
        real = self.p.grafica_accion(6, date(2026, 6, 1), "COP")
        mock = PortafolioMock().grafica_accion(6, date(2026, 6, 1), "COP")
        self.assertEqual(set(real), set(mock))
        self.assertEqual(list(real["velas"].columns), list(mock["velas"].columns))
        self.assertEqual(set(real["resumen"]), set(mock["resumen"]))


if __name__ == "__main__":
    unittest.main()
