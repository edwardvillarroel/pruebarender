"""Tests del mapper publico de productos.

`_a_publico_producto` es la frontera que ve el frontend, asi que es el lugar
donde se decide que etiqueta viaja en `badge` y si la fecha de alta sale en el
JSON. Home ordena "Lanzamientos" del mas nuevo al mas viejo, asi que
`creado_en` tiene que estar disponible o la seccion no se puede ordenar.
"""
from datetime import datetime
from uuid import uuid4

from app.api.routes.catalogo_routes import _a_publico_producto
from app.domain.entities.producto import Producto


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
