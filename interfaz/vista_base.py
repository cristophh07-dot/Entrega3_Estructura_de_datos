import re
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from interfaz.tabla_datos import TablaDatos
from interfaz.tema import Tema


class VistaBase(ctk.CTkFrame, ABC):
    """Base de las vistas con formulario y tabla (Activos, Operaciones y Flujos).

    Reúne lo que las tres hacen igual: marco con scroll, paneles, campos,
    lectura de números y fechas, mensajes de estado y la tabla con su botón
    de eliminar. El guardado es un método plantilla (Template Method): _guardar()
    fija los pasos (validar, crear el objeto, guardarlo, limpiar, recargar y
    actualizar el portafolio) y cada subclase completa solo lo propio con
    _validar(), _crear_objeto(), _guardar_objeto(), _mensaje_exito() y refrescar().
    """

    NOMBRES_TIPO = {"ACCION": "Acción", "CDT": "CDT", "BONO": "Bono", "TES": "TES"}
    SIN_ACTIVOS = "(sin activos registrados)"
    COLUMNAS_FORMULARIO = 4

    def __init__(self, master, repositorio, portafolio, titulo: str, subtitulo: str):
        super().__init__(master, fg_color=Tema.FONDO, corner_radius=0)
        self.repositorio = repositorio
        self.portafolio = portafolio
        self._marcos = {}    # clave -> marco (etiqueta + widget) de cada campo
        self._widgets = {}   # clave -> CTkEntry o CTkOptionMenu
        self._activos = {}   # etiqueta del menú -> activo (se llena en _actualizar_menu_activos)

        # El contenido va dentro de un marco con scroll porque puede no caber en 760 px.
        self._contenido = ctk.CTkScrollableFrame(
            self, fg_color=Tema.FONDO, corner_radius=0,
            scrollbar_button_color=Tema.BORDE, scrollbar_button_hover_color=Tema.TEXTO_SECUNDARIO)
        self._contenido.pack(fill="both", expand=True)

        encabezado = ctk.CTkFrame(self._contenido, fg_color="transparent")
        encabezado.pack(fill="x", padx=Tema.MARGEN, pady=(Tema.MARGEN, 12))
        ctk.CTkLabel(encabezado, text=titulo, font=Tema.FUENTE_TITULO,
                     text_color=Tema.TEXTO).pack(anchor="w")
        ctk.CTkLabel(encabezado, text=subtitulo, font=Tema.FUENTE_PEQUENA,
                     text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w")

    # ------------------------------------------------------------------ lo que cada vista completa
    @abstractmethod
    def _validar(self):
        """Lee el formulario. Devuelve (datos, errores); errores es {clave de campo: mensaje}."""

    @abstractmethod
    def _crear_objeto(self, datos: dict):
        """Construye el objeto de modelos/ (que vuelve a validar y puede lanzar ValueError)."""

    @abstractmethod
    def _guardar_objeto(self, objeto) -> None:
        """Lo guarda con el repositorio."""

    @abstractmethod
    def _mensaje_exito(self, objeto) -> str:
        """Texto que se muestra cuando se guardó bien."""

    @abstractmethod
    def refrescar(self) -> None:
        """Vuelve a leer los datos del repositorio y recarga la tabla."""

    # ------------------------------------------------------------------ guardado (método plantilla)
    def _guardar(self) -> None:
        datos, errores = self._validar()
        self._marcar_errores(errores)
        if errores:
            self._mostrar_estado(next(iter(errores.values())), error=True)
            return
        try:
            objeto = self._crear_objeto(datos)
            self._guardar_objeto(objeto)
        except ValueError as error:
            self._mostrar_estado(f"Dato inválido: {error}", error=True)
            return
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
            traceback.print_exc()
            self._mostrar_estado(f"No se pudo guardar: {error}", error=True)
            return

        self._limpiar()
        self.refrescar()
        try:
            self.portafolio.actualizar()
            self._mostrar_estado(self._mensaje_exito(objeto))
        except Exception as error:  # noqa: BLE001
            traceback.print_exc()
            self._mostrar_estado(f"Se guardó, pero no se pudo actualizar el portafolio: {error}",
                                 error=True)

    def _limpiar(self) -> None:
        """Vacía las entradas y quita los errores. Las subclases ponen sus valores por defecto."""
        for widget in self._widgets.values():
            if isinstance(widget, ctk.CTkEntry):
                widget.delete(0, "end")
        self._marcar_errores({})
        self._mostrar_estado("")

    def _eliminar_seleccionado(self, tabla: TablaDatos, eliminar, seleccion: str,
                               pregunta: str, exito: str) -> None:
        """Elimina la fila seleccionada de la tabla, pidiendo confirmación."""
        identificador = tabla.seleccionado()
        if identificador is None:
            self._mostrar_estado(seleccion, error=True)
            return
        if not messagebox.askyesno("Confirmar eliminación", pregunta):
            return
        try:
            eliminar(int(identificador))
            self.portafolio.actualizar()
        except Exception as error:  # noqa: BLE001
            traceback.print_exc()
            self._mostrar_estado(f"No se pudo eliminar: {error}", error=True)
        else:
            self.refrescar()
            self._mostrar_estado(exito)

    # ------------------------------------------------------------------ piezas de la pantalla
    @staticmethod
    def _crear_panel(master, titulo: str) -> ctk.CTkFrame:
        """Panel plano con borde de 1 px y el título separado por una línea fina."""
        panel = ctk.CTkFrame(master, fg_color=Tema.TARJETA, corner_radius=Tema.RADIO,
                             border_width=1, border_color=Tema.BORDE)
        ctk.CTkLabel(panel, text=titulo, font=Tema.FUENTE_SUBTITULO,
                     text_color=Tema.TEXTO).pack(anchor="w", padx=16, pady=(12, 10))
        ctk.CTkFrame(panel, height=1, fg_color=Tema.BORDE, corner_radius=0).pack(fill="x")
        return panel

    def _crear_panel_formulario(self, titulo: str) -> ctk.CTkFrame:
        panel = self._crear_panel(self._contenido, titulo)
        panel.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))
        cuerpo = ctk.CTkFrame(panel, fg_color="transparent")
        cuerpo.pack(fill="x", padx=16, pady=14)
        return cuerpo

    @staticmethod
    def _crear_selector(master, valores: list, comando) -> ctk.CTkSegmentedButton:
        selector = ctk.CTkSegmentedButton(
            master, values=valores, command=comando, font=Tema.FUENTE_NORMAL, width=360,
            height=34, corner_radius=Tema.RADIO, border_width=1, fg_color=Tema.BORDE,
            selected_color=Tema.BORDE, selected_hover_color=Tema.BORDE,
            unselected_color=Tema.FONDO, unselected_hover_color=Tema.HOVER, text_color=Tema.TEXTO)
        selector.set(valores[0])
        selector.pack(anchor="w")
        return selector

    def _crear_rejilla(self, master) -> ctk.CTkFrame:
        rejilla = ctk.CTkFrame(master, fg_color="transparent")
        rejilla.pack(fill="x", pady=(14, 0))
        for columna in range(self.COLUMNAS_FORMULARIO):
            rejilla.grid_columnconfigure(columna, weight=1, uniform="campos")
        return rejilla

    def _crear_campo(self, rejilla, clave: str, etiqueta: str, valores=None, ayuda: str = "",
                     comando=None) -> None:
        """Crea un campo (etiqueta + widget). Con 'valores' es un menú; sin ellos, una entrada de texto."""
        marco = ctk.CTkFrame(rejilla, fg_color="transparent")
        ctk.CTkLabel(marco, text=etiqueta, font=Tema.FUENTE_PEQUENA,
                     text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w", pady=(0, 4))
        if valores is None:
            widget = ctk.CTkEntry(
                marco, placeholder_text=ayuda, height=34, corner_radius=Tema.RADIO,
                border_width=1, border_color=Tema.BORDE, fg_color=Tema.FONDO,
                text_color=Tema.TEXTO, placeholder_text_color=Tema.TEXTO_SECUNDARIO,
                font=Tema.FUENTE_NORMAL)
            widget.bind("<Return>", lambda _evento: self._guardar())
        else:
            widget = ctk.CTkOptionMenu(
                marco, values=valores, command=comando, height=34, corner_radius=Tema.RADIO,
                anchor="w", fg_color=Tema.FONDO, button_color=Tema.BORDE,
                button_hover_color=Tema.HOVER, text_color=Tema.TEXTO, font=Tema.FUENTE_NORMAL,
                dropdown_font=Tema.FUENTE_NORMAL, dropdown_fg_color=Tema.PANEL,
                dropdown_hover_color=Tema.HOVER, dropdown_text_color=Tema.TEXTO)
        widget.pack(fill="x")
        self._marcos[clave] = marco
        self._widgets[clave] = widget

    def _colocar_campos(self, rejilla, claves: list) -> None:
        """Muestra solo los campos indicados, de a cuatro por fila."""
        for marco in self._marcos.values():
            marco.grid_forget()
        for posicion, clave in enumerate(claves):
            self._marcos[clave].grid(row=posicion // self.COLUMNAS_FORMULARIO,
                                     column=posicion % self.COLUMNAS_FORMULARIO,
                                     sticky="ew", padx=(0, 12), pady=(0, 10))

    def _crear_barra_acciones(self, master, texto_guardar: str) -> None:
        barra = ctk.CTkFrame(master, fg_color="transparent")
        barra.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(
            barra, text=texto_guardar, height=34, width=150, corner_radius=Tema.RADIO,
            font=Tema.FUENTE_NORMAL, fg_color=Tema.ACENTO, hover_color=Tema.ACENTO_HOVER,
            text_color=Tema.TEXTO_SOBRE_ACENTO, command=self._guardar).pack(side="left")
        ctk.CTkButton(
            barra, text="Limpiar", height=34, width=100, corner_radius=Tema.RADIO,
            font=Tema.FUENTE_NORMAL, fg_color="transparent", border_width=1,
            border_color=Tema.BORDE, text_color=Tema.TEXTO, hover_color=Tema.HOVER,
            command=self._limpiar).pack(side="left", padx=(10, 0))
        self._estado = ctk.CTkLabel(barra, text="", font=Tema.FUENTE_PEQUENA,
                                    text_color=Tema.TEXTO_SECUNDARIO, anchor="w", justify="left")
        self._estado.pack(side="left", padx=16)

    def _crear_tabla(self, titulo: str, columnas: list, altura: int = 9,
                     texto_eliminar: str = "", eliminar=None) -> TablaDatos:
        """Panel con una tabla y, si se indica, un botón para eliminar la fila seleccionada."""
        panel = self._crear_panel(self._contenido, titulo)
        panel.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))
        tabla = TablaDatos(panel, columnas, altura=altura)
        tabla.pack(fill="both", expand=True, padx=12, pady=(8, 8 if eliminar else 14))
        if eliminar:
            ctk.CTkButton(
                panel, text=texto_eliminar, height=32, corner_radius=Tema.RADIO,
                font=Tema.FUENTE_PEQUENA, fg_color="transparent", border_width=1,
                border_color=Tema.PERDIDA, text_color=Tema.PERDIDA, hover_color=Tema.HOVER,
                command=eliminar).pack(anchor="e", padx=16, pady=(0, 14))
        return tabla

    # ------------------------------------------------------------------ estado y errores
    def _mostrar_estado(self, texto: str, error: bool = False) -> None:
        self._estado.configure(text=texto, text_color=Tema.PERDIDA if error else Tema.TEXTO)

    def _marcar_errores(self, errores: dict) -> None:
        for clave, widget in self._widgets.items():
            if isinstance(widget, ctk.CTkEntry):
                widget.configure(border_color=Tema.PERDIDA if clave in errores else Tema.BORDE)

    # ------------------------------------------------------------------ lectura y validación
    def _leer_texto(self, clave: str) -> str:
        return self._widgets[clave].get().strip()

    @staticmethod
    def _leer_numero(texto: str) -> float:
        """Acepta 5000000, 5.000.000, 5.000.000,50, 10,5 y 10.5. Lanza ValueError si no es un número."""
        limpio = texto.strip().replace("$", "").replace("%", "").replace(" ", "")
        if "," in limpio:  # formato colombiano: punto = miles, coma = decimal
            limpio = limpio.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(\.\d{3})+", limpio):  # 5.000.000
            limpio = limpio.replace(".", "")
        if not re.fullmatch(r"-?\d+(\.\d+)?", limpio):
            raise ValueError("no es un número")
        return float(limpio)

    def _numero(self, errores: dict, clave: str, etiqueta: str, ejemplo: str,
                obligatorio: bool = True):
        """Lee un campo numérico. Si hay error lo anota en 'errores' y devuelve None."""
        texto = self._leer_texto(clave)
        if not texto:
            if obligatorio:
                errores[clave] = f"{etiqueta}: este campo es obligatorio."
            return None
        try:
            return self._leer_numero(texto)
        except ValueError:
            errores[clave] = f"{etiqueta}: escribe un número, por ejemplo {ejemplo}."
            return None

    def _fecha(self, errores: dict, clave: str, etiqueta: str):
        """Lee una fecha AAAA-MM-DD. Si hay error lo anota en 'errores' y devuelve None."""
        texto = self._leer_texto(clave)
        if not texto:
            errores[clave] = f"{etiqueta}: este campo es obligatorio."
            return None
        try:
            return datetime.strptime(texto, "%Y-%m-%d").date()
        except ValueError:
            errores[clave] = f"{etiqueta}: usa el formato AAAA-MM-DD, por ejemplo 2026-02-02."
            return None

    # ------------------------------------------------------------------ menú de activos (Operaciones y Flujos)
    def _actualizar_menu_activos(self) -> None:
        """Rellena el menú 'activo' con los activos registrados, conservando la elección si sigue existiendo."""
        self._activos = {}
        for activo in self.repositorio.listar_activos():
            etiqueta = f"{activo.nombre} ({self.NOMBRES_TIPO.get(activo.tipo, activo.tipo)})"
            if etiqueta in self._activos:  # dos activos con el mismo nombre y tipo
                etiqueta += f" #{activo.id}"
            self._activos[etiqueta] = activo
        menu = self._widgets["activo"]
        actual = menu.get()
        etiquetas = list(self._activos) or [self.SIN_ACTIVOS]
        menu.configure(values=etiquetas)
        menu.set(actual if actual in etiquetas else etiquetas[0])

    def _activo_elegido(self):
        """El activo seleccionado en el menú, o None si no hay activos registrados."""
        return self._activos.get(self._widgets["activo"].get())
