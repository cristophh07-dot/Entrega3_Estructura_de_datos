"""El sistema reproduce el Excel de referencia (Prueba_portafolio.xlsx) al centavo.
Ejecutar: py -m unittest tests.test_concordancia_excel -v

Datos de Nike tal como están en el Excel:
  30/01/2023  compra 20 acciones a US$ 127, TRM 4.548,50, comisión 24.261,699 (fórmula M6 del Excel)
  02/04/2023  dividendo US$ 0,34 por acción, TRM 4.646,08
  01/06/2023  dividendo US$ 0,34 por acción, TRM 4.177,58
  22/06/2023  venta de las 20 acciones a US$ 110, TRM 3.971,38, sin comisión (M9 = 0 en el Excel)
Saldo de cada fila en el Excel (columna N): −11.577.451,699 · −11.545.858,355 · −11.517.450,811 · −2.780.414,811
"""
import unittest
from datetime import date
from types import SimpleNamespace as N

import pandas as pd

from motor.comision_broker import ComisionBroker
from motor.portafolio import Portafolio

COMPRA, DIV1, DIV2, VENTA = date(2023, 1, 30), date(2023, 4, 2), date(2023, 6, 1), date(2023, 6, 22)
TRM = {COMPRA: 4_548.5, DIV1: 4_646.08, DIV2: 4_177.58, VENTA: 3_971.38}
SALDOS_EXCEL = [-11_577_451.699, -11_545_858.355, -11_517_450.811, -2_780_414.811]


class PreciosExcel:
    """La TRM de cada fecha, tal como está en la columna I del Excel."""

    def historial(self, ticker, desde):
        filas = [{"fecha": f, "precio": t} for f, t in sorted(TRM.items()) if f >= desde]
        return pd.DataFrame(filas if ticker == "COP=X" else [], columns=["fecha", "precio"])

    def precio_actual(self, ticker):
        return 110 * TRM[VENTA]

    def trm_actual(self):
        return TRM[VENTA]


class RepoExcel:
    def __init__(self, comision_compra, comision_venta):
        self.nike = N(id=1, nombre="Nike", tipo="ACCION", ticker="NKE", moneda="USD",
                      es_renta_fija=lambda: False)
        self.ops = [
            N(id=1, activo_id=1, tipo="COMPRA", fecha=COMPRA, cantidad=20,
              precio=127 * TRM[COMPRA], comision=comision_compra),
            N(id=2, activo_id=1, tipo="VENTA", fecha=VENTA, cantidad=20,
              precio=110 * TRM[VENTA], comision=comision_venta),
        ]
        self.flujos = [
            N(id=1, activo_id=1, tipo="DIVIDENDO", fecha=DIV1, valor_bruto=0.34 * TRM[DIV1] * 20, retencion=0.0),
            N(id=2, activo_id=1, tipo="DIVIDENDO", fecha=DIV2, valor_bruto=0.34 * TRM[DIV2] * 20, retencion=0.0),
        ]

    def listar_activos(self):
        return [self.nike]

    def listar_operaciones(self, activo_id=None):
        return self.ops

    def listar_flujos(self, activo_id=None):
        return self.flujos


class TestConcordanciaConElExcel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Las mismas comisiones que quedaron en el Excel
        cls.p = Portafolio(RepoExcel(24_261.699, 0.0), PreciosExcel(), fecha_corte=date(2023, 12, 31))

    def test_saldo_final_igual_al_excel(self):
        self.assertAlmostEqual(self.p.resumen()["ganancia"], -2_780_414.811, places=3)

    def test_saldo_fila_por_fila(self):
        filas = self.p.extracto(1)["filas"]
        self.assertEqual(list(filas["movimiento"]), ["Compra", "Dividendo", "Dividendo", "Venta"])
        for esperado, obtenido in zip(SALDOS_EXCEL, filas["saldo"]):
            self.assertAlmostEqual(obtenido, esperado, places=3)

    def test_columnas_del_excel(self):
        filas = self.p.extracto(1)["filas"]
        compra, div1 = filas.iloc[0], filas.iloc[1]
        self.assertAlmostEqual(compra["precio_usd"], 127)              # Valor US
        self.assertAlmostEqual(compra["precio_cop"], 577_659.5)        # Valor COP = E × I
        self.assertEqual(list(filas["acciones"]), [20, 20, 20, 0])     # Acciones = anterior + compra − venta
        self.assertAlmostEqual(div1["dividendo_usd"], 0.34)            # Dividendo por acción
        self.assertAlmostEqual(div1["dividendo_cop"], 1_579.6672 * 20, places=3)   # K × D

    def test_extracto_y_dashboard_dicen_lo_mismo(self):
        extracto = self.p.extracto(1)
        self.assertAlmostEqual(extracto["total"], self.p.posiciones()["ganancia"].iloc[0], places=4)
        self.assertEqual(extracto["acciones"], 0)

    def test_con_la_regla_de_comision_del_sistema(self):
        """Con el 0,2 % cobrado al comprar Y al vender (lo que la fórmula del Excel buscaba)."""
        c = ComisionBroker()
        compra, venta = c.comision(20 * 127 * TRM[COMPRA]), c.comision(20 * 110 * TRM[VENTA])
        p = Portafolio(RepoExcel(compra, venta), PreciosExcel(), fecha_corte=date(2023, 12, 31))
        esperado = -2_780_414.811 + 24_261.699 - compra - venta
        self.assertAlmostEqual(p.resumen()["ganancia"], esperado, places=2)


if __name__ == "__main__":
    unittest.main()
