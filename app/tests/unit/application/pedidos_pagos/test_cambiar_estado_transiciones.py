



from __future__ import annotations

import uuid

import pytest

from app.application.pedidos_pagos.cambiar_estado_pedido import (
    CambiarEstadoPedido,
    EstadoInvalidoError,
    PedidoDeOtroUsuarioError,
    PedidoNoEncontradoError,
    TransicionInvalidaError,
)
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido


class _PedidosFalsos:

    def __init__(self, pedido: Pedido | None = None):
        self._pedido = pedido
        self.cambios: list[tuple[uuid.UUID, EstadoPedido]] = []

    def get_by_id(self, pedido_id: uuid.UUID) -> Pedido | None:
        if self._pedido is None or self._pedido.id != pedido_id:
            return None
        return self._pedido

    def actualizar_estado(self, pedido_id: uuid.UUID, estado: EstadoPedido):
        assert self.cambios == [], "no debería haber más de un cambio por llamada"
        self.cambios.append((pedido_id, estado))
        if self._pedido is not None:
            self._pedido.estado = estado
            return self._pedido
        return None


def _pedido_en(estado: EstadoPedido) -> Pedido:
    return Pedido(usuario_id=uuid.uuid4(), estado=estado)


@pytest.mark.parametrize("origen", [EstadoPedido.PENDIENTE, EstadoPedido.ENVIADO])
def test_se_puede_entregar_desde_pendiente_y_desde_enviado(origen):
    repos = _PedidosFalsos(_pedido_en(origen))

    resultado = CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "entregado")

    assert resultado.estado is EstadoPedido.ENTREGADO
    assert repos.cambios == [(repos._pedido.id, EstadoPedido.ENTREGADO)]


@pytest.mark.parametrize("origen", [EstadoPedido.EN_PRODUCCION, EstadoPedido.CANCELADO])
def test_no_se_puede_entregar_desde_en_produccion_ni_desde_cancelado(origen):

    repos = _PedidosFalsos(_pedido_en(origen))

    with pytest.raises(TransicionInvalidaError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "entregado")

    assert repos.cambios == [], "un rechazo no puede dejar el pedido a medio cambiar"


@pytest.mark.parametrize("origen", [EstadoPedido.PENDIENTE, EstadoPedido.EN_PRODUCCION])
def test_se_puede_cancelar_antes_de_despachar(origen):
    repos = _PedidosFalsos(_pedido_en(origen))

    resultado = CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "cancelado")

    assert resultado.estado is EstadoPedido.CANCELADO
    assert repos.cambios == [(repos._pedido.id, EstadoPedido.CANCELADO)]


@pytest.mark.parametrize(
    "origen",
    [EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO, EstadoPedido.CANCELADO],
)
def test_no_se_puede_cancelar_un_pedido_que_ya_salio(origen):
    repos = _PedidosFalsos(_pedido_en(origen))

    with pytest.raises(TransicionInvalidaError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "cancelado")

    assert repos.cambios == [], "un rechazo no puede dejar el pedido a medio cambiar"


def test_no_se_puede_retroceder_desde_entregado():
    repos = _PedidosFalsos(_pedido_en(EstadoPedido.ENTREGADO))

    with pytest.raises(TransicionInvalidaError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "enviado")

    assert repos.cambios == []


def test_estado_desconocido_es_error_de_estado_invalido():

    repos = _PedidosFalsos(_pedido_en(EstadoPedido.PENDIENTE))

    with pytest.raises(EstadoInvalidoError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "finalizado")

    assert repos.cambios == []


@pytest.mark.parametrize("estado", [None, "", "   ", "finalizado", 42])
def test_estado_vacio_o_invalido_no_toca_la_base(estado):

    repos = _PedidosFalsos(_pedido_en(EstadoPedido.PENDIENTE))

    with pytest.raises(EstadoInvalidoError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, estado)

    assert repos.cambios == []


def test_acepta_el_nombre_del_enum_en_mayusculas():

    repos = _PedidosFalsos(_pedido_en(EstadoPedido.PENDIENTE))

    resultado = CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "ENTREGADO")

    assert resultado.estado is EstadoPedido.ENTREGADO


def test_pedido_inexistente():
    repos = _PedidosFalsos(None)

    with pytest.raises(PedidoNoEncontradoError):
        CambiarEstadoPedido(repos).ejecutar(uuid.uuid4(), "entregado")

    assert repos.cambios == []




@pytest.mark.parametrize("origen", [EstadoPedido.PENDIENTE, EstadoPedido.EN_PRODUCCION])
def test_el_dueno_cancela_su_pedido_antes_del_despacho(origen):
    repos = _PedidosFalsos(_pedido_en(origen))

    resultado = CambiarEstadoPedido(repos).cancelar(repos._pedido.id, repos._pedido.usuario_id)

    assert resultado.estado is EstadoPedido.CANCELADO
    assert repos.cambios == [(repos._pedido.id, EstadoPedido.CANCELADO)]


@pytest.mark.parametrize("origen", [EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO])
def test_el_dueno_no_cancela_un_pedido_ya_despachado(origen):
    repos = _PedidosFalsos(_pedido_en(origen))

    with pytest.raises(TransicionInvalidaError):
        CambiarEstadoPedido(repos).cancelar(repos._pedido.id, repos._pedido.usuario_id)

    assert repos.cambios == []


def test_nadie_cancela_el_pedido_de_otro():
    repos = _PedidosFalsos(_pedido_en(EstadoPedido.PENDIENTE))

    with pytest.raises(PedidoDeOtroUsuarioError):
        CambiarEstadoPedido(repos).cancelar(repos._pedido.id, uuid.uuid4())

    assert repos.cambios == []


def test_cancelar_un_pedido_inexistente():
    repos = _PedidosFalsos(None)

    with pytest.raises(PedidoNoEncontradoError):
        CambiarEstadoPedido(repos).cancelar(uuid.uuid4(), uuid.uuid4())

    assert repos.cambios == []
