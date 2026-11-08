import traceback
from datetime import date, datetime, timedelta

import customtkinter as ctk
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from interfaz.tabla_datos import TablaDatos
from interfaz.tema import Tema


class VistaDashboard(ctk.CTkFrame):
    """Resumen del portafolio: indicadores, gráficas y tablas, en pesos o en dólares.

    Todo se dibuja en refrescar(), que la VentanaPrincipal llama cada vez que
    se muestra esta vista. Los datos salen del portafolio (real o mock) y nunca
    se calculan aquí: la vista solo los presenta. El selector COP/USD le pasa
    moneda="COP" o "USD" a cada método del portafolio; en USD el motor convierte
    cada movimiento con la TRM de su fecha.
    """

    # (título, llave de portafolio.resumen(), formato, ¿verde/rojo según el signo?)
    INDICADORES = [
        ("Total invertido", "total_invertido", "dinero", False),
        ("Valor actual", "valor_actual", "dinero", False),
        ("Ganancia", "ganancia", "dinero", True),
        ("Rentabilidad acumulada", "rentabilidad_acumulada", "porcentaje", True),
        ("Rentabilidad E.A.", "rentabilidad_ea", "porcentaje", True),
    ]

    NOMBRES_TIPO = {
        "ACCION": "Acción", "CDT": "CDT", "BONO": "Bono", "TES": "TES",
        "DIVIDENDO": "Dividendo", "INTERES": "Interés", "CAPITAL": "Capital", "OTRO": "Otro",
    }

    COLUMNAS_POSICIONES = [
        ("nombre", "Activo", 180, "w"), ("tipo", "Tipo", 65, "w"),
        ("cantidad", "Cantidad", 80, "e"), ("costo", "Costo total", 115, "e"),
        ("valor", "Valor actual", 115, "e"), ("ingresos", "Ingresos", 100, "e"),
        ("ganancia", "Ganancia", 115, "e"), ("rentabilidad", "Rentab.", 85, "e"),
        ("peso", "Peso", 75, "e"),
    ]

    COLUMNAS_FLUJOS = [
        ("fecha", "Fecha", 95, "w"), ("nombre", "Activo", 190, "w"),
        ("tipo", "Tipo", 90, "w"), ("valor", "Valor", 110, "e"),
    ]

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, fg_color=Tema.FONDO, corner_radius=0)
        self.repositorio = repositorio
        self.portafolio = portafolio
        self._moneda = "COP"
        self._valores = {}    # llave del resumen -> etiqueta con el valor del indicador
        self._graficas = {}   # nombre -> (figura, ejes, lienzo)

        # El contenido va dentro de un marco con scroll porque no cabe en 760 px.
        self._contenido = ctk.CTkScrollableFrame(
            self, fg_color=Tema.FONDO, corner_radius=0,
            scrollbar_button_color=Tema.BORDE, scrollbar_button_hover_color=Tema.TEXTO_SECUNDARIO)
        self._contenido.pack(fill="both", expand=True)

        self._construir_encabezado()
        self._construir_indicadores()
        self._construir_fila_distribucion()
        self._construir_fila_ingresos()
        self._construir_fila_inferior()
        self._construir_tabla_posiciones()

    # ------------------------------------------------------------------ construcción
    def _construir_encabezado(self) -> None:
        marco = ctk.CTkFrame(self._contenido, fg_color="transparent")
        marco.pack(fill="x", padx=Tema.MARGEN, pady=(Tema.MARGEN, 12))
        marco.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(marco, text="Dashboard", font=Tema.FUENTE_TITULO,
                     text_color=Tema.TEXTO).grid(row=0, column=0, sticky="w")
        self._estado = ctk.CTkLabel(marco, text="", font=Tema.FUENTE_PEQUENA,
                                    text_color=Tema.TEXTO_SECUNDARIO)
        self._estado.grid(row=1, column=0, sticky="w")

        self._selector_moneda = ctk.CTkSegmentedButton(
            marco, values=["COP", "USD"], command=self._cambiar_moneda, font=Tema.FUENTE_NORMAL,
            width=130, height=34, corner_radius=Tema.RADIO, border_width=1, fg_color=Tema.BORDE,
            selected_color=Tema.BORDE, selected_hover_color=Tema.BORDE,
            unselected_color=Tema.FONDO, unselected_hover_color=Tema.HOVER, text_color=Tema.TEXTO)
        self._selector_moneda.set("COP")
        self._selector_moneda.grid(row=0, column=1, rowspan=2, sticky="e", padx=(0, 10))

        self._boton = ctk.CTkButton(
            marco, text="Actualizar precios", font=Tema.FUENTE_NORMAL, height=34, width=150,
            corner_radius=Tema.RADIO, fg_color="transparent", border_width=1,
            border_color=Tema.ACENTO, text_color=Tema.ACENTO, hover_color=Tema.HOVER,
            text_color_disabled=Tema.TEXTO_SECUNDARIO, command=self._actualizar_precios,
        )
        self._boton.grid(row=0, column=2, rowspan=2, sticky="e")

    def _construir_indicadores(self) -> None:
        """Un solo panel con los indicadores, separados por líneas verticales."""
        banda = ctk.CTkFrame(self._contenido, fg_color=Tema.TARJETA, corner_radius=Tema.RADIO,
                             border_width=1, border_color=Tema.BORDE)
        banda.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))
        for indice, (titulo, llave, _, _) in enumerate(self.INDICADORES):
            columna = indice * 2  # las columnas impares son las líneas separadoras
            banda.grid_columnconfigure(columna, weight=1, uniform="indicadores")
            if indice:
                ctk.CTkFrame(banda, width=1, height=1, fg_color=Tema.BORDE, corner_radius=0).grid(
                    row=0, column=columna - 1, sticky="ns", pady=12)
            celda = ctk.CTkFrame(banda, fg_color="transparent")
            celda.grid(row=0, column=columna, sticky="nsew")
            ctk.CTkLabel(celda, text=titulo, font=Tema.FUENTE_PEQUENA,
                         text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w", padx=16, pady=(12, 0))
            valor = ctk.CTkLabel(celda, text="-", font=Tema.FUENTE_TARJETA, text_color=Tema.TEXTO)
            valor.pack(anchor="w", padx=16, pady=(2, 12))
            self._valores[llave] = valor

    def _construir_fila_distribucion(self) -> None:
        fila = self._crear_fila(pesos=(1, 2))
        self._crear_grafica(fila, "distribucion", "Cómo está repartido el portafolio", 3.2, 3.2).grid(
            row=0, column=0, sticky="nsew", padx=(0, 6))
        self._crear_grafica(fila, "evolucion", "Valor del portafolio", 6.4, 3.2).grid(
            row=0, column=1, sticky="nsew", padx=(6, 0))

    def _construir_fila_ingresos(self) -> None:
        fila = self._crear_fila(pesos=(1, 2))
        self._crear_grafica(fila, "ingresos", "Ingresos recibidos", 3.2, 3.2).grid(
            row=0, column=0, sticky="nsew", padx=(0, 6))
        self._crear_grafica(fila, "dividendos", "Dividendos por acción", 6.4, 3.2).grid(
            row=0, column=1, sticky="nsew", padx=(6, 0))

    def _construir_fila_inferior(self) -> None:
        fila = self._crear_fila(pesos=(2, 3))
        self._crear_grafica(fila, "rentabilidad", "Rentabilidad por activo", 5, 3.2).grid(
            row=0, column=0, sticky="nsew", padx=(0, 6))

        panel = self._crear_panel(fila, "Próximos pagos")
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._tabla_flujos = TablaDatos(panel, self.COLUMNAS_FLUJOS, altura=7)
        self._tabla_flujos.pack(fill="both", expand=True, padx=12, pady=(8, 14))

    def _construir_tabla_posiciones(self) -> None:
        fila = self._crear_fila(pesos=(1,))
        panel = self._crear_panel(fila, "Posiciones")
        panel.grid(row=0, column=0, sticky="nsew")
        self._tabla_posiciones = TablaDatos(panel, self.COLUMNAS_POSICIONES, altura=8)
        self._tabla_posiciones.pack(fill="both", expand=True, padx=12, pady=(8, 14))

    def _crear_fila(self, pesos) -> ctk.CTkFrame:
        """Fila con columnas de proporción fija (1 y 2 = la segunda ocupa el doble)."""
        fila = ctk.CTkFrame(self._contenido, fg_color="transparent")
        fila.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))
        for columna, peso in enumerate(pesos):
            fila.grid_columnconfigure(columna, weight=peso, uniform="fila")
        return fila

    @staticmethod
    def _crear_panel(master, titulo: str) -> ctk.CTkFrame:
        """Panel plano con borde de 1 px y el título separado por una línea fina."""
        panel = ctk.CTkFrame(master, fg_color=Tema.TARJETA, corner_radius=Tema.RADIO,
                             border_width=1, border_color=Tema.BORDE)
        ctk.CTkLabel(panel, text=titulo, font=Tema.FUENTE_SUBTITULO,
                     text_color=Tema.TEXTO).pack(anchor="w", padx=16, pady=(12, 10))
        ctk.CTkFrame(panel, height=1, fg_color=Tema.BORDE, corner_radius=0).pack(fill="x")
        return panel

    def _crear_grafica(self, master, nombre: str, titulo: str, ancho: float, alto: float):
        """Panel con una figura de matplotlib incrustada (FigureCanvasTkAgg)."""
        panel = self._crear_panel(master, titulo)
        figura = Figure(figsize=(ancho, alto), dpi=100, facecolor=Tema.TARJETA, layout="constrained")
        ejes = figura.add_subplot(111)
        lienzo = FigureCanvasTkAgg(figura, master=panel)
        widget = lienzo.get_tk_widget()
        widget.configure(bg=Tema.TARJETA, highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._graficas[nombre] = (figura, ejes, lienzo)
        return panel

    # ------------------------------------------------------------------ actualización
    def refrescar(self) -> None:
        """Lee el portafolio una sola vez y redibuja todo. Un error se muestra en pantalla, no cierra el programa."""
        try:
            datos = self._leer_datos()
            self._actualizar_indicadores(datos["resumen"])
            self._dibujar_distribucion(datos["distribucion"])
            self._dibujar_evolucion(datos["serie"])
            self._dibujar_ingresos(datos["posiciones"])
            self._dibujar_dividendos(datos["posiciones"])
            self._dibujar_rentabilidad(datos["posiciones"])
            self._llenar_tablas(datos["posiciones"], datos["flujos"])
            nota = " Valores en dólares con la TRM de cada fecha." if self._moneda == "USD" else ""
            self._mostrar_estado(f"Datos al día. Revisado a las {datetime.now():%H:%M}.{nota}")
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
            traceback.print_exc()
            self._mostrar_estado(f"No se pudieron cargar los datos: {error}", error=True)

    def _leer_datos(self) -> dict:
        moneda = self._moneda
        return {
            "resumen": self.portafolio.resumen(moneda=moneda),
            "distribucion": self.portafolio.distribucion(moneda=moneda),
            "posiciones": self.portafolio.posiciones(moneda=moneda),
            "serie": self.portafolio.serie_valor(self._fecha_inicio(), moneda=moneda),
            "flujos": self.portafolio.proximos_flujos(moneda=moneda),
        }

    def _cambiar_moneda(self, moneda: str) -> None:
        self._moneda = moneda
        self.refrescar()

    def _actualizar_precios(self) -> None:
        self._boton.configure(state="disabled", text="Actualizando...")
        self.update_idletasks()  # pinta el cambio del botón antes de la espera
        try:
            self.portafolio.actualizar()
        except Exception as error:  # noqa: BLE001
            traceback.print_exc()
            self._mostrar_estado(f"No se pudieron actualizar los precios: {error}", error=True)
        else:
            self.refrescar()
        finally:
            self._boton.configure(state="normal", text="Actualizar precios")

    def _mostrar_estado(self, texto: str, error: bool = False) -> None:
        self._estado.configure(text=texto,
                               text_color=Tema.PERDIDA if error else Tema.TEXTO_SECUNDARIO)

    def _dinero(self, valor: float) -> str:
        return Tema.dinero(valor, self._moneda)

    def _abreviar(self, valor: float) -> str:
        """Valor corto para los ejes: $ 45,0 M, US$ 12,5 mil."""
        prefijo = "US$ " if self._moneda == "USD" else "$ "
        if abs(valor) >= 1_000_000:
            texto = f"{valor / 1_000_000:.1f} M"
        elif abs(valor) >= 1_000:
            texto = f"{valor / 1_000:.1f} mil"
        else:
            texto = f"{valor:.0f}"
        return prefijo + texto.replace(".", ",")

    def _actualizar_indicadores(self, resumen: dict) -> None:
        for _, llave, formato, con_signo in self.INDICADORES:
            valor = resumen[llave]
            texto = self._dinero(valor) if formato == "dinero" else Tema.porcentaje(valor)
            color = Tema.color_signo(valor) if con_signo else Tema.TEXTO
            self._valores[llave].configure(text=texto, text_color=color)

    def _fecha_inicio(self) -> date:
        """La serie del valor arranca en la primera operación registrada."""
        operaciones = self.repositorio.listar_operaciones()  # vienen ordenadas por fecha
        if operaciones:
            return operaciones[0].fecha
        return date.today() - timedelta(days=30)

    # ------------------------------------------------------------------ gráficas
    def _preparar_ejes(self, nombre: str):
        figura, ejes, lienzo = self._graficas[nombre]
        for leyenda in list(figura.legends):
            leyenda.remove()
        ejes.clear()
        ejes.set_axis_on()
        ejes.set_facecolor(Tema.TARJETA)
        ejes.spines[["top", "right"]].set_visible(False)
        for lado in ("left", "bottom"):
            ejes.spines[lado].set_color(Tema.BORDE)
        ejes.tick_params(colors=Tema.TEXTO_SECUNDARIO, labelsize=9, length=0)
        return figura, ejes, lienzo

    @staticmethod
    def _mensaje_vacio(ejes, texto: str = "Aún no hay datos para mostrar") -> None:
        ejes.set_axis_off()
        ejes.text(0.5, 0.5, texto, ha="center", va="center",
                  color=Tema.TEXTO_SECUNDARIO, fontsize=10, transform=ejes.transAxes)

    def _dibujar_aro(self, nombre: str, valores: list, colores: list, etiquetas: list,
                     titulo_centro: str) -> None:
        """Dona con el total al centro y la leyenda debajo. La usan 'distribucion' e 'ingresos'."""
        figura, ejes, lienzo = self._preparar_ejes(nombre)
        total = sum(valores)
        if total <= 0:
            self._mensaje_vacio(ejes)
        else:
            trozos, _ = ejes.pie(
                valores, colors=colores, startangle=90, counterclock=False,
                wedgeprops={"width": 0.3, "edgecolor": Tema.TARJETA, "linewidth": 3})
            ejes.text(0, 0.12, titulo_centro, ha="center", va="center",
                      color=Tema.TEXTO_SECUNDARIO, fontsize=8)
            ejes.text(0, -0.1, self._dinero(total), ha="center", va="center",
                      color=Tema.TEXTO, fontsize=10, fontweight="bold")
            figura.legend(trozos, etiquetas, loc="outside lower center", ncol=1, frameon=False,
                          labelcolor=Tema.TEXTO_SECUNDARIO, fontsize=9)
        lienzo.draw_idle()

    def _dibujar_distribucion(self, distribucion: dict) -> None:
        fija, variable = distribucion["renta_fija"], distribucion["renta_variable"]
        self._dibujar_aro(
            "distribucion", [fija["valor"], variable["valor"]],
            [Tema.RENTA_FIJA, Tema.RENTA_VARIABLE],
            [f"Renta fija: {Tema.porcentaje(fija['porcentaje'])}",
             f"Renta variable: {Tema.porcentaje(variable['porcentaje'])}"],
            "Valor actual")

    @staticmethod
    def _ingresos_por_tipo(posiciones) -> tuple:
        """(dividendos, intereses): los ingresos de las acciones y los de la renta fija."""
        acciones = posiciones["tipo"] == "ACCION"
        return (float(posiciones.loc[acciones, "ingresos"].sum()),
                float(posiciones.loc[~acciones, "ingresos"].sum()))

    def _dibujar_ingresos(self, posiciones) -> None:
        dividendos, intereses = self._ingresos_por_tipo(posiciones)
        total = dividendos + intereses
        porcentaje = lambda parte: Tema.porcentaje(parte / total) if total else Tema.porcentaje(0)
        self._dibujar_aro(
            "ingresos", [dividendos, intereses], [Tema.RENTA_VARIABLE, Tema.RENTA_FIJA],
            [f"Dividendos: {self._dinero(dividendos)} ({porcentaje(dividendos)})",
             f"Intereses: {self._dinero(intereses)} ({porcentaje(intereses)})"],
            "Total recibido")

    def _dibujar_dividendos(self, posiciones) -> None:
        _, ejes, lienzo = self._preparar_ejes("dividendos")
        acciones = posiciones[(posiciones["tipo"] == "ACCION") & (posiciones["ingresos"] > 0)]
        if acciones.empty:
            self._mensaje_vacio(ejes, "Aún no hay dividendos registrados")
        else:
            acciones = acciones.sort_values("ingresos")  # el que más pagó queda arriba
            valores = [float(v) for v in acciones["ingresos"]]
            barras = ejes.barh(list(acciones["nombre"]), valores, height=0.55, color=Tema.RENTA_VARIABLE)
            ejes.bar_label(barras, labels=[self._dinero(v) for v in valores], padding=4,
                           color=Tema.TEXTO, fontsize=8)
            ejes.xaxis.set_major_formatter(FuncFormatter(lambda v, _: self._abreviar(v)))
            ejes.margins(x=0.25)
        lienzo.draw_idle()

    def _dibujar_evolucion(self, serie) -> None:
        _, ejes, lienzo = self._preparar_ejes("evolucion")
        if serie is None or serie.empty:
            self._mensaje_vacio(ejes)
        else:
            ejes.plot(serie["fecha"], serie["valor"], color=Tema.TEXTO, linewidth=1.6)
            ejes.plot(serie["fecha"].iloc[-1], serie["valor"].iloc[-1], "o",
                      color=Tema.ACENTO, markersize=5)  # el último valor lleva el acento
            ejes.yaxis.set_major_formatter(FuncFormatter(lambda v, _: self._abreviar(v)))
            ejes.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
            ejes.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
            ejes.grid(axis="y", color=Tema.BORDE, linewidth=0.6)
        lienzo.draw_idle()

    def _dibujar_rentabilidad(self, posiciones) -> None:
        _, ejes, lienzo = self._preparar_ejes("rentabilidad")
        if posiciones.empty:
            self._mensaje_vacio(ejes)
        else:
            posiciones = posiciones.sort_values("rentabilidad")  # la mejor queda arriba
            rentabilidades = list(posiciones["rentabilidad"])
            barras = ejes.barh(list(posiciones["nombre"]), rentabilidades, height=0.55,
                               color=[Tema.color_signo(r) for r in rentabilidades])
            ejes.bar_label(barras, labels=[Tema.porcentaje(r) for r in rentabilidades],
                           padding=4, color=Tema.TEXTO, fontsize=8)
            ejes.axvline(0, color=Tema.BORDE, linewidth=1)
            ejes.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f} %"))
            ejes.margins(x=0.4)
        lienzo.draw_idle()

    # ------------------------------------------------------------------ tablas
    def _llenar_tablas(self, posiciones, flujos) -> None:
        total = float(posiciones["valor_actual"].sum()) if not posiciones.empty else 0.0
        filas = []
        for _, p in posiciones.iterrows():
            peso = p["valor_actual"] / total if total > 0 else 0.0
            filas.append([
                p["nombre"], self.NOMBRES_TIPO.get(p["tipo"], p["tipo"]), Tema.cantidad(p["cantidad"]),
                self._dinero(p["costo_total"]), self._dinero(p["valor_actual"]),
                self._dinero(p["ingresos"]), self._dinero(p["ganancia"]),
                Tema.porcentaje(p["rentabilidad"]), Tema.porcentaje(peso),
            ])
        self._tabla_posiciones.cargar(filas)

        filas = []
        for _, f in flujos.iterrows():
            filas.append([str(f["fecha"])[:10], f["nombre"],
                          self.NOMBRES_TIPO.get(f["tipo"], f["tipo"]), self._dinero(f["valor"])])
        self._tabla_flujos.cargar(filas)
