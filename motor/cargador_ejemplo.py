"""
CargadorEjemplo: llena la base de datos con el portafolio de ejemplo del proyecto.

Acciones: Apple, Ecopetrol, Nike y Coca-Cola.
Renta fija: un CDT, un bono corporativo y un TES.

- El precio de cada compra/venta de acciones se toma del HISTORIAL REAL
  (ServicioPrecios.historial) en la fecha de la operación. Si no hay internet,
  se usa un precio de respaldo.
- Los DIVIDENDOS son los que realmente pagó cada empresa (ServicioPrecios.dividendos)
  × las acciones que se tenían ese día, con su retención en la fuente.
- Los INTERESES y el CAPITAL de renta fija salen del calendario de GeneradorFlujos.

Solo carga si la base de datos está vacía (para no duplicar datos).
Se ejecuta con:  py main.py --cargar-ejemplo
"""
from datetime import date

from modelos.accion import Accion
from modelos.bono import Bono
from modelos.cdt import CDT
from modelos.flujo_caja import FlujoCaja
from modelos.operacion import Operacion
from modelos.tes import TES
from motor.generador_flujos import GeneradorFlujos


class CargadorEjemplo:
    """Crea los activos, operaciones y flujos del portafolio de ejemplo."""

    RETENCION_RENTA_FIJA = 0.07   # retención en la fuente sobre rendimientos financieros

    # nombre, ticker, moneda, retención de dividendos, precio de respaldo (COP)
    ACCIONES = [
        ("Apple", "AAPL", "USD", 0.30, 950_000),
        ("Ecopetrol", "EC", "USD", 0.10, 40_000),
        ("Nike", "NKE", "USD", 0.30, 290_000),
        ("Coca-Cola", "KO", "USD", 0.30, 287_000),
    ]

    # ticker, tipo, fecha, cantidad, comisión (COP)
    OPERACIONES_ACCIONES = [
        ("AAPL", "COMPRA", date(2026, 1, 15), 10, 15_000),
        ("EC", "COMPRA", date(2026, 1, 20), 100, 12_000),
        ("NKE", "COMPRA", date(2026, 2, 10), 20, 12_000),
        ("KO", "COMPRA", date(2026, 2, 12), 30, 12_000),
        ("AAPL", "VENTA", date(2026, 8, 20), 3, 10_000),
    ]

    def __init__(self, repositorio, servicio_precios, hoy=None):
        self.repositorio = repositorio
        self.servicio_precios = servicio_precios
        self.hoy = hoy or date.today()
        self.generador = GeneradorFlujos()

    # ------------------------------------------------------------------
    def cargar(self):
        """Carga el ejemplo. Devuelve cuántos registros creó (0 si ya había datos)."""
        if self.repositorio.listar_activos():
            print("[ejemplo] La base de datos ya tiene activos: no se carga nada.")
            return 0
        creados = 0
        creados += self._cargar_acciones()
        creados += self._cargar_renta_fija()
        print(f"[ejemplo] Portafolio de ejemplo cargado: {creados} registros.")
        return creados

    # ------------------------------------------------------------------
    def _cargar_acciones(self):
        creados = 0
        ids = {}
        for nombre, ticker, moneda, _, _ in self.ACCIONES:
            ids[ticker] = self.repositorio.guardar_activo(Accion(nombre, ticker, moneda))
            creados += 1

        respaldo = {t: p for _, t, _, _, p in self.ACCIONES}
        for ticker, tipo, fecha, cantidad, comision in self.OPERACIONES_ACCIONES:
            precio = self._precio_historico(ticker, fecha)
            if precio is None:   # sin internet: precio de respaldo (la venta, 7 % más caro)
                precio = respaldo[ticker] * (1.07 if tipo == "VENTA" else 1.0)
            self.repositorio.guardar_operacion(
                Operacion(ids[ticker], tipo, fecha, cantidad, precio, comision))
            creados += 1

        for _, ticker, _, retencion, _ in self.ACCIONES:
            creados += self._cargar_dividendos(ids[ticker], ticker, retencion)
        return creados

    def _precio_historico(self, ticker, fecha):
        """Último cierre real en o antes de 'fecha' (None si no hay datos)."""
        df = self.servicio_precios.historial(ticker, date(fecha.year, 1, 1))
        if df is None or df.empty:
            return None
        anteriores = df[df["fecha"] <= fecha]
        if anteriores.empty:
            return None
        return float(anteriores.iloc[-1]["precio"])

    def _cantidad_en(self, ticker, fecha):
        """Acciones que se tenían de 'ticker' en esa fecha según las operaciones."""
        cantidad = 0
        for t, tipo, f, c, _ in self.OPERACIONES_ACCIONES:
            if t == ticker and f < fecha:
                cantidad += c if tipo == "COMPRA" else -c
        return cantidad

    def _cargar_dividendos(self, activo_id, ticker, retencion):
        primera = min(f for t, _, f, _, _ in self.OPERACIONES_ACCIONES if t == ticker)
        df = self.servicio_precios.dividendos(ticker, primera)
        creados = 0
        if df is None or df.empty:
            return 0
        for _, fila in df.iterrows():
            fecha = fila["fecha"]
            cantidad = self._cantidad_en(ticker, fecha)
            if fecha > self.hoy or cantidad <= 0:
                continue
            valor = float(fila["valor_por_accion"]) * cantidad
            self.repositorio.guardar_flujo(
                FlujoCaja(activo_id, "DIVIDENDO", fecha, valor, retencion))
            creados += 1
        return creados

    # ------------------------------------------------------------------
    def _cargar_renta_fija(self):
        titulos = [
            # (título, fecha de compra, cantidad, precio por título, comisión)
            (CDT("CDT Banco 360 días", 5_000_000, 0.105,
                 date(2026, 2, 2), date(2027, 2, 2), 0),
             date(2026, 2, 2), 1, 5_000_000, 0),
            (Bono("Bono corporativo 2029", 10_000_000, 0.11,
                  date(2024, 5, 15), date(2029, 5, 15), 6, 0.105),
             date(2026, 3, 10), 1, 10_150_000, 25_000),
            (TES("TES COP 2031", 1_000_000, 0.07,
                 date(2020, 3, 26), date(2031, 3, 26), 12, 0.112),
             date(2026, 4, 6), 5, 905_000, 18_000),
        ]
        creados = 0
        for titulo, fecha, cantidad, precio, comision in titulos:
            activo_id = self.repositorio.guardar_activo(titulo)
            self.repositorio.guardar_operacion(
                Operacion(activo_id, "COMPRA", fecha, cantidad, precio, comision))
            creados += 2
            # Cupones y capital ya cobrados entre la compra y hoy
            for f in self.generador.flujos(titulo, desde=fecha, hasta=self.hoy):
                retencion = self.RETENCION_RENTA_FIJA if f["tipo"] == "INTERES" else 0.0
                self.repositorio.guardar_flujo(
                    FlujoCaja(activo_id, f["tipo"], f["fecha"],
                              f["valor"] * cantidad, retencion))
                creados += 1
        return creados