"""
Portafolio: junta todas las piezas del motor y entrega los resultados a la interfaz.

  Repositorio ──► activos, operaciones, flujos (todo guardado en COP)
                      │
                      ▼
                 Posicion (una por activo: cantidad, costo, ganancia realizada)
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
  ValoradorRentaVariable      ValoradorRentaFija ◄── GeneradorFlujos
  (acciones a precio          (CDT por causación,
   de mercado)                 bonos y TES por descuento)
        └─────────────┬─────────────┘
                      ▼
            CalculadoraRentabilidad ──► resumen(): acumulada y E.A.
                      ▲
            ConversorMoneda (si se pide moneda="USD": cada movimiento
                             se convierte con la TRM de su fecha)

Métodos del contrato que usa la interfaz (todos aceptan moneda="COP" o "USD"):
  actualizar(), resumen(), distribucion(), posiciones(),
  serie_valor(desde), proximos_flujos(dias)
"""
from datetime import date, timedelta
from types import SimpleNamespace

import pandas as pd

from motor.calculadora_rentabilidad import CalculadoraRentabilidad
from motor.conversor_moneda import ConversorMoneda
from motor.generador_flujos import GeneradorFlujos
from motor.posicion import Posicion
from motor.valorador_renta_fija import ValoradorRentaFija
from motor.valorador_renta_variable import ValoradorRentaVariable


class Portafolio:
    """Consolida el portafolio: valor, posiciones, distribución y rentabilidad."""

    MONEDAS = ("COP", "USD")
    COLUMNAS_POSICIONES = ["activo_id", "nombre", "tipo", "cantidad", "costo_total",
                           "valor_actual", "ingresos", "ganancia", "rentabilidad"]

    def __init__(self, repositorio, servicio_precios, fecha_corte=None):
        """fecha_corte: fecha a la que se valora (hoy si no se indica; las pruebas la fijan)."""
        self.repositorio = repositorio
        self.servicio_precios = servicio_precios
        self.fecha_corte = fecha_corte
        self.generador = GeneradorFlujos()
        self.valorador_rv = ValoradorRentaVariable(servicio_precios)
        self.valorador_rf = ValoradorRentaFija(self.generador)
        self.calculadora = CalculadoraRentabilidad()
        self.conversor = ConversorMoneda(servicio_precios)
        self.actualizar()

    # ------------------------------------------------------------------
    @property
    def hoy(self):
        return self.fecha_corte or date.today()

    @property
    def avisos(self):
        """Tickers sin precio de mercado (la interfaz puede mostrarlos)."""
        return list(self.valorador_rv.sin_precio)

    def actualizar(self):
        """Vuelve a leer todo del repositorio y recalcula. Se llama tras guardar algo."""
        self.valorador_rv.limpiar_cache()
        self.conversor.limpiar_cache()
        self._activos = self.repositorio.listar_activos()
        self._operaciones = self.repositorio.listar_operaciones()
        self._flujos = self.repositorio.listar_flujos()
        self.conversor.cargar(self._inicio())
        self._posiciones = {a.id: Posicion(a, self._operaciones, hasta=self.hoy)
                            for a in self._activos}
        self._valores = {a.id: self._valorar(self._posiciones[a.id])
                         for a in self._activos}

    def _valorar(self, posicion, fecha=None):
        """Valor en COP de una posición hoy (o en una fecha pasada, para la serie)."""
        activo = posicion.activo
        if activo.es_renta_fija():
            return self.valorador_rf.valor(posicion, fecha or self.hoy)
        if fecha is None:
            return self.valorador_rv.valor(posicion)
        if not posicion.esta_abierta:
            return 0.0
        precio = self.valorador_rv.precio_en_fecha(activo.ticker, fecha, self._inicio())
        if precio is None:
            return posicion.costo_total
        return posicion.cantidad * precio

    def _inicio(self):
        """Fecha de la primera operación (o hoy si no hay ninguna)."""
        return min((op.fecha for op in self._operaciones), default=self.hoy)

    # ------------------------------------------------------------------
    # Moneda
    # ------------------------------------------------------------------
    def _validar(self, moneda):
        if moneda not in self.MONEDAS:
            raise ValueError(f"moneda debe ser 'COP' o 'USD' (recibido: {moneda!r})")

    def _factor_hoy(self, moneda):
        """Multiplica un valor de HOY en COP para pasarlo a la moneda pedida."""
        return 1.0 if moneda == "COP" else 1 / self.conversor.trm_en(self.hoy)

    def _movimientos(self, moneda):
        """Operaciones y flujos hasta hoy, en la moneda pedida.
        En USD cada uno se convierte con la TRM de SU fecha."""
        ops = [op for op in self._operaciones if op.fecha <= self.hoy]
        fls = [f for f in self._flujos if f.fecha <= self.hoy]
        if moneda == "COP":
            return ops, fls
        c = self.conversor
        ops_usd = [SimpleNamespace(id=op.id, activo_id=op.activo_id, tipo=op.tipo,
                                   fecha=op.fecha, cantidad=op.cantidad,
                                   precio=c.a_usd(op.precio, op.fecha),
                                   comision=c.a_usd(op.comision, op.fecha))
                   for op in ops]
        fls_usd = [SimpleNamespace(id=f.id, activo_id=f.activo_id, tipo=f.tipo,
                                   fecha=f.fecha, retencion=f.retencion,
                                   valor_bruto=c.a_usd(f.valor_bruto, f.fecha))
                   for f in fls]
        return ops_usd, fls_usd

    # ------------------------------------------------------------------
    # Métodos del contrato
    # ------------------------------------------------------------------
    def resumen(self, moneda="COP"):
        self._validar(moneda)
        operaciones, flujos = self._movimientos(moneda)
        valor_actual = sum(self._valores.values()) * self._factor_hoy(moneda)
        return self.calculadora.calcular(operaciones, flujos, valor_actual, self.hoy)

    def distribucion(self, moneda="COP"):
        self._validar(moneda)
        f = self._factor_hoy(moneda)
        rf = sum(self._valores[a.id] for a in self._activos if a.es_renta_fija()) * f
        rv = sum(self._valores[a.id] for a in self._activos if not a.es_renta_fija()) * f
        total = rf + rv
        return {
            "renta_fija": {"valor": rf, "porcentaje": rf / total if total else 0.0},
            "renta_variable": {"valor": rv, "porcentaje": rv / total if total else 0.0},
        }

    def posiciones(self, moneda="COP"):
        """Una fila por activo que haya tenido compras (incluye los ya vendidos)."""
        self._validar(moneda)
        operaciones, flujos = self._movimientos(moneda)
        f = self._factor_hoy(moneda)
        filas = []
        for a in self._activos:
            p = Posicion(a, operaciones)
            if p.total_invertido <= 0:
                continue
            valor = self._valores[a.id] * f
            ingresos = self.calculadora.ingresos_netos(
                [x for x in flujos if x.activo_id == a.id])
            # ganancia = lo que vale + lo que ya entró (ventas y flujos) − lo que se pagó
            ganancia = valor + p.ventas_netas + ingresos - p.total_invertido
            filas.append({
                "activo_id": a.id, "nombre": a.nombre, "tipo": a.tipo,
                "cantidad": p.cantidad, "costo_total": p.costo_total,
                "valor_actual": valor, "ingresos": ingresos, "ganancia": ganancia,
                "rentabilidad": ganancia / p.total_invertido,
            })
        return pd.DataFrame(filas, columns=self.COLUMNAS_POSICIONES)

    def serie_valor(self, desde=None, moneda="COP"):
        """Valor diario del portafolio desde 'desde' (o la primera compra) hasta hoy."""
        self._validar(moneda)
        desde = desde or self._inicio()
        filas = []
        dia = desde
        while dia <= self.hoy:
            total = sum(self._valorar(Posicion(a, self._operaciones, hasta=dia), dia)
                        for a in self._activos)
            if moneda == "USD":
                total = self.conversor.a_usd(total, dia)
            filas.append({"fecha": dia, "valor": total})
            dia += timedelta(days=1)
        return pd.DataFrame(filas, columns=["fecha", "valor"])

    def proximos_flujos(self, dias=90, moneda="COP"):
        """Cupones y capital de renta fija que se van a recibir en los próximos días.
        En USD se usa la TRM de hoy (la futura no se conoce)."""
        self._validar(moneda)
        f = self._factor_hoy(moneda)
        limite = self.hoy + timedelta(days=dias)
        filas = []
        for a in self._activos:
            p = self._posiciones[a.id]
            if not a.es_renta_fija() or not p.esta_abierta:
                continue
            for flujo in self.generador.flujos(a, desde=self.hoy, hasta=limite):
                filas.append({"fecha": flujo["fecha"], "nombre": a.nombre,
                              "tipo": flujo["tipo"], "valor": flujo["valor"] * p.cantidad * f})
        filas.sort(key=lambda x: x["fecha"])
        return pd.DataFrame(filas, columns=["fecha", "nombre", "tipo", "valor"])