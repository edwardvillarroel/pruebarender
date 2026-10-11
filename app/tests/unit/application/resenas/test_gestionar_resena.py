"""Tests unitarios de `GestionarResena` con dobles en memoria.

La secuencia de validación es el contrato que las rutas traducen a códigos
HTTP (400/403/404/409), así que cada caso verifica DOS cosas: la excepción
correcta Y que no se llegó a tocar el repositorio de reseñas (una validación
que falla sin escribir filas no puede "pasar de largo").

El recálculo denormalizado de `productos.rating`/`resenas_count` vive en la
infraestructura (misma transacción que el INSERT, ver `ResenaRepository.crear`);
acá lo que se congela es que el caso de uso delega UNA sola vez en `crear`,
que es quien inserta y recalcula.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.resenas.gestionar_resena import (
    ComentarioInvalidoError,
    EstrellasInvalidasError,
    GestionarResena,
    NoAutorizadoError,
    NoEntregadoError,
    PedidoNoEncontradoError,
    ProductoNoEnPedidoError,
)
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import ResenaDuplicadaError


class _ResenasFake:
    """Reemplaza a `ResenaRepository`: guarda en memoria y puede simular el
    duplicado de negocio que en la base real levanta el `UNIQUE`."""

    def __init__(self, duplicada: bool = False) -> None:
        self.creadas = []
        self.duplicada = duplicada

    def crear(self, resena):
        if self.duplicada:
            raise ResenaDuplicadaError(
                "El producto ya tiene una reseña tuya en este pedido"
            )
        self.creadas.append(resena)
        return resena

    def listar_por_pedido(self, pedido_id):
        return [r for r in self.creadas if r.pedido_id == pedido_id]

    def listar_por_producto(self, producto_id):
        return [r for r in self.creadas if r.producto_id == producto_id]


class _PedidosFake:
    """Solo `get_by_id`: lo único que el caso de uso usa del repositorio."""

    def __init__(self, pedido: Pedido | None) -> None:
        self.pedido = pedido
        self.consultas = 0

    def get_by_id(self, pedido_id):
        self.consultas += 1
        if self.pedido is not None and pedido_id == self.pedido.id:
            return self.pedido
        return None


def _pedido(
    estado: EstadoPedido = EstadoPedido.ENTREGADO,
    usuario_id=None,
    producto_ids=(),
) -> Pedido:
    usuario_id = usuario_id or uuid4()
    pedido_id = uuid4()
    detalles = [
        DetallePedido(
            pedido_id=pedido_id,
            producto_id=producto_id,
            cantidad=1,
            precio_unitario=5000,
        )
        for producto_id in producto_ids
    ]
    return Pedido(
        usuario_id=usuario_id,
        estado=estado,
        total=5000,
        id=pedido_id,
        detalles=detalles,
    )


def _servicio(pedido: Pedido | None = None, duplicada: bool = False):
    resenas = _ResenasFake(duplicada=duplicada)
    pedidos = _PedidosFake(pedido)
    # `productos` viaja en el constructor por contrato del design, pero la
    # membresía se valida contra `pedido.detalles` (la fuente de verdad del
    # contenido del pedido), así que el doble no expone métodos: si el caso de
    # uso llegara a depender de él, este test revienta.
    servicio = GestionarResena(resenas, pedidos, object())
    return servicio, resenas, pedidos


# --- registrar: camino feliz -------------------------------------------------


def test_registrar_crea_la_resena_del_triple_correcto():
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, pedidos = _servicio(pedido)

    creada = servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 4)

    assert len(resenas.creadas) == 1
    guardada = resenas.creadas[0]
    assert guardada.usuario_id == pedido.usuario_id
    assert guardada.pedido_id == pedido.id
    assert guardada.producto_id == producto_id
    assert guardada.estrellas == 4
    assert creada is guardada, "el caso de uso debe devolver la reseña creada"
    assert pedidos.consultas == 1


def test_registrar_delega_una_vez_en_crear_que_es_quien_recalcula():
    """`crear` es INSERT + recálculo en la misma transacción: el caso de uso
    no puede insertar por su cuenta ni recalcular aparte."""
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)

    servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 5)

    assert len(resenas.creadas) == 1, (
        "una sola llamada a `crear`: duplicarla insertaría dos veces"
    )
    assert resenas.creadas[0].estrellas == 5


def test_producto_repetido_en_detalles_se_valida_por_conjunto_de_ids():
    """2 detalles del mismo producto siguen siendo un producto reseñable."""
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id, producto_id])
    servicio, resenas, _ = _servicio(pedido)

    servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 3)

    assert len(resenas.creadas) == 1


def test_registrar_con_comentario_lo_recorta_y_lo_persiste():
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)

    creada = servicio.registrar(
        pedido.usuario_id, pedido.id, producto_id, 4, comentario="  Muy bueno  "
    )

    assert creada.comentario == "Muy bueno", "el comentario debe guardarse recortado"
    assert resenas.creadas[0].comentario == "Muy bueno"


def test_registrar_sin_comentario_queda_none():
    """`comentario` es opcional: las llamadas viejas (4 args) siguen andando."""
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)

    servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 4)

    assert resenas.creadas[0].comentario is None


def test_registrar_con_comentario_solo_espacios_queda_none():
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)

    servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 4, comentario="   ")

    assert resenas.creadas[0].comentario is None


# --- registrar: validaciones -------------------------------------------------


@pytest.mark.parametrize("estrellas", [0, 6, -1, 3.5, "x", None, True])
def test_estrellas_invalidas_se_rechazan_antes_de_tocar_la_base(estrellas):
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, pedidos = _servicio(pedido)

    with pytest.raises(EstrellasInvalidasError):
        servicio.registrar(pedido.usuario_id, pedido.id, producto_id, estrellas)

    assert pedidos.consultas == 0, (
        "las estrellas se validan primero: no se ni consulta el pedido"
    )
    assert resenas.creadas == []


def test_estrellas_invalidas_ganan_sobre_pedido_inexistente():
    """Fija el orden de la secuencia: 400 antes que 404."""
    servicio, resenas, pedidos = _servicio(None)

    with pytest.raises(EstrellasInvalidasError):
        servicio.registrar(uuid4(), uuid4(), uuid4(), 0)

    assert pedidos.consultas == 0
    assert resenas.creadas == []


@pytest.mark.parametrize("comentario", [123, ["texto"], {"c": 1}, 3.5])
def test_comentario_no_texto_es_400_sin_tocar_la_base(comentario):
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, pedidos = _servicio(pedido)

    with pytest.raises(ComentarioInvalidoError):
        servicio.registrar(
            pedido.usuario_id, pedido.id, producto_id, 4, comentario=comentario
        )

    assert pedidos.consultas == 0, (
        "el comentario se valida antes de consultar el pedido"
    )
    assert resenas.creadas == []


def test_comentario_demasiado_largo_es_400_sin_tocar_la_base():
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, pedidos = _servicio(pedido)

    with pytest.raises(ComentarioInvalidoError):
        servicio.registrar(
            pedido.usuario_id,
            pedido.id,
            producto_id,
            4,
            comentario="a" * 1001,
        )

    assert pedidos.consultas == 0
    assert resenas.creadas == []


def test_estrellas_invalidas_ganan_sobre_comentario_invalido():
    """Fija el orden: las estrellas se validan antes que el comentario."""
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, pedidos = _servicio(pedido)

    with pytest.raises(EstrellasInvalidasError):
        servicio.registrar(
            pedido.usuario_id, pedido.id, producto_id, 0, comentario=123
        )

    assert pedidos.consultas == 0
    assert resenas.creadas == []


def test_pedido_inexistente_es_404_sin_escribir():
    producto_id = uuid4()
    servicio, resenas, pedidos = _servicio(None)

    with pytest.raises(PedidoNoEncontradoError):
        servicio.registrar(uuid4(), uuid4(), producto_id, 5)

    assert pedidos.consultas == 1
    assert resenas.creadas == []


def test_no_dueño_es_403_sin_escribir():
    producto_id = uuid4()
    pedido = _pedido(usuario_id=uuid4(), producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)

    with pytest.raises(NoAutorizadoError):
        servicio.registrar(uuid4(), pedido.id, producto_id, 5)

    assert resenas.creadas == []


@pytest.mark.parametrize(
    "estado",
    [
        EstadoPedido.PENDIENTE,
        EstadoPedido.EN_PRODUCCION,
        EstadoPedido.ENVIADO,
        EstadoPedido.CANCELADO,
    ],
)
def test_pedido_no_entregado_es_409_sin_escribir(estado):
    producto_id = uuid4()
    pedido = _pedido(estado=estado, producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)

    with pytest.raises(NoEntregadoError):
        servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 5)

    assert resenas.creadas == []


def test_producto_ajeno_es_404_sin_escribir():
    pedido = _pedido(producto_ids=[uuid4()])
    servicio, resenas, _ = _servicio(pedido)

    with pytest.raises(ProductoNoEnPedidoError):
        servicio.registrar(pedido.usuario_id, pedido.id, uuid4(), 5)

    assert resenas.creadas == []


def test_pedido_sin_detalles_es_404_para_cualquier_producto():
    pedido = _pedido(producto_ids=[])
    servicio, resenas, _ = _servicio(pedido)

    with pytest.raises(ProductoNoEnPedidoError):
        servicio.registrar(pedido.usuario_id, pedido.id, uuid4(), 5)

    assert resenas.creadas == []


def test_duplicado_propaga_ResenaDuplicadaError():
    """El 409 de negocio nace en `UNIQUE` y llega intacto hasta la ruta."""
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, _, _ = _servicio(pedido, duplicada=True)

    with pytest.raises(ResenaDuplicadaError):
        servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 5)


# --- listar_por_pedido -------------------------------------------------------


def test_listar_devuelve_las_resenas_del_pedido():
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)
    servicio.registrar(pedido.usuario_id, pedido.id, producto_id, 4)

    listadas = servicio.listar_por_pedido(pedido.usuario_id, pedido.id)

    assert [r.producto_id for r in listadas] == [producto_id]
    assert [r.estrellas for r in listadas] == [4]


def test_listar_sin_sesion_de_dueño_es_403():
    pedido = _pedido(producto_ids=[uuid4()])
    servicio, _, _ = _servicio(pedido)

    with pytest.raises(NoAutorizadoError):
        servicio.listar_por_pedido(uuid4(), pedido.id)


def test_listar_con_es_admin_permite_a_otro_usuario():
    """`es_admin=True` es el permiso del admin (mismo criterio que `_es_dueno`)."""
    pedido = _pedido(producto_ids=[uuid4()])
    servicio, _, _ = _servicio(pedido)

    listadas = servicio.listar_por_pedido(uuid4(), pedido.id, es_admin=True)

    assert listadas == []


def test_listar_pedido_inexistente_es_404():
    servicio, _, _ = _servicio(None)

    with pytest.raises(PedidoNoEncontradoError):
        servicio.listar_por_pedido(uuid4(), uuid4())


# --- listar_por_producto (vista publica) -------------------------------------


def test_listar_por_producto_delega_y_devuelve_lo_creado():
    producto_id = uuid4()
    pedido = _pedido(producto_ids=[producto_id])
    servicio, resenas, _ = _servicio(pedido)
    servicio.registrar(
        pedido.usuario_id, pedido.id, producto_id, 4, comentario="rico"
    )

    listadas = servicio.listar_por_producto(producto_id)

    assert [r.producto_id for r in listadas] == [producto_id]
    assert listadas[0].comentario == "rico"


def test_listar_por_producto_sin_resenas_devuelve_vacio():
    servicio, _, _ = _servicio(None)

    assert servicio.listar_por_producto(uuid4()) == []
