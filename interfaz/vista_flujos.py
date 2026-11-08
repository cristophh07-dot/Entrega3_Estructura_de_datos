import traceback
from datetime import date

from interfaz.tema import Tema
from interfaz.vista_base import VistaBase
from modelos.flujo_caja import FlujoCaja


class VistaFlujos(VistaBase):
    """Formulario para registrar dividendos, intereses y pagos de capital, y tabla con el historial.

    La retención se escribe en % y se pasa en decimal al modelo. Se valida que el
    tipo de flujo tenga sentido para el activo: los dividendos son de acciones y
    los intereses, de renta fija.
    """

    TIPOS = {"Dividendo": "DIVIDENDO", "Interés": "INTERES", "Capital": "CAPITAL", "Otro": "OTRO"}
    NOMBRES_FLUJO = {codigo: nombre for nombre, codigo in TIPOS.items()}
    RENTA_FIJA = ("CDT", "BONO", "TES")

    COLUMNAS = [
        ("fecha", "Fecha", 105, "w"), ("activo", "Activo", 220, "w"), ("tipo", "Tipo", 100, "w"),
        ("bruto", "Valor bruto", 130, "e"), ("retencion", "Retención", 100, "e"),
        ("neto", "Valor neto", 130, "e"),
    ]

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, repositorio, portafolio, "Flujos",
                         "Registra dividendos, intereses y pagos de capital recibidos.")

        cuerpo = self._crear_panel_formulario("Nuevo flujo")
        rejilla = self._crear_rejilla(cuerpo)
        self._crear_campo(rejilla, "activo", "Activo", valores=[self.SIN_ACTIVOS])
        self._crear_campo(rejilla, "tipo", "Tipo de flujo", valores=list(self.TIPOS))
        self._crear_campo(rejilla, "fecha", "Fecha de pago", ayuda="AAAA-MM-DD")
        self._crear_campo(rejilla, "valor_bruto", "Valor bruto (COP)", ayuda="Ej. 270.000")
        self._crear_campo(rejilla, "retencion", "Retención en la fuente (%)", ayuda="Vacío = 0")
        self._colocar_campos(rejilla, ["activo", "tipo", "fecha", "valor_bruto", "retencion"])
        self._crear_barra_acciones(cuerpo, "Registrar flujo")

        self._tabla = self._crear_tabla(
            "Historial de flujos", self.COLUMNAS, altura=10,
            texto_eliminar="Eliminar seleccionado",
            eliminar=lambda: self._eliminar_seleccionado(
                self._tabla, self.repositorio.eliminar_flujo,
                seleccion="Selecciona un flujo en la tabla.",
                pregunta="¿Eliminar el flujo seleccionado? No se puede deshacer.",
                exito="Flujo eliminado."))
        self._limpiar()

    def _limpiar(self) -> None:
        super()._limpiar()
        self._widgets["tipo"].set("Dividendo")
        self._widgets["fecha"].insert(0, date.today().isoformat())

    # ------------------------------------------------------------------ pasos del guardado
    def _validar(self):
        datos, errores = {}, {}
        activo = self._activo_elegido()
        tipo = self.TIPOS[self._widgets["tipo"].get()]
        if activo is None:
            errores["activo"] = "Primero registra un activo en la sección Activos."
        elif tipo == "DIVIDENDO" and activo.tipo != "ACCION":
            errores["tipo"] = "Los dividendos solo aplican a acciones. Para CDT, bonos y TES usa Interés o Capital."
        elif tipo == "INTERES" and activo.tipo not in self.RENTA_FIJA:
            errores["tipo"] = "Los intereses solo aplican a renta fija (CDT, bono o TES). Para acciones usa Dividendo."

        fecha = self._fecha(errores, "fecha", "Fecha de pago")
        bruto = self._numero(errores, "valor_bruto", "Valor bruto", "270.000")
        if bruto is not None and bruto <= 0:
            errores["valor_bruto"] = "El valor bruto debe ser mayor que 0."
        retencion = self._numero(errores, "retencion", "Retención", "10", obligatorio=False)
        if "retencion" not in errores and retencion is None:
            retencion = 0.0
        if retencion is not None and not 0 <= retencion <= 100:
            errores["retencion"] = "La retención debe estar entre 0 y 100 %."

        datos.update(activo_id=getattr(activo, "id", None), tipo=tipo, fecha=fecha, valor_bruto=bruto,
                     retencion=None if retencion is None else round(retencion / 100, 10))
        return datos, errores

    def _crear_objeto(self, datos: dict):
        return FlujoCaja(activo_id=datos["activo_id"], tipo=datos["tipo"], fecha=datos["fecha"],
                         valor_bruto=datos["valor_bruto"], retencion=datos["retencion"])

    def _guardar_objeto(self, flujo) -> None:
        self.repositorio.guardar_flujo(flujo)

    def _mensaje_exito(self, flujo) -> str:
        return f"{self.NOMBRES_FLUJO[flujo.tipo]} registrado por {Tema.pesos(flujo.valor_neto)} netos."

    # ------------------------------------------------------------------ tabla
    def refrescar(self) -> None:
        try:
            self._actualizar_menu_activos()
            por_id = {a.id: a for a in self._activos.values()}
            flujos = list(reversed(self.repositorio.listar_flujos()))  # lo más reciente arriba
            filas = []
            for f in flujos:
                activo = por_id.get(f.activo_id)
                filas.append([
                    f.fecha.isoformat(), activo.nombre if activo else f"Activo {f.activo_id}",
                    self.NOMBRES_FLUJO.get(f.tipo, f.tipo), Tema.pesos(f.valor_bruto),
                    Tema.porcentaje(f.retencion), Tema.pesos(f.valor_neto)])
            self._tabla.cargar(filas, ids=[f.id for f in flujos])
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
            traceback.print_exc()
            self._mostrar_estado(f"No se pudieron cargar los flujos: {error}", error=True)
