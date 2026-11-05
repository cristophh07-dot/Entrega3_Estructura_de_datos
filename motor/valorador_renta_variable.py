"""
ValoradorRentaVariable: valor de mercado de las posiciones en acciones.

valor = cantidad que se tiene × precio de mercado (en COP).
El precio lo da ServicioPrecios (que ya convierte USD → COP con la TRM
y, si no hay internet, devuelve el último precio guardado o el manual).
"""


class ValoradorRentaVariable:
    """Valora acciones con el precio actual o con el de una fecha pasada."""

    def __init__(self, servicio_precios):
        self.servicio_precios = servicio_precios
        self._cache_actual = {}      # ticker -> precio, para no pedirlo dos veces
        self._cache_historial = {}   # ticker -> {fecha: precio}
        self.sin_precio = []         # tickers que no se pudieron valorar

    def limpiar_cache(self):
        """Se llama en Portafolio.actualizar() para traer precios nuevos."""
        self._cache_actual.clear()
        self._cache_historial.clear()
        self.sin_precio.clear()

    def precio_actual(self, ticker):
        if ticker not in self._cache_actual:
            self._cache_actual[ticker] = self.servicio_precios.precio_actual(ticker)
        return self._cache_actual[ticker]

    def valor(self, posicion):
        """Valor de mercado hoy. Si no hay precio, usa el costo y lo registra."""
        if not posicion.esta_abierta:
            return 0.0
        ticker = posicion.activo.ticker
        precio = self.precio_actual(ticker)
        if precio is None:
            if ticker not in self.sin_precio:
                self.sin_precio.append(ticker)
            return posicion.costo_total   # sin precio: no inventa ganancia
        return posicion.cantidad * precio

    def precio_en_fecha(self, ticker, fecha, desde):
        """Último precio de cierre en o antes de 'fecha' (para la serie histórica)."""
        if ticker not in self._cache_historial:
            df = self.servicio_precios.historial(ticker, desde)
            self._cache_historial[ticker] = dict(zip(df["fecha"], df["precio"]))
        precios = self._cache_historial[ticker]
        anteriores = [f for f in precios if f <= fecha]
        if not anteriores:
            return None
        return precios[max(anteriores)]