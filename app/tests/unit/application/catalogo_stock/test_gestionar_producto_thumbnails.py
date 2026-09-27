"""Pruebas del thumbnail perezoso del catálogo.

Fijan las tres reglas que sostienen el diseño:
1. Si el thumbnail ya está cacheado, se devuelve sin volver a generar.
2. Si no existe, se genera desde la original y se guarda.
3. Si no se puede generar, se devuelve `None` para que la ruta sirva la
   imagen original en vez de dejar la tarjeta rota.
"""

from unittest.mock import Mock
from uuid import uuid4

from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.domain.entities.producto import ImagenProducto

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
    # Regenerar en cada request seria el bug completo: 2,4 MB de Pillow por
    # visita al catálogo.
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
    # El generador devuelve None cuando la foto ya cabe o no se puede decodificar.
    servicio, repositorio = _servicio(generador=Mock(return_value=None))

    assert servicio.obtener_thumb(uuid4()) is None
    assert servicio.obtener_thumb_color(uuid4()) is None
    # No se guarda un thumbnail vacio: quedaria cacheado como "ya existe".
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
