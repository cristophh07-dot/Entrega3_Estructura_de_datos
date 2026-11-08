import traceback

from interfaz.tema import Tema
from interfaz.vista_base import VistaBase
from modelos.accion import Accion
from modelos.bono import Bono
from modelos.cdt import CDT
from modelos.tes import TES


class VistaActivos(VistaBase):
    """Formulario para crear activos (acción, CDT, bono o TES) y tabla con los registrados.

    Los campos cambian según el tipo elegido. Los porcentajes se escriben en %
    en pantalla y se pasan en decimal a los modelos (10,5 % -> 0.105). El
    guardado lo hace VistaBase; aquí solo se define qué se valida y qué se crea.
    """

    TIPOS = {"Acción": "ACCION", "CDT": "CDT", "Bono": "BONO", "TES": "TES"}
    CLASES_RENTA_FIJA = {"CDT": CDT, "BONO": Bono, "TES": TES}
    PERIODICIDADES = {"Al vencimiento": 0, "Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
    NOMBRES_PERIODICIDAD = {meses: nombre for nombre, meses in PERIODICIDADES.items()}

    _TODOS = ("ACCION", "CDT", "BONO", "TES")
    _RENTA_FIJA = ("CDT", "BONO", "TES")

    # (clave, etiqueta, tipos en los que aparece, ayuda de la entrada o valores del menú)
    CAMPOS = [
        ("nombre", "Nombre", _TODOS, "Ej. Ecopetrol"),
        ("ticker", "Ticker (como en Yahoo Finance)", ("ACCION",), "Ej. AAPL"),
        ("moneda", "Moneda en que cotiza", ("ACCION",), ["COP", "USD"]),
        ("valor_nominal", "Valor nominal por título (COP)", _RENTA_FIJA, "Ej. 5.000.000"),
        ("tasa", "Tasa E.A. del título (%)", _RENTA_FIJA, "Ej. 10,5"),
        ("fecha_emision", "Fecha de emisión", _RENTA_FIJA, "AAAA-MM-DD"),
        ("fecha_vencimiento", "Fecha de vencimiento", _RENTA_FIJA, "AAAA-MM-DD"),
        ("periodicidad", "Pago de intereses", _RENTA_FIJA, list(PERIODICIDADES)),
        ("tasa_mercado", "Tasa de mercado E.A. (%), opcional", _RENTA_FIJA, "Vacío si no aplica"),
    ]

    COLUMNAS = [
        ("nombre", "Nombre", 170, "w"), ("tipo", "Tipo", 65, "w"), ("ticker", "Ticker", 100, "w"),
        ("nominal", "Nominal", 110, "e"), ("tasa", "Tasa E.A.", 80, "e"),
        ("emision", "Emisión", 100, "w"), ("vencimiento", "Vence", 100, "w"),
        ("pago", "Pago", 115, "w"), ("mercado", "T. mercado", 90, "e"),
    ]

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, repositorio, portafolio, "Activos",
                         "Registra acciones, CDT, bonos y TES antes de cargar operaciones.")
        self._tipo = "ACCION"

        cuerpo = self._crear_panel_formulario("Nuevo activo")
        self._selector = self._crear_selector(cuerpo, list(self.TIPOS), self._cambiar_tipo)
        self._rejilla = self._crear_rejilla(cuerpo)
        for clave, etiqueta, _, extra in self.CAMPOS:
            if isinstance(extra, list):
                self._crear_campo(self._rejilla, clave, etiqueta, valores=extra)
            else:
                self._crear_campo(self._rejilla, clave, etiqueta, ayuda=extra)
        self._crear_barra_acciones(cuerpo, "Guardar activo")

        self._tabla = self._crear_tabla("Activos registrados", self.COLUMNAS, altura=9)
        self._mostrar_campos()

    # ------------------------------------------------------------------ tipo y campos
    def _cambiar_tipo(self, etiqueta: str) -> None:
        self._tipo = self.TIPOS[etiqueta]
        self._widgets["periodicidad"].set(self._periodicidad_por_defecto())
        self._marcar_errores({})
        self._mostrar_campos()

    def _periodicidad_por_defecto(self) -> str:
        # Un CDT suele pagar todo al vencimiento; bonos y TES, cupones.
        return "Al vencimiento" if self._tipo == "CDT" else "Semestral"

    def _mostrar_campos(self) -> None:
        self._colocar_campos(self._rejilla, [c[0] for c in self.CAMPOS if self._tipo in c[2]])

    def _limpiar(self) -> None:
        super()._limpiar()
        self._widgets["moneda"].set("COP")
        self._widgets["periodicidad"].set(self._periodicidad_por_defecto())
        self._widgets["nombre"].focus_set()

    # ------------------------------------------------------------------ pasos del guardado
    def _validar(self):
        datos, errores = {"tipo": self._tipo, "nombre": self._leer_texto("nombre")}, {}
        if not datos["nombre"]:
            errores["nombre"] = "El nombre es obligatorio."

        if self._tipo == "ACCION":
            datos["ticker"] = self._leer_texto("ticker")
            datos["moneda"] = self._widgets["moneda"].get()
            if not datos["ticker"]:
                errores["ticker"] = "El ticker es obligatorio."
            elif not all(c.isalnum() or c in ".-^=" for c in datos["ticker"]):
                errores["ticker"] = "El ticker solo admite letras, números, punto y guion."
            elif any(getattr(a, "ticker", None) == datos["ticker"].upper()
                     for a in self.repositorio.listar_activos()):
                errores["ticker"] = "Ya existe una acción con ese ticker."
            return datos, errores

        nominal = self._numero(errores, "valor_nominal", "Valor nominal", "5.000.000")
        if nominal is not None and nominal <= 0:
            errores["valor_nominal"] = "El valor nominal debe ser mayor que 0."
        tasa = self._numero(errores, "tasa", "Tasa E.A.", "10,5")
        if tasa is not None and not 0 <= tasa <= 100:
            errores["tasa"] = "La tasa E.A. debe estar entre 0 y 100 %."
        mercado = self._numero(errores, "tasa_mercado", "Tasa de mercado", "10,5", obligatorio=False)
        if mercado is not None and not 0 <= mercado <= 100:
            errores["tasa_mercado"] = "La tasa de mercado debe estar entre 0 y 100 %."
        emision = self._fecha(errores, "fecha_emision", "Fecha de emisión")
        vencimiento = self._fecha(errores, "fecha_vencimiento", "Fecha de vencimiento")
        if emision and vencimiento and vencimiento <= emision:
            errores["fecha_vencimiento"] = "El vencimiento debe ser posterior a la emisión."

        datos.update(
            valor_nominal=nominal, tasa=tasa, tasa_mercado=mercado, fecha_emision=emision,
            fecha_vencimiento=vencimiento,
            periodicidad_meses=self.PERIODICIDADES[self._widgets["periodicidad"].get()])
        return datos, errores

    def _crear_objeto(self, datos: dict):
        if datos["tipo"] == "ACCION":
            return Accion(nombre=datos["nombre"], ticker=datos["ticker"], moneda=datos["moneda"])
        mercado = datos["tasa_mercado"]
        return self.CLASES_RENTA_FIJA[datos["tipo"]](
            nombre=datos["nombre"], valor_nominal=datos["valor_nominal"],
            tasa=round(datos["tasa"] / 100, 10), fecha_emision=datos["fecha_emision"],
            fecha_vencimiento=datos["fecha_vencimiento"],
            periodicidad_meses=datos["periodicidad_meses"],
            tasa_mercado=None if mercado is None else round(mercado / 100, 10))

    def _guardar_objeto(self, activo) -> None:
        self.repositorio.guardar_activo(activo)

    def _mensaje_exito(self, activo) -> str:
        return f"Activo guardado: {activo.nombre}"

    # ------------------------------------------------------------------ tabla
    def refrescar(self) -> None:
        try:
            self._tabla.cargar([self._fila(a) for a in self.repositorio.listar_activos()])
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
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
