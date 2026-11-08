import importlib

import customtkinter as ctk

from interfaz.tema import Tema


class VentanaPrincipal(ctk.CTk):
    """Ventana de la aplicación: menú lateral a la izquierda y la vista activa a la derecha.

    Cada vista es una clase de interfaz/ que se construye con
    (master, repositorio, portafolio). Se crea la primera vez que se abre
    y después se reutiliza; si tiene un método refrescar(), se llama cada
    vez que se muestra para que siempre tenga los datos al día.
    """

    # (texto del menú, módulo, clase). Las vistas se importan al abrirlas.
    SECCIONES = [
        ("Dashboard", "interfaz.vista_dashboard", "VistaDashboard"),
        ("Activos", "interfaz.vista_activos", "VistaActivos"),
        ("Operaciones", "interfaz.vista_operaciones", "VistaOperaciones"),
        ("Flujos", "interfaz.vista_flujos", "VistaFlujos"),
    ]

    def __init__(self, repositorio, portafolio):
        Tema.aplicar()
        super().__init__(fg_color=Tema.FONDO)

        self.repositorio = repositorio
        self.portafolio = portafolio
        self._vistas = {}    # nombre -> vista ya creada
        self._botones = {}   # nombre -> (botón del menú, indicador de sección activa)

        self.title("Seguimiento de portafolio de inversión")
        self.geometry(f"{Tema.ANCHO_VENTANA}x{Tema.ALTO_VENTANA}")
        self.minsize(1100, 680)

        # Columna 0: menú. Columna 1: línea separadora de 1 px. Columna 2: contenido.
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construir_menu()
        ctk.CTkFrame(self, width=1, height=1, fg_color=Tema.BORDE, corner_radius=0).grid(
            row=0, column=1, sticky="ns")
        self._area_contenido = ctk.CTkFrame(self, fg_color=Tema.FONDO, corner_radius=0)
        self._area_contenido.grid(row=0, column=2, sticky="nsew")
        self._area_contenido.grid_columnconfigure(0, weight=1)
        self._area_contenido.grid_rowconfigure(0, weight=1)

        self.mostrar_vista("Dashboard")

    def _construir_menu(self) -> None:
        menu = ctk.CTkFrame(self, width=Tema.ANCHO_MENU, corner_radius=0, fg_color=Tema.PANEL)
        menu.grid(row=0, column=0, sticky="nsew")
        menu.pack_propagate(False)  # mantiene el ancho fijo aunque tenga hijos

        ctk.CTkLabel(menu, text="Portafolio", font=Tema.FUENTE_TITULO,
                     text_color=Tema.TEXTO).pack(anchor="w", padx=20, pady=(24, 0))
        ctk.CTkLabel(menu, text="Renta fija y renta variable", font=Tema.FUENTE_PEQUENA,
                     text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w", padx=20, pady=(0, 20))
        ctk.CTkFrame(menu, height=1, fg_color=Tema.BORDE, corner_radius=0).pack(fill="x", pady=(0, 10))

        for nombre, _, _ in self.SECCIONES:
            fila = ctk.CTkFrame(menu, fg_color="transparent", corner_radius=0)
            fila.pack(fill="x", pady=1)
            # Franja de 3 px a la izquierda: se pinta con el acento en la sección activa.
            indicador = ctk.CTkFrame(fila, width=3, height=1, fg_color="transparent", corner_radius=0)
            indicador.pack(side="left", fill="y")
            boton = ctk.CTkButton(
                fila, text=nombre, anchor="w", height=40, font=Tema.FUENTE_MENU,
                corner_radius=0, fg_color="transparent", hover_color=Tema.HOVER, border_spacing=14,
                text_color=Tema.TEXTO_SECUNDARIO,
                command=lambda n=nombre: self.mostrar_vista(n),
            )
            boton.pack(side="left", fill="x", expand=True)
            self._botones[nombre] = (boton, indicador)

    def mostrar_vista(self, nombre: str) -> None:
        """Cambia a la vista indicada, creándola si es la primera vez."""
        if nombre not in self._vistas:
            vista = self._crear_vista(nombre)
            vista.grid(row=0, column=0, sticky="nsew")  # todas en la misma celda
            self._vistas[nombre] = vista

        vista = self._vistas[nombre]
        vista.tkraise()  # trae esta vista al frente
        if hasattr(vista, "refrescar"):
            vista.refrescar()
        self._marcar_boton_activo(nombre)

    def _crear_vista(self, nombre: str) -> ctk.CTkFrame:
        """Importa la clase de la vista y la construye; si aún no existe, muestra un aviso."""
        for texto, modulo, clase in self.SECCIONES:
            if texto != nombre:
                continue
            try:
                cls = getattr(importlib.import_module(modulo), clase)
            except ModuleNotFoundError as error:
                if error.name != modulo:  # falló otro import dentro de la vista: no ocultarlo
                    raise
                return self._crear_vista_pendiente(nombre)
            return cls(self._area_contenido, self.repositorio, self.portafolio)
        raise ValueError(f"Sección desconocida: {nombre}")

    def _crear_vista_pendiente(self, nombre: str) -> ctk.CTkFrame:
        marco = ctk.CTkFrame(self._area_contenido, fg_color=Tema.FONDO, corner_radius=0)
        ctk.CTkLabel(marco, text=nombre, font=Tema.FUENTE_TITULO,
                     text_color=Tema.TEXTO).pack(anchor="w", padx=Tema.MARGEN, pady=(Tema.MARGEN, 4))
        ctk.CTkLabel(marco, text="Esta vista todavía no está implementada.",
                     font=Tema.FUENTE_NORMAL,
                     text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w", padx=Tema.MARGEN)
        return marco

    def _marcar_boton_activo(self, activo: str) -> None:
        for nombre, (boton, indicador) in self._botones.items():
            if nombre == activo:
                boton.configure(fg_color=Tema.HOVER, text_color=Tema.TEXTO)
                indicador.configure(fg_color=Tema.ACENTO)
            else:
                boton.configure(fg_color="transparent", text_color=Tema.TEXTO_SECUNDARIO)
                indicador.configure(fg_color="transparent")
