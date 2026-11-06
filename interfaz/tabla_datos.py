from tkinter import ttk

import customtkinter as ctk

from interfaz.tema import Tema


class TablaDatos(ctk.CTkFrame):
    """Tabla con el estilo oscuro del Tema, reutilizada por todas las vistas.

    CustomTkinter no trae tablas, así que se envuelve un ttk.Treeview y se le
    aplica el estilo del Tema. Las columnas se describen como una lista de
    (clave, título, ancho, alineación) y las filas se cargan con cargar(),
    pasando los textos ya formateados.
    """

    def __init__(self, master, columnas, altura: int = 7):
        super().__init__(master, fg_color="transparent")
        self._aplicar_estilo()

        self._arbol = ttk.Treeview(
            self, columns=[c[0] for c in columnas], show="headings",
            height=altura, style="Tema.Treeview", selectmode="browse",
        )
        for clave, titulo, ancho, alineacion in columnas:
            self._arbol.heading(clave, text=titulo, anchor=alineacion)
            self._arbol.column(clave, width=ancho, anchor=alineacion, stretch=True)

        barra = ctk.CTkScrollbar(
            self, command=self._arbol.yview, width=12, fg_color="transparent",
            button_color=Tema.BORDE, button_hover_color=Tema.TEXTO_SECUNDARIO,
        )
        self._arbol.configure(yscrollcommand=barra.set)

        # Filas alternas: dan guía a la vista sin dibujar una línea por fila.
        self._arbol.tag_configure("par", background=Tema.TARJETA)
        self._arbol.tag_configure("impar", background=Tema.ZEBRA)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._arbol.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns", padx=(6, 0))

    @staticmethod
    def _aplicar_estilo() -> None:
        """El tema 'clam' es el que deja cambiar colores en Windows."""
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure(
            "Tema.Treeview", background=Tema.TARJETA, fieldbackground=Tema.TARJETA,
            foreground=Tema.TEXTO, rowheight=28, borderwidth=0, font=Tema.FUENTE_TABLA,
        )
        estilo.configure(
            "Tema.Treeview.Heading", background=Tema.TARJETA, foreground=Tema.TEXTO_SECUNDARIO,
            relief="flat", borderwidth=0, padding=(8, 6), font=Tema.FUENTE_TABLA,
        )
        estilo.map(
            "Tema.Treeview",
            background=[("selected", Tema.HOVER)], foreground=[("selected", Tema.TEXTO)],
        )
        estilo.map("Tema.Treeview.Heading", background=[("active", Tema.TARJETA)])
        estilo.layout("Tema.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    def cargar(self, filas) -> None:
        """Reemplaza el contenido. Cada fila es una lista de textos, en el orden de las columnas."""
        self._arbol.delete(*self._arbol.get_children())
        for indice, fila in enumerate(filas):
            self._arbol.insert("", "end", values=list(fila),
                               tags=("par" if indice % 2 == 0 else "impar",))
