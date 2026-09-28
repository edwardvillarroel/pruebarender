"""Tests del mapper publico de productos y de cómo se sirven sus fotos.

`_a_publico_producto` es la frontera que ve el frontend, asi que es el lugar
donde se decide que etiqueta viaja en `badge` y si la fecha de alta sale en el
JSON. Home ordena "Lanzamientos" del mas nuevo al mas viejo, asi que
`creado_en` tiene que estar disponible o la seccion no se puede ordenar.
"""
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

from app.api.routes.catalogo_routes import (
    CACHE_IMAGENES_SEGUNDOS,
    _a_publico_producto,
)
from app.domain.entities.producto import ImagenProducto, Producto


def _producto(**cambios) -> Producto:
    base = dict(
        nombre="Producto de prueba",
        categoria_id=uuid4(),
        precio=1000,
        stock=3,
    )
    base.update(cambios)
    return Producto(**base)


# --- Etiqueta de la tarjeta --------------------------------------------------


def test_un_lanzamiento_viaja_con_la_etiqueta_nuevo():
    publico = _a_publico_producto(_producto(nuevo_lanzamiento=True))

    assert publico["badge"] == "Nuevo"
    assert publico["nuevo_lanzamiento"] is True


def test_un_producto_normal_no_viaja_con_etiqueta():
    publico = _a_publico_producto(_producto())

    assert publico["badge"] is None
    assert publico["nuevo_lanzamiento"] is False


def test_un_badge_manual_no_se_pisa_cuando_no_es_lanzamiento():
    """`badge` es texto libre y ya se usa para etiquetas como "Best Seller".

    Derivar la etiqueta no puede borrar lo que el admin haya puesto a mano.
    """
    publico = _a_publico_producto(_producto(badge="Best Seller"))

    assert publico["badge"] == "Best Seller"


def test_la_etiqueta_nuevo_tiene_prioridad_sobre_el_badge_manual():
    """Con el flag prendido la tarjeta muestra "Nuevo".

    La tarjeta tiene un solo slot de etiqueta (`top: 10, left: 10`) asi que no
    hay lugar para dos. El badge manual sigue intacto en la base: es el flag el
    que manda en la respuesta.
    """
    publico = _a_publico_producto(_producto(badge="Best Seller", nuevo_lanzamiento=True))

    assert publico["badge"] == "Nuevo"


# --- Fecha de alta -----------------------------------------------------------


def test_la_fecha_de_alta_viaja_en_iso():
    """Home ordena por `creado_en`; sin esto la seccion no se puede ordenar."""
    fecha = datetime(2026, 9, 26, 3, 0, 28)

    publico = _a_publico_producto(_producto(creado_en=fecha))

    assert publico["creado_en"] == "2026-09-26T03:00:28"


def test_un_producto_sin_fecha_no_rompe_el_json():
    # `None` y no un str: el frontend compara `creado_en` contra strings.
    publico = _a_publico_producto(_producto(creado_en=None))

    assert publico["creado_en"] is None


def test_el_flag_siempre_viaja_como_booleano():
    """El `bool(...)` evita que la columna `NUMBER(1)` de Oracle llegue como 0/1.

    El `.filter(p => p.nuevo_lanzamiento)` del frontend funciona igual con 0/1,
    pero `aria-checked` y el switch recibirian 0/1 en vez de un booleano, que
    es lo que espera React.
    """
    publico = _a_publico_producto(_producto())

    assert publico["nuevo_lanzamiento"] is False
    assert isinstance(publico["nuevo_lanzamiento"], bool)


# --- Cache de las fotos servidas ---------------------------------------------


def _servicio_con_foto() -> Mock:
    foto = ImagenProducto(bytes=b"x" * 64, content_type="image/jpeg")
    thumb = ImagenProducto(bytes=b"y" * 32, content_type="image/jpeg")
    servicio = Mock()
    servicio.consultar_imagen.return_value = foto
    servicio.obtener_thumb.return_value = thumb
    servicio.consultar_imagen_color.return_value = foto
    servicio.obtener_thumb_color.return_value = thumb
    return servicio


def _assert_cacheable(respuesta) -> None:
    """Siete dias de cache, sin `no-cache` que lo contradiga.

    Se mira el `Cache-Control` ya parseado y no el header crudo: el orden de las
    directivas no es parte del contrato y Werkzeug lo arma segun el orden en que
    se setearon.
    """
    cache = respuesta.cache_control
    assert cache.max_age == CACHE_IMAGENES_SEGUNDOS
    # `no-cache` con `max-age` es una contradiccion: obliga al navegador a
    # revalidar en cada visita, que es justo lo que se vino a evitar.
    assert not cache.no_cache
    # Estas fotos no dependen de quien las pida, asi que un cache compartido
    # (gateway/CDN) las puede guardar.
    assert cache.public


def test_la_imagen_del_producto_se_sirve_cacheada(app, client):
    """Sin esto el navegador vuelve a pedir los MB de la foto en cada carga del
    catalogo, que es justo lo que el thumbnail vino a resolver."""
    app.config["PRODUCTO_SERVICE"] = _servicio_con_foto()

    respuesta = client.get(f"/api/productos/{uuid4()}/imagen")

    assert respuesta.status_code == 200
    assert respuesta.mimetype == "image/jpeg"
    _assert_cacheable(respuesta)


def test_el_thumbnail_del_producto_tambien_se_sirve_cacheado(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_foto()

    respuesta = client.get(f"/api/productos/{uuid4()}/thumb")

    assert respuesta.status_code == 200
    _assert_cacheable(respuesta)


def test_las_fotos_de_color_se_sirven_cacheadas(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_foto()

    color_id = uuid4()
    for ruta in (
        f"/api/productos/colores/{color_id}/imagen",
        f"/api/productos/colores/{color_id}/thumb",
    ):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200
        _assert_cacheable(respuesta)


def test_una_foto_inexistente_sigue_dando_404(app, client):
    servicio = _servicio_con_foto()
    servicio.consultar_imagen.return_value = None
    app.config["PRODUCTO_SERVICE"] = servicio

    respuesta = client.get(f"/api/productos/{uuid4()}/imagen")

    assert respuesta.status_code == 404
    assert respuesta.get_json()["mensaje"] == "Imagen no encontrada"


def test_la_cache_de_imagenes_dura_una_semana():
    # Si alguien cambia el valor, el peso de cada visita al catalogo cambia con
    # el: que el cambio sea una decisión consciente y no un número que se movió.
    assert CACHE_IMAGENES_SEGUNDOS == 604800
