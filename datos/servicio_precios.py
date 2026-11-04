
from datetime import date

import pandas as pd
import yfinance as yf

from datos.repositorio import Repositorio
from modelos.accion import Accion


class ServicioPrecios:

    TICKER_TRM = "COP=X"

    def __init__(self, repositorio: Repositorio) -> None:
        self.repositorio = repositorio

    def trm_actual(self) -> float:
        hoy = date.today()
        en_cache = self.repositorio._precio_en_fecha(self.TICKER_TRM, hoy)
        if en_cache is not None:
            return en_cache

        try:
            trm = self._descargar_ultimo_cierre(self.TICKER_TRM)
            if trm is not None and trm > 0:
                self.repositorio._guardar_precio(
                    self.TICKER_TRM, hoy, trm, "yfinance"
                )
                return trm
        except Exception:
            pass

        ultimo = self.repositorio._ultimo_precio(self.TICKER_TRM)
        if ultimo is not None:
            return ultimo[1]
        raise ValueError("no se pudo obtener la TRM (COP=X)")

    def precio_actual(self, ticker: str) -> float | None:
        if not isinstance(ticker, str) or not ticker.strip():
            return None
        ticker = ticker.strip().upper()
        hoy = date.today()

        en_cache = self.repositorio._precio_en_fecha(ticker, hoy)
        if en_cache is not None:
            return en_cache

        try:
            crudo = self._descargar_ultimo_cierre(ticker)
            if crudo is None or crudo <= 0:
                raise ValueError("sin cierre")
            precio_cop = self._a_cop(ticker, crudo)
            if precio_cop is None or precio_cop <= 0:
                raise ValueError("sin conversion")
            self.repositorio._guardar_precio(ticker, hoy, precio_cop, "yfinance")
            return precio_cop
        except Exception:
            ultimo = self.repositorio._ultimo_precio(ticker)
            if ultimo is not None:
                return ultimo[1]
            return None

    def historial(self, ticker: str, desde: date) -> pd.DataFrame:

        vacio = pd.DataFrame(columns=["fecha", "precio"])
        if not isinstance(ticker, str) or not ticker.strip():
            return vacio
        if type(desde) is not date:
            return vacio
        ticker = ticker.strip().upper()

        try:
            datos = yf.Ticker(ticker).history(
                start=desde.isoformat(),
                auto_adjust=False,
            )
            if datos is None or datos.empty:
                return vacio

            moneda = self._moneda_ticker(ticker)
            if moneda not in ("COP", "USD"):
                return vacio

            trm = self.trm_actual() if moneda == "USD" else None
            filas = []
            for indice, fila in datos.iterrows():
                cierre = float(fila["Close"])
                if cierre <= 0:
                    continue
                if moneda == "USD":
                    cierre = cierre * trm
                dia = (
                    indice.date()
                    if hasattr(indice, "date")
                    else date.fromisoformat(str(indice)[:10])
                )
                filas.append({"fecha": dia, "precio": cierre})
            if not filas:
                return vacio
            return pd.DataFrame(filas)
        except Exception:
            return vacio

    def dividendos(self, ticker: str, desde: date) -> pd.DataFrame:
        vacio = pd.DataFrame(columns=["fecha", "valor_por_accion"])
        if not isinstance(ticker, str) or not ticker.strip():
            return vacio
        if type(desde) is not date:
            return vacio
        ticker = ticker.strip().upper()

        try:
            serie = yf.Ticker(ticker).dividends
            if serie is None or len(serie) == 0:
                return vacio

            moneda = self._moneda_ticker(ticker)
            if moneda not in ("COP", "USD"):
                return vacio
            trm = self.trm_actual() if moneda == "USD" else None

            filas = []
            for indice, valor in serie.items():
                dia = (
                    indice.date()
                    if hasattr(indice, "date")
                    else date.fromisoformat(str(indice)[:10])
                )
                if dia < desde:
                    continue
                monto = float(valor)
                if monto <= 0:
                    continue
                if moneda == "USD":
                    monto = monto * trm
                filas.append({"fecha": dia, "valor_por_accion": monto})
            if not filas:
                return vacio
            return pd.DataFrame(filas)
        except Exception:
            return vacio

    def _descargar_ultimo_cierre(self, ticker: str) -> float | None:
        datos = yf.Ticker(ticker).history(period="5d", auto_adjust=False)
        if datos is None or datos.empty:
            return None
        cierre = float(datos["Close"].dropna().iloc[-1])
        if cierre <= 0:
            return None
        return cierre

    def _moneda_de_portafolio(self, ticker: str) -> str | None:
        ticker = ticker.strip().upper()
        for activo in self.repositorio.listar_activos():
            if isinstance(activo, Accion) and activo.ticker == ticker:
                return activo.moneda
        return None

    def _moneda_ticker(self, ticker: str) -> str | None:

        if ticker == self.TICKER_TRM:
            return "COP"

        en_portafolio = self._moneda_de_portafolio(ticker)
        if en_portafolio in ("COP", "USD"):
            return en_portafolio

        if ticker.endswith(".CL"):
            return "COP"

        try:
            info = yf.Ticker(ticker).info or {}
            moneda = info.get("currency") or info.get("financialCurrency")
            if isinstance(moneda, str) and moneda.strip().upper() in ("COP", "USD"):
                return moneda.strip().upper()
        except Exception:
            pass
        return None

    def _a_cop(self, ticker: str, precio: float) -> float | None:
        moneda = self._moneda_ticker(ticker)
        if moneda == "COP":
            return float(precio)
        if moneda == "USD":
            return float(precio) * self.trm_actual()
        return None