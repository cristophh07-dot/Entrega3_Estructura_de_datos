"""
ComisionBroker: comisión estándar que cobra el bróker por cada compra o venta.

Se toma como referencia la tarifa de trii (la plataforma más usada por personas
naturales en Colombia, 2026), que se cobra igual al comprar y al vender:
  - operaciones hasta $5.000.000: tarifa fija de $12.500 + IVA (19 %) = $14.875
  - operaciones de más de $5.000.000: 0,25 % del valor + IVA

    valor ≤ 5.000.000  →  comisión = 12.500 × 1,19
    valor > 5.000.000  →  comisión = valor × 0,25 % × 1,19

En $5.000.000 las dos reglas dan lo mismo ($14.875), así que la comisión no salta.
Es una sugerencia: el usuario la puede cambiar por la que le cobró su bróker.
"""


class ComisionBroker:
    """Calcula la comisión sugerida de una operación según su valor en pesos."""

    TARIFA_FIJA = 12_500.0     # COP, antes de IVA
    UMBRAL = 5_000_000.0       # COP: hasta aquí se cobra la tarifa fija
    PORCENTAJE = 0.0025        # 0,25 % sobre el valor, por encima del umbral
    IVA = 0.19

    def comision(self, valor_operacion: float) -> float:
        """Comisión en COP, con IVA, para una operación de 'valor_operacion' pesos."""
        if valor_operacion <= 0:
            return 0.0
        if valor_operacion <= self.UMBRAL:
            base = self.TARIFA_FIJA
        else:
            base = valor_operacion * self.PORCENTAJE
        return round(base * (1 + self.IVA), 2)

    def regla(self, valor_operacion: float) -> str:
        """Explica en una frase qué regla se aplicó (para mostrarla en el formulario)."""
        if valor_operacion <= self.UMBRAL:
            return "tarifa fija de $ 12.500 + IVA (operaciones hasta $ 5.000.000)"
        return "0,25 % + IVA sobre el valor (operaciones de más de $ 5.000.000)"
