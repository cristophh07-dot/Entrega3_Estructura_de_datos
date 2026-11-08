"""
PortafolioMock: imita a motor.portafolio.Portafolio.

Sirve para que la interfaz se construya sin esperar el motor.
Los valores son inventados pero coherentes con RepositorioMock:
el resumen y la distribución se suman a partir de las posiciones.
Tiene los mismos métodos y las mismas llaves/columnas que el contrato.
Todos aceptan moneda="COP" o "USD" (en USD divide por una TRM fija de 4.100).
"""
from datetime import date, timedelta
import math

import pandas as pd


class PortafolioMock:
    """Resultados falsos con la forma exacta del contrato."""

    # Costo de las 3 acciones de Apple que se vendieron (ya no están en posiciones).
    COSTO_VENDIDO = 2_854_500.0
    VENTAS = 3_050_000.0          # 3 × 1.020.000 − 10.000 de comisión
    COMISIONES = 104_000.0        # suma de todas las comisiones del ejemplo
    TRM = 4_100.0                 # pesos por dólar para mostrar valores en USD

    def __init__(self, repositorio=None, servicio_precios=None):
        self.repositorio = repositorio
        self.servicio_precios = servicio_precios

    def actualizar(self):
        """En el real recalcula todo; aquí no hace nada."""
        return None
    
    def trm_en(self, fecha=None):
        """TRM fija de ejemplo (en el real es la TRM histórica de esa fecha)."""
        return self.TRM

    def _factor(self, moneda):
        if moneda not in ("COP", "USD"):
            raise ValueError(f"moneda debe ser 'COP' o 'USD' (recibido: {moneda!r})")
        return 1.0 if moneda == "COP" else 1 / self.TRM

    def posiciones(self, moneda="COP"):
        f = self._factor(moneda)
        filas = [
            # id, nombre, tipo, cantidad, costo_total, valor_actual, ingresos netos
            (1, "Apple", "ACCION", 7, 6_660_500, 7_315_000, 25_200),
            (2, "Ecopetrol", "ACCION", 2_000, 4_312_000, 4_760_000, 540_000),
            (6, "Nike", "ACCION", 20, 5_812_000, 5_576_000, 23_534),
            (7, "Coca-Cola", "ACCION", 30, 8_622_000, 8_856_000, 91_266),
            (3, "CDT Banco 360 días", "CDT", 1, 5_000_000, 5_385_000, 0),
            (4, "Bono corporativo 2029", "BONO", 1, 10_175_000, 10_220_000, 513_600),
            (5, "TES COP 2031", "TES", 5, 4_543_000, 4_160_000, 0),
        ]
        datos = []
        for aid, nombre, tipo, cant, costo, valor, ingresos in filas:
            ganancia = valor + ingresos - costo
            datos.append({
                "activo_id": aid, "nombre": nombre, "tipo": tipo,
                "cantidad": cant, "costo_total": float(costo) * f,
                "valor_actual": float(valor) * f, "ingresos": float(ingresos) * f,
                "ganancia": float(ganancia) * f, "rentabilidad": ganancia / costo,
            })
        return pd.DataFrame(datos)

    def resumen(self, moneda="COP"):
        f = self._factor(moneda)
        pos = self.posiciones()
        total_invertido = pos["costo_total"].sum() + self.COSTO_VENDIDO
        valor_actual = pos["valor_actual"].sum()
        ingresos = pos["ingresos"].sum()
        ganancia = valor_actual + self.VENTAS + ingresos - total_invertido
        return {
            "total_invertido": float(total_invertido) * f,
            "ventas": self.VENTAS * f,
            "ingresos": float(ingresos) * f,
            "comisiones": self.COMISIONES * f,
            "valor_actual": float(valor_actual) * f,
            "ganancia": float(ganancia) * f,
            "rentabilidad_acumulada": float(ganancia / total_invertido),
            "rentabilidad_ea": 0.0751 if moneda == "COP" else 0.0928,  # valores fijos de ejemplo
        }

    def distribucion(self, moneda="COP"):
        pos = self.posiciones(moneda)
        rv = float(pos.loc[pos["tipo"] == "ACCION", "valor_actual"].sum())
        rf = float(pos.loc[pos["tipo"] != "ACCION", "valor_actual"].sum())
        total = rf + rv
        return {
            "renta_fija": {"valor": rf, "porcentaje": rf / total},
            "renta_variable": {"valor": rv, "porcentaje": rv / total},
        }

    def serie_valor(self, desde=None, moneda="COP"):
        f = self._factor(moneda)
        desde = desde or date(2026, 1, 15)
        final = self.resumen()["valor_actual"]
        hoy = date.today()
        dias = max((hoy - desde).days, 1)
        filas = []
        for i in range(dias + 1):
            d = desde + timedelta(days=i)
            base = final * (0.3 + 0.7 * min(i / 90, 1))   # se va comprando hasta abril
            valor = base * (0.97 + 0.03 * i / dias + 0.015 * math.sin(i / 11))
            filas.append({"fecha": d, "valor": round(valor * f, 2)})
        return pd.DataFrame(filas, columns=["fecha", "valor"])

    def proximos_flujos(self, dias=90, moneda="COP"):
        f = self._factor(moneda)
        hoy = date.today()
        filas = [
            {"fecha": date(2026, 11, 15), "nombre": "Bono corporativo 2029",
             "tipo": "INTERES", "valor": 535_000.0},
            {"fecha": date(2026, 12, 15), "nombre": "Coca-Cola",
             "tipo": "DIVIDENDO", "valor": 45_633.0},
            {"fecha": date(2027, 1, 2), "nombre": "Nike",
             "tipo": "DIVIDENDO", "valor": 23_534.0},
            {"fecha": date(2027, 2, 2), "nombre": "CDT Banco 360 días",
             "tipo": "CAPITAL", "valor": 5_525_000.0},
        ]
        limite = hoy + timedelta(days=dias)
        filas = [dict(x, valor=x["valor"] * f) for x in filas if hoy <= x["fecha"] <= limite]
        return pd.DataFrame(filas, columns=["fecha", "nombre", "tipo", "valor"])