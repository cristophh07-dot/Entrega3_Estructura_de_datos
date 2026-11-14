"""
ServicioVelas: precios diarios de apertura, máximo, mínimo y cierre (velas japonesas)
de una acción, descargados de Yahoo Finance con yfinance.

Los precios se entregan en la MONEDA ORIGINAL del ticker (USD para AAPL, NKE, KO, EC):
la conversión a pesos la hace el motor con la TRM de cada día (ConversorMoneda),
así cada vela queda convertida con la TRM correcta de su fecha.
"""
from datetime import date

import pandas as pd
import yfinance as yf


class ServicioVelas:
    """Descarga y guarda en memoria las velas diarias de cada ticker."""

    COLUMNAS = ["fecha", "apertura", "maximo", "minimo", "cierre"]

    def __init__(self):
        self._cache = {}   # ticker -> (desde, DataFrame)

    def velas(self, ticker: str, desde: date) -> pd.DataFrame:
        """Velas diarias desde 'desde' hasta hoy. DataFrame vacío si no hay datos o falla la descarga."""
        vacio = pd.DataFrame(columns=self.COLUMNAS)
        if not isinstance(ticker, str) or not ticker.strip() or not isinstance(desde, date):
            return vacio
        ticker = ticker.strip().upper()

        guardado = self._cache.get(ticker)
        if guardado is not None and guardado[0] <= desde:
            df = guardado[1]
            return df[df["fecha"] >= desde].reset_index(drop=True)

        try:
            datos = yf.Ticker(ticker).history(start=desde.isoformat(), auto_adjust=False)
        except Exception:   # sin internet, ticker inválido, Yahoo caído...
            return vacio
        if datos is None or datos.empty:
            return vacio

        filas = []
        for indice, fila in datos.iterrows():
            apertura, maximo = float(fila["Open"]), float(fila["High"])
            minimo, cierre = float(fila["Low"]), float(fila["Close"])
            if min(apertura, maximo, minimo, cierre) <= 0:
                continue   # día sin negociación o dato dañado
            dia = indice.date() if hasattr(indice, "date") else date.fromisoformat(str(indice)[:10])
            filas.append({"fecha": dia, "apertura": apertura, "maximo": maximo,
                          "minimo": minimo, "cierre": cierre})
        if not filas:
            return vacio
        df = pd.DataFrame(filas, columns=self.COLUMNAS)
        self._cache[ticker] = (desde, df)
        return df

    def limpiar_cache(self) -> None:
        """Se llama al actualizar precios, para volver a descargar."""
        self._cache.clear()
