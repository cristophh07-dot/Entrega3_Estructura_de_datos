"""
HistorialAccion: prepara los datos de la gráfica de velas de una acción.

Toma las velas en la moneda original del ticker y las pasa a la moneda pedida
con la TRM de CADA día:
    acción en USD vista en COP: precio × TRM de ese día
    acción en COP vista en USD: precio ÷ TRM de ese día

Además entrega:
  - las compras y ventas del usuario, con el precio por acción en esa moneda;
  - el costo promedio actual (con comisiones), para compararlo con el mercado;
  - un resumen del período: primer y último precio, variación, máximo y mínimo.

Si el período es largo, agrupa las velas por semana para que se lean bien.
"""
from types import SimpleNamespace

import pandas as pd

from motor.posicion import Posicion


class HistorialAccion:
    """Velas de una acción en COP o USD, con las operaciones y el costo promedio del usuario."""

    COLUMNAS = ["fecha", "apertura", "maximo", "minimo", "cierre"]
    MAX_VELAS_DIARIAS = 130   # más que esto (unos 6 meses de bolsa) se agrupa por semana

    def __init__(self, servicio_velas, conversor):
        self.servicio_velas = servicio_velas
        self.conversor = conversor

    # ------------------------------------------------------------------
    def velas(self, activo, desde, moneda="USD"):
        """Velas diarias en la moneda pedida."""
        df = self.servicio_velas.velas(activo.ticker, desde)
        if df is None or df.empty:
            return pd.DataFrame(columns=self.COLUMNAS)
        df = df[self.COLUMNAS].copy()
        nativa = getattr(activo, "moneda", "COP")
        if nativa != moneda:
            trm = df["fecha"].map(self.conversor.trm_en)
            factor = trm if moneda == "COP" else 1 / trm   # USD→COP multiplica; COP→USD divide
            for columna in ("apertura", "maximo", "minimo", "cierre"):
                df[columna] = df[columna] * factor
        return df.reset_index(drop=True)

    @classmethod
    def por_semana(cls, df):
        """Agrupa velas diarias en semanales: apertura del lunes, cierre del viernes,
        máximo y mínimo de toda la semana. La fecha es el primer día de la semana."""
        if df.empty:
            return df
        semanas = pd.to_datetime(df["fecha"]).dt.to_period("W")
        grupos = df.groupby(semanas, sort=True)
        return pd.DataFrame({
            "fecha": grupos["fecha"].first().values,
            "apertura": grupos["apertura"].first().values,
            "maximo": grupos["maximo"].max().values,
            "minimo": grupos["minimo"].min().values,
            "cierre": grupos["cierre"].last().values,
        }, columns=cls.COLUMNAS)

    def _precio_en(self, valor_cop, fecha, moneda):
        return valor_cop if moneda == "COP" else self.conversor.a_usd(valor_cop, fecha)

    def operaciones(self, activo, operaciones, desde, hasta, moneda="USD"):
        """Compras y ventas del activo en el período, con el precio por acción en la moneda pedida
        (sin comisión, para poder ubicarlo sobre la vela de ese día)."""
        filas = [{"fecha": op.fecha, "tipo": op.tipo, "cantidad": op.cantidad,
                  "precio": self._precio_en(op.precio, op.fecha, moneda)}
                 for op in operaciones
                 if op.activo_id == activo.id and desde <= op.fecha <= hasta]
        return pd.DataFrame(filas, columns=["fecha", "tipo", "cantidad", "precio"])

    def costo_promedio(self, activo, operaciones, hasta, moneda="USD"):
        """Costo promedio por acción de lo que se tiene hoy, con comisiones (None si no se tiene)."""
        propias = [op for op in operaciones if op.activo_id == activo.id and op.fecha <= hasta]
        if moneda == "USD":
            c = self.conversor
            propias = [SimpleNamespace(activo_id=op.activo_id, tipo=op.tipo, fecha=op.fecha,
                                       cantidad=op.cantidad,
                                       precio=c.a_usd(op.precio, op.fecha),
                                       comision=c.a_usd(op.comision, op.fecha))
                       for op in propias]
        posicion = Posicion(activo, propias)
        return posicion.costo_promedio if posicion.esta_abierta else None

    @staticmethod
    def resumen(df):
        """Primer y último precio del período, su variación, máximo y mínimo."""
        if df.empty:
            return {}
        inicio, ultimo = float(df["apertura"].iloc[0]), float(df["cierre"].iloc[-1])
        return {
            "desde": df["fecha"].iloc[0], "hasta": df["fecha"].iloc[-1],
            "precio_inicio": inicio, "ultimo_cierre": ultimo,
            "variacion": ultimo / inicio - 1,
            "maximo": float(df["maximo"].max()), "minimo": float(df["minimo"].min()),
        }

    # ------------------------------------------------------------------
    def grafica(self, activo, operaciones, desde, hasta, moneda="USD"):
        """Todo lo que necesita la vista de velas, en un solo diccionario."""
        diarias = self.velas(activo, desde, moneda)
        diarias = diarias[diarias["fecha"] <= hasta] if not diarias.empty else diarias
        semanal = len(diarias) > self.MAX_VELAS_DIARIAS
        return {
            "velas": self.por_semana(diarias) if semanal else diarias,
            "agrupacion": "semana" if semanal else "dia",
            "operaciones": self.operaciones(activo, operaciones, desde, hasta, moneda),
            "costo_promedio": self.costo_promedio(activo, operaciones, hasta, moneda),
            "resumen": self.resumen(diarias),
            "moneda": moneda,
        }
