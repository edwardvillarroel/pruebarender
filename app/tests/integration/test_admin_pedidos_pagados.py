"""El panel de admin muestra compras, no carritos abandonados.

El pedido se crea ANTES de que el cliente pague (`ProcesarPago.iniciar`), asi que
en la base hay pedidos que jamas se pagaron: el carrito se abandona, la pasarela
devuelve `failed`, o el cliente cierra la pestana. `GET /api/pedidos/admin`
traia todo eso y el admin tenia que filtrar a ojo cuales son compras reales,
separando compras de basura.

La regla ahora es una sola: al panel va lo que tiene pago `completado`. Por eso
el filtro va en el repositorio y no en el frontend, que es el que hay que
cambiar cada vez que aparece una pantalla nueva.

Un detalle que estos tests congelan a proposito: el filtro se hace con `EXISTS`
y no con `JOIN`, para que la cantidad de filas sea siempre la cantidad de
pedidos. `test_no_duplica_pedidos_con_varios_pagos` verifica que un pedido con
dos pagos (el reintento tipico de pasarela) aparezca una sola vez. Ojo con la
atribucion: hoy un `JOIN` tampoco lo duplicaria, porque el ORM deduplica la
entidad primaria por clave, pero es una garantia implicita del ORM y no del SQL.
Si alguien cambia el `EXISTS` por un `JOIN` y ademas empieza a seleccionar
columnas de `pagos` o a hacer eager-load de esa relacion, la deduplicacion
desaparece y el bug vuelve sin que nada lo haya avisado.
"""

from __future__ import annotations

import pytest

from app.infrastructure.database.connection import db
from app.infrastructure.database.models.pago_model import PagoModel
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.usuario_model import UsuarioModel


@pytest.fixture
def admin(db_sesion, centinela):
    """Usuario admin real.

    El rol lo lee el header `X-User-Rol` (el gateway es la frontera de
    confianza), pero el usuario existe de verdad para que el listado sea una
    lectura de la base y no un test de mocks.

    El `admin` va aparte del `usuario` y no reusa su centinela: `centinela` es
    function-scoped, asi que los dos fixtures comparten valor y con el mismo
    email el segundo insert viola `uq_usuarios_email`.
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


def _cabeceras_admin(admin) -> dict:
    return {"X-User-Id": str(admin.id), "X-User-Rol": "admin"}


def _pedido(usuario, centinela: str, sufijo: str) -> PedidoModel:
    """Pedido minimo persistido. El estado del pago se agrega aparte."""
    p = PedidoModel(
        usuario_id=usuario.id,
        total=1000,
        entrega="retiro",
        estado="pendiente",
    )
    db.session.add(p)
    db.session.commit()
    return p


def _pago(pedido: PedidoModel, estado: str) -> PagoModel:
    pago = PagoModel(
        pedido_id=pedido.id,
        monto=pedido.total,
        proveedor="tuu",
        estado=estado,
    )
    db.session.add(pago)
    db.session.commit()
    return pago


def _ids_del_panel(client, cabeceras) -> set[str]:
    """Ids que devuelve el panel. Set a proposito: el orden no es el contrato."""
    respuesta = client.get("/api/pedidos/admin", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.get_json()
    return {p["id"] for p in respuesta.get_json()["pedidos"]}


def test_panel_muestra_pedidos_con_pago_completado(client, usuario, centinela, admin):
    """El caso normal: una compra pagada aparece en el panel."""
    p = _pedido(usuario, centinela, "pagado")
    _pago(p, "completado")
    pid = str(p.id)

    assert pid in _ids_del_panel(client, _cabeceras_admin(admin))


def test_panel_excluye_pedido_sin_pago(client, usuario, centinela, admin):
    """Carrito abandonado: hay pedido en la base pero no hay pago."""
    p = _pedido(usuario, centinela, "abandonado")

    assert str(p.id) not in _ids_del_panel(client, _cabeceras_admin(admin))


def test_panel_excluye_pago_pendiente_y_fallido(client, usuario, centinela, admin):
    """El pedido existe y tiene pago, pero no se completo: no es una compra."""
    pendiente = _pedido(usuario, centinela, "pendiente")
    _pago(pendiente, "pendiente")
    fallido = _pedido(usuario, centinela, "fallido")
    _pago(fallido, "fallido")

    panel = _ids_del_panel(client, _cabeceras_admin(admin))
    assert str(pendiente.id) not in panel, "un pago sin completar no es una compra"
    assert str(fallido.id) not in panel, "un pago fallido no es una compra"


def test_no_duplica_pedidos_con_varios_pagos(client, usuario, centinela, admin):
    """Varias filas en `pagos` para el mismo pedido no repiten el pedido.

    Es lo que pasa cuando la pasarela se reintenta: queda el pago `fallido` del
    primer intento y el `completado` del segundo. El panel tiene que mostrar el
    pedido una vez, porque es una sola compra.
    """
    p = _pedido(usuario, centinela, "reintento")
    _pago(p, "fallido")
    _pago(p, "completado")
    pid = str(p.id)

    respuesta = client.get("/api/pedidos/admin", headers=_cabeceras_admin(admin))
    assert respuesta.status_code == 200, respuesta.get_json()
    ids = [ped["id"] for ped in respuesta.get_json()["pedidos"]]

    assert ids.count(pid) == 1, (
        f"el pedido aparece {ids.count(pid)} veces en el panel: "
        "una compra es una fila, sin importar cuantos intentos de pago tenga"
    )


def test_cliente_no_puede_ver_el_panel(client, usuario, centinela, admin):
    """El listado es del admin: un cliente no accede ni con su propio pedido."""
    p = _pedido(usuario, centinela, "ajeno")
    _pago(p, "completado")

    respuesta = client.get(
        "/api/pedidos/admin",
        headers={"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"},
    )

    assert respuesta.status_code == 403, respuesta.get_json()


def test_panel_ignora_pedidos_de_otros_usuarios(client, usuario, centinela, admin):
    """El filtro es global, no por usuario: el panel ve todas las compras."""
    propio = _pedido(usuario, centinela, "propio")
    _pago(propio, "completado")

    panel = _ids_del_panel(client, _cabeceras_admin(admin))

    assert str(propio.id) in panel, "el admin tiene que ver la compra de su cliente"