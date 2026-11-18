

from unittest.mock import Mock
from uuid import uuid4

from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.domain.entities.producto import ColorProducto, ImagenProducto, Producto

ORIGINAL = ImagenProducto(bytes=b"f" * 5000, content_type="image/jpeg")
THUMB = (b"t" * 300, "image/jpeg")


def _servicio(generador=Mock(return_value=THUMB)) -> tuple[GestionarProducto, Mock]:
    repositorio = Mock()
    repositorio.get_thumb_by_id.return_value = None
    repositorio.get_color_thumb_by_id.return_value = None
    repositorio.get_imagen_by_id.return_value = ORIGINAL
    repositorio.get_color_imagen_by_id.return_value = ORIGINAL
    return GestionarProducto(repositorio, generador_thumb=generador), repositorio


def test_genera_el_thumbnail_desde_la_original_y_lo_guarda():
    servicio, repositorio = _servicio()

    resultado = servicio.obtener_thumb(uuid4())

    assert resultado is not None
    assert resultado.bytes == THUMB[0]
    assert resultado.content_type == "image/jpeg"
    repositorio.guardar_thumb.assert_called_once()
    guardado = repositorio.guardar_thumb.call_args[0][1]
    assert guardado.bytes == THUMB[0]


def test_si_el_thumbnail_ya_esta_cacheado_no_regenera_ni_guarda():
    cacheado = ImagenProducto(bytes=b"cacheado", content_type="image/jpeg")
    generador = Mock(return_value=THUMB)
    repositorio = Mock()
    repositorio.get_thumb_by_id.return_value = cacheado

    servicio = GestionarProducto(repositorio, generador_thumb=generador)
    resultado = servicio.obtener_thumb(uuid4())

    assert resultado is cacheado
    generador.assert_not_called()
    repositorio.guardar_thumb.assert_not_called()
    repositorio.get_imagen_by_id.assert_not_called()


def test_sin_generador_devuelve_none_para_caer_a_la_original():
    repositorio = Mock()
    repositorio.get_thumb_by_id.return_value = None
    repositorio.get_color_thumb_by_id.return_value = None
    servicio = GestionarProducto(repositorio)

    assert servicio.obtener_thumb(uuid4()) is None
    assert servicio.obtener_thumb_color(uuid4()) is None
    repositorio.guardar_thumb.assert_not_called()


def test_producto_sin_foto_no_intenta_generar_nada():
    generador = Mock(return_value=THUMB)
    repositorio = Mock()
    repositorio.get_thumb_by_id.return_value = None
    repositorio.get_color_thumb_by_id.return_value = None
    repositorio.get_imagen_by_id.return_value = None
    repositorio.get_color_imagen_by_id.return_value = None
    servicio = GestionarProducto(repositorio, generador_thumb=generador)

    assert servicio.obtener_thumb(uuid4()) is None
    assert servicio.obtener_thumb_color(uuid4()) is None
    generador.assert_not_called()


def test_foto_demasiado_chica_o_ilegible_no_rompe_la_tarjeta():
    servicio, repositorio = _servicio(generador=Mock(return_value=None))

    assert servicio.obtener_thumb(uuid4()) is None
    assert servicio.obtener_thumb_color(uuid4()) is None
    repositorio.guardar_thumb.assert_not_called()
    repositorio.guardar_color_thumb.assert_not_called()


def test_thumb_de_color_genera_y_guarda():
    servicio, repositorio = _servicio()
    color_id = uuid4()

    resultado = servicio.obtener_thumb_color(color_id)

    assert resultado is not None
    assert resultado.bytes == THUMB[0]
    repositorio.guardar_color_thumb.assert_called_once()


def test_thumb_de_color_ya_cacheado_no_regenera():
    cacheado = ImagenProducto(bytes=b"cacheado", content_type="image/jpeg")
    generador = Mock(return_value=THUMB)
    repositorio = Mock()
    repositorio.get_color_thumb_by_id.return_value = cacheado
    servicio = GestionarProducto(repositorio, generador_thumb=generador)

    assert servicio.obtener_thumb_color(uuid4()) is cacheado
    generador.assert_not_called()




def _repositorio_para_guardar(color=None) -> Mock:
    repositorio = Mock()
    repositorio.get_by_id.return_value = Producto(
        nombre="Rana", categoria_id=uuid4(), precio=1000, stock=1
    )
    repositorio.guardar_color.return_value = color or ColorProducto(
        id=uuid4(), producto_id=uuid4(), nombre="Blanco", orden=0
    )
    return repositorio


def test_guardar_imagen_genera_y_persiste_el_thumbnail():
    generador = Mock(return_value=THUMB)
    repositorio = _repositorio_para_guardar()
    servicio = GestionarProducto(repositorio, generador_thumb=generador)
    producto_id = uuid4()

    servicio.guardar_imagen(producto_id, ORIGINAL)

    generador.assert_called_once_with(ORIGINAL.bytes, ORIGINAL.content_type)
    repositorio.guardar_thumb.assert_called_once()
    guardado = repositorio.guardar_thumb.call_args[0][1]
    assert (guardado.bytes, guardado.content_type) == THUMB


def test_el_thumbnail_se_guarda_para_el_producto_que_se_actualizo():
    repositorio = _repositorio_para_guardar()
    servicio = GestionarProducto(repositorio, generador_thumb=Mock(return_value=THUMB))
    producto_id = uuid4()

    servicio.guardar_imagen(producto_id, ORIGINAL)

    assert repositorio.guardar_thumb.call_args[0][0] == producto_id


def test_guardar_imagen_sin_generador_no_rompe():
    repositorio = _repositorio_para_guardar()
    servicio = GestionarProducto(repositorio)

    servicio.guardar_imagen(uuid4(), ORIGINAL)

    repositorio.guardar_imagen.assert_called_once()
    repositorio.guardar_thumb.assert_not_called()


def test_guardar_imagen_con_generador_que_devuelve_none_no_guarda_thumb():
    repositorio = _repositorio_para_guardar()
    servicio = GestionarProducto(
        repositorio, generador_thumb=Mock(return_value=None)
    )

    servicio.guardar_imagen(uuid4(), ORIGINAL)

    repositorio.guardar_thumb.assert_not_called()


def test_guardar_color_genera_y_persiste_el_thumbnail():
    color = ColorProducto(id=uuid4(), producto_id=uuid4(), nombre="Negro", orden=0)
    repositorio = _repositorio_para_guardar(color)
    generador = Mock(return_value=THUMB)
    servicio = GestionarProducto(repositorio, generador_thumb=generador)

    servicio.guardar_color(uuid4(), "Negro", ORIGINAL)

    generador.assert_called_once_with(ORIGINAL.bytes, ORIGINAL.content_type)
    repositorio.guardar_color_thumb.assert_called_once()
    assert repositorio.guardar_color_thumb.call_args[0][0] == color.id


def test_guardar_color_sin_generador_no_rompe():
    repositorio = _repositorio_para_guardar()
    servicio = GestionarProducto(repositorio)

    servicio.guardar_color(uuid4(), "Negro", ORIGINAL)

    repositorio.guardar_color.assert_called_once()
    assert repositorio.guardar_color.call_args[0][1] == "Negro"
    repositorio.guardar_color_thumb.assert_not_called()

