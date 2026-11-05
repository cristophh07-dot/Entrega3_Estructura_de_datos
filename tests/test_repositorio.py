import unittest
from datetime import date

from datos.repositorio import Repositorio
from modelos.accion import Accion
from modelos.bono import Bono
from modelos.cdt import CDT
from modelos.flujo_caja import FlujoCaja
from modelos.operacion import Operacion
from modelos.tes import TES


class TestRepositorio(unittest.TestCase):
    def setUp(self):
        self.repo = Repositorio(":memory:")

    def tearDown(self):
        self.repo.cerrar()

    def test_guardar_y_leer_accion(self):
        activo = Accion(nombre="Apple", ticker="AAPL", moneda="USD")
        id_guardado = self.repo.guardar_activo(activo)

        self.assertIsNotNone(id_guardado)
        self.assertEqual(activo.id, id_guardado)

        leido = self.repo.obtener_activo(id_guardado)
        self.assertIsInstance(leido, Accion)
        self.assertEqual(leido.nombre, "Apple")
        self.assertEqual(leido.ticker, "AAPL")
        self.assertEqual(leido.moneda, "USD")
        self.assertEqual(leido.tipo, "ACCION")
        self.assertFalse(leido.es_renta_fija())

    def test_guardar_y_leer_cdt(self):
        activo = CDT(
            nombre="CDT Bancolombia",
            valor_nominal=1_000_000,
            tasa=0.12,
            fecha_emision=date(2026, 1, 1),
            fecha_vencimiento=date(2027, 1, 1),
            periodicidad_meses=0,
        )
        id_guardado = self.repo.guardar_activo(activo)
        leido = self.repo.obtener_activo(id_guardado)

        self.assertIsInstance(leido, CDT)
        self.assertEqual(leido.tipo, "CDT")
        self.assertEqual(leido.valor_nominal, 1_000_000)
        self.assertEqual(leido.tasa, 0.12)
        self.assertEqual(leido.fecha_emision, date(2026, 1, 1))
        self.assertEqual(leido.fecha_vencimiento, date(2027, 1, 1))
        self.assertTrue(leido.es_renta_fija())

    def test_guardar_y_leer_bono(self):
        activo = Bono(
            nombre="Bono Ecopetrol",
            valor_nominal=100_000,
            tasa=0.10,
            fecha_emision=date(2026, 1, 1),
            fecha_vencimiento=date(2030, 1, 1),
            periodicidad_meses=6,
            tasa_mercado=0.11,
        )
        id_guardado = self.repo.guardar_activo(activo)
        leido = self.repo.obtener_activo(id_guardado)

        self.assertIsInstance(leido, Bono)
        self.assertEqual(leido.tipo, "BONO")
        self.assertEqual(leido.periodicidad_meses, 6)
        self.assertEqual(leido.tasa_mercado, 0.11)

    def test_guardar_y_leer_tes(self):
        activo = TES(
            nombre="TES 2032",
            valor_nominal=100_000,
            tasa=0.09,
            fecha_emision=date(2026, 1, 1),
            fecha_vencimiento=date(2032, 1, 1),
            periodicidad_meses=12,
        )
        id_guardado = self.repo.guardar_activo(activo)
        leido = self.repo.obtener_activo(id_guardado)

        self.assertIsInstance(leido, TES)
        self.assertEqual(leido.tipo, "TES")
        self.assertTrue(isinstance(leido, Bono))
        self.assertTrue(leido.es_renta_fija())

    def test_listar_activos_incluye_todos_los_tipos(self):
        self.repo.guardar_activo(Accion(nombre="Apple", ticker="AAPL", moneda="USD"))
        self.repo.guardar_activo(
            CDT(
                nombre="CDT",
                valor_nominal=1_000_000,
                tasa=0.12,
                fecha_emision=date(2026, 1, 1),
                fecha_vencimiento=date(2027, 1, 1),
            )
        )
        self.repo.guardar_activo(
            Bono(
                nombre="Bono",
                valor_nominal=100_000,
                tasa=0.1,
                fecha_emision=date(2026, 1, 1),
                fecha_vencimiento=date(2030, 1, 1),
                periodicidad_meses=6,
            )
        )
        self.repo.guardar_activo(
            TES(
                nombre="TES",
                valor_nominal=100_000,
                tasa=0.09,
                fecha_emision=date(2026, 1, 1),
                fecha_vencimiento=date(2032, 1, 1),
                periodicidad_meses=12,
            )
        )

        lista = self.repo.listar_activos()
        self.assertEqual(len(lista), 4)
        tipos = {a.tipo for a in lista}
        self.assertEqual(tipos, {"ACCION", "CDT", "BONO", "TES"})

    def test_guardar_y_leer_operacion(self):
        accion = Accion(nombre="Apple", ticker="AAPL", moneda="USD")
        self.repo.guardar_activo(accion)

        op = Operacion(
            activo_id=accion.id,
            tipo="COMPRA",
            fecha=date(2026, 3, 1),
            cantidad=10,
            precio=1500,
            comision=2000,
        )
        id_op = self.repo.guardar_operacion(op)
        self.assertEqual(op.id, id_op)

        leidas = self.repo.listar_operaciones(activo_id=accion.id)
        self.assertEqual(len(leidas), 1)
        self.assertEqual(leidas[0].tipo, "COMPRA")
        self.assertEqual(leidas[0].cantidad, 10)
        self.assertEqual(leidas[0].precio, 1500)
        self.assertEqual(leidas[0].flujo_neto, -17000)

    def test_operaciones_ordenadas_por_fecha(self):
        accion = Accion(nombre="Apple", ticker="AAPL", moneda="USD")
        self.repo.guardar_activo(accion)

        self.repo.guardar_operacion(
            Operacion(
                activo_id=accion.id,
                tipo="COMPRA",
                fecha=date(2026, 5, 1),
                cantidad=1,
                precio=100,
            )
        )
        self.repo.guardar_operacion(
            Operacion(
                activo_id=accion.id,
                tipo="COMPRA",
                fecha=date(2026, 3, 1),
                cantidad=1,
                precio=100,
            )
        )

        leidas = self.repo.listar_operaciones(activo_id=accion.id)
        self.assertEqual(leidas[0].fecha, date(2026, 3, 1))
        self.assertEqual(leidas[1].fecha, date(2026, 5, 1))

    def test_guardar_y_leer_flujo(self):
        accion = Accion(nombre="Apple", ticker="AAPL", moneda="USD")
        self.repo.guardar_activo(accion)

        flujo = FlujoCaja(
            activo_id=accion.id,
            tipo="DIVIDENDO",
            fecha=date(2026, 6, 1),
            valor_bruto=50_000,
            retencion=0.07,
        )
        id_fl = self.repo.guardar_flujo(flujo)
        self.assertEqual(flujo.id, id_fl)

        leidos = self.repo.listar_flujos(activo_id=accion.id)
        self.assertEqual(len(leidos), 1)
        self.assertEqual(leidos[0].tipo, "DIVIDENDO")
        self.assertAlmostEqual(leidos[0].valor_neto, 46_500)

    def test_eliminar_operacion_y_flujo(self):
        accion = Accion(nombre="Apple", ticker="AAPL", moneda="USD")
        self.repo.guardar_activo(accion)

        op = Operacion(
            activo_id=accion.id,
            tipo="VENTA",
            fecha=date(2026, 4, 1),
            cantidad=2,
            precio=2000,
            comision=100,
        )
        self.repo.guardar_operacion(op)

        fl = FlujoCaja(
            activo_id=accion.id,
            tipo="INTERES",
            fecha=date(2026, 4, 2),
            valor_bruto=10_000,
        )
        self.repo.guardar_flujo(fl)

        self.repo.eliminar_operacion(op.id)
        self.repo.eliminar_flujo(fl.id)

        self.assertEqual(self.repo.listar_operaciones(activo_id=accion.id), [])
        self.assertEqual(self.repo.listar_flujos(activo_id=accion.id), [])

    def test_guardar_precio_manual(self):
        self.repo.guardar_precio_manual("AAPL", date(2026, 3, 1), 1500)
        self.assertEqual(
            self.repo._precio_en_fecha("AAPL", date(2026, 3, 1)),
            1500,
        )

    def test_obtener_activo_inexistente(self):
        with self.assertRaises(ValueError):
            self.repo.obtener_activo(999)


if __name__ == "__main__":
    unittest.main()