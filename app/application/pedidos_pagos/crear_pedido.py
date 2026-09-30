"""Caso de uso: crear un pedido a partir de un carrito (sin pago aún).

Valida existencia/actividad/stock, calcula el total (envío + IVA) y persiste
el pedido con sus líneas en una sola transacción. No descuenta stock: eso
ocurre al confirmarse el pago (ver `ProcesarPago.confirmar`).
"""

from __future__ import annotations

import json
from uuid import UUID

from app.application.common.calculos import calcular_total_con_envio_y_iva
from app.application.common.dto import CrearPedidoDTO
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.domain.interfaces.repositories import PedidoRepository, ProductoRepository


class CrearPedido:
    """Caso de uso: pedido a partir de las líneas del cliente."""

    def __init__(
        self, pedidos: PedidoRepository, productos: ProductoRepository
    ) -> None:
        self._pedidos = pedidos
        self._productos = productos

    def ejecutar(self, dto: CrearPedidoDTO) -> Pedido:
        if not dto.items:
            raise ValueError("No hay productos para generar el pedido")

        pedido = Pedido(
            usuario_id=dto.usuario_id,
            direccion_envio=(
                json.dumps(dto.cliente, ensure_ascii=False) if dto.cliente else None
            ),
        )
        detalles = []
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
        return self._pedidos.crear_con_detalles(pedido, detalles)