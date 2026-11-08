"""Pruebas de ValoradorRentaFija. Ejecutar: py -m unittest tests.test_valorador_renta_fija -v"""
import unittest
from datetime import date
from types import SimpleNamespace

from motor.posicion import Posicion
from motor.valorador_renta_fija import ValoradorRentaFija


def titulo(tipo, vn, tasa, emision, vencimiento, periodicidad, tasa_mercado=None):
    return SimpleNamespace(id=1, nombre=tipo, tipo=tipo, valor_nominal=vn, tasa=tasa,
                           fecha_emision=emision, fecha_vencimiento=vencimiento,
                           periodicidad_meses=periodicidad, tasa_mercado=tasa_mercado)


class TestValoradorRentaFija(unittest.TestCase):

    def setUp(self):
        self.v = ValoradorRentaFija()
        self.cdt = titulo("CDT", 5_000_000, 0.105, date(2026, 2, 2), date(2027, 2, 2), 0)
        self.bono = titulo("BONO", 1_000_000, 0.10, date(2026, 1, 1), date(2028, 1, 1), 12)

    def test_cdt_causacion(self):
        # 182 días: 5.000.000 × 1,105^(182/365)
        esperado = 5_000_000 * 1.105 ** (182 / 365)
        self.assertAlmostEqual(self.v.precio(self.cdt, date(2026, 8, 3)), esperado)

    def test_cdt_el_dia_de_compra_vale_el_nominal(self):
        self.assertAlmostEqual(self.v.precio(self.cdt, date(2026, 2, 2)), 5_000_000)

    def test_bono_a_la_par(self):
        # Si la tasa de mercado = tasa del bono, el precio = valor nominal
        self.assertAlmostEqual(self.v.precio(self.bono, date(2026, 1, 1)), 1_000_000, places=4)

    def test_si_sube_la_tasa_baja_el_precio(self):
        caro = titulo("BONO", 1_000_000, 0.10, date(2026, 1, 1), date(2028, 1, 1), 12, 0.08)
        barato = titulo("BONO", 1_000_000, 0.10, date(2026, 1, 1), date(2028, 1, 1), 12, 0.12)
        hoy = date(2026, 1, 1)
        self.assertGreater(self.v.precio(caro, hoy), 1_000_000)
        self.assertLess(self.v.precio(barato, hoy), 1_000_000)
        # 100.000/1,12 + 1.100.000/1,12² = 966.198,98
        self.assertAlmostEqual(self.v.precio(barato, hoy), 966_198.98, places=2)

    def test_vencido_vale_cero(self):
        self.assertEqual(self.v.precio(self.cdt, date(2027, 2, 2)), 0.0)
        self.assertEqual(self.v.precio(self.bono, date(2029, 1, 1)), 0.0)

    def test_valor_multiplica_por_cantidad(self):
        compra = SimpleNamespace(activo_id=1, tipo="COMPRA", fecha=date(2026, 1, 1),
                                 cantidad=5, precio=1_000_000, comision=0)
        p = Posicion(self.bono, [compra])
        self.assertAlmostEqual(self.v.valor(p, date(2026, 1, 1)), 5_000_000, places=2)


if __name__ == "__main__":
    unittest.main()