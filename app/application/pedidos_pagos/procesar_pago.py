"""Caso de uso: iniciar y confirmar el pago de un pedido (pasarela externa).

Coordina pedido + pago + pasarela (TUU) usando solo interfaces del dominio.
El descuento de stock ocurre únicamente al confirmar `completed`; un pago
fallido/cancelado deja el pedido cancelado y el stock y carrito intactos.
Todas las mutaciones son idempotentes para tolerar el doble aviso de la
pasarela (callback server-to-server y redirección del navegador).
"""

from __future__ import annotations

import json
from typing import Any

from app.application.common.calculos import calcular_total_con_envio_y_iva
from app.application.common.dto import IniciarPagoDTO, ResultadoConfirmacionPago
from app.application.common.referencias import (
    codificar_referencia,
    decodificar_referencia,
)
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pago import Pago
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPago, EstadoPedido
from app.domain.interfaces.carrito_repository import CarritoRepository
from app.domain.interfaces.pasarela_pago import (
    ErrorPasarela,
    PasarelaPago,
    ResultadoIntentoPago,
    SolicitudPago,
)
from app.domain.interfaces.repositories import (
    PagoRepository,
    PedidoRepository,
    ProductoRepository,
)


class ProcesarPago:
    """Caso de uso: el ciclo completo de pago (inicio y confirmación)."""

    def __init__(
        self,
        pedidos: PedidoRepository,
        pagos: PagoRepository,
        productos: ProductoRepository,
        pasarela: PasarelaPago,
        carritos: CarritoRepository,
    ) -> None:
        self._pedidos = pedidos
        self._pagos = pagos
        self._productos = productos
        self._pasarela = pasarela
        self._carritos = carritos

    def iniciar(self, dto: IniciarPagoDTO) -> ResultadoIntentoPago:
        """Crea pedido + pago pendiente y abre el intento en la pasarela."""
        pedido, detalles = self._construir_pedido(dto)
        self._pedidos.crear_con_detalles(pedido, detalles)

        pago = Pago(pedido_id=pedido.id, monto=pedido.total, proveedor="tuu")
        self._pagos.add(pago)

        solicitud_referencia = codificar_referencia(pedido.id)
        solicitud = SolicitudPago(
            monto=pedido.total,
            referencia=solicitud_referencia,
            descripcion=f"Pedido {solicitud_referencia} en ApoloVibes",
            nombre_cliente=self._nombre_cliente(dto.cliente),
            email_cliente=(dto.cliente or {}).get("email", ""),
            telefono_cliente=(dto.cliente or {}).get("telefono", ""),
        )
        try:
            resultado = self._pasarela.crear_intento(solicitud)
        except ErrorPasarela:
            # El pedido quedó persistido: se marca cancelado para no dejar
            # órdenes huérfanas y se propaga el error para la capa de API.
            self._marcar_fallido(pedido, pago)
            raise

        pago.token = resultado.token
        self._pagos.update(pago)
        return resultado

    def confirmar(self, parametros: dict[str, str]) -> ResultadoConfirmacionPago:
        """Procesa la notificación de la pasarela (callback o redirect).

        `parametros` son los campos `x_*` (incluida `x_signature`) que envía
        TUU. Si la firma no vale, se rechaza sin tocar nada. El resultado es
        idempotente: repetir la misma notificación no duplica efectos.
        """
        if not self._pasarela.verificar_firma(parametros):
            raise ErrorPasarela("Firma inválida de la pasarela de pagos")

        referencia = parametros.get("x_reference")
        if not referencia:
            raise ErrorPasarela("La notificación no incluye la referencia del pedido")
        try:
            pedido_id = decodificar_referencia(referencia)
        except ValueError:
            raise ErrorPasarela("Referencia de pedido inválida")

        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise ErrorPasarela("Pedido no encontrado")
        pago = self._pagos.get_by_pedido(pedido_id)

        resultado = (parametros.get("x_result") or "").lower()
        if resultado == "completed":
            if pago is not None and pago.estado == EstadoPago.COMPLETADO:
                return ResultadoConfirmacionPago(
                    estado="completado", pedido_id=str(pedido.id),
                    mensaje="Pago ya confirmado",
                )
            try:
                self._descontar_stock(pedido)
            except ValueError as exc:
                # Caso límite: el stock se validó al crear el pedido; si cambió
                # antes de confirmarse, se rechaza sin descontar nada.
                return self._rechazar(pedido, pago, str(exc))
            if pago is not None:
                pago.estado = EstadoPago.COMPLETADO
                self._pagos.update(pago)
            self._carritos.eliminar(str(pedido.usuario_id))
            return ResultadoConfirmacionPago(
                estado="completado", pedido_id=str(pedido.id),
                mensaje="Pago confirmado",
            )

        if resultado in ("failed", "aborted", "cancelled"):
            if pago is not None and pago.estado == EstadoPago.FALLIDO:
                return ResultadoConfirmacionPago(
                    estado="fallido", pedido_id=str(pedido.id),
                    mensaje="Pago ya rechazado",
                )
            return self._rechazar(pedido, pago, "Pago rechazado por la pasarela")

        return ResultadoConfirmacionPago(
            estado="pendiente", pedido_id=str(pedido.id),
            mensaje="El pago aún no ha sido procesado",
        )

    def _construir_pedido(self, dto: IniciarPagoDTO) -> tuple[Pedido, list[DetallePedido]]:
        if not dto.items:
            raise ValueError("No hay productos para generar el pedido")

        pedido = Pedido(
            usuario_id=dto.usuario_id,
            direccion_envio=(
                json.dumps(dto.cliente, ensure_ascii=False) if dto.cliente else None
            ),
        )
        detalles: list[DetallePedido] = []
        subtotal = 0
        for item in dto.items:
            producto = self._productos.get_by_id(item.producto_id)
            if producto is None or not producto.activo:
                raise ValueError("Uno de los productos del pedido ya no está disponible")
            if producto.stock < item.cantidad:
                raise ValueError(
                    f"No hay stock suficiente de «{producto.nombre}» "
                    f"(disponible: {producto.stock})"
                )
            detalles.append(
                DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    precio_unitario=producto.precio,
                    color=getattr(item, "color", None),
                )
            )
            subtotal += producto.precio * item.cantidad

        pedido.total = calcular_total_con_envio_y_iva(subtotal, dto.entrega)
        pedido.detalles = detalles
        return pedido, detalles

    def _descontar_stock(self, pedido: Pedido) -> None:
        for detalle in pedido.detalles:
            producto = self._productos.get_by_id(detalle.producto_id)
            if producto is None or producto.stock < detalle.cantidad:
                raise ValueError(
                    f"No hay stock suficiente para completar el pedido "
                    f"(producto {detalle.producto_id})"
                )
            producto.stock -= detalle.cantidad
            self._productos.update(producto)

    def _marcar_fallido(self, pedido: Pedido, pago: Pago) -> None:
        pago.estado = EstadoPago.FALLIDO
        self._pagos.update(pago)
        self._pedidos.actualizar_estado(pedido.id, EstadoPedido.CANCELADO)

    def _rechazar(
        self, pedido: Pedido, pago: Pago | None, mensaje: str
    ) -> ResultadoConfirmacionPago:
        if pago is not None:
            pago.estado = EstadoPago.FALLIDO
            self._pagos.update(pago)
        self._pedidos.actualizar_estado(pedido.id, EstadoPedido.CANCELADO)
        return ResultadoConfirmacionPago(
            estado="fallido", pedido_id=str(pedido.id), mensaje=mensaje
        )

    @staticmethod
    def _nombre_cliente(cliente: dict[str, Any] | None) -> str:
        if not cliente:
            return "Cliente"
        nombre = " ".join(
            str(cliente.get(campo, "")).strip()
            for campo in ("nombre", "apellido")
            if str(cliente.get(campo, "")).strip()
        )
        return nombre or "Cliente"