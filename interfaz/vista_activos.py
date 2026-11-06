import re
import traceback
from datetime import datetime

import customtkinter as ctk

from interfaz.tabla_datos import TablaDatos
from interfaz.tema import Tema
from modelos.accion import Accion
from modelos.bono import Bono
from modelos.cdt import CDT
from modelos.tes import TES


class VistaActivos(ctk.CTkFrame):
    """Formulario para crear activos (acción, CDT, bono o TES) y tabla con los registrados.

    Los campos cambian según el tipo elegido. La vista valida lo que escribe
    el usuario (campos vacíos, números, fechas) y marca en rojo el campo con
    error. Luego construye el objeto de modelos/, que vuelve a validar, y lo
    guarda con el repositorio. Los porcentajes se escriben en % en pantalla y
    se pasan en decimal a los modelos (10,5 % -> 0.105).
    """

    TIPOS = {"Acción": "ACCION", "CDT": "CDT", "Bono": "BONO", "TES": "TES"}
    NOMBRES_TIPO = {codigo: nombre for nombre, codigo in TIPOS.items()}
    CLASES_RENTA_FIJA = {"CDT": CDT, "BONO": Bono, "TES": TES}
    PERIODICIDADES = {"Al vencimiento": 0, "Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
    NOMBRES_PERIODICIDAD = {meses: nombre for nombre, meses in PERIODICIDADES.items()}

    _TODOS = ("ACCION", "CDT", "BONO", "TES")
    _RENTA_FIJA = ("CDT", "BONO", "TES")

    # (clave, etiqueta, tipos en los que aparece, clase de widget, ayuda o valores)
    CAMPOS = [
        ("nombre", "Nombre", _TODOS, "texto", "Ej. Ecopetrol"),
        ("ticker", "Ticker (como en Yahoo Finance)", ("ACCION",), "texto", "Ej. AAPL"),
        ("moneda", "Moneda en que cotiza", ("ACCION",), "menu", ["COP", "USD"]),
        ("valor_nominal", "Valor nominal por título (COP)", _RENTA_FIJA, "texto", "Ej. 5.000.000"),
        ("tasa", "Tasa E.A. del título (%)", _RENTA_FIJA, "texto", "Ej. 10,5"),
        ("fecha_emision", "Fecha de emisión", _RENTA_FIJA, "texto", "AAAA-MM-DD"),
        ("fecha_vencimiento", "Fecha de vencimiento", _RENTA_FIJA, "texto", "AAAA-MM-DD"),
        ("periodicidad", "Pago de intereses", _RENTA_FIJA, "menu", list(PERIODICIDADES)),
        ("tasa_mercado", "Tasa de mercado E.A. (%), opcional", _RENTA_FIJA, "texto", "Vacío si no aplica"),
    ]

    COLUMNAS = [
        ("nombre", "Nombre", 170, "w"), ("tipo", "Tipo", 65, "w"), ("ticker", "Ticker", 100, "w"),
        ("nominal", "Nominal", 110, "e"), ("tasa", "Tasa E.A.", 80, "e"),
        ("emision", "Emisión", 100, "w"), ("vencimiento", "Vence", 100, "w"),
        ("pago", "Pago", 115, "w"), ("mercado", "T. mercado", 90, "e"),
    ]

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, fg_color=Tema.FONDO, corner_radius=0)
        self.repositorio = repositorio
        self.portafolio = portafolio
        self._tipo = "ACCION"
        self._marcos = {}   # clave -> marco (etiqueta + widget) de cada campo
        self._widgets = {}  # clave -> CTkEntry o CTkOptionMenu

        self._contenido = ctk.CTkScrollableFrame(
            self, fg_color=Tema.FONDO, corner_radius=0,
            scrollbar_button_color=Tema.BORDE, scrollbar_button_hover_color=Tema.TEXTO_SECUNDARIO)
        self._contenido.pack(fill="both", expand=True)

        self._construir_encabezado()
        self._construir_formulario()
        self._construir_tabla()
        self._mostrar_campos()

    # ------------------------------------------------------------------ construcción
    def _construir_encabezado(self) -> None:
        marco = ctk.CTkFrame(self._contenido, fg_color="transparent")
        marco.pack(fill="x", padx=Tema.MARGEN, pady=(Tema.MARGEN, 12))
        ctk.CTkLabel(marco, text="Activos", font=Tema.FUENTE_TITULO,
                     text_color=Tema.TEXTO).pack(anchor="w")
        ctk.CTkLabel(marco, text="Registra acciones, CDT, bonos y TES antes de cargar operaciones.",
                     font=Tema.FUENTE_PEQUENA, text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w")

    def _construir_formulario(self) -> None:
        panel = self._crear_panel(self._contenido, "Nuevo activo")
        panel.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))
        cuerpo = ctk.CTkFrame(panel, fg_color="transparent")
        cuerpo.pack(fill="x", padx=16, pady=14)

        self._selector = ctk.CTkSegmentedButton(
            cuerpo, values=list(self.TIPOS), command=self._cambiar_tipo, font=Tema.FUENTE_NORMAL,
            width=360, height=34, corner_radius=Tema.RADIO, border_width=1, fg_color=Tema.BORDE,
            selected_color=Tema.BORDE, selected_hover_color=Tema.BORDE,
            unselected_color=Tema.FONDO, unselected_hover_color=Tema.HOVER, text_color=Tema.TEXTO)
        self._selector.set("Acción")
        self._selector.pack(anchor="w")

        self._rejilla = ctk.CTkFrame(cuerpo, fg_color="transparent")
        self._rejilla.pack(fill="x", pady=(14, 0))
        for columna in range(4):
            self._rejilla.grid_columnconfigure(columna, weight=1, uniform="campos")

        for clave, etiqueta, _, clase, extra in self.CAMPOS:
            marco = ctk.CTkFrame(self._rejilla, fg_color="transparent")
            ctk.CTkLabel(marco, text=etiqueta, font=Tema.FUENTE_PEQUENA,
                         text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w", pady=(0, 4))
            if clase == "texto":
                widget = ctk.CTkEntry(
                    marco, placeholder_text=extra, height=34, corner_radius=Tema.RADIO,
                    border_width=1, border_color=Tema.BORDE, fg_color=Tema.FONDO,
                    text_color=Tema.TEXTO, placeholder_text_color=Tema.TEXTO_SECUNDARIO,
                    font=Tema.FUENTE_NORMAL)
                widget.bind("<Return>", lambda _evento: self._guardar())
            else:
                widget = ctk.CTkOptionMenu(
                    marco, values=extra, height=34, corner_radius=Tema.RADIO, anchor="w",
                    fg_color=Tema.FONDO, button_color=Tema.BORDE, button_hover_color=Tema.HOVER,
                    text_color=Tema.TEXTO, font=Tema.FUENTE_NORMAL, dropdown_font=Tema.FUENTE_NORMAL,
                    dropdown_fg_color=Tema.PANEL, dropdown_hover_color=Tema.HOVER,
                    dropdown_text_color=Tema.TEXTO)
            widget.pack(fill="x")
            self._marcos[clave] = marco
            self._widgets[clave] = widget

        acciones = ctk.CTkFrame(cuerpo, fg_color="transparent")
        acciones.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(
            acciones, text="Guardar activo", height=34, width=140, corner_radius=Tema.RADIO,
            font=Tema.FUENTE_NORMAL, fg_color=Tema.ACENTO, hover_color=Tema.ACENTO_HOVER,
            text_color=Tema.TEXTO_SOBRE_ACENTO, command=self._guardar).pack(side="left")
        ctk.CTkButton(
            acciones, text="Limpiar", height=34, width=100, corner_radius=Tema.RADIO,
            font=Tema.FUENTE_NORMAL, fg_color="transparent", border_width=1,
            border_color=Tema.BORDE, text_color=Tema.TEXTO, hover_color=Tema.HOVER,
            command=self._limpiar).pack(side="left", padx=(10, 0))
        self._estado = ctk.CTkLabel(acciones, text="", font=Tema.FUENTE_PEQUENA,
                                    text_color=Tema.TEXTO_SECUNDARIO, anchor="w", justify="left")
        self._estado.pack(side="left", padx=16)

    def _construir_tabla(self) -> None:
        panel = self._crear_panel(self._contenido, "Activos registrados")
        panel.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))
        self._tabla = TablaDatos(panel, self.COLUMNAS, altura=9)
        self._tabla.pack(fill="both", expand=True, padx=12, pady=(8, 14))

    @staticmethod
    def _crear_panel(master, titulo: str) -> ctk.CTkFrame:
        """Panel plano con borde de 1 px y el título separado por una línea fina."""
        panel = ctk.CTkFrame(master, fg_color=Tema.TARJETA, corner_radius=Tema.RADIO,
                             border_width=1, border_color=Tema.BORDE)
        ctk.CTkLabel(panel, text=titulo, font=Tema.FUENTE_SUBTITULO,
                     text_color=Tema.TEXTO).pack(anchor="w", padx=16, pady=(12, 10))
        ctk.CTkFrame(panel, height=1, fg_color=Tema.BORDE, corner_radius=0).pack(fill="x")
        return panel

    # ------------------------------------------------------------------ tipo y campos
    def _cambiar_tipo(self, etiqueta: str) -> None:
        self._tipo = self.TIPOS[etiqueta]
        # CDT suele pagar todo al vencimiento; bonos y TES, cupones.
        self._widgets["periodicidad"].set("Al vencimiento" if self._tipo == "CDT" else "Semestral")
        self._marcar_errores({})
        self._mostrar_campos()

    def _mostrar_campos(self) -> None:
        """Muestra solo los campos del tipo elegido, de a cuatro por fila."""
        for marco in self._marcos.values():
            marco.grid_forget()
        visibles = [c[0] for c in self.CAMPOS if self._tipo in c[2]]
        for posicion, clave in enumerate(visibles):
            self._marcos[clave].grid(row=posicion // 4, column=posicion % 4,
                                     sticky="ew", padx=(0, 12), pady=(0, 10))

    def _limpiar(self) -> None:
        for widget in self._widgets.values():
            if isinstance(widget, ctk.CTkEntry):
                widget.delete(0, "end")
        self._widgets["moneda"].set("COP")
        self._widgets["periodicidad"].set("Al vencimiento" if self._tipo == "CDT" else "Semestral")
        self._marcar_errores({})
        self._mostrar_estado("")
        self._widgets["nombre"].focus_set()

    # ------------------------------------------------------------------ validación
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

    def _validar(self):
        """Lee el formulario. Devuelve (datos, errores); errores es {clave: mensaje}."""
        datos, errores = {"tipo": self._tipo}, {}

        def texto(clave: str) -> str:
            return self._widgets[clave].get().strip()

        def numero(clave: str, etiqueta: str, ejemplo: str, obligatorio: bool = True):
            if not texto(clave):
                if obligatorio:
                    errores[clave] = f"{etiqueta}: este campo es obligatorio."
                return None
            try:
                return self._leer_numero(texto(clave))
            except ValueError:
                errores[clave] = f"{etiqueta}: escribe un número, por ejemplo {ejemplo}."
                return None

        def fecha(clave: str, etiqueta: str):
            if not texto(clave):
                errores[clave] = f"{etiqueta}: este campo es obligatorio."
                return None
            try:
                return datetime.strptime(texto(clave), "%Y-%m-%d").date()
            except ValueError:
                errores[clave] = f"{etiqueta}: usa el formato AAAA-MM-DD, por ejemplo 2026-02-02."
                return None

        datos["nombre"] = texto("nombre")
        if not datos["nombre"]:
            errores["nombre"] = "El nombre es obligatorio."

        if self._tipo == "ACCION":
            datos["ticker"] = texto("ticker")
            datos["moneda"] = self._widgets["moneda"].get()
            if not datos["ticker"]:
                errores["ticker"] = "El ticker es obligatorio."
            elif not re.fullmatch(r"[A-Za-z0-9.\-^=]+", datos["ticker"]):
                errores["ticker"] = "El ticker solo admite letras, números, punto y guion."
            elif any(getattr(a, "ticker", None) == datos["ticker"].upper()
                     for a in self.repositorio.listar_activos()):
                errores["ticker"] = "Ya existe una acción con ese ticker."
            return datos, errores

        nominal = numero("valor_nominal", "Valor nominal", "5.000.000")
        if nominal is not None and nominal <= 0:
            errores["valor_nominal"] = "El valor nominal debe ser mayor que 0."
        tasa = numero("tasa", "Tasa E.A.", "10,5")
        if tasa is not None and not 0 <= tasa <= 100:
            errores["tasa"] = "La tasa E.A. debe estar entre 0 y 100 %."
        mercado = numero("tasa_mercado", "Tasa de mercado", "10,5", obligatorio=False)
        if mercado is not None and not 0 <= mercado <= 100:
            errores["tasa_mercado"] = "La tasa de mercado debe estar entre 0 y 100 %."
        emision = fecha("fecha_emision", "Fecha de emisión")
        vencimiento = fecha("fecha_vencimiento", "Fecha de vencimiento")
        if emision and vencimiento and vencimiento <= emision:
            errores["fecha_vencimiento"] = "El vencimiento debe ser posterior a la emisión."

        datos.update(
            valor_nominal=nominal, tasa=tasa, tasa_mercado=mercado, fecha_emision=emision,
            fecha_vencimiento=vencimiento,
            periodicidad_meses=self.PERIODICIDADES[self._widgets["periodicidad"].get()])
        return datos, errores

    def _marcar_errores(self, errores: dict) -> None:
        for clave, widget in self._widgets.items():
            if isinstance(widget, ctk.CTkEntry):
                widget.configure(border_color=Tema.PERDIDA if clave in errores else Tema.BORDE)

    def _mostrar_estado(self, texto: str, error: bool = False) -> None:
        self._estado.configure(text=texto, text_color=Tema.PERDIDA if error else Tema.TEXTO)

    # ------------------------------------------------------------------ guardar
    def _crear_activo(self, datos: dict):
        """Construye el objeto de modelos/ (que vuelve a validar y puede lanzar ValueError)."""
        if datos["tipo"] == "ACCION":
            return Accion(nombre=datos["nombre"], ticker=datos["ticker"], moneda=datos["moneda"])
        mercado = datos["tasa_mercado"]
        return self.CLASES_RENTA_FIJA[datos["tipo"]](
            nombre=datos["nombre"], valor_nominal=datos["valor_nominal"],
            tasa=round(datos["tasa"] / 100, 10), fecha_emision=datos["fecha_emision"],
            fecha_vencimiento=datos["fecha_vencimiento"],
            periodicidad_meses=datos["periodicidad_meses"],
            tasa_mercado=None if mercado is None else round(mercado / 100, 10))

    def _guardar(self) -> None:
        datos, errores = self._validar()
        self._marcar_errores(errores)
        if errores:
            self._mostrar_estado(next(iter(errores.values())), error=True)
            return
        try:
            activo = self._crear_activo(datos)
            self.repositorio.guardar_activo(activo)
        except ValueError as error:
            self._mostrar_estado(f"Dato inválido: {error}", error=True)
            return
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
            traceback.print_exc()
            self._mostrar_estado(f"No se pudo guardar el activo: {error}", error=True)
            return

        self._limpiar()
        self.refrescar()
        try:
            self.portafolio.actualizar()
            self._mostrar_estado(f"Activo guardado: {activo.nombre}")
        except Exception as error:  # noqa: BLE001
            traceback.print_exc()
            self._mostrar_estado(f"Activo guardado, pero no se pudo actualizar el portafolio: {error}",
                                 error=True)

    # ------------------------------------------------------------------ tabla
    def refrescar(self) -> None:
        """Vuelve a leer los activos del repositorio y recarga la tabla."""
        try:
            self._tabla.cargar([self._fila(a) for a in self.repositorio.listar_activos()])
        except Exception as error:  # noqa: BLE001
            traceback.print_exc()
            self._mostrar_estado(f"No se pudieron cargar los activos: {error}", error=True)

    def _fila(self, activo) -> list:
        """Textos de una fila. Los campos que no aplican al tipo se muestran como '-'."""
        def dato(nombre, formato):
            valor = getattr(activo, nombre, None)
            return "-" if valor is None else formato(valor)

        ticker = f"{activo.ticker} ({activo.moneda})" if activo.tipo == "ACCION" else "-"
        return [
            activo.nombre, self.NOMBRES_TIPO.get(activo.tipo, activo.tipo), ticker,
            dato("valor_nominal", Tema.pesos), dato("tasa", Tema.porcentaje),
            dato("fecha_emision", lambda f: f.isoformat()),
            dato("fecha_vencimiento", lambda f: f.isoformat()),
            dato("periodicidad_meses", lambda m: self.NOMBRES_PERIODICIDAD.get(m, str(m))),
            dato("tasa_mercado", Tema.porcentaje),
        ]
