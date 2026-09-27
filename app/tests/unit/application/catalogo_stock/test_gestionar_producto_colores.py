from unittest.mock import Mock
from uuid import uuid4

from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.domain.entities.producto import (
    ColorProducto,
    FotoColorCatalogo,
    ImagenProducto,
    Producto,
)


def _repositorio(producto: Producto | None = None) -> Mock:
    repositorio = Mock()
    repositorio.get_by_id.return_value = producto
    repositorio.guardar_color.side_effect = lambda producto_id, nombre, imagen: ColorProducto(
        producto_id=producto_id, nombre=nombre
    )
    return repositorio


def _producto() -> Producto:
    return Producto(nombre="Hyrule", categoria_id=uuid4(), precio=11912, stock=5)


def _imagen() -> ImagenProducto:
    return ImagenProducto(bytes=b"jpeg-falso", content_type="image/jpeg")


def test_listar_colores_devuelve_lista_vacia_para_producto_de_una_foto():
    producto = _producto()
    repositorio = _repositorio(producto)
    repositorio.list_colores.return_value = []

    servicio = GestionarProducto(repositorio)

    # Sin colores declarados, el detalle usa la imagen unica del producto.
    assert servicio.listar_colores(producto.id) == []


def test_listar_colores_delega_en_el_repositorio():
    producto = _producto()
    esperado = [ColorProducto(producto_id=producto.id, nombre="Blanco")]
    repositorio = _repositorio(producto)
    repositorio.list_colores.return_value = esperado

    servicio = GestionarProducto(repositorio)

    assert servicio.listar_colores(producto.id) == esperado
    repositorio.list_colores.assert_called_once_with(producto.id)


def test_guardar_color_rechaza_producto_inexistente():
    servicio = GestionarProducto(_repositorio(None))

    try:
        servicio.guardar_color(uuid4(), "Blanco", _imagen())
    except ValueError as exc:
        assert "no encontrado" in str(exc)
    else:
        raise AssertionError("debio rechazar un producto inexistente")


def test_guardar_color_rechaza_nombre_vacio():
    producto = _producto()
    servicio = GestionarProducto(_repositorio(producto))

    for nombre in ("", "   "):
        try:
            servicio.guardar_color(producto.id, nombre, _imagen())
        except ValueError as exc:
            assert "color" in str(exc).lower()
        else:
            raise AssertionError(f"debio rechazar el nombre {nombre!r}")


def test_guardar_color_normaliza_el_nombre_antes_de_persistir():
    producto = _producto()
    repositorio = _repositorio(producto)
    servicio = GestionarProducto(repositorio)

    servicio.guardar_color(producto.id, "  Blanco  ", _imagen())

    assert repositorio.guardar_color.call_args[0][1] == "Blanco"


def test_guardar_color_devuelve_el_color_creado():
    producto = _producto()
    servicio = GestionarProducto(_repositorio(producto))

    color = servicio.guardar_color(producto.id, "Negro", _imagen())

    assert color.nombre == "Negro"
    assert color.producto_id == producto.id


def test_eliminar_color_delega_en_el_repositorio():
    color_id = uuid4()
    repositorio = _repositorio(_producto())
    servicio = GestionarProducto(repositorio)

    servicio.eliminar_color(color_id)

    repositorio.eliminar_color.assert_called_once_with(color_id)


def test_consultar_imagen_color_devuelve_none_si_no_hay_foto():
    repositorio = _repositorio(_producto())
    repositorio.get_color_imagen_by_id.return_value = None

    servicio = GestionarProducto(repositorio)

    assert servicio.consultar_imagen_color(uuid4()) is None


def test_listar_con_foto_de_color_no_consulta_colores_si_ya_hay_foto():
    producto = Producto(
        nombre="Con foto", categoria_id=uuid4(), precio=100, imagen="/api/productos/x/imagen"
    )
    repositorio = Mock()
    repositorio.list_activos.return_value = [producto]

    GestionarProducto(repositorio).listar_con_foto_de_color()

    # Con la foto principal no hay nada que completar: se evita la consulta.
    repositorio.primera_imagen_color_por_producto.assert_not_called()


def test_listar_con_foto_de_color_completa_con_el_primer_color():
    producto = Producto(nombre="Rana", categoria_id=uuid4(), precio=100, imagen=None)
    color_id = uuid4()
    repositorio = Mock()
    repositorio.list_activos.return_value = [producto]
    repositorio.primera_imagen_color_por_producto.return_value = {
        producto.id: FotoColorCatalogo(
            imagen_url=f"/api/productos/colores/{color_id}/imagen",
            imagen_thumb_url=f"/api/productos/colores/{color_id}/thumb",
        )
    }

    resultado = GestionarProducto(repositorio).listar_con_foto_de_color()

    assert resultado[0].imagen == f"/api/productos/colores/{color_id}/imagen"
    # La tarjeta necesita el thumbnail tambien cuando la foto viene de un color.
    assert resultado[0].imagen_thumb == f"/api/productos/colores/{color_id}/thumb"
    repositorio.primera_imagen_color_por_producto.assert_called_once_with([producto.id])


def test_listar_con_foto_de_color_sin_thumb_cacheado_no_inventa_la_url():
    producto = Producto(nombre="Rana", categoria_id=uuid4(), precio=100, imagen=None)
    color_id = uuid4()
    repositorio = Mock()
    repositorio.list_activos.return_value = [producto]
    repositorio.primera_imagen_color_por_producto.return_value = {
        producto.id: FotoColorCatalogo(
            imagen_url=f"/api/productos/colores/{color_id}/imagen",
            imagen_thumb_url=None,
        )
    }

    resultado = GestionarProducto(repositorio).listar_con_foto_de_color()

    # El thumbnail es perezoso: hasta que se pide no existe, y el frontend cae
    # a la imagen original en vez de pedir una URL que devolveria 404.
    assert resultado[0].imagen_thumb is None


def test_listar_con_foto_de_color_deja_la_imagen_principal_si_la_hay():
    con_foto = Producto(
        nombre="Hyrule", categoria_id=uuid4(), precio=100, imagen="/api/productos/h/imagen"
    )
    sin_foto = Producto(nombre="Rana", categoria_id=uuid4(), precio=100, imagen=None)
    repositorio = Mock()
    repositorio.list_activos.return_value = [con_foto, sin_foto]
    repositorio.primera_imagen_color_por_producto.return_value = {
        sin_foto.id: FotoColorCatalogo(imagen_url="/api/productos/colores/c/imagen")
    }

    resultado = GestionarProducto(repositorio).listar_con_foto_de_color()

    # Solo se consultan los que no tienen foto: la principal gana siempre.
    repositorio.primera_imagen_color_por_producto.assert_called_once_with([sin_foto.id])
    assert resultado[0].imagen == "/api/productos/h/imagen"
    assert resultado[1].imagen == "/api/productos/colores/c/imagen"


def test_listar_con_foto_de_color_no_inventa_imagen_si_no_hay_color():
    producto = Producto(nombre="Sin foto", categoria_id=uuid4(), precio=100, imagen=None)
    repositorio = Mock()
    repositorio.list_activos.return_value = [producto]
    repositorio.primera_imagen_color_por_producto.return_value = {}

    resultado = GestionarProducto(repositorio).listar_con_foto_de_color()

    assert resultado[0].imagen is None
