"""Pruebas de ValoradorRentaVariable. Ejecutar: py -m unittest tests.test_valorador_renta_variable -v"""
import unittest
from datetime import date
from types import SimpleNamespace

from mocks.servicio_precios_mock import ServicioPreciosMock
from motor.posicion import Posicion
from motor.valorador_renta_variable import ValoradorRentaVariable


def compra(activo_id, cantidad, precio):
    return SimpleNamespace(activo_id=activo_id, tipo="COMPRA", fecha=date(2026, 1, 15),
                           cantidad=cantidad, precio=precio, comision=0)


class TestValoradorRentaVariable(unittest.TestCase):

    def setUp(self):
        self.valorador = ValoradorRentaVariable(ServicioPreciosMock())

    def test_valor_con_precio_actual(self):
        nike = SimpleNamespace(id=6, nombre="Nike", ticker="NKE")
        p = Posicion(nike, [compra(6, 20, 290_000)])
        # 20 × 278.800 del mock
        self.assertAlmostEqual(self.valorador.valor(p), 5_576_000)

    def test_posicion_cerrada_vale_cero(self):
        ko = SimpleNamespace(id=7, nombre="Coca-Cola", ticker="KO")
        venta = SimpleNamespace(activo_id=7, tipo="VENTA", fecha=date(2026, 3, 1),
                                cantidad=30, precio=300_000, comision=0)
        p = Posicion(ko, [compra(7, 30, 287_000), venta])
        self.assertEqual(self.valorador.valor(p), 0.0)

    def test_sin_precio_usa_costo(self):
        raro = SimpleNamespace(id=9, nombre="Raro", ticker="NOEXISTE")
        p = Posicion(raro, [compra(9, 5, 1_000)])
        self.assertAlmostEqual(self.valorador.valor(p), 5_000)
        self.assertIn("NOEXISTE", self.valorador.sin_precio)

    def test_precio_en_fecha_toma_el_anterior(self):
        # 2026-10-03 es sábado: debe devolver el precio del viernes 2026-10-02
        sabado = self.valorador.precio_en_fecha("KO", date(2026, 10, 3), date(2026, 9, 1))
        viernes = self.valorador.precio_en_fecha("KO", date(2026, 10, 2), date(2026, 9, 1))
        self.assertIsNotNone(viernes)
        self.assertEqual(sabado, viernes)


if __name__ == "__main__":
    unittest.main()