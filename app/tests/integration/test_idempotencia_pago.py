




from __future__ import annotations

import uuid

import pytest

from app.domain.entities.pago import Pago
from app.domain.interfaces.repositories import ClaveIdempotenciaOcupada
from app.infrastructure.database.connection import db
from app.infrastructure.repositories.pago_repository import PagoRepository

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




def test_total_esperado_que_coincide_sigue_el_flujo_normal(
    client, producto, usuario, centinela
):
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
    esperado = f"${TOTAL_REAL + 5000:,}".replace(",", ".")
    real = f"${TOTAL_REAL:,}".replace(",", ".")
    assert esperado in mensaje, mensaje
    assert real in mensaje, mensaje
    assert _conteo_pedidos(usuario) == 0, "un total distinto no puede dejar pedido"
    assert _conteo_pagos(usuario) == 0, "un total distinto no puede dejar pago"


def test_sin_total_esperado_funciona_exactamente_igual_que_antes(
    client, producto, usuario, centinela
):

    respuesta = client.post(
        "/api/pago/crear",
        json=_body(producto(stock=10, nombre=f"{centinela}-compat").id),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert _conteo_pedidos(usuario) == 1


@pytest.mark.parametrize(
    "basura",
    [None, "", "abc", {}, [], True, False, -1, 0, 1.5, f"  {TOTAL_REAL}  ", "13.078"],
)
def test_total_esperado_basura_se_trata_como_ausente(
    client, producto, usuario, centinela, basura
):

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




def test_doble_click_devuelve_el_mismo_url_y_no_crea_otro_pedido(
    client, producto, usuario, centinela
):
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
    assert del_intruso.status_code == 409, del_intruso.get_json()
    assert del_dueno.get_json()["url"] not in str(del_intruso.get_json()), (
        "la respuesta al intruso filtra el destino del pago de otra persona"
    )
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

    respuesta = client.post(
        "/api/pago/crear",
        json=_body(producto(stock=10, nombre=f"{centinela}-clave").id,
                   claveIdempotencia=clave),
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert _conteo_pedidos(usuario) == 1


def test_la_carrera_de_doble_click_deja_una_sola_fila(app, producto, usuario, centinela):

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

    assert repo.get_by_clave_idempotencia(clave) is not None
    assert db.session.execute(
        db.text("SELECT count(*) FROM pagos WHERE clave_idempotencia = :c"),
        {"c": clave},
    ).scalar_one() == 1


def _crear_pedido_minimo(prod, usuario) -> uuid.UUID:
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