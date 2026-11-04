"""
PortafolioMock: imita a motor.portafolio.Portafolio.

Sirve para que la interfaz se construya sin esperar el motor.
Los valores son inventados pero coherentes entre sí. Tiene los mismos
métodos y las mismas llaves/columnas que el contrato.
"""
from datetime import date, timedelta
import math

import pandas as pd


class PortafolioMock:
    """Resultados falsos con la forma exacta del contrato."""

    def __init__(self, repositorio=None, servicio_precios=None):
        self.repositorio = repositorio
        self.servicio_precios = servicio_precios

    def actualizar(self):
        """En el real recalcula todo; aquí no hace nada."""
        return None

    def resumen(self):
        total_invertido = 28_175_000.0
        ventas = 3_050_000.0
        ingresos = 1_078_800.0
        comisiones = 80_000.0
        valor_actual = 26_840_000.0
        ganancia = valor_actual + ventas + ingresos - total_invertido
        return {
            "total_invertido": total_invertido,
            "ventas": ventas,
            "ingresos": ingresos,
            "comisiones": comisiones,
            "valor_actual": valor_actual,
            "ganancia": ganancia,
            "rentabilidad_acumulada": ganancia / total_invertido,
            "rentabilidad_ea": 0.1384,
        }

    def distribucion(self):
        rf, rv = 19_765_000.0, 7_075_000.0
        total = rf + rv
        return {
            "renta_fija": {"valor": rf, "porcentaje": rf / total},
            "renta_variable": {"valor": rv, "porcentaje": rv / total},
        }

    def posiciones(self):
        filas = [
            (1, "Apple", "ACCION", 7, 6_660_500, 7_315_000, 25_200),
            (2, "Ecopetrol", "ACCION", 2_000, 4_312_000, 4_760_000, 540_000),
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

    def serie_valor(self, desde=None):
        desde = desde or date(2026, 1, 15)
        hoy = date.today()
        dias = max((hoy - desde).days, 1)
        filas = []
        for i in range(dias + 1):
            d = desde + timedelta(days=i)
            base = 9_500_000 + 18_000_000 * min(i / 90, 1)
            valor = base * (1 + 0.04 * i / dias + 0.015 * math.sin(i / 11))
            filas.append({"fecha": d, "valor": round(valor, 2)})
        return pd.DataFrame(filas, columns=["fecha", "valor"])

    def proximos_flujos(self, dias=90):
        hoy = date.today()
        filas = [
            {"fecha": date(2026, 11, 15), "nombre": "Bono corporativo 2029",
             "tipo": "INTERES", "valor": 535_000.0},
            {"fecha": date(2027, 2, 2), "nombre": "CDT Banco 360 días",
             "tipo": "CAPITAL", "valor": 5_525_000.0},
        ]
        limite = hoy + timedelta(days=dias)
        filas = [f for f in filas if hoy <= f["fecha"] <= limite]
        return pd.DataFrame(filas, columns=["fecha", "nombre", "tipo", "valor"])
    