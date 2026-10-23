
from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from app.application.common.referencias import codificar_referencia
from app.domain.entities.pago import Pago
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPago, EstadoPedido
from app.domain.interfaces.pasarela_pago import (
    PasarelaPago,
    ResultadoIntentoPago,
    SolicitudPago,
)
from app.domain.interfaces.repositories import (
    DocumentoTributarioRepository,
    PagoRepository,
    PedidoRepository,
)
from app.infrastructure.repositories.cupon_repository import CuponRepository

logger = logging.getLogger(__name__)

_ESTADOS_PEDIDO_BLOQUEADOS = frozenset(
    {EstadoPedido.EN_PRODUCCION, EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO}
)
_ESTADOS_PAGO_CONFIRMADOS = frozenset(
    {EstadoPago.AUTORIZADO, EstadoPago.COMPLETADO, EstadoPago.REEMBOLSADO}
)


class PedidoNoPagadoNoEncontradoError(Exception):
    """El pedido no existe (o ya fue eliminado)."""


class PedidoNoPagadoDeOtroUsuarioError(Exception):
    """El pedido pertenece a otro usuario."""


class PedidoNoModificableError(ValueError):
    """El pedido ya no estÃ¡ en un estado que permita pagar o eliminar."""


class GestionarPedidoNoPagado:
    def __init__(
        self,
        pedidos: PedidoRepository,
        pagos: PagoRepository,
        pasarela: PasarelaPago,
        cupones: CuponRepository | None = None,
        documentos: DocumentoTributarioRepository | None = None,
    ) -> None:
        self._pedidos = pedidos
        self._pagos = pagos
        self._pasarela = pasarela
        self._cupones = cupones
        self._documentos = documentos

    def reintentar(
        self, pedido_id: UUID, usuario_id: UUID
    ) -> ResultadoIntentoPago:
        pedido = self._pedido_del_usuario(pedido_id, usuario_id)
        pago = self._pagos.get_by_pedido(pedido.id)
        self._validar_no_pagado(pedido, pago)

        if (
            pago is not None
            and pago.estado == EstadoPago.PENDIENTE
            and pago.url_intento
        ):
  
            return ResultadoIntentoPago(url=pago.url_intento, token=pago.token)

        datos = _datos_cliente(pedido)
        referencia = codificar_referencia(pedido.id)
        solicitud = SolicitudPago(
            monto=pedido.total,
            referencia=referencia,
            descripcion=f"Pedido {referencia} en ApoloVibes",
            nombre_cliente=_texto(datos.get("nombre")) or "Cliente",
            email_cliente=_texto(datos.get("email")),
            telefono_cliente=_texto(datos.get("telefono")),
            apellido_cliente=_texto(datos.get("apellido")) or "ApoloVibes",
        )
        resultado = self._pasarela.crear_intento(solicitud)

        self._pagos.add(
            Pago(
                pedido_id=pedido.id,
                monto=pedido.total,
                proveedor="tuu",
                token=resultado.token,
                url_intento=resultado.url,
                clave_idempotencia=str(uuid4()),
            )
        )
        if pedido.estado == EstadoPedido.CANCELADO:
            self._pedidos.actualizar_estado(pedido.id, EstadoPedido.PENDIENTE)
        return resultado

    def eliminar(self, pedido_id: UUID, usuario_id: UUID) -> None:
        pedido = self._pedido_del_usuario(pedido_id, usuario_id)
        pago = self._pagos.get_by_pedido(pedido.id)
        self._validar_no_pagado(pedido, pago)
        if self._documentos is not None and self._documentos.get_by_pedido(pedido.id):
            raise PedidoNoModificableError(
                "El pedido ya tiene un documento tributario emitido"
            )

        self._pagos.eliminar_por_pedido(pedido.id)
        self._pedidos.delete(pedido)
        self._liberar_cupon(pedido, usuario_id)

    def _pedido_del_usuario(self, pedido_id: UUID, usuario_id: UUID) -> Pedido:
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise PedidoNoPagadoNoEncontradoError("Pedido no encontrado")
        if pedido.usuario_id != usuario_id:
            raise PedidoNoPagadoDeOtroUsuarioError("No autorizado")
        return pedido

    @staticmethod
    def _validar_no_pagado(pedido: Pedido, pago: Pago | None) -> None:
        if pedido.estado in _ESTADOS_PEDIDO_BLOQUEADOS:
            raise PedidoNoModificableError(
                "El pedido ya estÃ¡ en preparaciÃ³n o fue entregado"
            )
        if pago is not None and pago.estado in _ESTADOS_PAGO_CONFIRMADOS:
            raise PedidoNoModificableError("El pedido ya tiene un pago confirmado")

    def _liberar_cupon(self, pedido: Pedido, usuario_id: UUID) -> None:
        """Devuelve el cupÃ³n si el pago nunca se completÃ³.

        Es best-effort: el pedido ya se eliminÃ³ y un cupÃ³n quemado no puede
        hacer fallar la operaciÃ³n que pidiÃ³ el cliente.
        """
        if not pedido.cupon_codigo or self._cupones is None:
            return
        try:
            cupon = self._cupones.get_by_codigo(pedido.cupon_codigo)
            if cupon is not None and cupon.usado:
                self._cupones.liberar(cupon, usuario_id)
        except Exception:  
            logger.exception(
                "No se pudo liberar el cupÃ³n %s del pedido %s",
                pedido.cupon_codigo,
                pedido.id,
            )


def _datos_cliente(pedido: Pedido) -> dict:
    if not pedido.direccion_envio:
        return {}
    try:
        datos = json.loads(pedido.direccion_envio)
    except (TypeError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _texto(valor) -> str:
    return str(valor or "").strip()

