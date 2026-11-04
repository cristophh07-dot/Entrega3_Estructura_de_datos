"""Certificado de Depósito a Término."""

from datetime import date

from modelos.renta_fija import RentaFija


class CDT(RentaFija):
    """CDT. Por defecto paga capital e intereses al vencimiento."""

    def __init__(
        self,
        nombre: str,
        valor_nominal: float,
        tasa: float,
        fecha_emision: date,
        fecha_vencimiento: date,
        periodicidad_meses: int = 0,
        tasa_mercado: float | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(
            nombre=nombre,
            tipo="CDT",
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