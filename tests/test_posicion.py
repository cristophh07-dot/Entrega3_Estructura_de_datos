"""Pruebas de Posicion. Ejecutar: py -m unittest tests.test_posicion -v"""
import unittest
from datetime import date
from types import SimpleNamespace

from motor.posicion import Posicion


def op(tipo, fecha, cantidad, precio, comision, activo_id=1):
    return SimpleNamespace(activo_id=activo_id, tipo=tipo, fecha=fecha,
                           cantidad=cantidad, precio=precio, comision=comision)


ACTIVO = SimpleNamespace(id=1, nombre="Prueba")


class TestPosicion(unittest.TestCase):

    def test_compra_suma_comision_al_costo(self):
        p = Posicion(ACTIVO, [op("COMPRA", date(2026, 1, 1), 10, 100, 20)])
        self.assertEqual(p.cantidad, 10)
        self.assertAlmostEqual(p.costo_total, 1020)
        self.assertAlmostEqual(p.costo_promedio, 102)

    def test_dos_compras_promedio_ponderado(self):
        p = Posicion(ACTIVO, [
            op("COMPRA", date(2026, 1, 1), 10, 100, 0),
            op("COMPRA", date(2026, 2, 1), 30, 120, 0),
        ])
        # (1000 + 3600) / 40 = 115
        self.assertAlmostEqual(p.costo_promedio, 115)

    def test_venta_parcial(self):
        p = Posicion(ACTIVO, [
            op("COMPRA", date(2026, 1, 1), 10, 100, 20),
            op("VENTA", date(2026, 3, 1), 4, 130, 10),
        ])
        self.assertAlmostEqual(p.cantidad, 6)
        self.assertAlmostEqual(p.ganancia_realizada, 510 - 408)
        self.assertAlmostEqual(p.costo_total, 612)
        self.assertAlmostEqual(p.costo_promedio, 102)  # no cambia al vender
        self.assertAlmostEqual(p.ventas_netas, 510)
        self.assertAlmostEqual(p.comisiones, 30)

    def test_ordena_por_fecha(self):
        p = Posicion(ACTIVO, [
            op("VENTA", date(2026, 3, 1), 4, 130, 0),
            op("COMPRA", date(2026, 1, 1), 10, 100, 0),
        ])
        self.assertAlmostEqual(p.cantidad, 6)

    def test_vender_de_mas_falla(self):
        with self.assertRaises(ValueError):
            Posicion(ACTIVO, [
                op("COMPRA", date(2026, 1, 1), 5, 100, 0),
                op("VENTA", date(2026, 2, 1), 6, 100, 0),
            ])

    def test_venta_total_cierra_posicion(self):
        p = Posicion(ACTIVO, [
            op("COMPRA", date(2026, 1, 1), 3, 100, 0),
            op("VENTA", date(2026, 2, 1), 3, 90, 0),
        ])
        self.assertFalse(p.esta_abierta)
        self.assertEqual(p.costo_total, 0)
        self.assertAlmostEqual(p.ganancia_realizada, -30)

    def test_filtra_otro_activo_y_fecha(self):
        p = Posicion(ACTIVO, [
            op("COMPRA", date(2026, 1, 1), 10, 100, 0),
            op("COMPRA", date(2026, 1, 1), 99, 1, 0, activo_id=2),
            op("COMPRA", date(2026, 6, 1), 10, 100, 0),
        ], hasta=date(2026, 3, 1))
        self.assertEqual(p.cantidad, 10)


if __name__ == "__main__":
    unittest.main()