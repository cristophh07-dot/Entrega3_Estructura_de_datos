"""Pruebas de ConversorMoneda y de Portafolio en USD. Ejecutar: py -m unittest tests.test_moneda -v"""
import unittest
from datetime import date
from types import SimpleNamespace

import pandas as pd

from mocks.portafolio_mock import PortafolioMock
from motor.conversor_moneda import ConversorMoneda
from motor.portafolio import Portafolio

COMPRA = date(2026, 2, 2)
HOY = date(2026, 11, 4)


class PreciosConTRM:
    """Servicio de precios de prueba: la TRM pasa de 4.000 (compra) a 3.200 (hoy)
    y la acción pasa de USD 100 a USD 120."""

    TRM = {COMPRA: 4_000.0, HOY: 3_200.0}
    USD = {COMPRA: 100.0, HOY: 120.0}

    def historial(self, ticker, desde):
        if ticker == "COP=X":
            filas = [{"fecha": f, "precio": t} for f, t in self.TRM.items() if f >= desde]
        else:   # precio en COP con la TRM de cada fecha
            filas = [{"fecha": f, "precio": self.USD[f] * self.TRM[f]}
                     for f in self.TRM if f >= desde]
        return pd.DataFrame(filas, columns=["fecha", "precio"])

    def precio_actual(self, ticker):
        return self.USD[HOY] * self.TRM[HOY]

    def trm_actual(self):
        return self.TRM[HOY]


class RepoUnaAccion:
    """10 acciones compradas a USD 100 con TRM 4.000 (400.000 COP cada una), sin comisión."""

    def __init__(self):
        self.accion = SimpleNamespace(id=1, nombre="Coca-Cola", tipo="ACCION",
                                      ticker="KO", moneda="USD", es_renta_fija=lambda: False)
        self.compra = SimpleNamespace(id=1, activo_id=1, tipo="COMPRA", fecha=COMPRA,
                                      cantidad=10, precio=400_000.0, comision=0.0)

    def listar_activos(self):
        return [self.accion]

    def listar_operaciones(self, activo_id=None):
        return [self.compra]

    def listar_flujos(self, activo_id=None):
        return []


class TestConversorMoneda(unittest.TestCase):

    def setUp(self):
        self.c = ConversorMoneda(PreciosConTRM())
        self.c.cargar(COMPRA)

    def test_usa_la_trm_de_la_fecha(self):
        self.assertEqual(self.c.trm_en(COMPRA), 4_000)
        self.assertAlmostEqual(self.c.a_usd(400_000, COMPRA), 100)

    def test_dia_sin_dato_toma_el_anterior(self):
        self.assertEqual(self.c.trm_en(date(2026, 6, 1)), 4_000)

    def test_sin_historial_usa_la_actual(self):
        self.assertEqual(self.c.trm_en(date(2025, 1, 1)), 3_200)


class TestPortafolioEnDolares(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.p = Portafolio(RepoUnaAccion(), PreciosConTRM(), fecha_corte=HOY)

    def test_en_usd_la_rentabilidad_es_la_de_la_accion(self):
        # De USD 100 a USD 120: +20 % en dólares
        self.assertAlmostEqual(self.p.resumen("USD")["rentabilidad_acumulada"], 0.20)
        self.assertAlmostEqual(self.p.resumen("USD")["total_invertido"], 1_000)
        self.assertAlmostEqual(self.p.resumen("USD")["valor_actual"], 1_200)

    def test_en_cop_incluye_el_efecto_del_dolar(self):
        # Pagué 4.000.000 COP y hoy vale 120 × 3.200 × 10 = 3.840.000 COP: −4 % en pesos
        self.assertAlmostEqual(self.p.resumen("COP")["rentabilidad_acumulada"], -0.04)

    def test_posiciones_y_distribucion_en_usd(self):
        fila = self.p.posiciones("USD").iloc[0]
        self.assertAlmostEqual(fila["costo_total"], 1_000)
        self.assertAlmostEqual(fila["rentabilidad"], 0.20)
        self.assertAlmostEqual(self.p.distribucion("USD")["renta_variable"]["valor"], 1_200)

    def test_moneda_invalida(self):
        with self.assertRaises(ValueError):
            self.p.resumen("EUR")


class TestMockAceptaMoneda(unittest.TestCase):

    def test_mock_tiene_los_mismos_parametros(self):
        m = PortafolioMock()
        self.assertLess(m.resumen("USD")["valor_actual"], m.resumen("COP")["valor_actual"])
        self.assertEqual(list(m.posiciones("USD").columns), list(m.posiciones().columns))
        self.assertGreater(len(m.serie_valor(moneda="USD")), 0)
        self.assertIsNotNone(m.proximos_flujos(90, "USD"))


if __name__ == "__main__":
    unittest.main()