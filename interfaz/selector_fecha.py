import calendar
from datetime import date

import customtkinter as ctk

from interfaz.tema import Tema


class SelectorFecha(ctk.CTkFrame):
    """Campo de fecha con un calendario desplegable, en vez de escribir AAAA-MM-DD.

    Se ve como un campo más del formulario ("sáb, 14 nov 2026  ▾"). Al hacer clic
    se despliega un calendario debajo:
      - flechas ‹ › para cambiar de mes y « » para cambiar de año;
      - los días en cuadrícula, de lunes a domingo;
      - el día de hoy con borde de color y el elegido relleno;
      - los días fuera del rango permitido (por ejemplo, el futuro en una compra) apagados;
      - botón "Hoy" y tecla Esc para cerrar.

    Para que las vistas existentes no cambien, se comporta como una entrada de texto:
    get() devuelve "AAAA-MM-DD" (o "" si no hay fecha), y delete()/insert() también funcionan.
    """

    DIAS_SEMANA = ["lu", "ma", "mi", "ju", "vi", "sá", "do"]
    MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    DIAS_NOMBRE = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

    def __init__(self, master, al_cambiar=None, minimo: date = None, maximo: date = None,
                 texto_vacio: str = "Elige una fecha"):
        super().__init__(master, fg_color="transparent")
        self._fecha = None
        self._al_cambiar = al_cambiar
        self.minimo, self.maximo = minimo, maximo
        self._texto_vacio = texto_vacio
        self._ventana = None          # calendario abierto (o None)
        self._mes_visible = None      # (año, mes) que muestra el calendario

        self._boton = ctk.CTkButton(
            self, text=texto_vacio, anchor="w", height=34, corner_radius=Tema.RADIO,
            border_width=1, border_color=Tema.BORDE, fg_color=Tema.FONDO, hover_color=Tema.HOVER,
            text_color=Tema.TEXTO_SECUNDARIO, font=Tema.FUENTE_NORMAL, command=self.abrir)
        self._boton.pack(fill="x")
        flecha = ctk.CTkLabel(self, text="▾", font=Tema.FUENTE_NORMAL, text_color=Tema.TEXTO_SECUNDARIO,
                              fg_color=Tema.FONDO, width=16)
        flecha.place(relx=1.0, rely=0.5, x=-12, anchor="e")
        flecha.bind("<Button-1>", lambda _e: self.abrir())

    # ------------------------------------------------------------------ como una entrada de texto
    def get(self) -> str:
        return self._fecha.isoformat() if self._fecha else ""

    def delete(self, *_args) -> None:
        self.establecer(None, avisar=False)

    def insert(self, _indice, texto: str) -> None:
        self.establecer(date.fromisoformat(texto.strip()), avisar=False)

    def configure(self, **kwargs):
        """border_color se aplica al campo visible (así se marcan los errores)."""
        if "border_color" in kwargs:
            self._boton.configure(border_color=kwargs.pop("border_color"))
        if kwargs:
            super().configure(**kwargs)

    # ------------------------------------------------------------------ valor
    @property
    def fecha(self):
        return self._fecha

    def establecer(self, fecha, avisar: bool = True) -> None:
        """Cambia la fecha mostrada. Si 'avisar', llama a al_cambiar (como si la eligiera el usuario)."""
        self._fecha = fecha
        if fecha is None:
            self._boton.configure(text=self._texto_vacio, text_color=Tema.TEXTO_SECUNDARIO)
        else:
            self._boton.configure(text=self.texto_largo(fecha), text_color=Tema.TEXTO)
        if avisar and self._al_cambiar:
            self._al_cambiar(fecha)

    def permitido(self, dia: date) -> bool:
        return (self.minimo is None or dia >= self.minimo) and (self.maximo is None or dia <= self.maximo)

    # ------------------------------------------------------------------ textos y cuadrícula (sin ventana: se pueden probar)
    @classmethod
    def texto_largo(cls, dia: date) -> str:
        """date(2026, 11, 14) -> 'sáb, 14 nov 2026'."""
        return f"{cls.DIAS_NOMBRE[dia.weekday()]}, {dia.day} {cls.MESES[dia.month - 1][:3]} {dia.year}"

    @staticmethod
    def semanas_del_mes(anio: int, mes: int):
        """Filas de 7 días (lunes a domingo) del mes; None donde no hay día de ese mes."""
        semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(anio, mes)
        return [[d if d.month == mes else None for d in semana] for semana in semanas]

    @staticmethod
    def mover_mes(anio: int, mes: int, pasos: int):
        """(2026, 12) + 1 -> (2027, 1). pasos = ±12 mueve un año."""
        total = anio * 12 + (mes - 1) + pasos
        return total // 12, total % 12 + 1

    # ------------------------------------------------------------------ calendario desplegable
    def abrir(self) -> None:
        if self._ventana is not None:
            self.cerrar()
            return
        base = self._fecha or (min(date.today(), self.maximo) if self.maximo else date.today())
        self._mes_visible = (base.year, base.month)

        self._ventana = ventana = ctk.CTkToplevel(self, fg_color=Tema.PANEL)
        ventana.withdraw()
        ventana.overrideredirect(True)          # sin barra de título: se ve como un menú desplegable
        ventana.attributes("-topmost", True)
        marco = ctk.CTkFrame(ventana, fg_color=Tema.PANEL, corner_radius=Tema.RADIO,
                             border_width=1, border_color=Tema.BORDE)
        marco.pack(fill="both", expand=True)
        self._marco = marco
        self._dibujar_mes()

        # Debajo del campo, sin salirse de la pantalla
        self.update_idletasks()
        ventana.update_idletasks()
        x, y = self._boton.winfo_rootx(), self._boton.winfo_rooty() + self._boton.winfo_height() + 4
        alto = ventana.winfo_reqheight()
        if y + alto > self.winfo_screenheight():
            y = self._boton.winfo_rooty() - alto - 4
        ventana.geometry(f"+{x}+{y}")
        ventana.deiconify()
        ventana.lift()
        ventana.focus_force()
        ventana.bind("<Escape>", lambda _e: self.cerrar())
        # Clic en cualquier otra parte de la aplicación: se cierra
        self._raiz_clic = self.winfo_toplevel().bind("<Button-1>", self._clic_fuera, add="+")

    def _clic_fuera(self, evento) -> None:
        if self._ventana is None:
            return
        v = self._ventana
        dentro = (v.winfo_rootx() <= evento.x_root <= v.winfo_rootx() + v.winfo_width()
                  and v.winfo_rooty() <= evento.y_root <= v.winfo_rooty() + v.winfo_height())
        en_campo = (self._boton.winfo_rootx() <= evento.x_root <= self._boton.winfo_rootx() + self._boton.winfo_width()
                    and self._boton.winfo_rooty() <= evento.y_root <= self._boton.winfo_rooty() + self._boton.winfo_height())
        if not dentro and not en_campo:
            self.cerrar()

    def cerrar(self) -> None:
        if self._ventana is not None:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._raiz_clic)
            except Exception:  # noqa: BLE001
                pass
            self._ventana.destroy()
            self._ventana = None

    def _dibujar_mes(self) -> None:
        for hijo in self._marco.winfo_children():
            hijo.destroy()
        anio, mes = self._mes_visible
        hoy = date.today()

        # Encabezado: « ‹  noviembre 2026  › »
        cabecera = ctk.CTkFrame(self._marco, fg_color="transparent")
        cabecera.pack(fill="x", padx=10, pady=(10, 6))
        for texto, pasos, lado, ayuda in (("«", -12, "left", "Año anterior"), ("‹", -1, "left", "Mes anterior"),
                                          ("»", 12, "right", "Año siguiente"), ("›", 1, "right", "Mes siguiente")):
            ctk.CTkButton(cabecera, text=texto, width=30, height=30, corner_radius=Tema.RADIO,
                          fg_color="transparent", hover_color=Tema.HOVER, text_color=Tema.TEXTO,
                          font=Tema.FUENTE_SUBTITULO,
                          command=lambda p=pasos: self._cambiar_mes(p)).pack(side=lado)
        ctk.CTkLabel(cabecera, text=f"{self.MESES[mes - 1].capitalize()} {anio}",
                     font=Tema.FUENTE_SUBTITULO, text_color=Tema.TEXTO).pack(side="left", expand=True)

        # Cuadrícula de días
        rejilla = ctk.CTkFrame(self._marco, fg_color="transparent")
        rejilla.pack(padx=10)
        for columna, nombre in enumerate(self.DIAS_SEMANA):
            ctk.CTkLabel(rejilla, text=nombre, width=38, font=Tema.FUENTE_PEQUENA,
                         text_color=Tema.TEXTO_SECUNDARIO).grid(row=0, column=columna, pady=(0, 2))
        for fila, semana in enumerate(self.semanas_del_mes(anio, mes), start=1):
            for columna, dia in enumerate(semana):
                if dia is None:
                    ctk.CTkLabel(rejilla, text="", width=38, height=34).grid(row=fila, column=columna)
                    continue
                elegido, es_hoy, activo = dia == self._fecha, dia == hoy, self.permitido(dia)
                ctk.CTkButton(
                    rejilla, text=str(dia.day), width=38, height=34, corner_radius=Tema.RADIO,
                    font=Tema.FUENTE_NORMAL,
                    fg_color=Tema.ACENTO if elegido else "transparent",
                    hover_color=Tema.ACENTO_HOVER if elegido else Tema.HOVER,
                    text_color=Tema.TEXTO_SOBRE_ACENTO if elegido else Tema.TEXTO,
                    text_color_disabled=Tema.BORDE,
                    border_width=1 if es_hoy and not elegido else 0, border_color=Tema.ACENTO,
                    state="normal" if activo else "disabled",
                    command=lambda d=dia: self._elegir(d),
                ).grid(row=fila, column=columna, padx=1, pady=1)

        # Pie: Hoy y Cerrar
        pie = ctk.CTkFrame(self._marco, fg_color="transparent")
        pie.pack(fill="x", padx=10, pady=(6, 10))
        ctk.CTkButton(pie, text="Hoy", width=70, height=30, corner_radius=Tema.RADIO,
                      fg_color="transparent", border_width=1, border_color=Tema.BORDE,
                      hover_color=Tema.HOVER, text_color=Tema.TEXTO, font=Tema.FUENTE_PEQUENA,
                      state="normal" if self.permitido(hoy) else "disabled",
                      command=lambda: self._elegir(hoy)).pack(side="left")
        ctk.CTkButton(pie, text="Cerrar", width=70, height=30, corner_radius=Tema.RADIO,
                      fg_color="transparent", hover_color=Tema.HOVER, text_color=Tema.TEXTO_SECUNDARIO,
                      font=Tema.FUENTE_PEQUENA, command=self.cerrar).pack(side="right")

    def _cambiar_mes(self, pasos: int) -> None:
        self._mes_visible = self.mover_mes(*self._mes_visible, pasos)
        self._dibujar_mes()

    def _elegir(self, dia: date) -> None:
        self.cerrar()
        self.establecer(dia)
