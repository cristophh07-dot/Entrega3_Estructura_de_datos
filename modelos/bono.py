"""Bono de renta fija."""

from datetime import date

from modelos.renta_fija import RentaFija


class Bono(RentaFija):
    """Bono. TES hereda de esta clase."""

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
        super().__init__(
            nombre=nombre,
            tipo="BONO",
            valor_nominal=valor_nominal,
            tasa=tasa,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            periodicidad_meses=periodicidad_meses,
            tasa_mercado=tasa_mercado,
            id=id,
        )

    def es_renta_fija(self) -> bool:
        return True