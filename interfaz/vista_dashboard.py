import traceback
from datetime import date, datetime, timedelta

import customtkinter as ctk
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator

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

    # Las tres partes en que se separa la ganancia: (nombre, llave del portafolio, color)
    PARTES_GANANCIA = [
        ("Valorización", "ganancia_no_realizada", Tema.VALORIZACION),
        ("Ventas", "ganancia_realizada", Tema.VENTAS),
        ("Dividendos e intereses", "ingresos", Tema.RENDIMIENTOS),
    ]

    COLUMNAS_FLUJOS = [
        ("fecha", "Fecha", 95, "w"), ("nombre", "Activo", 190, "w"),
        ("tipo", "Tipo", 90, "w"), ("valor", "Valor", 110, "e"),
    ]

    # Períodos de la gráfica "Valor del portafolio": (texto del botón, días hacia atrás).
    # None = desde la primera compra.
    PERIODOS = [("1M", 30), ("3M", 91), ("6M", 182), ("Desde el inicio", None)]

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, fg_color=Tema.FONDO, corner_radius=0)
        self.repositorio = repositorio
        self.portafolio = portafolio
        self._moneda = "COP"
        self._periodo = "Desde el inicio"
        self._serie = None    # serie completa del valor; el período solo recorta lo que se dibuja
        self._valores = {}    # llave del resumen -> etiqueta con el valor del indicador
        self._graficas = {}   # nombre -> (figura, ejes, lienzo)

        # El contenido va dentro de un marco con scroll porque no cabe en 760 px.
        self._contenido = ctk.CTkScrollableFrame(
            self, fg_color=Tema.FONDO, corner_radius=0,
            scrollbar_button_color=Tema.BORDE, scrollbar_button_hover_color=Tema.TEXTO_SECUNDARIO)
        self._contenido.pack(fill="both", expand=True)

        self._construir_encabezado()
        self._construir_indicadores()
        self._construir_fila_ganancia()
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

    def _construir_fila_ganancia(self) -> None:
        """Justo debajo de las tarjetas: de dónde sale la ganancia y qué aporta cada activo."""
        fila = self._crear_fila(pesos=(2, 3))
        self._crear_grafica(fila, "origen_ganancia", "¿De dónde sale la ganancia?", 4.6, 3.6).grid(
            row=0, column=0, sticky="nsew", padx=(0, 6))
        self._crear_grafica(fila, "ganancia_activos", "Lo que aporta cada activo a la ganancia",
                            6.9, 3.6).grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    def _construir_fila_distribucion(self) -> None:
        fila = self._crear_fila(pesos=(1, 2))
        self._crear_grafica(fila, "distribucion", "Cómo está repartido el portafolio", 3.2, 3.2).grid(
            row=0, column=0, sticky="nsew", padx=(0, 6))
        panel = self._crear_grafica(fila, "evolucion", "Valor del portafolio", 6.4, 3.2)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        # Botones de período, en la esquina superior derecha del panel
        self._selector_periodo = ctk.CTkSegmentedButton(
            panel, values=[texto for texto, _ in self.PERIODOS], command=self._cambiar_periodo,
            font=Tema.FUENTE_PEQUENA,
            height=28, corner_radius=Tema.RADIO, border_width=1, fg_color=Tema.BORDE,
            selected_color=Tema.BORDE, selected_hover_color=Tema.BORDE,
            unselected_color=Tema.FONDO, unselected_hover_color=Tema.HOVER, text_color=Tema.TEXTO)
        self._selector_periodo.set(self._periodo)
        self._selector_periodo.place(relx=1.0, x=-12, y=8, anchor="ne")

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
            self._dibujar_origen_ganancia(datos["resumen"])
            self._dibujar_ganancia_activos(datos["posiciones"])
            self._dibujar_distribucion(datos["distribucion"])
            self._serie = datos["serie"]
            self._dibujar_evolucion(self._serie)
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

    def _cambiar_periodo(self, periodo: str) -> None:
        """Solo redibuja la gráfica del valor: la serie ya está calculada."""
        self._periodo = periodo
        self._dibujar_evolucion(self._serie)

    def _recortar_periodo(self, serie):
        """Deja solo los días del período elegido (1M, 3M, 6M o todo)."""
        dias = dict(self.PERIODOS)[self._periodo]
        if dias is None or serie is None or serie.empty:
            return serie
        desde = serie["fecha"].iloc[-1] - timedelta(days=dias)
        return serie[serie["fecha"] >= desde]

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

    def _con_signo(self, valor: float) -> str:
        """+$ 1,9 M / -$ 33,2 mil: valor corto con su signo, para las etiquetas de las barras."""
        texto = self._abreviar(abs(valor))
        return ("-" if valor < 0 else "+") + texto

    def _eje(self, valor: float) -> str:
        """Etiqueta corta para los ejes: -$ 200 mil, $ 1,5 M (el signo va antes del $)."""
        texto = self._abreviar(abs(valor)).replace(",0 ", " ")
        return ("-" if valor < 0 else "") + texto

    def _dibujar_origen_ganancia(self, resumen: dict) -> None:
        """Gráfica de cascada: cada parte se apila sobre la anterior hasta llegar a la ganancia total."""
        _, ejes, lienzo = self._preparar_ejes("origen_ganancia")
        if any(llave not in resumen for _, llave, _ in self.PARTES_GANANCIA):
            self._mensaje_vacio(ejes, "El portafolio no trae el desglose de la ganancia")
            lienzo.draw_idle()
            return
        partes = [(nombre, float(resumen[llave]), color) for nombre, llave, color in self.PARTES_GANANCIA]
        total = float(resumen["ganancia"])
        nombres = [n.replace(" e ", "\ne ") for n, _, _ in partes] + ["Ganancia\ntotal"]
        acumulado = 0.0
        for x, (_, valor, color) in enumerate(partes):
            base = acumulado if valor >= 0 else acumulado + valor
            ejes.bar(x, abs(valor), bottom=base, width=0.62, color=color,
                     edgecolor=Tema.TARJETA, linewidth=1.5)
            arriba = base + abs(valor)
            ejes.text(x, arriba, self._con_signo(valor), ha="center", va="bottom",
                      color=Tema.TEXTO, fontsize=9, fontweight="bold")
            if total > 0 and all(v >= 0 for _, v, _ in partes):
                ejes.text(x, base + abs(valor) / 2, f"{valor / total * 100:.0f} %",
                          ha="center", va="center", color=Tema.FONDO, fontsize=8)
            nuevo = acumulado + valor
            ejes.plot([x + 0.31, x + 0.69], [nuevo, nuevo], color=Tema.TEXTO_SECUNDARIO,
                      linewidth=0.8, linestyle=(0, (2, 2)))  # conector hacia la siguiente barra
            acumulado = nuevo
        x_total = len(partes)
        ejes.bar(x_total, abs(total), bottom=min(total, 0), width=0.62, color=Tema.TOTAL,
                 edgecolor=Tema.TARJETA, linewidth=1.5)
        ejes.text(x_total, max(total, 0), self._con_signo(total), ha="center", va="bottom",
                  color=Tema.color_signo(total), fontsize=10, fontweight="bold")
        ejes.axhline(0, color=Tema.BORDE, linewidth=1)
        ejes.set_xticks(range(len(nombres)), nombres, fontsize=8.5, color=Tema.TEXTO)
        ejes.yaxis.set_major_locator(MaxNLocator(nbins=5))
        ejes.yaxis.set_major_formatter(FuncFormatter(lambda v, _: self._eje(v)))
        ejes.grid(axis="y", color=Tema.BORDE, linewidth=0.6)
        ejes.set_axisbelow(True)
        ejes.margins(y=0.15)
        lienzo.draw_idle()

    def _dibujar_ganancia_activos(self, posiciones) -> None:
        """Una barra por activo, partida en las tres partes. Lo positivo va a la derecha del cero,
        lo negativo a la izquierda, y el rombo marca la ganancia neta del activo."""
        figura, ejes, lienzo = self._preparar_ejes("ganancia_activos")
        columnas = [llave for _, llave, _ in self.PARTES_GANANCIA]
        if posiciones.empty or any(c not in posiciones for c in columnas):
            self._mensaje_vacio(ejes, "El portafolio no trae el desglose por activo")
            lienzo.draw_idle()
            return
        posiciones = posiciones.sort_values("ganancia")  # el que más aporta queda arriba
        nombres = list(posiciones["nombre"])
        for y, (_, fila) in enumerate(posiciones.iterrows()):
            derecha = izquierda = 0.0
            for _, llave, color in self.PARTES_GANANCIA:
                valor = float(fila[llave])
                if valor == 0:
                    continue
                inicio = derecha if valor > 0 else izquierda
                ejes.barh(y, valor, left=inicio, height=0.58, color=color,
                          edgecolor=Tema.TARJETA, linewidth=1.5)
                if valor > 0:
                    derecha += valor
                else:
                    izquierda += valor
            neta = float(fila["ganancia"])
            ejes.plot(neta, y, marker="D", markersize=5, color=Tema.TEXTO,
                      markeredgecolor=Tema.TARJETA, markeredgewidth=1, zorder=3)
            borde = derecha if neta >= 0 else izquierda
            ejes.text(borde, y, f"  {self._con_signo(neta)}  " if neta >= 0 else f"{self._con_signo(neta)}  ",
                      ha="left" if neta >= 0 else "right", va="center",
                      color=Tema.TEXTO, fontsize=8)
        ejes.set_yticks(range(len(nombres)), nombres, fontsize=8.5, color=Tema.TEXTO)
        ejes.axvline(0, color=Tema.TEXTO_SECUNDARIO, linewidth=1)
        ejes.xaxis.set_major_locator(MaxNLocator(nbins=5))
        ejes.xaxis.set_major_formatter(FuncFormatter(lambda v, _: self._eje(v)))
        ejes.grid(axis="x", color=Tema.BORDE, linewidth=0.6)
        ejes.set_axisbelow(True)
        ejes.margins(x=0.18)
        leyenda = [Patch(color=c, label=n) for n, _, c in self.PARTES_GANANCIA]
        leyenda.append(Line2D([], [], marker="D", linestyle="", color=Tema.TEXTO,
                              markersize=5, label="Ganancia neta"))
        figura.legend(handles=leyenda, loc="outside lower center", ncol=4, frameon=False,
                      labelcolor=Tema.TEXTO_SECUNDARIO, fontsize=8.5, handlelength=1.2)
        lienzo.draw_idle()

    def _dibujar_evolucion(self, serie) -> None:
        _, ejes, lienzo = self._preparar_ejes("evolucion")
        serie = self._recortar_periodo(serie)
        if serie is None or serie.empty:
            self._mensaje_vacio(ejes)
        else:
            ejes.plot(serie["fecha"], serie["valor"], color=Tema.TEXTO, linewidth=1.6)
            ejes.plot(serie["fecha"].iloc[-1], serie["valor"].iloc[-1], "o",
                      color=Tema.ACENTO, markersize=5)  # el último valor lleva el acento
            ejes.yaxis.set_major_formatter(FuncFormatter(lambda v, _: self._abreviar(v)))
            ejes.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
            corto = (serie["fecha"].iloc[-1] - serie["fecha"].iloc[0]).days <= 100
            ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m" if corto else "%m/%Y"))
            ejes.grid(axis="y", color=Tema.BORDE, linewidth=0.6)
            # Cuánto cambió el valor entre el primer y el último día que se ven
            inicial, final = serie["valor"].iloc[0], serie["valor"].iloc[-1]
            if inicial > 0:
                cambio = final - inicial
                texto = f"Cambio en el período: {self._con_signo(cambio)} ({cambio / inicial:+.1%})"
                ejes.set_title(texto.replace(".", ","), loc="left", fontsize=9, pad=8,
                               color=Tema.GANANCIA if cambio >= 0 else Tema.PERDIDA)
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
