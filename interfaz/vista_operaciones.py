import traceback
from datetime import date

import customtkinter as ctk

from interfaz.tema import Tema
from interfaz.vista_base import VistaBase
from modelos.operacion import Operacion


class VistaOperaciones(VistaBase):
    """Formulario para registrar compras y ventas, y tabla con el historial.

    Además de validar los campos, impide vender más de lo que se tiene: simula
    el historial del activo con la operación nueva y rechaza la venta si en
    algún momento el saldo quedaría negativo.
    """

    TIPOS = {"Compra": "COMPRA", "Venta": "VENTA"}
    NOMBRES_OPERACION = {codigo: nombre for nombre, codigo in TIPOS.items()}

    COLUMNAS = [
        ("fecha", "Fecha", 105, "w"), ("activo", "Activo", 190, "w"), ("tipo", "Tipo", 80, "w"),
        ("cantidad", "Cantidad", 90, "e"), ("precio", "Precio", 120, "e"),
        ("comision", "Comisión", 100, "e"), ("bruto", "Valor bruto", 130, "e"),
        ("neto", "Flujo neto", 130, "e"),
    ]

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, repositorio, portafolio, "Operaciones",
                         "Registra compras y ventas. Los precios van en pesos colombianos (COP).")
        self._tipo = "COMPRA"

        cuerpo = self._crear_panel_formulario("Nueva operación")
        self._selector = self._crear_selector(cuerpo, list(self.TIPOS), self._cambiar_tipo)
        rejilla = self._crear_rejilla(cuerpo)
        self._crear_campo(rejilla, "activo", "Activo", valores=[self.SIN_ACTIVOS],
                          comando=lambda _valor: self._actualizar_pista())
        self._crear_campo(rejilla, "fecha", "Fecha", ayuda="AAAA-MM-DD")
        self._crear_campo(rejilla, "cantidad", "Cantidad (acciones o títulos)", ayuda="Ej. 10")
        self._crear_campo(rejilla, "precio", "Precio por unidad (COP)", ayuda="Ej. 950.000")
        self._crear_campo(rejilla, "comision", "Comisión del bróker (COP)", ayuda="Vacío = 0")
        self._colocar_campos(rejilla, ["activo", "fecha", "cantidad", "precio", "comision"])
        self._pista = ctk.CTkLabel(cuerpo, text="", font=Tema.FUENTE_PEQUENA,
                                   text_color=Tema.TEXTO_SECUNDARIO, anchor="w", justify="left")
        self._pista.pack(fill="x", pady=(0, 6))
        self._crear_barra_acciones(cuerpo, "Registrar operación")

        self._tabla = self._crear_tabla(
            "Historial de operaciones", self.COLUMNAS, altura=10,
            texto_eliminar="Eliminar seleccionada",
            eliminar=lambda: self._eliminar_seleccionado(
                self._tabla, self.repositorio.eliminar_operacion,
                seleccion="Selecciona una operación en la tabla.",
                pregunta="¿Eliminar la operación seleccionada? No se puede deshacer.",
                exito="Operación eliminada."))
        self._limpiar()

    # ------------------------------------------------------------------ formulario
    def _cambiar_tipo(self, etiqueta: str) -> None:
        self._tipo = self.TIPOS[etiqueta]

    def _limpiar(self) -> None:
        super()._limpiar()
        self._widgets["fecha"].insert(0, date.today().isoformat())  # lo más común: hoy

    def _actualizar_pista(self) -> None:
        """Recuerda en qué unidades se escribe según el activo elegido."""
        activo = self._activo_elegido()
        if activo is None:
            texto = "Primero registra un activo en la sección Activos."
        elif getattr(activo, "moneda", None) == "USD":
            texto = ("Esta acción cotiza en USD: escribe el precio ya convertido a pesos "
                     "con la TRM del día de la operación.")
        elif activo.tipo != "ACCION":
            texto = "Renta fija: la cantidad es el número de títulos y el precio es por título."
        else:
            texto = ""
        self._pista.configure(text=texto)

    # ------------------------------------------------------------------ pasos del guardado
    def _validar(self):
        datos, errores = {"tipo": self._tipo}, {}
        activo = self._activo_elegido()
        if activo is None:
            errores["activo"] = "Primero registra un activo en la sección Activos."
        fecha = self._fecha(errores, "fecha", "Fecha")
        cantidad = self._numero(errores, "cantidad", "Cantidad", "10")
        if cantidad is not None and cantidad <= 0:
            errores["cantidad"] = "La cantidad debe ser mayor que 0."
        precio = self._numero(errores, "precio", "Precio", "950.000")
        if precio is not None and precio <= 0:
            errores["precio"] = "El precio debe ser mayor que 0."
        comision = self._numero(errores, "comision", "Comisión", "15.000", obligatorio=False)
        if "comision" not in errores and comision is None:
            comision = 0.0
        if comision is not None and comision < 0:
            errores["comision"] = "La comisión no puede ser negativa."

        if not errores and self._tipo == "VENTA":
            mensaje = self._error_de_saldo(activo.id, fecha, cantidad)
            if mensaje:
                errores["cantidad"] = mensaje

        datos.update(activo_id=getattr(activo, "id", None), fecha=fecha, cantidad=cantidad,
                     precio=precio, comision=comision)
        return datos, errores

    def _error_de_saldo(self, activo_id: int, fecha: date, cantidad: float):
        """Simula el historial con la venta nueva. Devuelve un mensaje si el saldo quedaría negativo."""
        movimientos = [
            (o.fecha, 0 if o.tipo == "COMPRA" else 1, o.cantidad if o.tipo == "COMPRA" else -o.cantidad)
            for o in self.repositorio.listar_operaciones(activo_id)]
        movimientos.append((fecha, 1, -cantidad))
        saldo = 0.0
        for dia, _, variacion in sorted(movimientos):  # en un mismo día, primero las compras
            saldo += variacion
            if saldo < -1e-9:
                return (f"No puedes vender tanto: el {dia.isoformat()} el saldo quedaría negativo. "
                        "Revisa la cantidad o la fecha.")
        return None

    def _crear_objeto(self, datos: dict):
        return Operacion(activo_id=datos["activo_id"], tipo=datos["tipo"], fecha=datos["fecha"],
                         cantidad=datos["cantidad"], precio=datos["precio"], comision=datos["comision"])

    def _guardar_objeto(self, operacion) -> None:
        self.repositorio.guardar_operacion(operacion)

    def _mensaje_exito(self, operacion) -> str:
        activo = self.repositorio.obtener_activo(operacion.activo_id)
        return f"{self.NOMBRES_OPERACION[operacion.tipo]} registrada: {activo.nombre if activo else ''}"

    # ------------------------------------------------------------------ tabla
    def refrescar(self) -> None:
        try:
            self._actualizar_menu_activos()
            self._actualizar_pista()
            por_id = {a.id: a for a in self._activos.values()}
            operaciones = list(reversed(self.repositorio.listar_operaciones()))  # lo más reciente arriba
            filas = []
            for o in operaciones:
                activo = por_id.get(o.activo_id)
                filas.append([
                    o.fecha.isoformat(), activo.nombre if activo else f"Activo {o.activo_id}",
                    self.NOMBRES_OPERACION.get(o.tipo, o.tipo), Tema.cantidad(o.cantidad),
                    Tema.pesos(o.precio), Tema.pesos(o.comision), Tema.pesos(o.valor_bruto),
                    Tema.pesos(o.flujo_neto)])
            self._tabla.cargar(filas, ids=[o.id for o in operaciones])
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
            traceback.print_exc()
            self._mostrar_estado(f"No se pudieron cargar las operaciones: {error}", error=True)
