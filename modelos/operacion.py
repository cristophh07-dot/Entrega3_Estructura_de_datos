
from datetime import date


class Operacion:

    TIPOS_VALIDOS = ("COMPRA", "VENTA")

    def __init__(
        self,
        activo_id: int,
        tipo: str,
        fecha: date,
        cantidad: float,
        precio: float,
        comision: float = 0.0,
        id: int | None = None,
    ) -> None:
        if not isinstance(activo_id, int) or isinstance(activo_id, bool) or activo_id < 1:
            raise ValueError("activo_id debe ser un entero positivo")
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(f"tipo inválido: {tipo!r}. Debe ser 'COMPRA' o 'VENTA'")
        if type(fecha) is not date:
            raise ValueError("fecha debe ser datetime.date (sin hora)")
        if isinstance(cantidad, bool) or not isinstance(cantidad, (int, float)) or cantidad <= 0:
            raise ValueError("cantidad debe ser mayor que 0")
        if isinstance(precio, bool) or not isinstance(precio, (int, float)) or precio <= 0:
            raise ValueError("precio debe ser mayor que 0")
        if isinstance(comision, bool) or not isinstance(comision, (int, float)) or comision < 0:
            raise ValueError("comision debe ser mayor o igual que 0")
        if id is not None and (not isinstance(id, int) or isinstance(id, bool) or id < 1):
            raise ValueError("id debe ser un entero positivo o None")
        self.id = id
        self.activo_id = activo_id
        self.tipo = tipo
        self.fecha = fecha
        self.cantidad = float(cantidad)
        self.precio = float(precio)
        self.comision = float(comision)

    @property
    def valor_bruto(self) -> float:
        return self.cantidad * self.precio

    @property
    def flujo_neto(self) -> float:
        if self.tipo == "COMPRA":
            return -(self.valor_bruto + self.comision)
        return self.valor_bruto - self.comision

    def __str__(self) -> str:
        identificador = self.id if self.id is not None else "sin id"
        cantidad_txt = (
            f"{self.cantidad:.0f}" if float(self.cantidad).is_integer()
            else f"{self.cantidad}"
        )
        return (
            f"{self.tipo} activo_id={self.activo_id} "
            f"{cantidad_txt} x {self.precio:,.2f} COP "
            f"comision={self.comision:,.2f} neto={self.flujo_neto:,.2f} "
            f"el {self.fecha.isoformat()} ({identificador})"
        )