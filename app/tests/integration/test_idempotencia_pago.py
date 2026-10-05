"""WU6: el cliente paga el total que vio, y un doble click no duplica el pedido.

`POST /api/pago/crear` hace DOS cosas distintas antes de que el cliente pague:

1. **Confia en un total.** El frontend ya manda `totalEsperado`, el total que
   mostro en pantalla. El backend lo recalcula siempre desde la base y nunca lo
   contrastaba: si el precio de un producto cambia entre que el cliente arma el
   carrito y que aprieta "Pagar", se cobraba una cifra que nadie vio. Ahora se
   contrasta y, si no coincide, se aborta ANTES de crear el pedido.

2. **Crea el pedido antes de cobrar.** El pedido existe aunque el cliente nunca
   pague. Un doble click (o un reintento del navegador, o el boton aplastado dos
   veces) manda el POST dos veces y quedan dos pedidos, dos pagos y dos intentos
   en la pasarela. `claveIdempotencia` hace que la segunda peticion no cree nada
   y devuelva el mismo destino que la primera.

El caso caro es la **carrera**: dos peticiones con la misma clave que se cruzan
y no se ven entre si, las dos llegan al INSERT y el indice unico revienta la
segunda. Si eso no se maneja termina en un 500 y el cliente pierde el pago, asi
que el test del final la fuerza en el repositorio.
"""

from __future__ import annotations

import uuid

import pytest

from app.domain.entities.pago import Pago
from app.domain.interfaces.repositories import ClaveIdempotenciaOcupada
from app.infrastructure.database.connection import db
from app.infrastructure.repositories.pago_repository import PagoRepository

# precio 5000 + envio 5990 (subtotal < 50000) = 10990. El precio YA viene con
# IVA desde la base, asi que no se multiplica por 1.19: ver `test_calculos.py`.
TOTAL_REAL = 10990


def _cabeceras(usuario) -> dict:
    return {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}


def _body(producto_id, **extra) -> dict:
    base = {
        "entrega": "envio",
        "cliente": {
            "nombre": "Ana",
            "apellido": "Prueba",
            "email": "ana@caracterizacion.test",
        },
        "items": [{"id": str(producto_id), "cantidad": 1}],
    }
    base.update(extra)
    return base


def _conteo_pedidos(usuario) -> int:
    return db.session.execute(
        db.text("SELECT count(*) FROM pedidos WHERE usuario_id = :uid"),
        {"uid": usuario.id},
    ).scalar_one()


def _conteo_pagos(usuario) -> int:
    return db.session.execute(
        db.text(
            "SELECT count(*) FROM pagos p "
            "JOIN pedidos pe ON pe.id = p.pedido_id "
            "WHERE pe.usuario_id = :uid"
        ),
        {"uid": usuario.id},
    ).scalar_one()


# --------------------------------------------------------------------------
# WU6a: totalEsperado
# --------------------------------------------------------------------------


def test_total_esperado_que_coincide_sigue_el_flujo_normal(
    client, producto, usuario, centinela
):
    """El caminofeliz: el cliente vio el total correcto y el pago arranca."""
    respuesta = client.post(
        "/api/pago/crear",
        json=_body(
            producto(stock=10, nombre=f"{centinela}-ok").id, totalEsperado=TOTAL_REAL
        ),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert respuesta.get_json()["url"]
    assert _conteo_pedidos(usuario) == 1
    assert _conteo_pagos(usuario) == 1


def test_total_esperado_distinto_da_409_y_no_deja_pedido_ni_pago(
    client, producto, usuario, centinela
):
    """El precio cambio entre el carrito y el pago: se aborta limpio.

    Lo importante es el final: ni pedido ni pago. Si quedara el pedido, el
    cliente tendria una orden por un precio que nunca acepto, y el admin la
    veria en el panel.
    """
    respuesta = client.post(
        "/api/pago/crear",
        json=_body(
            producto(stock=10, nombre=f"{centinela}-cambio").id,
            totalEsperado=TOTAL_REAL + 5000,
        ),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 409, respuesta.get_json()
    mensaje = respuesta.get_json()["mensaje"]
    # Los dos importes van con separador de miles chileno. Se derivan de
    # TOTAL_REAL y no se escriben a mano, para que este test no se pudra cuando
    # cambie el precio de la fixture.
    esperado = f"${TOTAL_REAL + 5000:,}".replace(",", ".")
    real = f"${TOTAL_REAL:,}".replace(",", ".")
    assert esperado in mensaje, mensaje
    assert real in mensaje, mensaje
    assert _conteo_pedidos(usuario) == 0, "un total distinto no puede dejar pedido"
    assert _conteo_pagos(usuario) == 0, "un total distinto no puede dejar pago"


def test_sin_total_esperado_funciona_exactamente_igual_que_antes(
    client, producto, usuario, centinela
):
    """Compatibilidad: un cliente que no manda el campo sigue pagando bien.

    `totalEsperado` es opcional a proposito. Validarlo sin default romperia a
    cualquier cliente viejo y a las pruebas que arman el body a mano.
    """
    respuesta = client.post(
        "/api/pago/crear",
        json=_body(producto(stock=10, nombre=f"{centinela}-compat").id),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert _conteo_pedidos(usuario) == 1


@pytest.mark.parametrize(
    "basura",
    # f-string para que el caso con espacios siga siendo el total REAL: un
    # entero parseable pero distinto del real es un 409, no un dato basura.
    [None, "", "abc", {}, [], True, False, -1, 0, 1.5, f"  {TOTAL_REAL}  ", "13.078"],
)
def test_total_esperado_basura_se_trata_como_ausente(
    client, producto, usuario, centinela, basura
):
    """Un dato que no es un total usable se ignora, no rompe la ruta.

    Ojo con `"13.078"`: es un total escrito con separador de miles.
    `int()` no lo parsea, asi que se descarta y el pago sigue sin validar. Es
    el precio de no adivinar formatos: el frontend manda el numero plano.
    """
    respuesta = client.post(
        "/api/pago/crear",
        json=_body(
            producto(stock=10, nombre=f"{centinela}-basura").id, totalEsperado=basura
        ),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert _conteo_pedidos(usuario) == 1


def test_un_total_esperado_absurdamente_grande_es_un_mismatch_real(
    client, producto, usuario, centinela
):
    """Un numero enorme SI es un total, solo que no es el de este pedido.

    No va en la lista de basura: es un entero valido, asi que la comparacion
    aplica y el 409 es la respuesta correcta. Se separa del resto para dejar
    escrito que "raro" y "distinto" no son lo mismo.
    """
    respuesta = client.post(
        "/api/pago/crear",
        json=_body(
            producto(stock=10, nombre=f"{centinela}-enorme").id,
            totalEsperado=999999999999999999999999,
        ),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 409, respuesta.get_json()
    assert _conteo_pedidos(usuario) == 0


# --------------------------------------------------------------------------
# WU6b: claveIdempotencia
# --------------------------------------------------------------------------


def test_doble_click_devuelve_el_mismo_url_y_no_crea_otro_pedido(
    client, producto, usuario, centinela
):
    """La segunda peticion con la misma clave es un reintento, no una compra."""
    clave = f"clave-{centinela}"
    cuerpo = _body(producto(stock=10, nombre=f"{centinela}-doble").id)

    primera = client.post(
        "/api/pago/crear", json={**cuerpo, "claveIdempotencia": clave},
        headers=_cabeceras(usuario),
    )
    segunda = client.post(
        "/api/pago/crear", json={**cuerpo, "claveIdempotencia": clave},
        headers=_cabeceras(usuario),
    )

    assert primera.status_code == 200, primera.get_json()
    assert segunda.status_code == 200, segunda.get_json()
    assert segunda.get_json() == primera.get_json(), (
        "el reintento tiene que devolver exactamente el mismo destino, no uno nuevo"
    )
    assert _conteo_pedidos(usuario) == 1, "el doble click creo dos pedidos"
    assert _conteo_pagos(usuario) == 1, "el doble click creo dos pagos"


def test_misma_clave_con_items_distintos_no_crea_nada_nuevo(
    client, producto, usuario, centinela, categoria
):
    """La clave manda sobre el contenido: el reintento no rehace el pedido.

    Si el cliente cambio el carrito entre la peticion y el reintento, la clave
    sigue apuntando al pago original. Es lo correcto: cobrar lo que ya se
    mandio a la pasarela es lo unico coherente.
    """
    clave = f"clave-{centinela}"
    primero = producto(stock=10, nombre=f"{centinela}-a")
    segundo = producto(stock=10, nombre=f"{centinela}-b")

    original = client.post(
        "/api/pago/crear",
        json=_body(primero.id, claveIdempotencia=clave),
        headers=_cabeceras(usuario),
    )
    reintento = client.post(
        "/api/pago/crear",
        json=_body(segundo.id, claveIdempotencia=clave),
        headers=_cabeceras(usuario),
    )

    assert original.status_code == 200, original.get_json()
    assert reintento.status_code == 200, reintento.get_json()
    assert reintento.get_json()["token"] == original.get_json()["token"]
    assert _conteo_pedidos(usuario) == 1


def test_la_clave_de_otro_usuario_no_le_devuelve_su_url(
    client, producto, usuario, centinela, db_sesion
):
    """La clave identifica el pago, no concede acceso a el.

    Sin la guarda de propiedad, un cliente que mandara la clave de otro
    obtendria la URL de pago de esa persona y podria pagarla en su nombre. Con
    la guarda, el chequeo previo dice que la clave no es suya y el flujo sigue
    hasta el INSERT, donde el indice unico global la rechaza.

    Y aqui esta una restriccion de diseño que conviene tener escrita: el indice
    es UNICO GLOBAL, no por usuario. Por lo tanto dos personas no pueden
    reutilizar la misma clave, ni por accidente. Es aceptable porque la clave la
    genera el cliente y en la practica es un UUID, pero significa que la
    "propiedad" de la clave no se puede relajar a nivel base: o el indice pasa
    a ser `(usuario_id, clave_idempotencia)`, o el conflicto entre usuarios se
    resuelve con un 409. Aqui se eligio el 409.
    """
    from app.infrastructure.database.models.usuario_model import UsuarioModel

    intruso = UsuarioModel(
        email=f"{centinela}-intruso@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="Intruso",
        apellido="Prueba",
    )
    db_sesion.add(intruso)
    db_sesion.commit()

    clave = f"clave-{centinela}"
    cuerpo = _body(producto(stock=10, nombre=f"{centinela}-ajena").id)

    del_dueno = client.post(
        "/api/pago/crear", json={**cuerpo, "claveIdempotencia": clave},
        headers=_cabeceras(usuario),
    )
    del_intruso = client.post(
        "/api/pago/crear", json={**cuerpo, "claveIdempotencia": clave},
        headers=_cabeceras(intruso),
    )

    assert del_dueno.status_code == 200, del_dueno.get_json()
    # 409, nunca 500 y nunca el url del dueno.
    assert del_intruso.status_code == 409, del_intruso.get_json()
    assert del_dueno.get_json()["url"] not in str(del_intruso.get_json()), (
        "la respuesta al intruso filtra el destino del pago de otra persona"
    )
    # El pedido del intruso se descarto: no pago, no huerfano.
    assert _conteo_pedidos(intruso) == 0
    assert _conteo_pedidos(usuario) == 1, "el pago del dueno no se toco"


@pytest.mark.parametrize(
    "clave",
    [
        "clave con espacios",
        "clave; DROP TABLE pagos;--",
        "clave/../otra",
        "a" * 101,
        12345,
        None,
        {"a": 1},
    ],
)
def test_clave_invalida_se_trata_como_ausente(
    client, producto, usuario, centinela, clave
):
    """La clave viene del cliente: se filtra, y si no pasa no hay idempotencia.

    Lo que no puede pasar es un 500 ni una inyeccion. El pago tiene que
    funcionar igual que si la clave no existiera.
    """
    respuesta = client.post(
        "/api/pago/crear",
        json=_body(producto(stock=10, nombre=f"{centinela}-clave").id,
                   claveIdempotencia=clave),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert _conteo_pedidos(usuario) == 1


def test_la_carrera_de_doble_click_deja_una_sola_fila(app, producto, usuario, centinela):
    """Dos INSERT con la misma clave en vuelo simultaneo: gana uno.

    Esta es la carrera que no se puede cerrar con el chequeo previo, porque las
    dos peticiones no se llegan a ver. La resuelve el indice unico, y lo
    importante es que el repositorio la traduzca a una excepcion de dominio y
    **revierta la sesion**: sin rollback, todo query posterior revienta con
    "current transaction is aborted" y el 409 se convierte en un 500.
    """
    clave = f"clave-carrera-{centinela}"
    repo = PagoRepository()
    pedido_id = _crear_pedido_minimo(producto(stock=10, nombre=f"{centinela}-carrera"), usuario)

    primero = Pago(
        pedido_id=pedido_id, monto=TOTAL_REAL, proveedor="tuu", clave_idempotencia=clave
    )
    repo.add(primero)

    segundo = Pago(
        pedido_id=pedido_id, monto=TOTAL_REAL, proveedor="tuu", clave_idempotencia=clave
    )
    with pytest.raises(ClaveIdempotenciaOcupada):
        repo.add(segundo)

    # La sesion quedo utilizable: si no, el siguiente query explota.
    assert repo.get_by_clave_idempotencia(clave) is not None
    assert db.session.execute(
        db.text("SELECT count(*) FROM pagos WHERE clave_idempotencia = :c"),
        {"c": clave},
    ).scalar_one() == 1


def _crear_pedido_minimo(prod, usuario) -> uuid.UUID:
    """Pedido minimo para poder colgarle pagos en un test del repositorio."""
    from app.infrastructure.database.models.detalle_pedido_model import (
        DetallePedidoModel,
    )
    from app.infrastructure.database.models.pedido_model import PedidoModel

    pedido = PedidoModel(usuario_id=usuario.id, total=TOTAL_REAL, entrega="envio")
    pedido.detalles.append(
        DetallePedidoModel(producto_id=prod.id, cantidad=1, precio_unitario=5000)
    )
    db.session.add(pedido)
    db.session.commit()
    return pedido.id