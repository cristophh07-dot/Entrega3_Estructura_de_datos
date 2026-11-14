"""
CargadorEjemplo: llena la base de datos con el portafolio de ejemplo del proyecto.

Acciones: Apple, Ecopetrol, Nike y Coca-Cola.
Renta fija: un CDT, un bono corporativo y un TES.

Sigue la misma lógica del Excel de referencia (Prueba_portafolio.xlsx):
- Precio en COP de cada compra/venta = precio en USD de ese día × TRM de ese día.
- Dividendo en COP = dividendo por acción en USD × TRM de ese día × acciones que se tenían.
- Comisión = 0,2 % del valor de la operación (ComisionBroker), al comprar y al vender.
- Sin retención en la fuente (el Excel no descuenta impuestos; si se quiere, se registra
  la retención al anotar el dividendo en la sección Flujos).
- Los INTERESES y el CAPITAL de renta fija salen del calendario de GeneradorFlujos.

Los precios y dividendos en USD vienen de ServicioVelas (Yahoo Finance) y la TRM
histórica de ConversorMoneda. Sin internet se usan precios de respaldo.

Solo carga si la base de datos está vacía (para no duplicar datos).
Se ejecuta con:  py main.py --cargar-ejemplo
"""
from datetime import date, timedelta

from modelos.accion import Accion
from modelos.bono import Bono
from modelos.cdt import CDT
from modelos.flujo_caja import FlujoCaja
from modelos.operacion import Operacion
from modelos.tes import TES
from motor.comision_broker import ComisionBroker
from motor.conversor_moneda import ConversorMoneda
from motor.generador_flujos import GeneradorFlujos


class CargadorEjemplo:
    """Crea los activos, operaciones y flujos del portafolio de ejemplo."""

    RETENCION = 0.0   # como en el Excel: sin retención en la fuente

    # nombre, ticker, moneda, precio de respaldo en USD (si no hay internet)
    ACCIONES = [
        ("Apple", "AAPL", "USD", 230.0),
        ("Ecopetrol", "EC", "USD", 11.0),
        ("Nike", "NKE", "USD", 70.0),
        ("Coca-Cola", "KO", "USD", 70.0),
    ]

    # ticker, tipo, fecha, cantidad
    OPERACIONES_ACCIONES = [
        ("AAPL", "COMPRA", date(2026, 1, 15), 10),
        ("EC", "COMPRA", date(2026, 1, 20), 100),
        ("NKE", "COMPRA", date(2026, 2, 10), 20),
        ("KO", "COMPRA", date(2026, 2, 12), 30),
        ("AAPL", "VENTA", date(2026, 8, 20), 3),
    ]

    def __init__(self, repositorio, servicio_precios, hoy=None, servicio_velas=None):
        self.repositorio = repositorio
        self.servicio_precios = servicio_precios
        self.servicio_velas = servicio_velas
        self.hoy = hoy or date.today()
        self.generador = GeneradorFlujos()
        self.comisiones = ComisionBroker()
        self.conversor = ConversorMoneda(servicio_precios)
        self.conversor.cargar(min(f for _, _, f, _ in self.OPERACIONES_ACCIONES))

    # ------------------------------------------------------------------
    def cargar(self):
        """Carga el ejemplo. Devuelve cuántos registros creó (0 si ya había datos)."""
        if self.repositorio.listar_activos():
            print("[ejemplo] La base de datos ya tiene activos: no se carga nada.")
            return 0
        creados = self._cargar_acciones() + self._cargar_renta_fija()
        print(f"[ejemplo] Portafolio de ejemplo cargado: {creados} registros.")
        return creados

    # ------------------------------------------------------------------ acciones
    def _cargar_acciones(self):
        creados = 0
        ids, monedas, respaldo = {}, {}, {}
        for nombre, ticker, moneda, precio_respaldo in self.ACCIONES:
            ids[ticker] = self.repositorio.guardar_activo(Accion(nombre, ticker, moneda))
            monedas[ticker], respaldo[ticker] = moneda, precio_respaldo
            creados += 1

        for ticker, tipo, fecha, cantidad in self.OPERACIONES_ACCIONES:
            precio_original = self._cierre(ticker, fecha)
            if precio_original is None:   # sin internet: respaldo (la venta, 7 % más caro)
                precio_original = respaldo[ticker] * (1.07 if tipo == "VENTA" else 1.0)
            precio_cop = self._a_pesos(precio_original, monedas[ticker], fecha)   # USD × TRM del día
            comision = self.comisiones.comision(cantidad * precio_cop)             # 0,2 %
            self.repositorio.guardar_operacion(
                Operacion(ids[ticker], tipo, fecha, cantidad, precio_cop, comision))
            creados += 1

        for _, ticker, moneda, _ in self.ACCIONES:
            creados += self._cargar_dividendos(ids[ticker], ticker, moneda)
        return creados

    def _a_pesos(self, valor, moneda, fecha):
        return valor * self.conversor.trm_en(fecha) if moneda == "USD" else valor

    def _cierre(self, ticker, fecha):
        """Precio de cierre en la moneda original del último día de bolsa en o antes de 'fecha'."""
        if self.servicio_velas is None:
            return None
        velas = self.servicio_velas.velas(ticker, fecha - timedelta(days=10))
        if velas is None or velas.empty:
            return None
        anteriores = velas[velas["fecha"] <= fecha]
        return float(anteriores.iloc[-1]["cierre"]) if not anteriores.empty else None

    def _cantidad_en(self, ticker, fecha):
        """Acciones que se tenían de 'ticker' antes de 'fecha' (como la columna Acciones del Excel)."""
        cantidad = 0
        for t, tipo, f, c in self.OPERACIONES_ACCIONES:
            if t == ticker and f < fecha:
                cantidad += c if tipo == "COMPRA" else -c
        return cantidad

    def _cargar_dividendos(self, activo_id, ticker, moneda):
        """Dividendo en COP = dividendo por acción (moneda original) × TRM del día × acciones."""
        if self.servicio_velas is None or not hasattr(self.servicio_velas, "dividendos"):
            return 0
        primera = min(f for t, _, f, _ in self.OPERACIONES_ACCIONES if t == ticker)
        df = self.servicio_velas.dividendos(ticker, primera)
        creados = 0
        for _, fila in df.iterrows():
            fecha = fila["fecha"]
            cantidad = self._cantidad_en(ticker, fecha)
            if fecha > self.hoy or cantidad <= 0:
                continue
            por_accion_cop = self._a_pesos(float(fila["valor_por_accion"]), moneda, fecha)
            self.repositorio.guardar_flujo(
                FlujoCaja(activo_id, "DIVIDENDO", fecha, por_accion_cop * cantidad, self.RETENCION))
            creados += 1
        return creados

    # ------------------------------------------------------------------ renta fija
    def _cargar_renta_fija(self):
        titulos = [
            # (título, fecha de compra, cantidad, precio por título)
            (CDT("CDT Banco 360 días", 5_000_000, 0.105,
                 date(2026, 2, 2), date(2027, 2, 2), 0),
             date(2026, 2, 2), 1, 5_000_000),
            (Bono("Bono corporativo 2029", 10_000_000, 0.11,
                  date(2024, 5, 15), date(2029, 5, 15), 6, 0.105),
             date(2026, 3, 10), 1, 10_150_000),
            (TES("TES COP 2031", 1_000_000, 0.07,
                 date(2020, 3, 26), date(2031, 3, 26), 12, 0.112),
             date(2026, 4, 6), 5, 905_000),
        ]
        creados = 0
        for titulo, fecha, cantidad, precio in titulos:
            activo_id = self.repositorio.guardar_activo(titulo)
            # El CDT se abre directo en el banco, sin comisión; bono y TES pagan el 0,2 %
            comision = 0.0 if titulo.tipo == "CDT" else self.comisiones.comision(cantidad * precio)
            self.repositorio.guardar_operacion(
                Operacion(activo_id, "COMPRA", fecha, cantidad, precio, comision))
            creados += 2
            # Cupones y capital ya cobrados entre la compra y hoy
            for f in self.generador.flujos(titulo, desde=fecha, hasta=self.hoy):
                self.repositorio.guardar_flujo(
                    FlujoCaja(activo_id, f["tipo"], f["fecha"], f["valor"] * cantidad, self.RETENCION))
                creados += 1
        return creados
