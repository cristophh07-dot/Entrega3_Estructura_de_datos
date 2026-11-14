import traceback
from datetime import date, datetime

import customtkinter as ctk

from interfaz.tema import Tema
from interfaz.vista_base import VistaBase
from modelos.operacion import Operacion


class VistaOperaciones(VistaBase):
    """Formulario para registrar compras y ventas, y tabla con el historial.

    Para no tener que buscar datos a mano:
      - al elegir el activo y la fecha, el precio se llena solo con el precio de
        mercado de ese día (portafolio.precio_sugerido);
      - al escribir la cantidad, la comisión se calcula sola con la tarifa estándar
        del bróker (portafolio.comision_sugerida);
      - en una venta se muestra cuántas acciones se tienen en esa fecha.
    Los dos campos siguen siendo editables: si el usuario los cambia, se respeta su valor.

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
                         "Registra compras y ventas. El precio y la comisión se llenan solos; "
                         "puedes cambiarlos. Todo en pesos colombianos (COP).")
        self._tipo = "COMPRA"
        self._precio_manual = False      # True si el usuario escribió el precio
        self._comision_manual = False    # True si el usuario escribió la comisión
        self._estado_precio = None       # "mercado" | "sin_precio" | None
        self._regla_comision = ""

        cuerpo = self._crear_panel_formulario("Nueva operación")
        self._selector = self._crear_selector(cuerpo, list(self.TIPOS), self._cambiar_tipo)
        rejilla = self._crear_rejilla(cuerpo)
        self._crear_campo(rejilla, "activo", "Activo", valores=[self.SIN_ACTIVOS],
                          comando=lambda _valor: self._al_cambiar_activo())
        self._crear_campo(rejilla, "fecha", "Fecha", ayuda="AAAA-MM-DD")
        self._crear_campo(rejilla, "cantidad", "Cantidad (acciones o títulos)", ayuda="Ej. 10")
        self._crear_campo(rejilla, "precio", "Precio por unidad (COP)", ayuda="Se llena solo")
        self._crear_campo(rejilla, "comision", "Comisión del bróker (COP)", ayuda="Se calcula sola")
        self._colocar_campos(rejilla, ["activo", "fecha", "cantidad", "precio", "comision"])
        self._pista = ctk.CTkLabel(cuerpo, text="", font=Tema.FUENTE_PEQUENA,
                                   text_color=Tema.TEXTO_SECUNDARIO, anchor="w", justify="left")
        self._pista.pack(fill="x", pady=(0, 6))
        self._crear_barra_acciones(cuerpo, "Registrar operación")
        self._conectar_eventos()

        self._tabla = self._crear_tabla(
            "Historial de operaciones", self.COLUMNAS, altura=10,
            texto_eliminar="Eliminar seleccionada",
            eliminar=lambda: self._eliminar_seleccionado(
                self._tabla, self.repositorio.eliminar_operacion,
                seleccion="Selecciona una operación en la tabla.",
                pregunta="¿Eliminar la operación seleccionada? No se puede deshacer.",
                exito="Operación eliminada."))
        self._limpiar()

    def _conectar_eventos(self) -> None:
        """Cada cambio en el formulario actualiza el precio, la comisión y la pista."""
        self._widgets["fecha"].bind("<FocusOut>", lambda _e: self._sugerir_precio())
        self._widgets["fecha"].bind("<KeyRelease>", lambda _e: self._sugerir_precio())
        self._widgets["cantidad"].bind("<KeyRelease>", lambda _e: self._recalcular())
        self._widgets["precio"].bind("<Key>", lambda e: self._marcar_manual(e, "precio"))
        self._widgets["precio"].bind("<KeyRelease>", lambda _e: self._recalcular())
        self._widgets["comision"].bind("<Key>", lambda e: self._marcar_manual(e, "comision"))

    def _marcar_manual(self, evento, campo: str) -> None:
        """Si el usuario escribe en el precio o la comisión, ya no se llenan solos."""
        escribe = (evento.char and evento.char.isprintable()) or evento.keysym in ("BackSpace", "Delete")
        if not escribe:
            return   # Tab, flechas, Enter...
        if campo == "precio":
            self._precio_manual = True
        else:
            self._comision_manual = True

    # ------------------------------------------------------------------ llenado automático
    def _cambiar_tipo(self, etiqueta: str) -> None:
        self._tipo = self.TIPOS[etiqueta]
        self._actualizar_pista()

    def _al_cambiar_activo(self) -> None:
        self._precio_manual = False   # otro activo: vuelve a sugerir su precio
        self._sugerir_precio()

    def _fecha_valida(self):
        try:
            return datetime.strptime(self._leer_texto("fecha"), "%Y-%m-%d").date()
        except ValueError:
            return None

    def _numero_valido(self, clave: str):
        try:
            return self._leer_numero(self._leer_texto(clave))
        except ValueError:
            return None

    def _escribir(self, clave: str, texto: str) -> None:
        campo = self._widgets[clave]
        campo.delete(0, "end")
        campo.insert(0, texto)

    def _sugerir_precio(self) -> None:
        """Pone el precio de mercado del activo en la fecha elegida (si el usuario no lo cambió)."""
        activo, fecha = self._activo_elegido(), self._fecha_valida()
        if activo is None or fecha is None or self._precio_manual:
            self._recalcular()
            return
        try:
            precio = self.portafolio.precio_sugerido(activo, fecha)
        except Exception:  # noqa: BLE001 - sin internet o sin datos: se escribe a mano
            traceback.print_exc()
            precio = None
        if precio:
            self._escribir("precio", Tema._numero(precio, 2 if precio < 1000 else 0))
            self._estado_precio = "mercado"
        else:
            self._escribir("precio", "")
            self._estado_precio = "sin_precio"
        self._recalcular()

    def _recalcular(self) -> None:
        """Calcula la comisión estándar con cantidad × precio (si el usuario no la cambió)."""
        cantidad, precio = self._numero_valido("cantidad"), self._numero_valido("precio")
        if cantidad and precio and cantidad > 0 and precio > 0:
            comision, self._regla_comision = self.portafolio.comision_sugerida(cantidad * precio)
            if not self._comision_manual:
                self._escribir("comision", Tema._numero(round(comision), 0))
        else:
            self._regla_comision = ""
            if not self._comision_manual:
                self._escribir("comision", "")
        self._actualizar_pista()

    def _limpiar(self) -> None:
        super()._limpiar()
        self._precio_manual = self._comision_manual = False
        self._estado_precio, self._regla_comision = None, ""
        self._widgets["fecha"].insert(0, date.today().isoformat())  # lo más común: hoy
        self._sugerir_precio()

    def _actualizar_pista(self) -> None:
        """Explica de dónde salió cada valor del formulario."""
        activo = self._activo_elegido()
        if activo is None:
            self._pista.configure(text="Primero registra un activo en la sección Activos.")
            return
        fecha, precio = self._fecha_valida(), self._numero_valido("precio")
        renta_fija = activo.tipo != "ACCION"
        lineas = []

        if self._precio_manual:
            lineas.append("Precio escrito a mano.")
        elif self._estado_precio == "mercado" and fecha:
            lineas.append(f"Precio de mercado del {fecha.isoformat()}. "
                          "Puedes cambiarlo por el que te dio tu bróker.")
        elif self._estado_precio == "sin_precio":
            lineas.append("No se encontró precio para esa fecha; escríbelo a mano.")

        if getattr(activo, "moneda", None) == "USD" and precio and fecha:
            trm = self.portafolio.trm_en(fecha)
            lineas.append(f"≈ {Tema.dolares(precio / trm)} por acción "
                          f"(TRM {Tema._numero(trm, 2)} del {fecha.isoformat()}).")
        if renta_fija:
            lineas.append("Renta fija: la cantidad es el número de títulos y el precio es por título.")

        if self._comision_manual:
            lineas.append("Comisión escrita a mano.")
        elif self._regla_comision:
            lineas.append(f"Comisión estándar: {self._regla_comision}. Puedes cambiarla.")

        if self._tipo == "VENTA" and fecha:
            tienes = self.portafolio.cantidad_disponible(activo.id, fecha)
            unidad = "títulos" if renta_fija else "acciones"
            lineas.append(f"Tienes {Tema.cantidad(tienes)} {unidad} de {activo.nombre} al {fecha.isoformat()}.")

        self._pista.configure(text="\n".join(lineas))

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
            if not self._leer_texto("precio"):
                self._sugerir_precio()
            else:
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
