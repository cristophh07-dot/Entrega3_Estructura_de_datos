"""Pruebas de GeneradorFlujos. Ejecutar: py -m unittest tests.test_generador_flujos -v"""
import unittest
from datetime import date
from types import SimpleNamespace

from motor.generador_flujos import GeneradorFlujos


def titulo(vn, tasa, emision, vencimiento, periodicidad):
    return SimpleNamespace(valor_nominal=vn, tasa=tasa, fecha_emision=emision,
                           fecha_vencimiento=vencimiento,
                           periodicidad_meses=periodicidad)


class TestGeneradorFlujos(unittest.TestCase):

    def setUp(self):
        self.g = GeneradorFlujos()
        # Mismos títulos del RepositorioMock
        self.cdt = titulo(5_000_000, 0.105, date(2026, 2, 2), date(2027, 2, 2), 0)
        self.bono = titulo(10_000_000, 0.11, date(2024, 5, 15), date(2029, 5, 15), 6)
        self.tes = titulo(1_000_000, 0.07, date(2020, 3, 26), date(2031, 3, 26), 12)

    def test_cdt_un_solo_pago(self):
        f = self.g.flujos(self.cdt)
        self.assertEqual(len(f), 2)                       # interés + capital
        self.assertEqual(f[0]["fecha"], date(2027, 2, 2))
        self.assertAlmostEqual(f[0]["valor"], 525_000)    # 365 días al 10,5 %
        self.assertEqual(f[1]["tipo"], "CAPITAL")
        self.assertEqual(f[1]["valor"], 5_000_000)

    def test_tes_cupon_anual(self):
        self.assertAlmostEqual(self.g.cupon(self.tes), 70_000)
        self.assertEqual(len(self.g.fechas_pago(self.tes)), 11)   # 2021 a 2031

    def test_bono_cupon_semestral_equivalente(self):
        # (1,11)^(6/12) − 1 = 5,3565 % por semestre
        self.assertAlmostEqual(self.g.cupon(self.bono), 535_653.75, places=2)
        fechas = self.g.fechas_pago(self.bono)
        self.assertEqual(len(fechas), 10)                          # 5 años × 2
        self.assertEqual(fechas[0], date(2024, 11, 15))
        self.assertEqual(fechas[-1], date(2029, 5, 15))

    def test_filtro_desde_hasta(self):
        f = self.g.flujos(self.bono, desde=date(2026, 1, 1), hasta=date(2026, 12, 31))
        self.assertEqual([x["fecha"] for x in f], [date(2026, 5, 15), date(2026, 11, 15)])

    def test_capital_solo_al_vencimiento(self):
        capitales = [x for x in self.g.flujos(self.tes) if x["tipo"] == "CAPITAL"]
        self.assertEqual(len(capitales), 1)
        self.assertEqual(capitales[0]["fecha"], date(2031, 3, 26))

    def test_ultimo_pago(self):
        self.assertEqual(self.g.ultimo_pago(self.bono, date(2026, 8, 1)), date(2026, 5, 15))
        self.assertEqual(self.g.ultimo_pago(self.cdt, date(2026, 8, 1)), date(2026, 2, 2))

    def test_sumar_meses_fin_de_mes(self):
        self.assertEqual(GeneradorFlujos.sumar_meses(date(2026, 8, 31), -6), date(2026, 2, 28))


if __name__ == "__main__":
    unittest.main()
    