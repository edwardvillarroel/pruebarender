from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.domain.entities.pedido import Pedido
from app.domain.entities.seguimiento_starken import SeguimientoStarken
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import PedidoRepository
from app.domain.interfaces.starken import ErrorStarken, StarkenSeguimientoCliente
from app.domain.time import utcnow

MAX_LARGO_CODIGO = 50

_ESTADOS_QUE_ADELANTAN_A_ENVIADO = frozenset(
    {EstadoPedido.PENDIENTE, EstadoPedido.EN_PRODUCCION, EstadoPedido.ENVIADO}
)


class GestionarSeguimientoStarken:
    def __init__(
        self,
        repositorio: PedidoRepository,
        cliente: StarkenSeguimientoCliente,
    ) -> None:
        self._repositorio = repositorio
        self._cliente = cliente

    def listar_todos(self) -> list[Pedido]:
        return self._repositorio.list_pagados()

    def listar_propios(self, usuario_id: UUID) -> list[Pedido]:
        return self._repositorio.list_by_usuario(usuario_id)

    def registrar_codigo(self, pedido_id: UUID, codigo: str) -> Pedido:
        codigo = (codigo or "").strip()
        if not codigo:
            raise ValueError("El código de seguimiento es obligatorio")
        if len(codigo) > MAX_LARGO_CODIGO:
            raise ValueError(
                f"El código de seguimiento no puede superar {MAX_LARGO_CODIGO} caracteres"
            )

        pedido = self._repositorio.get_by_id(pedido_id)
        if pedido is None:
            raise ValueError("Pedido no encontrado")

        seguimiento = self._consultar_o_nada(codigo)
        actualizado_en = seguimiento.consultado_en if seguimiento else None
        persistido = self._repositorio.actualizar_seguimiento(
            pedido_id,
            codigo_seguimiento=codigo,
            estado_seguimiento=seguimiento.estado if seguimiento else None,
            actualizado_en=actualizado_en,
        )
        pedido_actual = persistido or pedido

        if pedido_actual.estado in _ESTADOS_QUE_ADELANTAN_A_ENVIADO:
            pedido_actual = (
                self._repositorio.actualizar_estado(pedido_id, EstadoPedido.ENVIADO)
                or pedido_actual
            )
        return pedido_actual

    def sincronizar(
        self, pedido_id: UUID
    ) -> tuple[Pedido, SeguimientoStarken | None]:
        pedido = self._repositorio.get_by_id(pedido_id)
        if pedido is None:
            raise ValueError("Pedido no encontrado")
        if not pedido.codigo_seguimiento:
            raise ValueError("El pedido no tiene código de seguimiento")

        seguimiento = self._consultar_o_nada(pedido.codigo_seguimiento)
        actualizado_en = (
            seguimiento.consultado_en if seguimiento else utcnow()
        )
        persistido = self._repositorio.actualizar_seguimiento(
            pedido_id,
            codigo_seguimiento=pedido.codigo_seguimiento,
            estado_seguimiento=seguimiento.estado if seguimiento else None,
            actualizado_en=actualizado_en,
        )
        return (persistido or pedido), seguimiento

    def _consultar_o_nada(self, codigo: str) -> SeguimientoStarken | None:
        try:
            return self._cliente.consultar(codigo)
        except ErrorStarken:
            return None