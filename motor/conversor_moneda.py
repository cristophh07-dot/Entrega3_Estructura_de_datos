"""
ConversorMoneda: pasa valores de pesos (COP) a dólares (USD) con la TRM de cada fecha.

Todo el sistema guarda el dinero en COP. Para ver la rentabilidad en USD,
cada movimiento se convierte con la TRM del DÍA en que ocurrió:

    valor en USD = valor en COP / TRM de esa fecha

La TRM se toma del historial del ticker "COP=X" (pesos por dólar) que da
ServicioPrecios. Si una fecha no tiene TRM (fin de semana, festivo), se usa
la del último día hábil anterior. Si no hay historial (sin internet), se usa
la TRM actual para todo.
"""
from bisect import bisect_right
from datetime import date


class ConversorMoneda:
    """Convierte COP → USD usando la TRM histórica."""

    TICKER_TRM = "COP=X"

    def __init__(self, servicio_precios):
        self.servicio_precios = servicio_precios
        self._fechas = []     # fechas ordenadas con TRM conocida
        self._trms = []       # TRM de cada una de esas fechas
        self._trm_actual = None

    def limpiar_cache(self):
        self._fechas, self._trms, self._trm_actual = [], [], None

    def cargar(self, desde):
        """Descarga una sola vez el historial de la TRM desde 'desde'."""
        df = self.servicio_precios.historial(self.TICKER_TRM, desde)
        if df is not None and not df.empty:
            pares = sorted(zip(df["fecha"], df["precio"]))
            self._fechas = [f for f, _ in pares]
            self._trms = [float(t) for _, t in pares]

    def trm_actual(self):
        if self._trm_actual is None:
            self._trm_actual = float(self.servicio_precios.trm_actual())
        return self._trm_actual

    def trm_en(self, fecha):
        """TRM del último día con dato en o antes de 'fecha'."""
        i = bisect_right(self._fechas, fecha)
        if i == 0:                       # no hay historial antes de esa fecha
            return self.trm_actual()
        return self._trms[i - 1]

    def a_usd(self, valor_cop, fecha=None):
        return valor_cop / self.trm_en(fecha or date.today())