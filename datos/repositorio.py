"""Persistencia SQLite del portafolio."""

import sqlite3
from datetime import date

from modelos.accion import Accion
from modelos.bono import Bono
from modelos.cdt import CDT
from modelos.flujo_caja import FlujoCaja
from modelos.operacion import Operacion
from modelos.tes import TES


class Repositorio:
    """Guarda y lee activos, operaciones, flujos y precios manuales.

    Fechas en texto ISO AAAA-MM-DD. Consultas siempre con parámetros.
    """

    def __init__(self, ruta_db: str = "portafolio.db") -> None:
        self.ruta_db = ruta_db
        self._conexion = sqlite3.connect(ruta_db)
        self._conexion.row_factory = sqlite3.Row
        self._conexion.execute("PRAGMA foreign_keys = ON")
        self._crear_tablas()

    def cerrar(self) -> None:
        self._conexion.close()

    def _crear_tablas(self) -> None:
        self._conexion.executescript(
            """
            CREATE TABLE IF NOT EXISTS activos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                ticker TEXT,
                moneda TEXT,
                valor_nominal REAL,
                tasa REAL,
                fecha_emision TEXT,
                fecha_vencimiento TEXT,
                periodicidad_meses INTEGER,
                tasa_mercado REAL
            );

            CREATE TABLE IF NOT EXISTS operaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activo_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                fecha TEXT NOT NULL,
                cantidad REAL NOT NULL,
                precio REAL NOT NULL,
                comision REAL NOT NULL,
                FOREIGN KEY (activo_id) REFERENCES activos(id)
            );

            CREATE TABLE IF NOT EXISTS flujos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activo_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                fecha TEXT NOT NULL,
                valor_bruto REAL NOT NULL,
                retencion REAL NOT NULL,
                FOREIGN KEY (activo_id) REFERENCES activos(id)
            );

            CREATE TABLE IF NOT EXISTS precios (
                ticker TEXT NOT NULL,
                fecha TEXT NOT NULL,
                precio REAL NOT NULL,
                fuente TEXT NOT NULL,
                PRIMARY KEY (ticker, fecha)
            );
            """
        )
        self._conexion.commit()

    def guardar_activo(self, activo) -> int:
        fila = self._fila_activo(activo)
        if activo.id is None:
            cursor = self._conexion.execute(
                """
                INSERT INTO activos (
                    nombre, tipo, ticker, moneda, valor_nominal, tasa,
                    fecha_emision, fecha_vencimiento, periodicidad_meses, tasa_mercado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                fila,
            )
            activo.id = int(cursor.lastrowid)
        else:
            cursor = self._conexion.execute(
                """
                UPDATE activos SET
                    nombre = ?, tipo = ?, ticker = ?, moneda = ?,
                    valor_nominal = ?, tasa = ?, fecha_emision = ?,
                    fecha_vencimiento = ?, periodicidad_meses = ?, tasa_mercado = ?
                WHERE id = ?
                """,
                (*fila, activo.id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"no existe un activo con id={activo.id}")
        self._conexion.commit()
        return activo.id

    def guardar_operacion(self, op: Operacion) -> int:
        valores = (
            op.activo_id,
            op.tipo,
            op.fecha.isoformat(),
            op.cantidad,
            op.precio,
            op.comision,
        )
        try:
            if op.id is None:
                cursor = self._conexion.execute(
                    """
                    INSERT INTO operaciones
                        (activo_id, tipo, fecha, cantidad, precio, comision)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    valores,
                )
                op.id = int(cursor.lastrowid)
            else:
                cursor = self._conexion.execute(
                    """
                    UPDATE operaciones SET
                        activo_id = ?, tipo = ?, fecha = ?,
                        cantidad = ?, precio = ?, comision = ?
                    WHERE id = ?
                    """,
                    (*valores, op.id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"no existe una operacion con id={op.id}")
            self._conexion.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"no existe un activo con id={op.activo_id}"
            ) from exc
        return op.id

    def guardar_flujo(self, flujo: FlujoCaja) -> int:
        valores = (
            flujo.activo_id,
            flujo.tipo,
            flujo.fecha.isoformat(),
            flujo.valor_bruto,
            flujo.retencion,
        )
        try:
            if flujo.id is None:
                cursor = self._conexion.execute(
                    """
                    INSERT INTO flujos
                        (activo_id, tipo, fecha, valor_bruto, retencion)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    valores,
                )
                flujo.id = int(cursor.lastrowid)
            else:
                cursor = self._conexion.execute(
                    """
                    UPDATE flujos SET
                        activo_id = ?, tipo = ?, fecha = ?,
                        valor_bruto = ?, retencion = ?
                    WHERE id = ?
                    """,
                    (*valores, flujo.id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"no existe un flujo con id={flujo.id}")
            self._conexion.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"no existe un activo con id={flujo.activo_id}"
            ) from exc
        return flujo.id

    def eliminar_operacion(self, id: int) -> None:
        cursor = self._conexion.execute(
            "DELETE FROM operaciones WHERE id = ?", (id,)
        )
        if cursor.rowcount == 0:
            raise ValueError(f"no existe una operacion con id={id}")
        self._conexion.commit()

    def eliminar_flujo(self, id: int) -> None:
        cursor = self._conexion.execute(
            "DELETE FROM flujos WHERE id = ?", (id,)
        )
        if cursor.rowcount == 0:
            raise ValueError(f"no existe un flujo con id={id}")
        self._conexion.commit()

    def listar_activos(self) -> list:
        filas = self._conexion.execute(
            "SELECT * FROM activos ORDER BY id"
        ).fetchall()
        return [self._activo_desde_fila(fila) for fila in filas]

    def obtener_activo(self, id: int):
        fila = self._conexion.execute(
            "SELECT * FROM activos WHERE id = ?", (id,)
        ).fetchone()
        if fila is None:
            raise ValueError(f"no existe un activo con id={id}")
        return self._activo_desde_fila(fila)

    def listar_operaciones(self, activo_id: int | None = None) -> list[Operacion]:
        if activo_id is None:
            filas = self._conexion.execute(
                "SELECT * FROM operaciones ORDER BY fecha, id"
            ).fetchall()
        else:
            filas = self._conexion.execute(
                """
                SELECT * FROM operaciones
                WHERE activo_id = ?
                ORDER BY fecha, id
                """,
                (activo_id,),
            ).fetchall()
        return [self._operacion_desde_fila(fila) for fila in filas]

    def listar_flujos(self, activo_id: int | None = None) -> list[FlujoCaja]:
        if activo_id is None:
            filas = self._conexion.execute(
                "SELECT * FROM flujos ORDER BY fecha, id"
            ).fetchall()
        else:
            filas = self._conexion.execute(
                """
                SELECT * FROM flujos
                WHERE activo_id = ?
                ORDER BY fecha, id
                """,
                (activo_id,),
            ).fetchall()
        return [self._flujo_desde_fila(fila) for fila in filas]

    def guardar_precio_manual(self, ticker: str, fecha: date, precio: float) -> None:
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("ticker debe ser un texto no vacío")
        if type(fecha) is not date:
            raise ValueError("fecha debe ser datetime.date (sin hora)")
        if isinstance(precio, bool) or not isinstance(precio, (int, float)) or precio <= 0:
            raise ValueError("precio debe ser mayor que 0")
        self._conexion.execute(
            """
            INSERT INTO precios (ticker, fecha, precio, fuente)
            VALUES (?, ?, ?, 'manual')
            ON CONFLICT(ticker, fecha) DO UPDATE SET
                precio = excluded.precio,
                fuente = 'manual'
            """,
            (ticker.strip().upper(), fecha.isoformat(), float(precio)),
        )
        self._conexion.commit()

    def _fila_activo(self, activo) -> tuple:
        ticker = getattr(activo, "ticker", None)
        moneda = getattr(activo, "moneda", None)
        valor_nominal = getattr(activo, "valor_nominal", None)
        tasa = getattr(activo, "tasa", None)
        fecha_emision = getattr(activo, "fecha_emision", None)
        fecha_vencimiento = getattr(activo, "fecha_vencimiento", None)
        periodicidad = getattr(activo, "periodicidad_meses", None)
        tasa_mercado = getattr(activo, "tasa_mercado", None)
        return (
            activo.nombre,
            activo.tipo,
            ticker,
            moneda,
            valor_nominal,
            tasa,
            fecha_emision.isoformat() if fecha_emision is not None else None,
            fecha_vencimiento.isoformat() if fecha_vencimiento is not None else None,
            periodicidad,
            tasa_mercado,
        )

    def _activo_desde_fila(self, fila: sqlite3.Row):
        tipo = fila["tipo"]
        if tipo == "ACCION":
            return Accion(
                nombre=fila["nombre"],
                ticker=fila["ticker"],
                moneda=fila["moneda"],
                id=fila["id"],
            )
        comunes = dict(
            nombre=fila["nombre"],
            valor_nominal=fila["valor_nominal"],
            tasa=fila["tasa"],
            fecha_emision=date.fromisoformat(fila["fecha_emision"]),
            fecha_vencimiento=date.fromisoformat(fila["fecha_vencimiento"]),
            periodicidad_meses=fila["periodicidad_meses"],
            tasa_mercado=fila["tasa_mercado"],
            id=fila["id"],
        )
        if tipo == "CDT":
            return CDT(**comunes)
        if tipo == "BONO":
            return Bono(**comunes)
        if tipo == "TES":
            return TES(**comunes)
        raise ValueError(f"tipo de activo desconocido en la base: {tipo!r}")

    @staticmethod
    def _operacion_desde_fila(fila: sqlite3.Row) -> Operacion:
        return Operacion(
            activo_id=fila["activo_id"],
            tipo=fila["tipo"],
            fecha=date.fromisoformat(fila["fecha"]),
            cantidad=fila["cantidad"],
            precio=fila["precio"],
            comision=fila["comision"],
            id=fila["id"],
        )

    @staticmethod
    def _flujo_desde_fila(fila: sqlite3.Row) -> FlujoCaja:
        return FlujoCaja(
            activo_id=fila["activo_id"],
            tipo=fila["tipo"],
            fecha=date.fromisoformat(fila["fecha"]),
            valor_bruto=fila["valor_bruto"],
            retencion=fila["retencion"],
            id=fila["id"],
        )