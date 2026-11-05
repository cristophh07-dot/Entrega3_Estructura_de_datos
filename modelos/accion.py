

from modelos.activo import Activo


class Accion(Activo):

    MONEDAS_VALIDAS = ("COP", "USD")

    def __init__(
        self,
        nombre: str,
        ticker: str,
        moneda: str = "COP",
        id: int | None = None,
    ) -> None:
        super().__init__(nombre=nombre, tipo="ACCION", id=id)
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("ticker debe ser un texto no vacío")
        moneda = moneda.strip().upper() if isinstance(moneda, str) else moneda
        if moneda not in self.MONEDAS_VALIDAS:
            raise ValueError(
                f"moneda inválida: {moneda!r}. Debe ser 'COP' o 'USD'"
            )
        self.ticker = ticker.strip().upper()
        self.moneda = moneda

    def es_renta_fija(self) -> bool:
        return False

    def __str__(self) -> str:
        identificador = self.id if self.id is not None else "sin id"
        return (
            f"ACCION '{self.nombre}' ticker={self.ticker} "
            f"moneda={self.moneda} ({identificador})"
        )