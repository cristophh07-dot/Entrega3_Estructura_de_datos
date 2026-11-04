"""
Punto de entrada único del sistema de seguimiento de portafolio.

Ejecutar:  py main.py          → usa las clases reales
           py main.py --mock   → usa los datos falsos de mocks/

Mientras alguna parte real no exista todavía, main.py usa
automáticamente su mock y lo avisa en consola.
"""
import sys


def crear_repositorio(usar_mock):
    if not usar_mock:
        try:
            from datos.repositorio import Repositorio
            return Repositorio()
        except ImportError:
            print("[main] datos.repositorio aún no existe: uso RepositorioMock")
    from mocks.repositorio_mock import RepositorioMock
    return RepositorioMock()


def crear_servicio_precios(repositorio, usar_mock):
    if not usar_mock:
        try:
            from datos.servicio_precios import ServicioPrecios
            return ServicioPrecios(repositorio)
        except ImportError:
            print("[main] datos.servicio_precios aún no existe: uso ServicioPreciosMock")
    from mocks.servicio_precios_mock import ServicioPreciosMock
    return ServicioPreciosMock(repositorio)


def crear_portafolio(repositorio, precios, usar_mock):
    if not usar_mock:
        try:
            from motor.portafolio import Portafolio
            return Portafolio(repositorio, precios)
        except ImportError:
            print("[main] motor.portafolio aún no existe: uso PortafolioMock")
    from mocks.portafolio_mock import PortafolioMock
    return PortafolioMock(repositorio, precios)


def main():
    usar_mock = "--mock" in sys.argv
    repositorio = crear_repositorio(usar_mock)
    precios = crear_servicio_precios(repositorio, usar_mock)
    portafolio = crear_portafolio(repositorio, precios, usar_mock)

    try:
        from interfaz.ventana_principal import VentanaPrincipal
    except ImportError:
        print("[main] interfaz.ventana_principal aún no existe. Resumen en consola:")
        for clave, valor in portafolio.resumen().items():
            print(f"  {clave:<24} {valor:,.4f}")
        return

    VentanaPrincipal(repositorio, portafolio).mainloop()


if __name__ == "__main__":
    main()