"""
RepositorioMock: imita a datos.repositorio.Repositorio (contrato común).

Devuelve datos falsos en memoria para que motor/ e interfaz/ puedan
trabajar sin esperar la base de datos real. Los objetos son
SimpleNamespace con EXACTAMENTE los atributos del contrato, así el
código que los usa funciona igual con las clases reales de modelos/.

Se reemplaza en main.py por Repositorio() cuando datos/ esté listo.
"""
from datetime import date
from types import SimpleNamespace


class RepositorioMock:
    """Repositorio en memoria con un portafolio de ejemplo."""

    def __init__(self, ruta_db="portafolio.db"):
        self.ruta_db = ruta_db
        self._activos = {}
        self._operaciones = {}
        self._flujos = {}
        self._precios_manuales = {}
        self._siguiente_id = 1
        self._cargar_ejemplo()

    # ------------------------------------------------------------------
    # Constructores de objetos falsos (mismos atributos que modelos/)
    # ------------------------------------------------------------------
    @staticmethod
    def _accion(id_, nombre, ticker, moneda):
        return SimpleNamespace(
            id=id_, nombre=nombre, tipo="ACCION", ticker=ticker, moneda=moneda,
            es_renta_fija=lambda: False,
        )

    @staticmethod
    def _renta_fija(id_, nombre, tipo, valor_nominal, tasa, fecha_emision,
                    fecha_vencimiento, periodicidad_meses, tasa_mercado=None):
        return SimpleNamespace(
            id=id_, nombre=nombre, tipo=tipo, valor_nominal=valor_nominal,
            tasa=tasa, fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            periodicidad_meses=periodicidad_meses, tasa_mercado=tasa_mercado,
            es_renta_fija=lambda: True,
        )

    @staticmethod
    def _operacion(id_, activo_id, tipo, fecha, cantidad, precio, comision):
        valor_bruto = cantidad * precio
        if tipo == "COMPRA":
            flujo_neto = -(valor_bruto + comision)
        else:
            flujo_neto = valor_bruto - comision
        return SimpleNamespace(
            id=id_, activo_id=activo_id, tipo=tipo, fecha=fecha,
            cantidad=cantidad, precio=precio, comision=comision,
            valor_bruto=valor_bruto, flujo_neto=flujo_neto,
        )

    @staticmethod
    def _flujo(id_, activo_id, tipo, fecha, valor_bruto, retencion=0.0):
        return SimpleNamespace(
            id=id_, activo_id=activo_id, tipo=tipo, fecha=fecha,
            valor_bruto=valor_bruto, retencion=retencion,
            valor_neto=valor_bruto * (1 - retencion),
        )

    def _nuevo_id(self):
        nuevo = self._siguiente_id
        self._siguiente_id += 1
        return nuevo

    # ------------------------------------------------------------------
    # Portafolio de ejemplo
    # ------------------------------------------------------------------
    def _cargar_ejemplo(self):
        # Ticker de Ecopetrol solo ilustrativo: Josué debe verificar el real.
        activos = [
            self._accion(1, "Apple", "AAPL", "USD"),
            self._accion(2, "Ecopetrol", "ECOPETROL", "COP"),
            self._renta_fija(3, "CDT Banco 360 días", "CDT", 5_000_000, 0.105,
                             date(2026, 2, 2), date(2027, 2, 2), 0),
            self._renta_fija(4, "Bono corporativo 2029", "BONO", 10_000_000,
                             0.11, date(2024, 5, 15), date(2029, 5, 15), 6,
                             0.105),
            self._renta_fija(5, "TES COP 2031", "TES", 1_000_000, 0.07,
                             date(2020, 3, 26), date(2031, 3, 26), 12, 0.112),
            self._accion(6, "Nike", "NKE", "USD"),
            self._accion(7, "Coca-Cola", "KO", "USD"),
        ]
        for a in activos:
            self._activos[a.id] = a

        operaciones = [
            self._operacion(1, 1, "COMPRA", date(2026, 1, 15), 10, 950_000, 15_000),
            self._operacion(2, 2, "COMPRA", date(2026, 1, 20), 2_000, 2_150, 12_000),
            self._operacion(3, 3, "COMPRA", date(2026, 2, 2), 1, 5_000_000, 0),
            self._operacion(4, 4, "COMPRA", date(2026, 3, 10), 1, 10_150_000, 25_000),
            self._operacion(5, 5, "COMPRA", date(2026, 4, 6), 5, 905_000, 18_000),
            self._operacion(6, 1, "VENTA", date(2026, 8, 20), 3, 1_020_000, 10_000),
            self._operacion(7, 6, "COMPRA", date(2026, 2, 10), 20, 290_000, 12_000),
            self._operacion(8, 7, "COMPRA", date(2026, 2, 12), 30, 287_000, 12_000),
        ]
        for o in operaciones:
            self._operaciones[o.id] = o

        flujos = [
            self._flujo(1, 1, "DIVIDENDO", date(2026, 5, 15), 36_000, 0.30),
            self._flujo(2, 2, "DIVIDENDO", date(2026, 4, 28), 600_000, 0.10),
            self._flujo(3, 4, "INTERES", date(2026, 5, 15), 535_000, 0.04),
            self._flujo(4, 7, "DIVIDENDO", date(2026, 4, 1), 65_190, 0.30),
            self._flujo(5, 6, "DIVIDENDO", date(2026, 7, 1), 33_620, 0.30),
            self._flujo(6, 7, "DIVIDENDO", date(2026, 7, 1), 65_190, 0.30),
        ]
        for f in flujos:
            self._flujos[f.id] = f

        self._siguiente_id = 100

    # ------------------------------------------------------------------
    # Métodos del contrato
    # ------------------------------------------------------------------
    def guardar_activo(self, activo):
        if getattr(activo, "id", None) is None:
            activo.id = self._nuevo_id()
        self._activos[activo.id] = activo
        return activo.id

    def guardar_operacion(self, op):
        if getattr(op, "id", None) is None:
            op.id = self._nuevo_id()
        self._operaciones[op.id] = op
        return op.id

    def guardar_flujo(self, flujo):
        if getattr(flujo, "id", None) is None:
            flujo.id = self._nuevo_id()
        self._flujos[flujo.id] = flujo
        return flujo.id

    def eliminar_operacion(self, id):
        self._operaciones.pop(id, None)

    def eliminar_flujo(self, id):
        self._flujos.pop(id, None)

    def listar_activos(self):
        return list(self._activos.values())

    def obtener_activo(self, id):
        return self._activos.get(id)

    def listar_operaciones(self, activo_id=None):
        ops = [o for o in self._operaciones.values()
               if activo_id is None or o.activo_id == activo_id]
        return sorted(ops, key=lambda o: o.fecha)

    def listar_flujos(self, activo_id=None):
        fls = [f for f in self._flujos.values()
               if activo_id is None or f.activo_id == activo_id]
        return sorted(fls, key=lambda f: f.fecha)

    def guardar_precio_manual(self, ticker, fecha, precio):
        self._precios_manuales[(ticker, fecha)] = precio