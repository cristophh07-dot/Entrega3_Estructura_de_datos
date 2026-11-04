"""
ServicioPreciosMock: imita a datos.servicio_precios.ServicioPrecios.

Precios fijos y un historial sintético (reproducible) para probar el
motor y las gráficas sin internet. Todo en COP.
"""
from datetime import date, timedelta
import math

import pandas as pd


class ServicioPreciosMock:
    """Precios falsos con los mismos métodos del contrato."""

    TRM = 4_100.0

    # Precio actual en COP (las acciones en USD ya convertidas con la TRM).
    _PRECIOS = {
        "AAPL": 1_045_000.0,
        "ECOPETROL": 2_380.0,
        "NKE": 278_800.0,
        "KO": 295_200.0,
    }

    _DIVIDENDOS = {
        "AAPL": [(date(2026, 5, 15), 3_600.0)],
        "ECOPETROL": [(date(2026, 4, 28), 300.0)],
        "NKE": [(date(2026, 7, 1), 1_681.0)],
        "KO": [(date(2026, 4, 1), 2_173.0), (date(2026, 7, 1), 2_173.0)],
    }

    def __init__(self, repositorio=None):
        self.repositorio = repositorio

    def precio_actual(self, ticker):
        return self._PRECIOS.get(ticker)

    def historial(self, ticker, desde):
        """Serie diaria suave que termina en el precio actual."""
        final = self._PRECIOS.get(ticker)
        if final is None:
            return pd.DataFrame(columns=["fecha", "precio"])
        hoy = date.today()
        dias = max((hoy - desde).days, 0)
        semilla = sum(ord(c) for c in ticker)
        filas = []
        for i in range(dias + 1):
            d = desde + timedelta(days=i)
            if d.weekday() >= 5:  # sin mercado fines de semana
                continue
            avance = i / dias if dias else 1
            ruido = 0.03 * math.sin(i / 9 + semilla)
            precio = final * (0.88 + 0.12 * avance + ruido)
            filas.append({"fecha": d, "precio": round(precio, 2)})
        return pd.DataFrame(filas, columns=["fecha", "precio"])

    def dividendos(self, ticker, desde):
        filas = [{"fecha": f, "valor_por_accion": v}
                 for f, v in self._DIVIDENDOS.get(ticker, []) if f >= desde]
        return pd.DataFrame(filas, columns=["fecha", "valor_por_accion"])

    def trm_actual(self):
        return self.TRM