"""
ExtractoMovimientos: los movimientos de un activo, fila por fila, como en el Excel de referencia.

Cada compra, venta, dividendo o pago de renta fija es una fila, en orden de fecha,
con las mismas columnas del Excel (Prueba_portafolio.xlsx):

  Fecha | Movimiento | Compra | Venta | Acciones | Valor US | TRM | Valor COP |
  Dividendo US | Dividendo COP | Comisión | Flujo | Saldo

y las mismas fórmulas:
  Acciones   = acciones de la fila anterior + compra − venta
  Valor COP  = Valor US × TRM de ese día
  Dividendo COP = dividendo por acción × TRM × acciones que se tenían
  Saldo      = saldo anterior − compras + ventas + dividendos − comisiones

Al final:  resultado total = saldo + lo que valen hoy las acciones que aún se tienen.
Si ya se vendió todo, el resultado es el saldo (como en el Excel). Es igual a la
"ganancia" de ese activo en el dashboard.
"""
import pandas as pd


class ExtractoMovimientos:
    """Arma el extracto de un activo a partir de sus operaciones y flujos (en COP)."""

    COLUMNAS = ["fecha", "movimiento", "compra", "venta", "acciones", "precio_usd", "trm",
                "precio_cop", "dividendo_usd", "dividendo_cop", "comision", "flujo", "saldo"]
    NOMBRES = {"COMPRA": "Compra", "VENTA": "Venta", "DIVIDENDO": "Dividendo",
               "INTERES": "Interés", "CAPITAL": "Pago de capital", "OTRO": "Otro ingreso"}
    # En un mismo día: primero compras, luego dividendos y pagos, y al final ventas
    ORDEN = {"COMPRA": 0, "DIVIDENDO": 1, "INTERES": 1, "CAPITAL": 1, "OTRO": 1, "VENTA": 2}

    def __init__(self, conversor):
        self.conversor = conversor

    def extracto(self, activo, operaciones, flujos, valor_actual_cop):
        en_usd = getattr(activo, "moneda", "COP") == "USD"
        movimientos = ([("op", o) for o in operaciones if o.activo_id == activo.id]
                       + [("flujo", f) for f in flujos if f.activo_id == activo.id])
        movimientos.sort(key=lambda m: (m[1].fecha, self.ORDEN.get(m[1].tipo, 1)))

        filas, acciones, saldo = [], 0.0, 0.0
        for clase, m in movimientos:
            trm = self.conversor.trm_en(m.fecha)
            fila = dict.fromkeys(self.COLUMNAS)
            fila.update(fecha=m.fecha, movimiento=self.NOMBRES.get(m.tipo, m.tipo), trm=trm,
                        compra=0.0, venta=0.0, comision=0.0)
            if clase == "op":
                valor = m.cantidad * m.precio
                if m.tipo == "COMPRA":
                    fila["compra"], flujo = m.cantidad, -valor - m.comision
                    acciones += m.cantidad
                else:
                    fila["venta"], flujo = m.cantidad, valor - m.comision
                    acciones -= m.cantidad
                fila.update(precio_cop=m.precio, comision=m.comision,
                            precio_usd=m.precio / trm if en_usd else None)
            else:
                neto = m.valor_bruto * (1 - m.retencion)
                flujo = neto
                fila["dividendo_cop"] = neto
                if m.tipo == "DIVIDENDO" and acciones > 0:
                    por_accion = m.valor_bruto / acciones
                    fila["dividendo_usd"] = por_accion / trm if en_usd else None
            saldo += flujo
            fila.update(acciones=acciones, flujo=flujo, saldo=saldo)
            filas.append(fila)

        return {
            "filas": pd.DataFrame(filas, columns=self.COLUMNAS),
            "acciones": acciones,
            "saldo": saldo,
            "valor_actual": valor_actual_cop,
            "total": saldo + valor_actual_cop,
        }
