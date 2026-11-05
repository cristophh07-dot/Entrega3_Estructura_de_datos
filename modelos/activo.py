
from abc import ABC, abstractmethod


class Activo(ABC):

    TIPOS_VALIDOS = ("ACCION", "CDT", "BONO", "TES")

    def __init__(self, nombre: str, tipo: str, id: int | None = None) -> None:
        if not isinstance(nombre, str) or not nombre.strip():
            raise ValueError("nombre debe ser un texto no vacío")
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(
                f"tipo inválido: {tipo!r}. Debe ser uno de {self.TIPOS_VALIDOS}"
            )
        if id is not None and (not isinstance(id, int) or isinstance(id, bool) or id < 1):
            raise ValueError("id debe ser un entero positivo o None")
        self.id = id
        self.nombre = nombre.strip()
        self.tipo = tipo

    @abstractmethod
    def es_renta_fija(self) -> bool:

    def __str__(self) -> str:
        identificador = self.id if self.id is not None else "sin id"
        return f"{self.tipo} '{self.nombre}' ({identificador})"