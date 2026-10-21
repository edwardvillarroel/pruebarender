"""Pruebas del ranking de productos mas vendidos.

El caso de uso es dueño de dos reglas que no se pueden dejar en manos de la
ruta ni del repositorio:

1. La ventana de venta ("7d", "30d", "todo") se traduce a una cota inferior de
   tiempo. Un periodo desconocido es un error de contrato: ignorarlo en
   silencio devolveria el historico completo donde el frontend pidio la
   semana, y el titulo "Los mas vendidos de la semana" mentiria.
2. El limite se acota. Sin tope, un `limite=100000` arrastra el catalogo
   entero a memoria.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.domain.entities.producto import FotoColorCatalogo, Producto, ProductoVendido
from app.domain.time import utcnow


def _servicio(vendidos=None) -> tuple[GestionarProducto, Mock]:
    repositorio = Mock()
    repositorio.listar_mas_vendidos.return_value = vendidos or []
    repositorio.primera_imagen_color_por_producto.return_value = {}
    return GestionarProducto(repositorio), repositorio


def _producto(**cambios) -> Producto:
    base = dict(nombre="Producto de prueba", categoria_id=uuid4(), precio=1000, stock=3)
    base.update(cambios)
    return Producto(**base)


def _dias_que_transcurren(desde) -> float:
    return (utcnow() - desde).total_seconds() / 86400


# --- Ventana de venta --------------------------------------------------------


def test_el_periodo_todo_no_pone_cota_inferior():
    """El historico completo no acota por fecha."""
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos("todo", 10)

    desde, _ = repositorio.listar_mas_vendidos.call_args[0]
    assert desde is None


def test_el_periodo_de_una_semana_acota_a_siete_dias():
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos("7d", 10)

    desde, _ = repositorio.listar_mas_vendidos.call_args[0]
    assert desde is not None
    assert _dias_que_transcurren(desde) == pytest.approx(7, abs=0.01)


def test_el_periodo_de_un_mes_acota_a_treinta_dias():
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos("30d", 10)

    desde, _ = repositorio.listar_mas_vendidos.call_args[0]
    assert _dias_que_transcurren(desde) == pytest.approx(30, abs=0.01)


def test_un_periodo_desconocido_es_un_error_y_no_el_historico():
    """Un typo no puede devolver el historico completo en silencio."""
    servicio, _ = _servicio()

    with pytest.raises(ValueError):
        servicio.listar_mas_vendidos("7-semanas", 10)


def test_el_periodo_acepta_variantes_de_mayusculas_y_espacios():
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos(" 7D ", 10)

    desde, _ = repositorio.listar_mas_vendidos.call_args[0]
    assert _dias_que_transcurren(desde) == pytest.approx(7, abs=0.01)


def test_sin_periodo_se_toma_el_historico():
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos()

    desde, _ = repositorio.listar_mas_vendidos.call_args[0]
    assert desde is None


# --- Limite ------------------------------------------------------------------


def test_el_limite_se_acota_al_maximo():
    """Sin tope, un `limite=100000` arrastra el catalogo entero a memoria."""
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos("todo", 100000)

    _, limite = repositorio.listar_mas_vendidos.call_args[0]
    assert limite == 50


def test_un_limite_cero_o_negativo_se_pone_en_uno():
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos("todo", 0)

    _, limite = repositorio.listar_mas_vendidos.call_args[0]
    assert limite == 1


def test_un_limite_que_no_es_numero_usa_el_default():
    """La ruta pasa el query param crudo: si no es un numero, no es un error."""
    servicio, repositorio = _servicio()

    servicio.listar_mas_vendidos("todo", "diez")

    _, limite = repositorio.listar_mas_vendidos.call_args[0]
    assert limite == 10


# --- Contenido del ranking ----------------------------------------------------


def test_devuelve_los_vendidos_tal_como_los_dio_el_repositorio():
    """El orden del ranking lo fija la agregacion del repositorio."""
    vendidos = [
        ProductoVendido(producto=_producto(nombre="Primero"), unidades=9, ingresos=9000),
        ProductoVendido(producto=_producto(nombre="Segundo"), unidades=4, ingresos=4000),
    ]
    servicio, _ = _servicio(vendidos)

    resultado = servicio.listar_mas_vendidos("todo", 10)

    assert [v.producto.nombre for v in resultado] == ["Primero", "Segundo"]


def test_un_producto_sin_foto_usa_la_foto_de_su_primer_color():
    """Las tarjetas del ranking se pintan como las del catalogo: sin foto se
    ven rotas."""
    producto = _producto(imagen=None)
    vendidos = [ProductoVendido(producto=producto, unidades=2, ingresos=2000)]
    servicio, repositorio = _servicio(vendidos)
    repositorio.primera_imagen_color_por_producto.return_value = {
        producto.id: FotoColorCatalogo(
            imagen_url="/api/productos/colores/abc/imagen",
            imagen_thumb_url="/api/productos/colores/abc/thumb",
        )
    }

    resultado = servicio.listar_mas_vendidos("todo", 10)

    assert resultado[0].producto.imagen == "/api/productos/colores/abc/imagen"
    assert resultado[0].producto.imagen_thumb == "/api/productos/colores/abc/thumb"


def test_un_producto_con_foto_no_consulta_los_colores():
    producto = _producto(imagen="/api/productos/abc/imagen")
    servicio, repositorio = _servicio(
        [ProductoVendido(producto=producto, unidades=1, ingresos=1000)]
    )

    servicio.listar_mas_vendidos("todo", 10)

    repositorio.primera_imagen_color_por_producto.assert_not_called()
