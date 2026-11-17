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

        # Acciones de ejemplo para la gráfica de velas: id -> (ticker, moneda original)
    _ACCIONES = {1: ("AAPL", "USD"), 2: ("ECOPETROL", "COP"), 6: ("NKE", "USD"), 7: ("KO", "USD")}
    # Operaciones de ejemplo en COP por acción: id -> [(fecha, tipo, cantidad, precio)]
    _OPERACIONES = {
        1: [(date(2026, 1, 15), "COMPRA", 10, 950_000.0), (date(2026, 8, 20), "VENTA", 3, 1_020_000.0)],
        2: [(date(2026, 1, 20), "COMPRA", 2_000, 2_150.0)],
        6: [(date(2026, 2, 10), "COMPRA", 20, 290_000.0)],
        7: [(date(2026, 2, 12), "COMPRA", 30, 287_000.0)],
    }

    def grafica_accion(self, activo_id, desde, moneda="USD"):
        """Velas de ejemplo con la misma forma que Portafolio.grafica_accion (TRM fija de 4.100)."""
        from mocks.servicio_velas_mock import ServicioVelasMock
        f = self._factor(moneda)
        if activo_id not in self._ACCIONES:
            raise ValueError("La gráfica de velas es solo para acciones")
        ticker, nativa = self._ACCIONES[activo_id]
        velas = ServicioVelasMock().velas(ticker, desde)
        a_cop = self.TRM if nativa == "USD" else 1.0     # moneda original -> COP
        for columna in ("apertura", "maximo", "minimo", "cierre"):
            velas[columna] = velas[columna] * a_cop * f
        semanal = len(velas) > 130
        if semanal:
            semana = pd.to_datetime(velas["fecha"]).dt.to_period("W")
            g = velas.groupby(semana)
            velas = pd.DataFrame({"fecha": g["fecha"].first().values,
                                  "apertura": g["apertura"].first().values,
                                  "maximo": g["maximo"].max().values,
                                  "minimo": g["minimo"].min().values,
                                  "cierre": g["cierre"].last().values})
        ops = pd.DataFrame([{"fecha": d, "tipo": t, "cantidad": c, "precio": p * f}
                            for d, t, c, p in self._OPERACIONES[activo_id] if d >= desde],
                           columns=["fecha", "tipo", "cantidad", "precio"])
        pos = self.posiciones().set_index("activo_id").loc[activo_id]
        resumen = {}
        if not velas.empty:
            inicio, ultimo = float(velas["apertura"].iloc[0]), float(velas["cierre"].iloc[-1])
            resumen = {"desde": velas["fecha"].iloc[0], "hasta": velas["fecha"].iloc[-1],
                       "precio_inicio": inicio, "ultimo_cierre": ultimo,
                       "variacion": ultimo / inicio - 1,
                       "maximo": float(velas["maximo"].max()), "minimo": float(velas["minimo"].min())}
        return {"velas": velas, "agrupacion": "semana" if semanal else "dia", "operaciones": ops,
                "costo_promedio": float(pos["costo_total"]) / float(pos["cantidad"]) * f,
                "resumen": resumen, "moneda": moneda}

    # Precios de ejemplo en COP por unidad (los mismos de ServicioPreciosMock)
    _PRECIOS_SUGERIDOS = {"AAPL": 1_045_000.0, "ECOPETROL": 2_380.0,
                          "NKE": 278_800.0, "KO": 295_200.0}

    def extracto(self, activo_id):
        """Extracto de ejemplo con las mismas columnas que Portafolio.extracto (TRM fija de 4.100)."""
        columnas = ["fecha", "movimiento", "compra", "venta", "acciones", "precio_usd", "trm",
                    "precio_cop", "dividendo_usd", "dividendo_cop", "comision", "flujo", "saldo"]
        pos = self.posiciones().set_index("activo_id").loc[activo_id]
        filas, acciones, saldo = [], 0.0, 0.0
        movimientos = [(d, t, c, p) for d, t, c, p in self._OPERACIONES.get(activo_id, [])]
        if pos["ingresos"]:
            movimientos.append((date(2026, 6, 15), "DIVIDENDO", 0, float(pos["ingresos"])))
        for d, tipo, cantidad, valor in sorted(movimientos):
            fila = dict.fromkeys(columnas)
            fila.update(fecha=d, trm=self.TRM, compra=0.0, venta=0.0, comision=0.0)
            if tipo == "DIVIDENDO":
                flujo = valor
                fila.update(movimiento="Dividendo", dividendo_cop=valor,
                            dividendo_usd=valor / acciones / self.TRM if acciones else None)
            else:
                comision = round(cantidad * valor * 0.002, 2)
                if tipo == "COMPRA":
                    acciones += cantidad; flujo = -cantidad * valor - comision
                    fila.update(movimiento="Compra", compra=cantidad)
                else:
                    acciones -= cantidad; flujo = cantidad * valor - comision
                    fila.update(movimiento="Venta", venta=cantidad)
                fila.update(precio_cop=valor, precio_usd=valor / self.TRM, comision=comision)
            saldo += flujo
            fila.update(acciones=acciones, flujo=flujo, saldo=saldo)
            filas.append(fila)
        valor_actual = float(pos["valor_actual"])
        return {"filas": pd.DataFrame(filas, columns=columnas), "acciones": acciones,
                "saldo": saldo, "valor_actual": valor_actual, "total": saldo + valor_actual}

    def comision_sugerida(self, valor_operacion):
        """Misma regla del real (la del Excel): 0,2 % del valor de la operación."""
        regla = "0,2 % del valor de la operación, igual al comprar y al vender"
        return (round(valor_operacion * 0.002, 2) if valor_operacion > 0 else 0.0), regla

    def cantidad_disponible(self, activo_id, fecha=None):
        """Cantidad de ejemplo que se tiene hoy de cada activo."""
        pos = self.posiciones().set_index("activo_id")
        return float(pos.loc[activo_id, "cantidad"]) if activo_id in pos.index else 0.0

    def precio_sugerido(self, activo, fecha=None):
        """Precio de ejemplo para prellenar el formulario (en el real es el de mercado)."""
        if activo.es_renta_fija():
            return float(activo.valor_nominal)
        return self._PRECIOS_SUGERIDOS.get(getattr(activo, "ticker", None))
    
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
            (3, "CDT Bancolombia 360 días", "CDT", 1, 5_000_000, 5_385_000, 0),
            (4, "Bono Itaú 2030 (BITU125SA060)", "BONO", 1, 10_175_000, 10_220_000, 513_600),
            (5, "TES 7% 2031 (TFIT10260331)", "TES", 50, 4_543_000, 4_160_000, 0),
        ]
        datos = []
        for aid, nombre, tipo, cant, costo, valor, ingresos in filas:
            # Solo Apple tuvo una venta: su ganancia incluye lo ganado al vender
            realizada = self.VENTAS - self.COSTO_VENDIDO if nombre == "Apple" else 0.0
            invertido = costo + (self.COSTO_VENDIDO if nombre == "Apple" else 0.0)
            no_realizada = valor - costo
            ganancia = no_realizada + realizada + ingresos
            datos.append({
                "activo_id": aid, "nombre": nombre, "tipo": tipo,
                "cantidad": cant, "costo_total": float(costo) * f,
                "valor_actual": float(valor) * f, "ingresos": float(ingresos) * f,
                "ganancia": float(ganancia) * f, "rentabilidad": ganancia / invertido,
                "ganancia_no_realizada": float(no_realizada) * f,
                "ganancia_realizada": float(realizada) * f,
            })
        return pd.DataFrame(datos)

    def resumen(self, moneda="COP"):
        f = self._factor(moneda)
        pos = self.posiciones()
        total_invertido = pos["costo_total"].sum() + self.COSTO_VENDIDO
        valor_actual = pos["valor_actual"].sum()
        ingresos = pos["ingresos"].sum()
        ganancia = valor_actual + self.VENTAS + ingresos - total_invertido
        realizada = self.VENTAS - self.COSTO_VENDIDO
        no_realizada = valor_actual - pos["costo_total"].sum()
        return {
            "total_invertido": float(total_invertido) * f,
            "ventas": self.VENTAS * f,
            "ingresos": float(ingresos) * f,
            "comisiones": self.COMISIONES * f,
            "valor_actual": float(valor_actual) * f,
            "ganancia": float(ganancia) * f,
            "ganancia_realizada": float(realizada) * f,
            "ganancia_no_realizada": float(no_realizada) * f,
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
            {"fecha": date(2026, 12, 18), "nombre": "Bono Itaú 2030 (BITU125SA060)",
             "tipo": "INTERES", "valor": 535_000.0},
            {"fecha": date(2026, 12, 15), "nombre": "Coca-Cola",
             "tipo": "DIVIDENDO", "valor": 45_633.0},
            {"fecha": date(2027, 1, 2), "nombre": "Nike",
             "tipo": "DIVIDENDO", "valor": 23_534.0},
            {"fecha": date(2027, 2, 18), "nombre": "CDT Bancolombia 360 días",
             "tipo": "CAPITAL", "valor": 5_525_000.0},
        ]
        limite = hoy + timedelta(days=dias)
        filas = [dict(x, valor=x["valor"] * f) for x in filas if hoy <= x["fecha"] <= limite]
        return pd.DataFrame(filas, columns=["fecha", "nombre", "tipo", "valor"])