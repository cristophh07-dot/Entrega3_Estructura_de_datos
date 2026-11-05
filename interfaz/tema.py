import customtkinter as ctk


class Tema:
    """Estilo visual compartido por todas las vistas.

    Todo lo que se ve (colores, fuentes, tamaños) y todo el formato de números
    (pesos y porcentajes) vive aquí. Si algo se quiere cambiar en la
    aplicación, se cambia en este archivo y las vistas lo heredan.
    No se instancia: se usa directamente como Tema.ACENTO, Tema.pesos(...), etc.
    """

    # ---- Colores: modo oscuro, azul pizarra con un solo acento dorado ----
    FONDO = "#10141C"
    PANEL = "#161B26"
    TARJETA = "#1C2230"
    BORDE = "#2A3244"
    TEXTO = "#E9ECF2"
    TEXTO_SECUNDARIO = "#8F9AB0"
    ACENTO = "#D9A441"
    ACENTO_HOVER = "#C28F32"
    TEXTO_SOBRE_ACENTO = "#10141C"

    # Colores con significado financiero
    GANANCIA = "#3DBE8B"
    PERDIDA = "#E5586B"

    # Colores de las gráficas
    RENTA_FIJA = "#5B9BD5"
    RENTA_VARIABLE = "#D9A441"

    # ---- Fuentes (familia, tamaño, peso) ----
    FAMILIA = "Segoe UI"
    FUENTE_TITULO = (FAMILIA, 26, "bold")
    FUENTE_SUBTITULO = (FAMILIA, 16, "bold")
    FUENTE_NORMAL = (FAMILIA, 14)
    FUENTE_PEQUENA = (FAMILIA, 12)
    FUENTE_TABLA = (FAMILIA, 12)
    FUENTE_MENU = (FAMILIA, 15)
    FUENTE_TARJETA = (FAMILIA, 20, "bold")

    # ---- Tamaños ----
    ANCHO_VENTANA = 1280
    ALTO_VENTANA = 760
    ANCHO_MENU = 220
    RADIO = 10
    MARGEN = 20

    @staticmethod
    def aplicar() -> None:
        """Activa el modo oscuro. Se llama una vez, antes de crear la ventana."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    # ---- Formato de números (estilo colombiano: 1.250.000,50) ----
    @staticmethod
    def _numero(valor: float, decimales: int) -> str:
        """Formatea con '.' para miles y ',' para decimales."""
        texto = f"{valor:,.{decimales}f}"  # 1,250,000.50
        return texto.replace(",", "#").replace(".", ",").replace("#", ".")

    @staticmethod
    def pesos(valor: float) -> str:
        """1250000 -> '$ 1.250.000'. Los negativos quedan '-$ 1.250.000'."""
        entero = round(valor)
        signo = "-" if entero < 0 else ""
        return f"{signo}$ {Tema._numero(abs(entero), 0)}"

    @staticmethod
    def cantidad(valor: float) -> str:
        """Acciones o títulos: sin decimales si es entera (2000 -> '2.000')."""
        decimales = 0 if float(valor).is_integer() else 2
        return Tema._numero(float(valor), decimales)

    @staticmethod
    def porcentaje(decimal: float) -> str:
        """Recibe la tasa en decimal (0.1235) y la muestra como '12,35 %'."""
        return f"{Tema._numero(decimal * 100, 2)} %"

    @staticmethod
    def color_signo(valor: float) -> str:
        """Verde si es ganancia, rojo si es pérdida, texto normal si es cero."""
        if valor > 0:
            return Tema.GANANCIA
        if valor < 0:
            return Tema.PERDIDA
        return Tema.TEXTO
