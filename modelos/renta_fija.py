"""Clase abstracta de renta fija (CDT, bono, TES)."""

from abc import ABC
from datetime import date

from modelos.activo import Activo


class RentaFija(Activo, ABC):
    """Título de renta fija. No se instancia directamente.

    Tasas en decimal E.A. (0.12 = 12 %).
    periodicidad_meses: 0 = paga todo al vencimiento; si no, 1, 3, 6 o 12.
    tasa_mercado: tasa E.A. para valorar. Si es None se usa tasa.
    """

    PERIODICIDADES_VALIDAS = (0, 1, 3, 6, 12)
    TIPOS_RENTA_FIJA = ("CDT", "BONO", "TES")

    def __init__(
        self,
        nombre: str,
        tipo: str,
        valor_nominal: float,
        tasa: float,
        fecha_emision: date,
        fecha_vencimiento: date,
        periodicidad_meses: int,
        tasa_mercado: float | None = None,
        id: int | None = None,
    ) -> None:
        if tipo not in self.TIPOS_RENTA_FIJA:
            raise ValueError(
                f"tipo inválido para RentaFija: {tipo!r}. "
                f"Debe ser uno de {self.TIPOS_RENTA_FIJA}"
            )
        super().__init__(nombre=nombre, tipo=tipo, id=id)
        self.valor_nominal = self._dinero_positivo(valor_nominal, "valor_nominal")
        self.tasa = self._tasa(tasa, "tasa")
        if type(fecha_emision) is not date:
            raise ValueError("fecha_emision debe ser datetime.date (sin hora)")
        if type(fecha_vencimiento) is not date:
            raise ValueError("fecha_vencimiento debe ser datetime.date (sin hora)")
        if fecha_vencimiento <= fecha_emision:
            raise ValueError("fecha_vencimiento debe ser posterior a fecha_emision")
        if periodicidad_meses not in self.PERIODICIDADES_VALIDAS:
            raise ValueError(
                "periodicidad_meses debe ser 0, 1, 3, 6 o 12 "
                f"(recibido: {periodicidad_meses})"
            )
        if tasa_mercado is not None:
            tasa_mercado = self._tasa(tasa_mercado, "tasa_mercado")
        self.fecha_emision = fecha_emision
        self.fecha_vencimiento = fecha_vencimiento
        self.periodicidad_meses = periodicidad_meses
        self.tasa_mercado = tasa_mercado

    @staticmethod
    def _dinero_positivo(valor: float, campo: str) -> float:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor <= 0:
            raise ValueError(f"{campo} debe ser un número mayor que 0")
        return float(valor)

    @staticmethod
    def _tasa(valor: float, campo: str) -> float:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor < 0:
            raise ValueError(f"{campo} debe ser un decimal >= 0 (0.12 = 12 %)")
        return float(valor)

    def tasa_de_valoracion(self) -> float:
        """Tasa E.A. para valorar: la de mercado si existe, si no la contractual."""
        if self.tasa_mercado is not None:
            return self.tasa_mercado
        return self.tasa

    # es_renta_fija queda abstracto (lo define Activo).
    # Lo implementan CDT y Bono. Así RentaFija no se puede instanciar.

    def __str__(self) -> str:
        identificador = self.id if self.id is not None else "sin id"
        mercado = (
            f"{self.tasa_mercado:.4%}" if self.tasa_mercado is not None else "misma"
        )
        return (
            f"{self.tipo} '{self.nombre}' nominal={self.valor_nominal:,.2f} COP "
            f"tasa={self.tasa:.4%} mercado={mercado} "
            f"{self.fecha_emision.isoformat()}→{self.fecha_vencimiento.isoformat()} "
            f"cada {self.periodicidad_meses} mes(es) ({identificador})"
        )