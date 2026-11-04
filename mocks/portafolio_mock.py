"""
PortafolioMock: imita a motor.portafolio.Portafolio.

Sirve para que la interfaz se construya sin esperar el motor.
Los valores son inventados pero coherentes con RepositorioMock:
el resumen y la distribución se suman a partir de las posiciones.
Tiene los mismos métodos y las mismas llaves/columnas que el contrato.
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

    def __init__(self, repositorio=None, servicio_precios=None):
        self.repositorio = repositorio
        self.servicio_precios = servicio_precios

    def actualizar(self):
        """En el real recalcula todo; aquí no hace nada."""
        return None

    def posiciones(self):
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
                "cantidad": cant, "costo_total": float(costo),
                "valor_actual": float(valor), "ingresos": float(ingresos),
                "ganancia": float(ganancia), "rentabilidad": ganancia / costo,
            })
        return pd.DataFrame(datos)

    def resumen(self):
        pos = self.posiciones()
        total_invertido = pos["costo_total"].sum() + self.COSTO_VENDIDO
        valor_actual = pos["valor_actual"].sum()
        ingresos = pos["ingresos"].sum()
        ganancia = valor_actual + self.VENTAS + ingresos - total_invertido
        return {
            "total_invertido": float(total_invertido),
            "ventas": self.VENTAS,
            "ingresos": float(ingresos),
            "comisiones": self.COMISIONES,
            "valor_actual": float(valor_actual),
            "ganancia": float(ganancia),
            "rentabilidad_acumulada": float(ganancia / total_invertido),
            "rentabilidad_ea": 0.0751,   # valor fijo de ejemplo
        }

    def distribucion(self):
        pos = self.posiciones()
        rv = float(pos.loc[pos["tipo"] == "ACCION", "valor_actual"].sum())
        rf = float(pos.loc[pos["tipo"] != "ACCION", "valor_actual"].sum())
        total = rf + rv
        return {
            "renta_fija": {"valor": rf, "porcentaje": rf / total},
            "renta_variable": {"valor": rv, "porcentaje": rv / total},
        }

    def serie_valor(self, desde=None):
        desde = desde or date(2026, 1, 15)
        final = self.resumen()["valor_actual"]
        hoy = date.today()
        dias = max((hoy - desde).days, 1)
        filas = []
        for i in range(dias + 1):
            d = desde + timedelta(days=i)
            base = final * (0.3 + 0.7 * min(i / 90, 1))   # se va comprando hasta abril
            valor = base * (0.97 + 0.03 * i / dias + 0.015 * math.sin(i / 11))
            filas.append({"fecha": d, "valor": round(valor, 2)})
        return