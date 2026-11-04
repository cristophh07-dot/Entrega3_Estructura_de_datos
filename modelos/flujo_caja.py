
from datetime import date


class FlujoCaja:

    TIPOS_VALIDOS = ("DIVIDENDO", "INTERES", "CAPITAL", "OTRO")

    def __init__(
        self,
        activo_id: int,
        tipo: str,
        fecha: date,
        valor_bruto: float,
        retencion: float = 0.0,
        id: int | None = None,
    ) -> None:
        if not isinstance(activo_id, int) or isinstance(activo_id, bool) or activo_id < 1:
            raise ValueError("activo_id debe ser un entero positivo")
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(
                f"tipo inválido: {tipo!r}. Debe ser uno de {self.TIPOS_VALIDOS}"
            )
        if type(fecha) is not date:
            raise ValueError("fecha debe ser datetime.date (sin hora)")
        if (
            isinstance(valor_bruto, bool)
            or not isinstance(valor_bruto, (int, float))
            or valor_bruto <= 0
        ):
            raise ValueError("valor_bruto debe ser mayor que 0")
        if (
            isinstance(retencion, bool)
            or not isinstance(retencion, (int, float))
            or not 0 <= retencion <= 1
        ):
            raise ValueError("retencion debe estar entre 0 y 1")
        if id is not None and (not isinstance(id, int) or isinstance(id, bool) or id < 1):
            raise ValueError("id debe ser un entero positivo o None")
        self.id = id
        self.activo_id = activo_id
        self.tipo = tipo
        self.fecha = fecha
        self.valor_bruto = float(valor_bruto)
        self.retencion = float(retencion)

    @property
    def valor_neto(self) -> float:
        return self.valor_bruto * (1 - self.retencion)

    def __str__(self) -> str:
        identificador = self.id if self.id is not None else "sin id"
        return (
            f"{self.tipo} activo_id={self.activo_id} "
            f"bruto={self.valor_bruto:,.2f} COP retencion={self.retencion:.2%} "
            f"neto={self.valor_neto:,.2f} el {self.fecha.isoformat()} ({identificador})"
        )