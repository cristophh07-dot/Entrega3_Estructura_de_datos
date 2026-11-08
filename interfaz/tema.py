import customtkinter as ctk


class Tema:
    """Estilo visual compartido por todas las vistas.

    Referencia de diseño: paneles planos de estilo terminal financiero, con
    bordes de 1 px, esquinas casi rectas, una base neutra y un solo acento.

    Todo lo que se ve (colores, fuentes, tamaños) y todo el formato de números
    (pesos y porcentajes) vive aquí. Si algo se quiere cambiar en la
    aplicación, se cambia en este archivo y las vistas lo heredan.
    No se instancia: se usa directamente como Tema.ACENTO, Tema.pesos(...), etc.
    """

    # ---- Colores: grafito neutro; la jerarquía sale del tono y de líneas de 1 px ----
    FONDO = "#111214"
    PANEL = "#16171A"       # barra lateral
    TARJETA = "#16171A"     # superficie de los paneles
    ZEBRA = "#1B1C20"       # filas alternas de las tablas
    HOVER = "#202226"
    BORDE = "#363940"
    TEXTO = "#E7E8EA"
    TEXTO_SECUNDARIO = "#8A8E97"
    ACENTO = "#E0A23A"
    ACENTO_HOVER = "#C98F2E"
    TEXTO_SOBRE_ACENTO = "#111214"

    # Colores con significado financiero
    GANANCIA = "#4CAF82"
    PERDIDA = "#D95C5C"

    # Colores de las gráficas (el acento solo marca lo importante)
    RENTA_FIJA = "#6F7886"
    RENTA_VARIABLE = "#E0A23A"

    # ---- Fuentes (familia, tamaño, peso) ----
    FAMILIA = "Segoe UI"
    FAMILIA_NEGRITA = "Segoe UI Semibold"
    FUENTE_TITULO = (FAMILIA_NEGRITA, 22)
    FUENTE_SUBTITULO = (FAMILIA_NEGRITA, 13)
    FUENTE_NORMAL = (FAMILIA, 13)
    FUENTE_PEQUENA = (FAMILIA, 12)
    FUENTE_TABLA = (FAMILIA, 12)
    FUENTE_MENU = (FAMILIA, 14)
    FUENTE_TARJETA = (FAMILIA_NEGRITA, 20)

    # ---- Tamaños ----
    ANCHO_VENTANA = 1280
    ALTO_VENTANA = 760
    ANCHO_MENU = 200
    RADIO = 2
    MARGEN = 16

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
    def dolares(valor: float) -> str:
        """1234.5 -> 'US$ 1.234,50'. Los negativos quedan '-US$ 1.234,50'."""
        signo = "-" if round(valor, 2) < 0 else ""
        return f"{signo}US$ {Tema._numero(abs(valor), 2)}"

    @staticmethod
    def dinero(valor: float, moneda: str = "COP") -> str:
        """Formatea un valor en la moneda indicada ('COP' o 'USD')."""
        return Tema.dolares(valor) if moneda == "USD" else Tema.pesos(valor)

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
