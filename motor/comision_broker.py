"""
ComisionBroker: comisión que cobra el bróker por cada compra o venta.

Se usa la misma regla del Excel de referencia del proyecto (Prueba_portafolio.xlsx):

    comisión = 0,2 % × valor de la operación (cantidad × precio en COP)

y se cobra igual al comprar y al vender. Es una tarifa de mercado real: Valores
Bancolombia, por ejemplo, cobra 0,2 % (+ IVA) por compra o venta de acciones.
Como en el Excel, aquí no se suma el IVA.

Es una sugerencia: el usuario la puede cambiar por la que le cobró su bróker.
"""


class ComisionBroker:
    """Calcula la comisión sugerida de una operación según su valor en pesos."""

    PORCENTAJE = 0.002   # 0,2 % del valor de la operación

    def comision(self, valor_operacion: float) -> float:
        """Comisión en COP para una compra o venta de 'valor_operacion' pesos."""
        if valor_operacion <= 0:
            return 0.0
        return round(valor_operacion * self.PORCENTAJE, 2)

    def regla(self, valor_operacion: float = 0) -> str:
        """Explica en una frase la regla (para mostrarla en el formulario)."""
        return "0,2 % del valor de la operación, igual al comprar y al vender"
