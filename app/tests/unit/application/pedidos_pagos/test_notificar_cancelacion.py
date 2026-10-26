"""El aviso de anulacion aceptada por Tuu: quien lo enciende y quien lo apaga.

El badge del cliente no es un adorno: significa "Tuu acepto anular tu pedido y
nadie te lo habia dicho". Por eso el aviso solo puede nacer sobre un pedido
cancelado, y marcar el aviso como visto debe ser idempotente — abrir el modal dos
veces no puede romper nada ni reabrir el badge.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.application.pedidos_pagos.notificar_cancelacion import (
    AvisoPedidoNoEncontradoError,
    NotificarCancelacion,
    PedidoSinCancelarError,
)
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido


class _PedidosFalsos:
    """Repositorio en memoria que registra los avisos."""

    def __init__(self, pedido: Pedido | None = None):
        self._pedido = pedido
        self.avisados: list[uuid.UUID] = []
        self.vistos: list[uuid.UUID] = []

    def get_by_id(self, pedido_id):
        if self._pedido is None or self._pedido.id != pedido_id:
            return None
        return self._pedido

    def marcar_aviso_cancelacion(self, pedido_id):
        self.avisados.append(pedido_id)
        self._pedido.aviso_cancelacion_en = datetime.now(timezone.utc)
        self._pedido.aviso_cancelacion_visto = False
        return self._pedido

    def marcar_aviso_cancelacion_visto(self, pedido_id):
        self.vistos.append(pedido_id)
        self._pedido.aviso_cancelacion_visto = True
        return self._pedido


def _pedido(estado: EstadoPedido = EstadoPedido.CANCELADO) -> Pedido:
    return Pedido(usuario_id=uuid.uuid4(), estado=estado)


def test_avisa_sobre_un_pedido_cancelado():
    pedido = _pedido()
    repositorio = _PedidosFalsos(pedido)

    actualizado = NotificarCancelacion(repositorio).informar_cliente(pedido.id)

    assert repositorio.avisados == [pedido.id]
    assert actualizado.aviso_cancelacion_en is not None
    assert actualizado.aviso_cancelacion_visto is False


@pytest.mark.parametrize(
    "estado",
    [
        EstadoPedido.PENDIENTE,
        EstadoPedido.EN_PRODUCCION,
        EstadoPedido.ENVIADO,
        EstadoPedido.ENTREGADO,
    ],
)
def test_no_avisa_sobre_un_pedido_que_no_esta_cancelado(estado):
    pedido = _pedido(estado)
    repositorio = _PedidosFalsos(pedido)

    with pytest.raises(PedidoSinCancelarError):
        NotificarCancelacion(repositorio).informar_cliente(pedido.id)

    assert repositorio.avisados == []


def test_no_avisa_sobre_un_pedido_inexistente():
    repositorio = _PedidosFalsos(None)

    with pytest.raises(AvisoPedidoNoEncontradoError):
        NotificarCancelacion(repositorio).informar_cliente(uuid.uuid4())


def test_marcar_visto_apaga_el_aviso_existente():
    pedido = _pedido()
    pedido.aviso_cancelacion_en = datetime.now(timezone.utc)
    repositorio = _PedidosFalsos(pedido)

    NotificarCancelacion(repositorio).marcar_visto(pedido.id)

    assert repositorio.vistos == [pedido.id]
    assert pedido.aviso_cancelacion_visto is True


def test_marcar_visto_sin_aviso_no_toca_la_base():
    pedido = _pedido()
    repositorio = _PedidosFalsos(pedido)

    resultado = NotificarCancelacion(repositorio).marcar_visto(pedido.id)

    assert repositorio.vistos == []
    assert resultado is pedido
    assert pedido.aviso_cancelacion_visto is False


def test_marcar_visto_dos_veces_es_idempotente():
    pedido = _pedido()
    pedido.aviso_cancelacion_en = datetime.now(timezone.utc)
    repositorio = _PedidosFalsos(pedido)
    servicio = NotificarCancelacion(repositorio)

    servicio.marcar_visto(pedido.id)
    servicio.marcar_visto(pedido.id)

    assert repositorio.vistos == [pedido.id]
