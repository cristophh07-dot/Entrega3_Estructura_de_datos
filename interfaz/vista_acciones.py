import traceback
from datetime import date, timedelta

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator

from interfaz.tema import Tema


class VistaAcciones(ctk.CTkFrame):
    """Cómo ha subido o bajado cada acción, con una gráfica de velas japonesas.

    Cada vela es un día (o una semana si el período es largo):
      - el cuerpo va de la apertura al cierre: verde si cerró más alto, rojo si cerró más bajo;
      - la línea fina (mecha) va del mínimo al máximo de ese día.
    Encima se marcan las compras (▲) y ventas (▼) del usuario y su costo promedio,
    para comparar a qué precio compró con lo que vale hoy.

    Los datos salen de portafolio.grafica_accion(); la vista solo los dibuja.
    """

    # (texto del botón, días hacia atrás; None = desde la primera compra)
    PERIODOS = [("1M", 30), ("3M", 91), ("6M", 182), ("1A", 365), ("Desde la compra", None)]
    MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

    # (título, llave del resumen, ¿verde/rojo según el signo?)
    INDICADORES = [
        ("Último cierre", "ultimo_cierre", False),
        ("Variación en el período", "variacion", True),
        ("Máximo del período", "maximo", False),
        ("Mínimo del período", "minimo", False),
        ("Tu costo promedio", "costo_promedio", False),
    ]

    COLOR_COMPRA = Tema.VALORIZACION
    COLOR_VENTA = Tema.VENTAS

    def __init__(self, master, repositorio, portafolio):
        super().__init__(master, fg_color=Tema.FONDO, corner_radius=0)
        self.repositorio = repositorio
        self.portafolio = portafolio
        self._moneda = "USD"
        self._periodo = "Desde la compra"
        self._acciones = {}       # texto del menú -> activo
        self._valores = {}        # llave -> etiqueta del indicador
        self._velas = None        # velas que se están mostrando (para el detalle al pasar el mouse)

        self._contenido = ctk.CTkScrollableFrame(
            self, fg_color=Tema.FONDO, corner_radius=0,
            scrollbar_button_color=Tema.BORDE, scrollbar_button_hover_color=Tema.TEXTO_SECUNDARIO)
        self._contenido.pack(fill="both", expand=True)

        self._construir_encabezado()
        self._construir_controles()
        self._construir_indicadores()
        self._construir_grafica()

    # ------------------------------------------------------------------ construcción
    def _construir_encabezado(self) -> None:
        marco = ctk.CTkFrame(self._contenido, fg_color="transparent")
        marco.pack(fill="x", padx=Tema.MARGEN, pady=(Tema.MARGEN, 12))
        ctk.CTkLabel(marco, text="Acciones", font=Tema.FUENTE_TITULO,
                     text_color=Tema.TEXTO).pack(anchor="w")
        self._estado = ctk.CTkLabel(
            marco, text="Cómo ha subido o bajado cada acción, día a día.",
            font=Tema.FUENTE_PEQUENA, text_color=Tema.TEXTO_SECUNDARIO)
        self._estado.pack(anchor="w")

    def _construir_controles(self) -> None:
        fila = ctk.CTkFrame(self._contenido, fg_color="transparent")
        fila.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))

        ctk.CTkLabel(fila, text="Acción", font=Tema.FUENTE_PEQUENA,
                     text_color=Tema.TEXTO_SECUNDARIO).pack(side="left", padx=(0, 8))
        self._menu_accion = ctk.CTkOptionMenu(
            fila, values=["(sin acciones)"], command=lambda _: self._dibujar(), width=220, height=34,
            font=Tema.FUENTE_NORMAL, corner_radius=Tema.RADIO, fg_color=Tema.TARJETA,
            button_color=Tema.BORDE, button_hover_color=Tema.HOVER, text_color=Tema.TEXTO,
            dropdown_fg_color=Tema.TARJETA, dropdown_hover_color=Tema.HOVER,
            dropdown_text_color=Tema.TEXTO)
        self._menu_accion.pack(side="left", padx=(0, 20))

        self._selector_periodo = self._segmentado(fila, [p for p, _ in self.PERIODOS], self._cambiar_periodo)
        self._selector_periodo.set(self._periodo)
        self._selector_periodo.pack(side="left", padx=(0, 20))

        self._selector_moneda = self._segmentado(fila, ["USD", "COP"], self._cambiar_moneda)
        self._selector_moneda.set(self._moneda)
        self._selector_moneda.pack(side="right")

    @staticmethod
    def _segmentado(master, valores, comando):
        return ctk.CTkSegmentedButton(
            master, values=valores, command=comando, font=Tema.FUENTE_NORMAL, height=34,
            corner_radius=Tema.RADIO, border_width=1, fg_color=Tema.BORDE,
            selected_color=Tema.BORDE, selected_hover_color=Tema.BORDE,
            unselected_color=Tema.FONDO, unselected_hover_color=Tema.HOVER, text_color=Tema.TEXTO)

    def _construir_indicadores(self) -> None:
        banda = ctk.CTkFrame(self._contenido, fg_color=Tema.TARJETA, corner_radius=Tema.RADIO,
                             border_width=1, border_color=Tema.BORDE)
        banda.pack(fill="x", padx=Tema.MARGEN, pady=(0, 12))
        for indice, (titulo, llave, _) in enumerate(self.INDICADORES):
            columna = indice * 2
            banda.grid_columnconfigure(columna, weight=1, uniform="indicadores")
            if indice:
                ctk.CTkFrame(banda, width=1, height=1, fg_color=Tema.BORDE, corner_radius=0).grid(
                    row=0, column=columna - 1, sticky="ns", pady=12)
            celda = ctk.CTkFrame(banda, fg_color="transparent")
            celda.grid(row=0, column=columna, sticky="nsew")
            ctk.CTkLabel(celda, text=titulo, font=Tema.FUENTE_PEQUENA,
                         text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w", padx=16, pady=(12, 0))
            valor = ctk.CTkLabel(celda, text="-", font=Tema.FUENTE_TARJETA, text_color=Tema.TEXTO)
            valor.pack(anchor="w", padx=16, pady=(2, 0))
            nota = ctk.CTkLabel(celda, text="", font=Tema.FUENTE_PEQUENA, text_color=Tema.TEXTO_SECUNDARIO)
            nota.pack(anchor="w", padx=16, pady=(0, 10))
            self._valores[llave] = (valor, nota)

    def _construir_grafica(self) -> None:
        panel = ctk.CTkFrame(self._contenido, fg_color=Tema.TARJETA, corner_radius=Tema.RADIO,
                             border_width=1, border_color=Tema.BORDE)
        panel.pack(fill="both", expand=True, padx=Tema.MARGEN, pady=(0, Tema.MARGEN))
        self._titulo_grafica = ctk.CTkLabel(panel, text="", font=Tema.FUENTE_SUBTITULO,
                                            text_color=Tema.TEXTO)
        self._titulo_grafica.pack(anchor="w", padx=16, pady=(12, 10))
        ctk.CTkFrame(panel, height=1, fg_color=Tema.BORDE, corner_radius=0).pack(fill="x")

        self._figura = Figure(figsize=(10.4, 4.6), dpi=100, facecolor=Tema.TARJETA, layout="constrained")
        self._ejes = self._figura.add_subplot(111)
        self._lienzo = FigureCanvasTkAgg(self._figura, master=panel)
        widget = self._lienzo.get_tk_widget()
        widget.configure(bg=Tema.TARJETA, highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self._lienzo.mpl_connect("motion_notify_event", self._al_mover_mouse)

        # Detalle de la vela bajo el mouse (fecha, apertura, máximo, mínimo, cierre)
        self._detalle = ctk.CTkLabel(panel, text="Pasa el mouse sobre una vela para ver su detalle.",
                                     font=Tema.FUENTE_PEQUENA, text_color=Tema.TEXTO_SECUNDARIO)
        self._detalle.pack(anchor="w", padx=16, pady=(0, 12))

    # ------------------------------------------------------------------ datos
    def refrescar(self) -> None:
        """La ventana lo llama al mostrar la vista: recarga la lista de acciones y redibuja."""
        anterior = self._menu_accion.get()
        acciones = [a for a in self.repositorio.listar_activos() if not a.es_renta_fija()]
        self._acciones = {f"{a.nombre} ({a.ticker})": a for a in acciones}
        opciones = list(self._acciones) or ["(sin acciones)"]
        self._menu_accion.configure(values=opciones)
        self._menu_accion.set(anterior if anterior in self._acciones else opciones[0])
        self._dibujar()

    def _cambiar_periodo(self, periodo: str) -> None:
        self._periodo = periodo
        self._dibujar()

    def _cambiar_moneda(self, moneda: str) -> None:
        self._moneda = moneda
        self._dibujar()

    def _desde(self, activo) -> date:
        """Fecha de inicio según el período elegido."""
        dias = dict(self.PERIODOS)[self._periodo]
        if dias is not None:
            return date.today() - timedelta(days=dias)
        compras = [op.fecha for op in self.repositorio.listar_operaciones(activo.id)]
        return (min(compras) - timedelta(days=7)) if compras else date.today() - timedelta(days=365)

    def _dibujar(self) -> None:
        activo = self._acciones.get(self._menu_accion.get())
        if activo is None:
            self._limpiar("Aún no hay acciones registradas. Agrégalas en la sección Activos.")
            return
        try:
            datos = self.portafolio.grafica_accion(activo.id, self._desde(activo), moneda=self._moneda)
        except Exception as error:  # noqa: BLE001 - la interfaz no debe caerse
            traceback.print_exc()
            self._limpiar(f"No se pudieron cargar las velas: {error}", error=True)
            return
        if datos["velas"].empty:
            self._limpiar("No se encontraron precios para este período (¿hay conexión a internet?).")
            return
        self._mostrar_indicadores(datos)
        unidad = "semanales" if datos["agrupacion"] == "semana" else "diarias"
        self._titulo_grafica.configure(text=f"Velas {unidad} · {activo.nombre} ({activo.ticker}) · {self._moneda}")
        self.dibujar_velas(self._ejes, datos)
        self._velas = datos["velas"]
        self._lienzo.draw_idle()
        self._estado.configure(text="Cómo ha subido o bajado cada acción, día a día.",
                               text_color=Tema.TEXTO_SECUNDARIO)

    def _limpiar(self, mensaje: str, error: bool = False) -> None:
        for valor, nota in self._valores.values():
            valor.configure(text="-", text_color=Tema.TEXTO)
            nota.configure(text="")
        self._titulo_grafica.configure(text="")
        self._ejes.clear()
        self._ejes.set_axis_off()
        self._ejes.text(0.5, 0.5, mensaje, ha="center", va="center", color=Tema.TEXTO_SECUNDARIO,
                        fontsize=10, transform=self._ejes.transAxes)
        self._velas = None
        self._lienzo.draw_idle()
        self._estado.configure(text=mensaje, text_color=Tema.PERDIDA if error else Tema.TEXTO_SECUNDARIO)

    def _mostrar_indicadores(self, datos: dict) -> None:
        resumen, costo = datos["resumen"], datos["costo_promedio"]
        valores = dict(resumen, costo_promedio=costo)
        for _, llave, con_signo in self.INDICADORES:
            etiqueta, nota = self._valores[llave]
            valor = valores.get(llave)
            if valor is None:
                etiqueta.configure(text="-", text_color=Tema.TEXTO)
                nota.configure(text="Ya no tienes esta acción" if llave == "costo_promedio" else "")
                continue
            if llave == "variacion":
                texto = ("+" if valor > 0 else "") + Tema.porcentaje(valor)
            else:
                texto = self._precio(valor)
            etiqueta.configure(text=texto, text_color=Tema.color_signo(valor) if con_signo else Tema.TEXTO)
            nota.configure(text="")
        self._valores["variacion"][1].configure(
            text=f"desde {self._fecha(resumen['desde'])} ({self._precio(resumen['precio_inicio'])})")
        if costo:
            frente = resumen["ultimo_cierre"] / costo - 1
            self._valores["costo_promedio"][1].configure(
                text=f"Hoy vale {'+' if frente > 0 else ''}{Tema.porcentaje(frente)} frente a tu costo",
                text_color=Tema.color_signo(frente))

    # ------------------------------------------------------------------ formato
    def _precio(self, valor: float) -> str:
        """Precio de una acción: US$ 72,15 o $ 295.200."""
        return Tema.dolares(valor) if self._moneda == "USD" else Tema.pesos(valor)

    def _precio_eje(self, valor: float) -> str:
        if self._moneda == "USD":
            return f"US$ {valor:,.0f}".replace(",", ".") if valor >= 100 else f"US$ {valor:.1f}".replace(".", ",")
        return f"$ {valor / 1000:,.0f} mil".replace(",", ".") if valor >= 10_000 else f"$ {valor:,.0f}".replace(",", ".")

    def _fecha(self, dia: date, con_anio: bool = True) -> str:
        texto = f"{dia.day} {self.MESES[dia.month - 1]}"
        return f"{texto} {dia.year}" if con_anio else texto

    # ------------------------------------------------------------------ gráfica
    def dibujar_velas(self, ejes, datos: dict) -> None:
        """Dibuja las velas, las compras/ventas y el costo promedio en unos ejes de matplotlib."""
        velas, ops, costo = datos["velas"], datos["operaciones"], datos["costo_promedio"]
        figura = ejes.figure
        for leyenda in list(figura.legends):
            leyenda.remove()
        ejes.clear()
        ejes.set_axis_on()
        ejes.set_facecolor(Tema.TARJETA)
        ejes.spines[["top", "right", "left"]].set_visible(False)
        ejes.spines["bottom"].set_color(Tema.BORDE)
        ejes.tick_params(colors=Tema.TEXTO_SECUNDARIO, labelsize=9, length=0)

        x = list(range(len(velas)))
        aperturas, cierres = list(velas["apertura"]), list(velas["cierre"])
        maximos, minimos = list(velas["maximo"]), list(velas["minimo"])
        colores = [Tema.GANANCIA if c >= a else Tema.PERDIDA for a, c in zip(aperturas, cierres)]
        rango = max(maximos) - min(minimos) or 1
        ancho = 0.62 if len(x) < 90 else 0.72

        ejes.vlines(x, minimos, maximos, colors=colores, linewidth=1)            # mechas
        alturas = [max(abs(c - a), rango * 0.002) for a, c in zip(aperturas, cierres)]
        ejes.bar(x, alturas, bottom=[min(a, c) for a, c in zip(aperturas, cierres)],
                 width=ancho, color=colores, linewidth=0)                         # cuerpos

        # Compras y ventas, sobre la vela del día en que se hicieron, a su precio
        fechas = list(velas["fecha"])
        def indice(dia):
            anteriores = [i for i, f in enumerate(fechas) if f <= dia]
            return anteriores[-1] if anteriores else None
        leyenda = [Patch(color=Tema.GANANCIA, label="Cerró más alto de lo que abrió"),
                   Patch(color=Tema.PERDIDA, label="Cerró más bajo")]
        for tipo, marcador, color, texto in (("COMPRA", "^", self.COLOR_COMPRA, "Tu compra"),
                                             ("VENTA", "v", self.COLOR_VENTA, "Tu venta")):
            filas = ops[ops["tipo"] == tipo] if not ops.empty else ops
            puntos = [(indice(f), p) for f, p in zip(filas["fecha"], filas["precio"]) if indice(f) is not None]
            if puntos:
                ejes.scatter([i for i, _ in puntos], [p for _, p in puntos], marker=marcador, s=90,
                             color=color, edgecolors=Tema.TARJETA, linewidths=1.5, zorder=4)
                leyenda.append(Line2D([], [], marker=marcador, linestyle="", color=color,
                                      markersize=7, label=texto))

        if costo:
            ejes.axhline(costo, color=Tema.ACENTO, linewidth=1.2, linestyle=(0, (5, 3)), zorder=3)
            ejes.annotate(f"Tu costo promedio {self._precio(costo)}", xy=(0, costo),
                          xycoords=("axes fraction", "data"), xytext=(6, 5), textcoords="offset points",
                          ha="left", va="bottom", color=Tema.ACENTO, fontsize=8.5, zorder=5,
                          bbox={"boxstyle": "round,pad=0.25", "facecolor": Tema.TARJETA,
                                "edgecolor": "none", "alpha": 0.9})
            leyenda.append(Line2D([], [], color=Tema.ACENTO, linestyle=(0, (5, 3)), label="Tu costo promedio"))

        # Último cierre resaltado a la derecha
        ejes.annotate(self._precio(cierres[-1]), xy=(x[-1], cierres[-1]), xytext=(8, 0),
                      textcoords="offset points", va="center", color=Tema.TEXTO, fontsize=8.5,
                      fontweight="bold")

        semanal = datos.get("agrupacion") == "semana"
        pasos = max(1, len(x) // 6)
        marcas = x[::pasos]
        ejes.set_xticks(marcas, [self._fecha(fechas[i], con_anio=semanal or i == 0) for i in marcas])
        ejes.set_xlim(-1, len(x) + max(3, len(x) * 0.06))
        ejes.yaxis.set_major_locator(MaxNLocator(nbins=6))
        ejes.yaxis.set_major_formatter(FuncFormatter(lambda v, _: self._precio_eje(v)))
        ejes.grid(axis="y", color=Tema.BORDE, linewidth=0.6)
        ejes.set_axisbelow(True)

        figura.legend(handles=leyenda, loc="outside lower center", ncol=len(leyenda), frameon=False,
                      labelcolor=Tema.TEXTO_SECUNDARIO, fontsize=8.5, handlelength=1.4)

    def _al_mover_mouse(self, evento) -> None:
        """Muestra apertura, máximo, mínimo y cierre de la vela bajo el mouse."""
        if self._velas is None or evento.inaxes is not self._ejes or evento.xdata is None:
            return
        i = int(round(evento.xdata))
        if not 0 <= i < len(self._velas):
            return
        v = self._velas.iloc[i]
        cambio = v["cierre"] / v["apertura"] - 1
        self._detalle.configure(
            text=(f"{self._fecha(v['fecha'])}   ·   Apertura {self._precio(v['apertura'])}   ·   "
                  f"Máximo {self._precio(v['maximo'])}   ·   Mínimo {self._precio(v['minimo'])}   ·   "
                  f"Cierre {self._precio(v['cierre'])} ({'+' if cambio > 0 else ''}{Tema.porcentaje(cambio)})"),
            text_color=Tema.TEXTO)
