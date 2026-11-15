import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from datos.repositorio import Repositorio
from datos.servicio_precios import ServicioPrecios
from modelos.accion import Accion


def _historial(valores_por_fecha, zona):
    indice = pd.DatetimeIndex(
        [pd.Timestamp(f, tz=zona) for f in valores_por_fecha]
    )
    return pd.DataFrame({"Close": list(valores_por_fecha.values())}, index=indice)


def _dividendos(valores_por_fecha, zona):
    indice = pd.DatetimeIndex(
        [pd.Timestamp(f, tz=zona) for f in valores_por_fecha]
    )
    return pd.Series(list(valores_por_fecha.values()), index=indice)


class TestTrmHistorica(unittest.TestCase):
    def setUp(self):
        self.repo = Repositorio(":memory:")
        self.servicio = ServicioPrecios(self.repo)
        self.repo.guardar_activo(Accion(nombre="Apple", ticker="AAPL", moneda="USD"))
        self.repo.guardar_activo(Accion(nombre="Ecopetrol", ticker="ECOPETROL.CL", moneda="COP"))

    def tearDown(self):
        self.repo.cerrar()

    def _yfinance_falso(self, acciones, trm, dividendos=None, trm_falla=False):
        llamadas = []

        def fabrica(simbolo):
            llamadas.append(simbolo)
            if simbolo == "COP=X":
                if trm_falla:
                    raise RuntimeError("sin internet")
                return SimpleNamespace(history=lambda **kw: trm)
            return SimpleNamespace(
                history=lambda **kw: acciones,
                dividends=dividendos,
            )

        return patch("datos.servicio_precios.yf.Ticker", side_effect=fabrica), llamadas

    def test_cada_precio_usa_la_trm_de_su_propio_dia(self):
        acciones = _historial(
            {"2026-03-02": 100.0, "2026-03-03": 110.0}, "America/New_York"
        )
        trm = _historial(
            {"2026-03-02": 4000.0, "2026-03-03": 4100.0}, "America/Bogota"
        )
        parche, _ = self._yfinance_falso(acciones, trm)
        with parche:
            df = self.servicio.historial("AAPL", date(2026, 3, 2))
        self.assertEqual(list(df["fecha"]), [date(2026, 3, 2), date(2026, 3, 3)])
        self.assertAlmostEqual(df["precio"].iloc[0], 100.0 * 4000.0)
        self.assertAlmostEqual(df["precio"].iloc[1], 110.0 * 4100.0)

    def test_dia_sin_trm_usa_la_del_ultimo_dia_habil_anterior(self):
        acciones = _historial(
            {"2026-03-03": 100.0, "2026-03-04": 100.0, "2026-03-05": 100.0},
            "America/New_York",
        )
        trm = _historial(
            {"2026-03-03": 4000.0, "2026-03-05": 4200.0}, "America/Bogota"
        )
        parche, _ = self._yfinance_falso(acciones, trm)
        with parche:
            df = self.servicio.historial("AAPL", date(2026, 3, 3))
        self.assertAlmostEqual(df["precio"].iloc[0], 400000.0)
        self.assertAlmostEqual(df["precio"].iloc[1], 400000.0)
        self.assertAlmostEqual(df["precio"].iloc[2], 420000.0)

    def test_trm_de_fin_de_semana_arrastra_el_viernes(self):
        acciones = _historial({"2026-03-07": 50.0}, "America/New_York")
        trm = _historial(
            {"2026-03-06": 3900.0, "2026-03-09": 4300.0}, "America/Bogota"
        )
        parche, _ = self._yfinance_falso(acciones, trm)
        with parche:
            df = self.servicio.historial("AAPL", date(2026, 3, 6))
        self.assertAlmostEqual(df["precio"].iloc[0], 50.0 * 3900.0)

    def test_dividendos_usan_la_trm_del_dia_del_pago(self):
        trm = _historial(
            {"2026-02-10": 3800.0, "2026-05-12": 4400.0}, "America/Bogota"
        )
        divs = _dividendos(
            {"2026-02-10": 0.25, "2026-05-12": 0.26}, "America/New_York"
        )
        parche, _ = self._yfinance_falso(_historial({}, "UTC"), trm, dividendos=divs)
        with parche:
            df = self.servicio.dividendos("AAPL", date(2026, 2, 1))
        self.assertAlmostEqual(df["valor_por_accion"].iloc[0], 0.25 * 3800.0)
        self.assertAlmostEqual(df["valor_por_accion"].iloc[1], 0.26 * 4400.0)

    def test_dividendo_anterior_a_desde_se_ignora(self):
        trm = _historial({"2026-02-10": 3800.0}, "America/Bogota")
        divs = _dividendos({"2025-11-10": 0.24}, "America/New_York")
        parche, _ = self._yfinance_falso(_historial({}, "UTC"), trm, dividendos=divs)
        with parche:
            df = self.servicio.dividendos("AAPL", date(2026, 2, 1))
        self.assertTrue(df.empty)

    def test_accion_en_cop_no_se_convierte_ni_descarga_la_trm(self):
        acciones = _historial({"2026-03-02": 1500.0}, "America/Bogota")
        trm = _historial({"2026-03-02": 4000.0}, "America/Bogota")
        parche, llamadas = self._yfinance_falso(acciones, trm)
        with parche:
            df = self.servicio.historial("ECOPETROL.CL", date(2026, 3, 2))
        self.assertAlmostEqual(df["precio"].iloc[0], 1500.0)
        self.assertNotIn("COP=X", llamadas)

    def test_si_falla_la_trm_historica_usa_la_trm_actual(self):
        acciones = _historial({"2026-03-02": 100.0}, "America/New_York")
        parche, _ = self._yfinance_falso(acciones, None, trm_falla=True)
        with parche, patch.object(ServicioPrecios, "trm_actual", return_value=4000.0):
            df = self.servicio.historial("AAPL", date(2026, 3, 2))
        self.assertAlmostEqual(df["precio"].iloc[0], 400000.0)


if __name__ == "__main__":
    unittest.main()