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
        self._botones = {}   # nombre -> botón del menú

        self.title("Seguimiento de portafolio de inversión")
        self.geometry(f"{Tema.ANCHO_VENTANA}x{Tema.ALTO_VENTANA}")
        self.minsize(1100, 680)

        # Columna 0: menú (ancho fijo). Columna 1: contenido (ocupa el resto).
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construir_menu()
        self._area_contenido = ctk.CTkFrame(self, fg_color=Tema.FONDO, corner_radius=0)
        self._area_contenido.grid(row=0, column=1, sticky="nsew")
        self._area_contenido.grid_columnconfigure(0, weight=1)
        self._area_contenido.grid_rowconfigure(0, weight=1)

        self.mostrar_vista("Dashboard")

    def _construir_menu(self) -> None:
        menu = ctk.CTkFrame(self, width=Tema.ANCHO_MENU, corner_radius=0, fg_color=Tema.PANEL)
        menu.grid(row=0, column=0, sticky="nsew")
        menu.pack_propagate(False)  # mantiene el ancho fijo aunque tenga hijos

        ctk.CTkLabel(menu, text="Portafolio", font=Tema.FUENTE_TITULO,
                     text_color=Tema.ACENTO).pack(anchor="w", padx=24, pady=(28, 0))
        ctk.CTkLabel(menu, text="Renta fija y renta variable", font=Tema.FUENTE_PEQUENA,
                     text_color=Tema.TEXTO_SECUNDARIO).pack(anchor="w", padx=24, pady=(0, 28))

        for nombre, _, _ in self.SECCIONES:
            boton = ctk.CTkButton(
                menu, text=nombre, anchor="w", height=42, font=Tema.FUENTE_MENU,
                corner_radius=Tema.RADIO, fg_color="transparent",
                hover_color=Tema.TARJETA, text_color=Tema.TEXTO_SECUNDARIO,
                command=lambda n=nombre: self.mostrar_vista(n),
            )
            boton.pack(fill="x", padx=14, pady=3)
            self._botones[nombre] = boton

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
        for nombre, boton in self._botones.items():
            if nombre == activo:
                boton.configure(fg_color=Tema.TARJETA, text_color=Tema.ACENTO)
            else:
                boton.configure(fg_color="transparent", text_color=Tema.TEXTO_SECUNDARIO)
