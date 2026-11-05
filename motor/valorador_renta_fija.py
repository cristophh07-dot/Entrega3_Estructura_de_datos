"""
ValoradorRentaFija: cuánto vale hoy un CDT, un bono o un TES.

Tasas efectivas anuales, base 365 días. Valores por UN título:

1. CDT → por CAUSACIÓN (el interés se va acumulando día a día):
     valor = VN × (1 + tasa) ^ (días desde el último pago / 365)
   Ej.: CDT de 5.000.000 al 10,5 % E.A., a los 182 días vale ≈ 5.255.000.

2. BONO y TES → a PRECIO DE MERCADO (valor presente de lo que falta por cobrar):
     precio = Σ  F / (1 + r) ^ (días hasta el pago / 365)
   F = cada cupón y el capital futuro (de GeneradorFlujos);
   r = tasa_mercado del título (si no tiene, se usa su propia tasa).
   Si la tasa de mercado SUBE, el precio BAJA (y al revés).

Después del vencimiento el título vale 0: el dinero ya entró como
flujos de INTERES y CAPITAL registrados en FlujoCaja.
"""
from datetime import date

from motor.generador_flujos import GeneradorFlujos


class ValoradorRentaFija:
    """Valora títulos de renta fija por causación o por descuento de flujos."""

    BASE_DIAS = 365

    def __init__(self, generador=None):
        self.generador = generador or GeneradorFlujos()

    def precio(self, titulo, fecha=None):
        """Valor de UN título en 'fecha' (hoy si no se indica)."""
        fecha = fecha or date.today()
        if fecha < titulo.fecha_emision or fecha >= titulo.fecha_vencimiento:
            return 0.0
        if titulo.tipo == "CDT":
            return self._por_causacion(titulo, fecha)
        return self._por_descuento(titulo, fecha)

    def _por_causacion(self, titulo, fecha):
        desde = self.generador.ultimo_pago(titulo, fecha)
        dias = (fecha - desde).days
        return titulo.valor_nominal * (1 + titulo.tasa) ** (dias / self.BASE_DIAS)

    def _por_descuento(self, titulo, fecha):
        r = titulo.tasa_mercado if titulo.tasa_mercado is not None else titulo.tasa
        total = 0.0
        for flujo in self.generador.flujos(titulo, desde=fecha):
            dias = (flujo["fecha"] - fecha).days
            total += flujo["valor"] / (1 + r) ** (dias / self.BASE_DIAS)
        return total

    def valor(self, posicion, fecha=None):
        """Valor de toda la posición: precio por título × cantidad de títulos."""
        if not posicion.esta_abierta:
            return 0.0
        return self.precio(posicion.activo, fecha) * posicion.cantidad