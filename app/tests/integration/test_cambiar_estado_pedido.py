"""El endpoint de cambiar estado: el contrato HTTP que el admin necesita.

El caso de uso ya tiene sus tests de transiciones.Estos fijan lo que el resto
del sistema ve: el codigo de estado HTTP y la forma de la respuesta.

El codigo importa porque el frontend decide que mostrar segun el status y no
puede parsear el mensaje:

- 400: no entendi el estado ("finalizado" no es un estado de este sistema).
- 404: el pedido no existe.
- 409: entendi el estado, pero no se puede (cancelado -> entregado). 409 y no
  400 porque el pedido es real y el estado es valido: lo que no se puede es la
  operacion, y un 400 manda a corregir el request cuando el request esta bien.

Y el otro punto: registrar el codigo de Starken avanza el pedido a `enviado`.
Si no, el admin carga el codigo y el pedido se queda en `pendiente` hasta que
ademas vaya a cambiarlo a mano, y el panel muestra un pedido con despacho real
como si siguiera sin salir.
"""

from __future__ import annotations

import pytest

from app.infrastructure.database.connection import db
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.usuario_model import UsuarioModel


@pytest.fixture
def admin(db_sesion, centinela):
    """Admin real, con email propio: `centinela` es function-scoped y la
    comparte con el fixture `usuario`, asi que reusarla rompe `uq_usuarios_email`.
    """
    u = UsuarioModel(
        email=f"{centinela}-admin@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="R0 Caracterizacion",
        apellido="Admin",
        rol="admin",
    )
    db_sesion.add(u)
    db_sesion.commit()
    return u


def _cabeceras(admin) -> dict:
    return {"X-User-Id": str(admin.id), "X-User-Rol": "admin"}


def _pedido(usuario, estado: str) -> PedidoModel:
    p = PedidoModel(
        usuario_id=usuario.id,
        total=1000,
        entrega="retiro",
        estado=estado,
    )
    db.session.add(p)
    db.session.commit()
    return p


def _estado_en_la_base(pedido_id) -> str:
    """Estado leido con SQL crudo: la sesion de SQLAlchemy puede tener cacheado
    el valor viejo y el test pasaria sin comprobar nada."""
    return db.session.execute(
        db.text("SELECT estado FROM pedidos WHERE id = :i"), {"i": pedido_id}
    ).scalar_one()


def test_admin_marca_entregado_y_queda_persistido(client, usuario, admin):
    p = _pedido(usuario, "pendiente")

    respuesta = client.patch(
        f"/api/pedidos/{p.id}/estado",
        json={"estado": "entregado"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert respuesta.get_json()["estado"] == "entregado"
    assert _estado_en_la_base(p.id) == "entregado", (
        "la respuesta dijo entregado pero el pedido no cambio en la base"
    )


def test_transicion_no_permitida_es_409_y_no_cambia_nada(client, usuario, admin):
    """Cancelado no se entrega, y el rechazo no toca el pedido."""
    p = _pedido(usuario, "cancelado")

    respuesta = client.patch(
        f"/api/pedidos/{p.id}/estado",
        json={"estado": "entregado"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 409, respuesta.get_json()
    assert respuesta.get_json()["mensaje"], "el frontend muestra err.mensaje"
    assert _estado_en_la_base(p.id) == "cancelado"


def test_estado_desconocido_es_400(client, usuario, admin):
    """"Finalizado" es la etiqueta del boton, no un estado de la base."""
    p = _pedido(usuario, "pendiente")

    respuesta = client.patch(
        f"/api/pedidos/{p.id}/estado",
        json={"estado": "finalizado"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 400, respuesta.get_json()
    assert "entregado" in respuesta.get_json()["mensaje"], (
        "el 400 tiene que enumerar los estados validos: el admin esta adivinando"
    )
    assert _estado_en_la_base(p.id) == "pendiente"


def test_body_sin_estado_es_400(client, usuario, admin):
    p = _pedido(usuario, "pendiente")

    respuesta = client.patch(
        f"/api/pedidos/{p.id}/estado", json={}, headers=_cabeceras(admin)
    )

    assert respuesta.status_code == 400, respuesta.get_json()


def test_pedido_inexistente_es_404(client, usuario, admin):
    import uuid

    respuesta = client.patch(
        f"/api/pedidos/{uuid.uuid4()}/estado",
        json={"estado": "entregado"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 404, respuesta.get_json()


def test_cliente_no_puede_cambiar_el_estado(client, usuario, centinela):
    """El endpoint es del admin: un cliente no mueve su propio pedido."""
    p = _pedido(usuario, "pendiente")

    respuesta = client.patch(
        f"/api/pedidos/{p.id}/estado",
        json={"estado": "entregado"},
        headers={"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"},
    )

    assert respuesta.status_code == 403, respuesta.get_json()
    assert _estado_en_la_base(p.id) == "pendiente"


def test_sin_sesion_es_401(client, usuario):
    p = _pedido(usuario, "pendiente")

    respuesta = client.patch(
        f"/api/pedidos/{p.id}/estado", json={"estado": "entregado"}
    )

    assert respuesta.status_code == 401, respuesta.get_json()


def test_registrar_codigo_starken_avanza_a_enviado(client, usuario, admin):
    """Cargar la OF es despachar: el pedido pasa a `enviado` en la misma operacion."""
    p = _pedido(usuario, "pendiente")

    respuesta = client.post(
        f"/api/pedidos/{p.id}/seguimiento",
        json={"codigo": "OF123456789"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert respuesta.get_json()["estado"] == "enviado"
    assert _estado_en_la_base(p.id) == "enviado", (
        "se guardo el codigo pero el pedido quedo en pendiente: el panel miente"
    )


def test_registrar_codigo_con_transportista_se_persiste_y_se_devuelve(
    client, usuario, admin
):
    """El transportista elegido en el panel viaja al pedido y vuelve en la lista."""
    p = _pedido(usuario, "pendiente")

    respuesta = client.post(
        f"/api/pedidos/{p.id}/seguimiento",
        json={"codigo": "OF98765", "transportista": "bluexpress"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert respuesta.get_json()["transportista"] == "bluexpress", (
        "el serializador no devuelve el transportista que se acaba de guardar"
    )
    en_la_base = db.session.execute(
        db.text("SELECT transportista FROM pedidos WHERE id = :i"), {"i": p.id}
    ).scalar_one()
    assert en_la_base == "bluexpress", (
        "la respuesta dijo bluexpress pero la base guardo otra cosa"
    )


def test_registrar_codigo_sin_transportista_no_borra_el_guardado(
    client, usuario, admin
):
    """Sincronizar o re-registrar sin transportista no lo pisa con NULL."""
    p = _pedido(usuario, "pendiente")
    client.post(
        f"/api/pedidos/{p.id}/seguimiento",
        json={"codigo": "OF11111", "transportista": "starken"},
        headers=_cabeceras(admin),
    )

    respuesta = client.post(
        f"/api/pedidos/{p.id}/seguimiento",
        json={"codigo": "OF22222"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert respuesta.get_json()["transportista"] == "starken", (
        "un re-registro sin transportista borro el transportista previo"
    )


@pytest.mark.parametrize("estado", ["entregado", "cancelado"])
def test_registrar_codigo_no_reabre_un_pedido_cerrado(client, usuario, admin, estado):
    """Corregir el codigo de un pedido ya cerrado no lo revierte.

    Es el caso donde el admin se equivoca de pedido: si cargar la OF abriera de
    nuevo un pedido entregado o cancelado, un typo le desfinaliza la compra a un
    cliente que ya la recibio.
    """
    p = _pedido(usuario, estado)

    respuesta = client.post(
        f"/api/pedidos/{p.id}/seguimiento",
        json={"codigo": "OF999"},
        headers=_cabeceras(admin),
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert _estado_en_la_base(p.id) == estado, (
        f"registrar el codigo movio un pedido {estado} a "
        f"{_estado_en_la_base(p.id)}"
    )


def test_registrar_codigo_no_revierte_un_enviado(client, usuario, admin):
    """Un pedido ya `enviado` sigue `enviado`: la operacion es idempotente."""
    p = _pedido(usuario, "enviado")

    client.post(
        f"/api/pedidos/{p.id}/seguimiento",
        json={"codigo": "OF111"},
        headers=_cabeceras(admin),
    )

    assert _estado_en_la_base(p.id) == "enviado"