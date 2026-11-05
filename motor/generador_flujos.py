"""
GeneradorFlujos: calendario de pagos de un título de renta fija.

Reglas (todas con tasas efectivas anuales y base 365 días):

1. periodicidad_meses = 0  (típico de un CDT):
   un único pago al vencimiento.
     interés = VN × ((1 + tasa) ^ (días del plazo / 365) − 1)
     capital = VN

2. periodicidad_meses = 1, 3, 6 o 12  (bonos y TES):
   se paga un cupón cada 'periodicidad' meses, contando HACIA ATRÁS
   desde el vencimiento, y el capital al final.
     cupón = VN × ((1 + tasa) ^ (meses / 12) − 1)

   Ejemplo: TES de VN 1.000.000, tasa 7 %, anual → cupón de 70.000
   cada año y 1.000.000 de capital al vencimiento.

Cada flujo es un diccionario {"fecha", "tipo", "valor"} con tipo
"INTERES" o "CAPITAL", por UN título (luego se multiplica por la cantidad).
"""
import calendar
from datetime import date


class GeneradorFlujos:
    """Genera las fechas y valores de pago de CDT, bonos y TES."""

    BASE_DIAS = 365

    @staticmethod
    def sumar_meses(fecha, meses):
        """Suma (o resta, si meses < 0) meses a una fecha.
        Si el día no existe en el mes destino (ej. 31 de abril),
        usa el último día de ese mes."""
        total = fecha.month - 1 + meses
        anio = fecha.year + total // 12
        mes = total % 12 + 1
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        return date(anio, mes, min(fecha.day, ultimo_dia))

    def fechas_pago(self, titulo):
        """Todas las fechas de pago del título, de la más vieja a la más nueva."""
        if titulo.periodicidad_meses == 0:
            return [titulo.fecha_vencimiento]
        fechas = []
        k = 0
        while True:
            fecha = self.sumar_meses(titulo.fecha_vencimiento,
                                     -k * titulo.periodicidad_meses)
            if fecha <= titulo.fecha_emision:
                break
            fechas.append(fecha)
            k += 1
        return sorted(fechas)

    def cupon(self, titulo):
        """Valor de cada cupón periódico por título."""
        if titulo.periodicidad_meses == 0:
            dias = (titulo.fecha_vencimiento - titulo.fecha_emision).days
            return titulo.valor_nominal * ((1 + titulo.tasa) ** (dias / self.BASE_DIAS) - 1)
        return titulo.valor_nominal * ((1 + titulo.tasa) ** (titulo.periodicidad_meses / 12) - 1)

    def flujos(self, titulo, desde=None, hasta=None):
        """Flujos de UN título con fecha > desde y <= hasta.
        Sin 'desde' empieza en la emisión; sin 'hasta' llega al vencimiento."""
        valor_cupon = self.cupon(titulo)
        resultado = []
        for fecha in self.fechas_pago(titulo):
            if desde is not None and fecha <= desde:
                continue
            if hasta is not None and fecha > hasta:
                continue
            resultado.append({"fecha": fecha, "tipo": "INTERES", "valor": valor_cupon})
            if fecha == titulo.fecha_vencimiento:
                resultado.append({"fecha": fecha, "tipo": "CAPITAL",
                                  "valor": float(titulo.valor_nominal)})
        return resultado

    def ultimo_pago(self, titulo, fecha):
        """Última fecha de pago en o antes de 'fecha' (o la emisión si no ha pagado).
        Sirve para saber desde cuándo se están causando intereses."""
        anteriores = [f for f in self.fechas_pago(titulo) if f <= fecha]
        return max(anteriores) if anteriores else titulo.fecha_emision
