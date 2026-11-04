"""Título de Tesorería (TES). Es un bono emitido por la Nación."""

from datetime import date

from modelos.bono import Bono
from modelos.renta_fija import RentaFija


class TES(Bono):
    """TES. Misma estructura que Bono, con tipo 'TES'."""

    def __init__(
        self,
        nombre: str,
        valor_nominal: float,
        tasa: float,
        fecha_emision: date,
        fecha_vencimiento: date,
        periodicidad_meses: int,
        tasa_mercado: float | None = None,
        id: int | None = None,
    ) -> None:
        # No usamos Bono.__init__ porque ese fija tipo="BONO".
        # Llamamos a RentaFija y mantenemos la herencia TES → Bono.
        RentaFija.__init__(
            self,
            nombre=nombre,
            tipo="TES",
            valor_nominal=valor_nominal,
            tasa=tasa,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            periodicidad_meses=periodicidad_meses,
            tasa_mercado=tasa_mercado,
            id=id,
        )