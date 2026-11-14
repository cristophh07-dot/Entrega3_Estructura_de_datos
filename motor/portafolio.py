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
from motor.comision_broker import ComisionBroker
from motor.conversor_moneda import ConversorMoneda
from motor.extracto_movimientos import ExtractoMovimientos
from motor.generador_flujos import GeneradorFlujos
from motor.historial_accion import HistorialAccion
from motor.posicion import Posicion
from motor.valorador_renta_fija import ValoradorRentaFija
from motor.valorador_renta_variable import ValoradorRentaVariable


class Portafolio:
    """Consolida el portafolio: valor, posiciones, distribución y rentabilidad."""

    MONEDAS = ("COP", "USD")
    COLUMNAS_POSICIONES = ["activo_id", "nombre", "tipo", "cantidad", "costo_total",
                           "valor_actual", "ingresos", "ganancia", "rentabilidad",
                           "ganancia_no_realizada", "ganancia_realizada"]

    def __init__(self, repositorio, servicio_precios, fecha_corte=None, servicio_velas=None):
        """fecha_corte: fecha a la que se valora (hoy si no se indica; las pruebas la fijan).
        servicio_velas: opcional; da las velas diarias de cada acción para la vista de velas."""
        self.repositorio = repositorio
        self.servicio_precios = servicio_precios
        self.fecha_corte = fecha_corte
        self.generador = GeneradorFlujos()
        self.valorador_rv = ValoradorRentaVariable(servicio_precios)
        self.valorador_rf = ValoradorRentaFija(self.generador)
        self.calculadora = CalculadoraRentabilidad()
        self.conversor = ConversorMoneda(servicio_precios)
        self.comision_broker = ComisionBroker()
        self.servicio_velas = servicio_velas
        self.historial_accion = (HistorialAccion(servicio_velas, self.conversor)
                                 if servicio_velas is not None else None)
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
        if self.servicio_velas is not None:
            self.servicio_velas.limpiar_cache()
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

    def grafica_accion(self, activo_id, desde, moneda="USD"):
        """Datos de la gráfica de velas de una acción, desde 'desde' hasta hoy:
        {"velas", "agrupacion", "operaciones", "costo_promedio", "resumen", "moneda"}.
        Sin servicio de velas o sin datos, "velas" viene vacío."""
        self._validar(moneda)
        activo = next((a for a in self._activos if a.id == activo_id), None)
        if activo is None or activo.es_renta_fija():
            raise ValueError("La gráfica de velas es solo para acciones")
        if self.historial_accion is None:
            vacio = pd.DataFrame(columns=HistorialAccion.COLUMNAS)
            return {"velas": vacio, "agrupacion": "dia",
                    "operaciones": pd.DataFrame(columns=["fecha", "tipo", "cantidad", "precio"]),
                    "costo_promedio": None, "resumen": {}, "moneda": moneda}
        return self.historial_accion.grafica(activo, self._operaciones, desde, self.hoy, moneda)

    def extracto(self, activo_id):
        """Movimientos del activo fila por fila, con las columnas del Excel de referencia
        y el saldo acumulado: {"filas", "acciones", "saldo", "valor_actual", "total"} (en COP)."""
        activo = next((a for a in self._activos if a.id == activo_id), None)
        if activo is None:
            raise ValueError(f"No existe el activo {activo_id}")
        operaciones = [op for op in self._operaciones if op.fecha <= self.hoy]
        flujos = [f for f in self._flujos if f.fecha <= self.hoy]
        return ExtractoMovimientos(self.conversor).extracto(
            activo, operaciones, flujos, self._valores.get(activo_id, 0.0))

    def comision_sugerida(self, valor_operacion):
        """Comisión estándar en COP para una compra o venta de 'valor_operacion' pesos,
        y la frase que explica la regla aplicada: (comision, regla)."""
        return (self.comision_broker.comision(valor_operacion),
                self.comision_broker.regla(valor_operacion))

    def cantidad_disponible(self, activo_id, fecha=None):
        """Acciones o títulos que se tienen de un activo en 'fecha' (hoy si no se indica).
        Sirve para mostrar cuánto se puede vender."""
        fecha = fecha or self.hoy
        activo = next((a for a in self._activos if a.id == activo_id), None)
        if activo is None:
            return 0.0
        return Posicion(activo, self._operaciones, hasta=fecha).cantidad

    def precio_sugerido(self, activo, fecha=None):
        """Precio de mercado por unidad, en COP, para prellenar el formulario de operaciones.
        - Acción: último cierre en o antes de 'fecha' (hoy: precio actual).
        - CDT, bono o TES: su valor por título en esa fecha (causación o descuento).
        Devuelve None si no hay dato (sin internet, título vencido o fecha sin precios)."""
        fecha = fecha or self.hoy
        if activo.es_renta_fija():
            precio = self.valorador_rf.precio(activo, fecha)
            return precio if precio > 0 else None
        if fecha >= self.hoy:
            return self.valorador_rv.precio_actual(activo.ticker)
        if fecha >= self._inicio():   # mismo historial que usa la gráfica (ya descargado)
            return self.valorador_rv.precio_en_fecha(activo.ticker, fecha, self._inicio())
        df = self.servicio_precios.historial(activo.ticker, fecha - timedelta(days=10))
        if df is None or df.empty:
            return None
        anteriores = df[df["fecha"] <= fecha]
        return float(anteriores.iloc[-1]["precio"]) if not anteriores.empty else None
    
    def trm_en(self, fecha=None):
        """TRM (pesos por dólar) de una fecha; hoy si no se indica.
        La interfaz la usa para convertir a COP los precios que se escriben en USD."""
        return self.conversor.trm_en(fecha or self.hoy)
    
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
        """Totales y rentabilidad. La ganancia se separa en tres partes que suman exacto:
          ganancia = ganancia_no_realizada + ganancia_realizada + ingresos
          - no realizada: valor hoy − costo de lo que AÚN se tiene (valorización)
          - realizada:    lo recibido en ventas − lo que había costado lo vendido
          - ingresos:     dividendos e intereses netos de retención"""
        self._validar(moneda)
        operaciones, flujos = self._movimientos(moneda)
        valor_actual = sum(self._valores.values()) * self._factor_hoy(moneda)
        datos = self.calculadora.calcular(operaciones, flujos, valor_actual, self.hoy)
        posiciones = [Posicion(a, operaciones) for a in self._activos]
        costo_vigente = sum(p.costo_total for p in posiciones)
        datos["ganancia_realizada"] = sum(p.ganancia_realizada for p in posiciones)
        datos["ganancia_no_realizada"] = valor_actual - costo_vigente
        return datos

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
        """Una fila por activo que haya tenido compras (incluye los ya vendidos).
        La ganancia de cada activo se separa igual que en resumen():
          ganancia = ganancia_no_realizada + ganancia_realizada + ingresos"""
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
                "ganancia_no_realizada": valor - p.costo_total,
                "ganancia_realizada": p.ganancia_realizada,
            })
        return pd.DataFrame(filas, columns=self.COLUMNAS_POSICIONES)

    def serie_valor(self, desde=None, moneda="COP"):
        """Valor diario del portafolio desde 'desde' (o la primera compra) hasta hoy."""
        self._validar(moneda)
        desde = desde or self._inicio()
        filas = []
        dia = desde
        while dia <= self.hoy:
            if dia == self.hoy:   # el último punto es exactamente el "Valor actual" de las tarjetas
                total = sum(self._valores.values())
            else:
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