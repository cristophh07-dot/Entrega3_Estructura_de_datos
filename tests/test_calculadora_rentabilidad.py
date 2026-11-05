"""Pruebas de CalculadoraRentabilidad. Ejecutar: py -m unittest tests.test_calculadora_rentabilidad -v"""
import unittest
from datetime import date
from types import SimpleNamespace

from motor.calculadora_rentabilidad import CalculadoraRentabilidad


def op(tipo, fecha, cantidad, precio, comision=0):
    return SimpleNamespace(activo_id=1, tipo=tipo, fecha=fecha,
                           cantidad=cantidad, precio=precio, comision=comision)


def flujo(fecha, valor, retencion=0.0):
    return SimpleNamespace(activo_id=1, tipo="DIVIDENDO", fecha=fecha,
                           valor_bruto=valor, retencion=retencion)


class TestCalculadoraRentabilidad(unittest.TestCase):

    def setUp(self):
        self.c = CalculadoraRentabilidad()

    def test_un_anio_exacto_da_la_misma_tasa(self):
        # Invierto 1.000.000 y al año vale 1.100.000 → 10 % acumulado y 10 % E.A.
        r = self.c.calcular([op("COMPRA", date(2025, 1, 1), 1, 1_000_000)], [],
                            1_100_000, date(2026, 1, 1))
        self.assertAlmostEqual(r["rentabilidad_acumulada"], 0.10)
        self.assertAlmostEqual(r["rentabilidad_ea"], 0.10, places=6)

    def test_control_medio_anio(self):
        # Una sola compra: EA = (1 + R_acum)^(365/días) − 1
        r = self.c.calcular([op("COMPRA", date(2026, 1, 1), 1, 1_000_000)], [],
                            1_050_000, date(2026, 7, 2))
        dias = (date(2026, 7, 2) - date(2026, 1, 1)).days
        esperado = 1.05 ** (365 / dias) - 1
        self.assertAlmostEqual(r["rentabilidad_ea"], esperado, places=6)

    def test_comision_y_retencion(self):
        ops = [op("COMPRA", date(2026, 1, 1), 10, 100, comision=20)]   # paga 1.020
        fls = [flujo(date(2026, 6, 1), 100, retencion=0.30)]           # recibe 70
        r = self.c.calcular(ops, fls, 1_000, date(2027, 1, 1))
        self.assertAlmostEqual(r["total_invertido"], 1_020)
        self.assertAlmostEqual(r["ingresos"], 70)
        self.assertAlmostEqual(r["ganancia"], 1_000 + 70 - 1_020)
        self.assertAlmostEqual(r["comisiones"], 20)

    def test_venta_cuenta_como_entrada(self):
        ops = [op("COMPRA", date(2026, 1, 1), 10, 100),
               op("VENTA", date(2026, 6, 1), 10, 120, comision=10)]    # recibe 1.190
        r = self.c.calcular(ops, [], 0, date(2026, 12, 1))
        self.assertAlmostEqual(r["ventas"], 1_190)
        self.assertAlmostEqual(r["rentabilidad_acumulada"], 0.19)
        self.assertGreater(r["rentabilidad_ea"], 0.19)   # se ganó en menos de un año

    def test_perdida_da_tasa_negativa(self):
        r = self.c.calcular([op("COMPRA", date(2025, 1, 1), 1, 1_000_000)], [],
                            800_000, date(2026, 1, 1))
        self.assertAlmostEqual(r["rentabilidad_ea"], -0.20, places=6)

    def test_sin_entradas_no_calcula_ea(self):
        r = self.c.calcular([op("COMPRA", date(2026, 1, 1), 1, 1_000)], [], 0, date(2026, 6, 1))
        self.assertEqual(r["rentabilidad_ea"], 0.0)

    def test_vpn_es_cero_en_la_tasa_encontrada(self):
        fc = [(date(2025, 1, 1), -1000), (date(2025, 7, 1), 50), (date(2026, 3, 1), 1_080)]
        tasa = self.c.xirr(fc)
        self.assertAlmostEqual(self.c.valor_presente(tasa, fc), 0, places=6)


if __name__ == "__main__":
    unittest.main()