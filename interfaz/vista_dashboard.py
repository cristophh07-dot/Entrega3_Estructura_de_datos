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
    """Resumen del portafolio: tarjetas, gráficas y tablas.

    Todo se dibuja en refrescar(), que la VentanaPrincipal llama cada vez que
    se muestra esta vista. Los datos salen del portafolio (real o mock) y
    nunca se calculan aquí: la vista solo los presenta.
    """

    # (título, llave de portafolio.resumen(), formato, ¿verde/rojo según el signo?)
    INDICADORES = [
        ("Total invertido", "total_invertido", "pesos", False),
        ("Valor actual", "valor_actual", "pesos", False),
        ("Ganancia", "ganancia", "pesos", True),
        ("Rentabilidad acumulada", "rentabilidad_acumulada", "porcentaje", True),
        ("Rentabilidad E.A.", "rentabilidad_ea", "porcentaje", True),
    ]

    NOMBRES_TIPO = {
        "ACCION": "Acción", "CDT": "CDT", "BONO": "Bono", "TES": "TES",
        "DIVIDENDO": "Dividendo", "INTERES": "Interés", "CAPITAL": "Capital", "OTRO": "Otro",
    }

    COLUMNAS_POSICIONES = [
        ("nombre", "Activo", 200, "w"), ("tipo", "Tipo", 70, "w"),
        ("cantidad", "Cantidad", 95, "e"), ("costo", "Costo total", 115, "e"),
        ("valor", "Valor actual", 115, "e"), ("ingresos", "Ingresos", 100, "e"),
        ("ganancia", "Ganancia", 120, "e"), ("rentabilidad", "Rentabilidad", 120, "e"),
    ]

    COLUMNAS_FLUJOS = [
        ("fecha", "Fecha", 95, "w"), ("nombre", "Activo", 190, "w"),
        ("tipo", "Tipo", 90, "w"), ("valor", "Valor", 110, "e"),
    ]

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, fg_color=Tema.FONDO, corner_radius=0)
        self.repositorio = repositorio
        self.portafolio = portafolio
        self._valores = {}    # llave del resumen -> etiqueta con el valor de la tarjeta
        self._graficas = {}   # nombre -> (figura, ejes, lienzo)

        # El contenido va dentro de un marco con scroll porque no cabe en 760 px.
        self._contenido = ctk.CTkScrollableFrame(
            self, fg_color=Tema.FONDO, corner_radius=0,
            scrollbar_button_color=Tema.BORDE, scrollbar_button_hover_color=Tema.TEXTO_SECUNDARIO)
        self._contenido.pack(fill="both", expand=True)

        self._construir_encabezado()
        self._construir_indicadores()
        self._construir_fila_graficas()
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

        self._boton = ctk.CTkButton(
            marco, text="Actualizar precios", font=Tema.FUENTE_NORMAL, height=34, width=150,
            corner_radius=Tema.RADIO, fg_color="transparent", border_width=1,
            border_color=Tema.ACENTO, text_color=Tema.ACENTO, hover_color=Tema.HOVER,
            text_color_disabled=Tema.TEXTO_SECUNDARIO, command=self._actualizar_precios,
        )
        self._boton.grid(row=0, column=1, rowspan=2, sticky="e")

    def _construir_indicadores(self) -> None:
        """Un solo panel con los cinco indicadores, separados por líneas verticales."""
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

    def _construir_fila_graficas(self) -> None:
        fila = self._crear_fila(pesos=(1, 2))
        self._crear_grafica(fila, "distribucion", "Distribución", 3.2, 3.2).grid(
            row=0, column=0, sticky="nsew", padx=(0, 6))
        self._crear_grafica(fila, "evolucion", "Valor del portafolio", 6.4, 3.2).grid(
            row=0, column=1, sticky="nsew", padx=(6, 0))

    def _construir_fila_inferior(self) -> None:
        fila = self._crear_fila(pesos=(2, 3))
        self._crear_grafica(fila, "rentabilidad", "Rentabilidad por activo", 5, 3.2).grid(
            row=0, column=0, sticky="nsew", padx=(0, 6))

        tarjeta = self._crear_panel(fila, "Próximos pagos")
        tarjeta.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._tabla_flujos = TablaDatos(tarjeta, self.COLUMNAS_FLUJOS, altura=7)
        self._tabla_flujos.pack(fill="both", expand=True, padx=12, pady=(8, 14))

    def _construir_tabla_posiciones(self) -> None:
        fila = self._crear_fila(pesos=(1,))
        tarjeta = self._crear_panel(fila, "Posiciones")
        tarjeta.grid(row=0, column=0, sticky="nsew")
        self._tabla_posiciones = TablaDatos(tarjeta, self.COLUMNAS_POSICIONES, altura=8)
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
        """Tarjeta con una figura de matplotlib incrustada (FigureCanvasTkAgg)."""
        tarjeta = self._crear_panel(master, titulo)
        figura = Figure(figsize=(ancho, alto), dpi=100, facecolor=Tema.TARJETA, layout="constrained")
        ejes = figura.add_subplot(111)
        lienzo = FigureCanvasTkAgg(figura, master=tarjeta)
        widget = lienzo.get_tk_widget()
        widget.configure(bg=Tema.TARJETA, highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._graficas[nombre] = (figura, ejes, lienzo)
        return tarjeta

    # ------------------------------------------------------------------ actualización
    def refrescar(self) -> None:
        """Lee el portafolio y redibuja todo. Un error se muestra en pantalla, no cierra el programa."""
        try:
            self._actualizar_tarjetas()
            self._dibujar_distribucion()
            self._dibujar_evolucion()
            self._dibujar_rentabilidad()
            self._llenar_tablas()
            self._mostrar_estado(f"Datos al día. Revisado a las {datetime.now():%H:%M}")
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
            traceback.print_exc()
            self._mostrar_estado(f"No se pudieron cargar los datos: {error}", error=True)

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

    def _actualizar_tarjetas(self) -> None:
        resumen = self.portafolio.resumen()
        for _, llave, formato, con_signo in self.INDICADORES:
            valor = resumen[llave]
            texto = Tema.pesos(valor) if formato == "pesos" else Tema.porcentaje(valor)
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
    def _mensaje_vacio(ejes) -> None:
        ejes.set_axis_off()
        ejes.text(0.5, 0.5, "Aún no hay datos para mostrar", ha="center", va="center",
                  color=Tema.TEXTO_SECUNDARIO, fontsize=10, transform=ejes.transAxes)

    @staticmethod
    def _millones(valor: float) -> str:
        return f"$ {valor / 1_000_000:.1f}".replace(".", ",") + " M"

    def _dibujar_distribucion(self) -> None:
        figura, ejes, lienzo = self._preparar_ejes("distribucion")
        distribucion = self.portafolio.distribucion()
        valores = [distribucion["renta_fija"]["valor"], distribucion["renta_variable"]["valor"]]
        if sum(valores) <= 0:
            self._mensaje_vacio(ejes)
        else:
            trozos, _ = ejes.pie(
                valores, colors=[Tema.RENTA_FIJA, Tema.RENTA_VARIABLE], startangle=90,
                counterclock=False, wedgeprops={"width": 0.3, "edgecolor": Tema.TARJETA, "linewidth": 3},
            )
            ejes.text(0, 0.12, "Valor actual", ha="center", va="center",
                      color=Tema.TEXTO_SECUNDARIO, fontsize=8)
            ejes.text(0, -0.1, Tema.pesos(sum(valores)), ha="center", va="center",
                      color=Tema.TEXTO, fontsize=10, fontweight="bold")
            # Los porcentajes van en la leyenda: no caben dentro del aro.
            etiquetas = [
                f"Renta fija: {Tema.porcentaje(distribucion['renta_fija']['porcentaje'])}",
                f"Renta variable: {Tema.porcentaje(distribucion['renta_variable']['porcentaje'])}",
            ]
            figura.legend(trozos, etiquetas, loc="outside lower center", ncol=1, frameon=False,
                          labelcolor=Tema.TEXTO_SECUNDARIO, fontsize=9)
        lienzo.draw_idle()

    def _dibujar_evolucion(self) -> None:
        _, ejes, lienzo = self._preparar_ejes("evolucion")
        serie = self.portafolio.serie_valor(self._fecha_inicio())
        if serie is None or serie.empty:
            self._mensaje_vacio(ejes)
        else:
            ejes.plot(serie["fecha"], serie["valor"], color=Tema.TEXTO, linewidth=1.6)
            ejes.plot(serie["fecha"].iloc[-1], serie["valor"].iloc[-1], "o",
                      color=Tema.ACENTO, markersize=5)  # el último valor lleva el acento
            ejes.yaxis.set_major_formatter(FuncFormatter(lambda v, _: self._millones(v)))
            ejes.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
            ejes.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
            ejes.grid(axis="y", color=Tema.BORDE, linewidth=0.6)
        lienzo.draw_idle()

    def _dibujar_rentabilidad(self) -> None:
        _, ejes, lienzo = self._preparar_ejes("rentabilidad")
        posiciones = self.portafolio.posiciones()
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
    def _llenar_tablas(self) -> None:
        filas = []
        for _, p in self.portafolio.posiciones().iterrows():
            filas.append([
                p["nombre"], self.NOMBRES_TIPO.get(p["tipo"], p["tipo"]), Tema.cantidad(p["cantidad"]),
                Tema.pesos(p["costo_total"]), Tema.pesos(p["valor_actual"]), Tema.pesos(p["ingresos"]),
                Tema.pesos(p["ganancia"]), Tema.porcentaje(p["rentabilidad"]),
            ])
        self._tabla_posiciones.cargar(filas)

        filas = []
        for _, f in self.portafolio.proximos_flujos().iterrows():
            filas.append([str(f["fecha"])[:10], f["nombre"],
                          self.NOMBRES_TIPO.get(f["tipo"], f["tipo"]), Tema.pesos(f["valor"])])
        self._tabla_flujos.cargar(filas)
