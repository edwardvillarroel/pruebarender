"""Cambiar el estado de un pedido: la regla vive en el caso de uso, no en la ruta.

El admin tiene un botón de "Finalizado" y el backend tiene un `PATCH`. Lo
interesante no es que el estado cambie, es QUÉTransiciones existen:

- `pendiente -> entregado` y `enviado -> entregado` son las unicas validas.
  Las dos llegan al mismo estado final, asi que no hay un estado "finalizado"
  nuevo: hay dos caminos hacia `entregado`. Uno es el retiro (el cliente llega
  al local, no hay orden de flete que esperar) y el otro es la entrega de Starken.
- `cancelado -> entregado` NO vale. Resucitar una compra cancelada, o retroceder
  desde `entregado`, son errores que el frontend nunca va a cometer porque el
  boton no existe, pero la API es publica para el gateway y no depende de que
  la UI sea cuidadosa.

Por eso la validacion va en `CambiarEstadoPedido`: si viviera en la ruta, el
siguiente que agregue una forma de cambiar el estado (un worker deventory sync,
un script de cierre de dia) se saltearia la regla sin enterarse.
"""

from __future__ import annotations

import uuid

import pytest

from app.application.pedidos_pagos.cambiar_estado_pedido import (
    CambiarEstadoPedido,
    EstadoInvalidoError,
    PedidoNoEncontradoError,
    TransicionInvalidaError,
)
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido


class _PedidosFalsos:
    """Repositorio en memoria que registra lo que se le pide cambiar."""

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
    """Los dos caminos validos de la regla: retiro y entrega con Starken."""
    repos = _PedidosFalsos(_pedido_en(origen))

    resultado = CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "entregado")

    assert resultado.estado is EstadoPedido.ENTREGADO
    assert repos.cambios == [(repos._pedido.id, EstadoPedido.ENTREGADO)]


@pytest.mark.parametrize("origen", [EstadoPedido.EN_PRODUCCION, EstadoPedido.CANCELADO])
def test_no_se_puede_entregar_desde_en_produccion_ni_desde_cancelado(origen):
    """`en_produccion` no tiene orden de flete: el pedido no salió.

    `cancelado -> entregado` es el caso importante: el pago fallo o el cliente
    cancelo, y "des-cancelar" desde la API dejaria una compra fantasma con stock
    descontado.
    """
    repos = _PedidosFalsos(_pedido_en(origen))

    with pytest.raises(TransicionInvalidaError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "entregado")

    assert repos.cambios == [], "un rechazo no puede dejar el pedido a medio cambiar"


def test_no_se_puede_retroceder_desde_entregado():
    """`entregado` es terminal: no vuelve a `enviado` ni a `pendiente`."""
    repos = _PedidosFalsos(_pedido_en(EstadoPedido.ENTREGADO))

    with pytest.raises(TransicionInvalidaError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "enviado")

    assert repos.cambios == []


def test_estado_desconocido_es_error_de_estado_invalido():
    """Un estado que no existe en el enum es 400, no una transicion invalida.

    Son dos cosas distintas: "no entendi el estado" (cliente, 400) y "ese
    cambio no se puede" (regla de negocio, 409). Mezclarlas hace que un typo del
    frontend se vea como un problema de negocio.
    """
    repos = _PedidosFalsos(_pedido_en(EstadoPedido.PENDIENTE))

    with pytest.raises(EstadoInvalidoError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "finalizado")

    assert repos.cambios == []


@pytest.mark.parametrize("estado", [None, "", "   ", "finalizado", 42])
def test_estado_vacio_o_invalido_no_toca_la_base(estado):
    """Falta el campo o no es un estado: se rechaza antes de leer el pedido.

    Que se rechace antes de tocar la base importa: el pedido inexistente y el
    estado invalido tienen que poder distinguirse (404 contra 400), asi que el
    estado se valida primero y no al reves.
    """
    repos = _PedidosFalsos(_pedido_en(EstadoPedido.PENDIENTE))

    with pytest.raises(EstadoInvalidoError):
        CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, estado)

    assert repos.cambios == []


def test_acepta_el_nombre_del_enum_en_mayusculas():
    """Tolerancia concreta: el enum se llama `ENTREGADO`, el valor es `entregado`.

    El frontend manda el valor, pero que un `ENTREGADO` en mayusculas no sea un
    400 confuso evita un ticket por un detalle de serializacion.
    """
    repos = _PedidosFalsos(_pedido_en(EstadoPedido.PENDIENTE))

    resultado = CambiarEstadoPedido(repos).ejecutar(repos._pedido.id, "ENTREGADO")

    assert resultado.estado is EstadoPedido.ENTREGADO


def test_pedido_inexistente():
    repos = _PedidosFalsos(None)

    with pytest.raises(PedidoNoEncontradoError):
        CambiarEstadoPedido(repos).ejecutar(uuid.uuid4(), "entregado")

    assert repos.cambios == []