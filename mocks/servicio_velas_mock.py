"""
ServicioVelasMock: imita a datos.servicio_velas.ServicioVelas.

Genera velas diarias inventadas (siempre las mismas para cada ticker), sin
fines de semana, en la moneda original del ticker: USD para AAPL, NKE y KO;
COP para ECOPETROL. Sirve para probar la vista de velas sin internet.
"""
from datetime import date, timedelta
import random

import pandas as pd


class ServicioVelasMock:
    """Velas falsas con las mismas columnas que ServicioVelas."""

    COLUMNAS = ["fecha", "apertura", "maximo", "minimo", "cierre"]

    # Precio de cierre de "hoy" en la moneda original (AAPL, NKE y KO en USD; ECOPETROL en COP)
    _CIERRE_FINAL = {"AAPL": 254.88, "NKE": 68.0, "KO": 72.0, "EC": 12.5, "ECOPETROL": 2_380.0}

    # Dividendos por acción en la moneda original: ticker -> [(fecha ex-dividendo, valor)]
    _DIVIDENDOS = {
        "AAPL": [(date(2026, 2, 9), 0.26), (date(2026, 5, 11), 0.27), (date(2026, 8, 10), 0.27)],
        "NKE": [(date(2026, 3, 2), 0.41), (date(2026, 6, 1), 0.41), (date(2026, 9, 1), 0.41)],
        "KO": [(date(2026, 3, 13), 0.53), (date(2026, 6, 15), 0.53), (date(2026, 9, 15), 0.53)],
        "EC": [(date(2026, 4, 29), 0.66)],
    }

    def __init__(self, hoy=None):
        self.hoy = hoy or date.today()

    def velas(self, ticker, desde):
        final = self._CIERRE_FINAL.get(str(ticker).upper())
        if final is None or desde > self.hoy:
            return pd.DataFrame(columns=self.COLUMNAS)
        azar = random.Random(sum(ord(c) for c in ticker))   # misma serie cada vez
        dias = [desde + timedelta(days=i) for i in range((self.hoy - desde).days + 1)]
        dias = [d for d in dias if d.weekday() < 5]
        # Camino aleatorio hacia atrás desde el cierre final
        cierres = [final]
        for _ in dias[1:]:
            cierres.append(cierres[-1] / (1 + azar.gauss(0.0004, 0.014)))
        cierres.reverse()
        filas, anterior = [], cierres[0] * (1 - 0.003)
        for d, cierre in zip(dias, cierres):
            apertura = anterior * (1 + azar.gauss(0, 0.004))
            alto = max(apertura, cierre) * (1 + abs(azar.gauss(0, 0.006)))
            bajo = min(apertura, cierre) * (1 - abs(azar.gauss(0, 0.006)))
            filas.append({"fecha": d, "apertura": apertura, "maximo": alto,
                          "minimo": bajo, "cierre": cierre})
            anterior = cierre
        return pd.DataFrame(filas, columns=self.COLUMNAS)

    def dividendos(self, ticker, desde):
        filas = [{"fecha": f, "valor_por_accion": v}
                 for f, v in self._DIVIDENDOS.get(str(ticker).upper(), []) if f >= desde and f <= self.hoy]
        return pd.DataFrame(filas, columns=["fecha", "valor_por_accion"])

    def limpiar_cache(self):
        return None
