"""
CalculadoraRentabilidad: rentabilidad acumulada y rentabilidad efectiva anual (E.A.).

Todo sale de los FLUJOS DE DINERO con su fecha:
  - Compras  → salen  (negativos): −(cantidad × precio + comisión)
  - Ventas   → entran (positivos):   cantidad × precio − comisión
  - Dividendos, intereses y capital → entran (positivos), netos de retención
  - Valor actual del portafolio → se toma como si entrara HOY (positivo)

1. Rentabilidad acumulada (cuánto se ganó sobre lo invertido, sin importar el tiempo):
     R_acum = (valor_actual + ventas + ingresos − total_invertido) / total_invertido

2. Rentabilidad E.A. = TIR por fechas (XIRR): la tasa que hace cero
   el valor presente de todos los flujos:
     Σ  CF_j / (1 + EA) ^ ((t_j − t_0) / 365) = 0
   Se resuelve con scipy.optimize.brentq (busca la raíz en un intervalo).

Prueba de control: con UNA sola compra y sin ingresos,
   EA = (1 + R_acum) ^ (365 / días) − 1
"""
from datetime import date

from scipy.optimize import brentq


class CalculadoraRentabilidad:
    """Calcula los totales del portafolio, la rentabilidad acumulada y la E.A."""

    BASE_DIAS = 365
    TASA_MIN = -0.9999     # no se puede perder más del 100 %
    TASA_MAX = 100.0       # 10.000 % E.A. como techo de búsqueda

    # ------------------------------------------------------------------
    # Totales
    # ------------------------------------------------------------------
    @staticmethod
    def total_invertido(operaciones):
        return sum(op.cantidad * op.precio + op.comision
                   for op in operaciones if op.tipo == "COMPRA")

    @staticmethod
    def ventas_netas(operaciones):
        return sum(op.cantidad * op.precio - op.comision
                   for op in operaciones if op.tipo == "VENTA")

    @staticmethod
    def comisiones(operaciones):
        return sum(op.comision for op in operaciones)

    @staticmethod
    def ingresos_netos(flujos):
        return sum(f.valor_bruto * (1 - f.retencion) for f in flujos)

    # ------------------------------------------------------------------
    # Rentabilidad acumulada
    # ------------------------------------------------------------------
    @staticmethod
    def rentabilidad_acumulada(total_invertido, ventas, ingresos, valor_actual):
        if total_invertido <= 0:
            return 0.0
        return (valor_actual + ventas + ingresos - total_invertido) / total_invertido

    # ------------------------------------------------------------------
    # Rentabilidad E.A. (XIRR)
    # ------------------------------------------------------------------
    @staticmethod
    def flujos_de_caja(operaciones, flujos, valor_actual, fecha):
        """Lista de (fecha, monto) con el signo correcto, ordenada por fecha."""
        lista = []
        for op in operaciones:
            if op.tipo == "COMPRA":
                lista.append((op.fecha, -(op.cantidad * op.precio + op.comision)))
            else:
                lista.append((op.fecha, op.cantidad * op.precio - op.comision))
        for f in flujos:
            lista.append((f.fecha, f.valor_bruto * (1 - f.retencion)))
        if valor_actual > 0:
            lista.append((fecha, valor_actual))
        return sorted(lista, key=lambda x: x[0])

    def valor_presente(self, tasa, flujos_caja):
        """VPN de los flujos a una tasa E.A. (la función a la que se le busca el cero)."""
        t0 = flujos_caja[0][0]
        return sum(monto / (1 + tasa) ** ((f - t0).days / self.BASE_DIAS)
                   for f, monto in flujos_caja)

    def xirr(self, flujos_caja):
        """Tasa E.A. que hace VPN = 0. Devuelve None si no se puede calcular."""
        montos = [m for _, m in flujos_caja]
        if not any(m < 0 for m in montos) or not any(m > 0 for m in montos):
            return None            # se necesita al menos una salida y una entrada
        if (flujos_caja[-1][0] - flujos_caja[0][0]).days == 0:
            return None            # todo el mismo día: no hay tiempo para anualizar
        f = lambda r: self.valor_presente(r, flujos_caja)
        try:
            return brentq(f, self.TASA_MIN, self.TASA_MAX)
        except ValueError:         # la función no cambia de signo en el intervalo
            return None

    # ------------------------------------------------------------------
    # Todo junto (lo usa Portafolio.resumen)
    # ------------------------------------------------------------------
    def calcular(self, operaciones, flujos, valor_actual, fecha=None):
        fecha = fecha or date.today()
        invertido = self.total_invertido(operaciones)
        ventas = self.ventas_netas(operaciones)
        ingresos = self.ingresos_netos(flujos)
        ganancia = valor_actual + ventas + ingresos - invertido
        ea = self.xirr(self.flujos_de_caja(operaciones, flujos, valor_actual, fecha))
        return {
            "total_invertido": invertido,
            "ventas": ventas,
            "ingresos": ingresos,
            "comisiones": self.comisiones(operaciones),
            "valor_actual": valor_actual,
            "ganancia": ganancia,
            "rentabilidad_acumulada": self.rentabilidad_acumulada(
                invertido, ventas, ingresos, valor_actual),
            "rentabilidad_ea": ea if ea is not None else 0.0,
        }