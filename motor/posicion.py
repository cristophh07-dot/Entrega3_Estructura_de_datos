"""
Posicion: estado de la tenencia de UN activo a partir de sus operaciones.

Método de costo: PROMEDIO PONDERADO.
- En cada COMPRA el costo total sube por (cantidad × precio + comisión):
  la comisión de compra es parte de lo que costó el activo.
- En cada VENTA se saca del costo total la parte proporcional a lo vendido
  (costo promedio × cantidad vendida). El costo promedio NO cambia al vender.
  La ganancia realizada es lo que se recibió neto de comisión menos ese costo.

Ejemplo:
  compra 10 a 100 con comisión 20  → costo_total 1.020, promedio 102
  vende   4 a 130 con comisión 10  → recibe 510, costo vendido 408,
                                     ganancia realizada 102, quedan 6 con costo 612
"""


class Posicion:
    """Tenencia de un activo: cantidad, costo y ganancia realizada."""

    TOLERANCIA = 1e-9

    def __init__(self, activo, operaciones, hasta=None):
        """
        activo: objeto con atributo id (Accion, CDT, Bono o TES).
        operaciones: operaciones del portafolio (se filtran las de este activo).
        hasta: date opcional; solo cuenta operaciones hasta esa fecha
               (lo usa Portafolio.serie_valor para reconstruir el pasado).
        """
        self.activo = activo
        self.cantidad = 0.0
        self.costo_total = 0.0          # costo de lo que AÚN se tiene
        self.total_invertido = 0.0      # todo lo pagado en compras (+ comisiones)
        self.ventas_netas = 0.0         # todo lo recibido en ventas (− comisiones)
        self.comisiones = 0.0
        self.ganancia_realizada = 0.0
        self.fecha_primera_compra = None

        propias = [op for op in operaciones
                   if op.activo_id == activo.id
                   and (hasta is None or op.fecha <= hasta)]
        for op in sorted(propias, key=lambda o: o.fecha):
            self._aplicar(op)

    # ------------------------------------------------------------------
    def _aplicar(self, op):
        if op.tipo == "COMPRA":
            self._comprar(op)
        elif op.tipo == "VENTA":
            self._vender(op)
        else:
            raise ValueError(f"Tipo de operación desconocido: {op.tipo}")

    def _comprar(self, op):
        pagado = op.cantidad * op.precio + op.comision
        self.cantidad += op.cantidad
        self.costo_total += pagado
        self.total_invertido += pagado
        self.comisiones += op.comision
        if self.fecha_primera_compra is None:
            self.fecha_primera_compra = op.fecha

    def _vender(self, op):
        if op.cantidad > self.cantidad + self.TOLERANCIA:
            raise ValueError(
                f"Venta de {op.cantidad} en {op.fecha} supera la cantidad "
                f"disponible ({self.cantidad}) de {getattr(self.activo, 'nombre', self.activo.id)}"
            )
        costo_vendido = self.costo_promedio * op.cantidad
        recibido = op.cantidad * op.precio - op.comision

        self.ganancia_realizada += recibido - costo_vendido
        self.ventas_netas += recibido
        self.comisiones += op.comision
        self.cantidad -= op.cantidad
        self.costo_total -= costo_vendido

        if self.cantidad < self.TOLERANCIA:   # se vendió todo: limpia residuos
            self.cantidad = 0.0
            self.costo_total = 0.0

    # ------------------------------------------------------------------
    @property
    def costo_promedio(self):
        """Costo por unidad de lo que se tiene (0 si no hay unidades)."""
        if self.cantidad <= 0:
            return 0.0
        return self.costo_total / self.cantidad

    @property
    def esta_abierta(self):
        return self.cantidad > 0

    def ganancia_no_realizada(self, valor_actual):
        """Ganancia "en papel": valor de mercado de lo que se tiene − su costo."""
        return valor_actual - self.costo_total

    def __repr__(self):
        return (f"Posicion(activo={self.activo.id}, cantidad={self.cantidad:g}, "
                f"costo_total={self.costo_total:,.2f}, "
                f"ganancia_realizada={self.ganancia_realizada:,.2f})")