"""Adaptador de correo del backend sobre el cliente compartido de Resend."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import STOCK_BAJO, Producto
from app.domain.entities.solicitud_diseno import SolicitudDiseno
from app.domain.interfaces.correo import ServicioCorreo
from shared.correo import plantillas
from shared.correo.cliente import ClienteCorreo, _leer_config
from shared.correo.formato import formatear_fecha, formatear_pesos
from shared.correo.modelos import (
    CotizacionCorreo,
    DescuentoCorreo,
    ItemCorreo,
    PedidoCorreo,
    ProductoCorreo,
)

logger = logging.getLogger(__name__)

_ETIQUETA_ESTADO_PAGO = {
    "completado": "Pagado",
}

_ETIQUETA_ENTREGA = {
    "envio": "Envío a domicilio",
    "retiro": "Retiro",
}

_formato_clp = formatear_pesos
_fecha_chile = formatear_fecha


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _numero(valor: Any) -> float | None:
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _entero(valor: Any) -> int | None:
    numero = _numero(valor)
    return int(numero) if numero is not None else None


def _direccion_y_notas(pedido: Pedido) -> tuple[str | None, str | None]:
    if not pedido.direccion_envio:
        return None, None
    try:
        datos = json.loads(pedido.direccion_envio)
    except (TypeError, ValueError):
        return None, None
    if not isinstance(datos, dict):
        return None, None

    partes = [
        _texto(datos.get("direccion")),
        _texto(datos.get("comuna")),
        _texto(datos.get("ciudad")),
        _texto(datos.get("region")),
    ]
    direccion = ", ".join(parte for parte in partes if parte) or None
    notas = (
        _texto(datos.get("notas"))
        or _texto(datos.get("nota"))
        or _texto(datos.get("indicaciones"))
        or None
    )
    return direccion, notas


def _items_correo(pedido: Pedido) -> list[ItemCorreo]:
    items = []
    for detalle in pedido.detalles:
        precio_unitario = int(detalle.precio_unitario or 0)
        cantidad = int(detalle.cantidad or 0)
        items.append(
            ItemCorreo(
                nombre=_texto(detalle.nombre) or "Producto",
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=precio_unitario * cantidad,
            )
        )
    return items


def _descuentos_correo(pedido: Pedido) -> list[DescuentoCorreo]:
    descuentos = []
    if pedido.descuento_productos:
        descuentos.append(
            DescuentoCorreo(
                etiqueta="Descuento",
                monto=int(pedido.descuento_productos),
            )
        )
    if pedido.descuento_cupon:
        etiqueta = "Cupón"
        if pedido.cupon_codigo:
            etiqueta = f"Cupón ({pedido.cupon_codigo})"
        descuentos.append(
            DescuentoCorreo(etiqueta=etiqueta, monto=int(pedido.descuento_cupon))
        )
    return descuentos


def _pedido_correo(
    pedido: Pedido, cliente_email: str, estado_pago: str
) -> PedidoCorreo:
    items = _items_correo(pedido)
    descuentos = _descuentos_correo(pedido)
    subtotal = int(pedido.subtotal) if pedido.subtotal is not None else sum(
        item.subtotal for item in items
    )
    descuento_total = int(
        (pedido.descuento_productos or 0) + (pedido.descuento_cupon or 0)
    )
    total = int(pedido.total or 0)
    costo_envio = max(0, total - (subtotal - descuento_total))
    direccion, notas = _direccion_y_notas(pedido)

    return PedidoCorreo(
        numero=str(pedido.id)[:8],
        fecha=pedido.creado_en,
        email_cliente=cliente_email,
        estado_pago=_ETIQUETA_ESTADO_PAGO.get(estado_pago, estado_pago),
        items=items,
        descuentos=descuentos,
        subtotal=subtotal,
        descuento_total=descuento_total,
        costo_envio=costo_envio,
        total=total,
        tipo_entrega=_ETIQUETA_ENTREGA.get(pedido.entrega, pedido.entrega or ""),
        direccion=direccion,
        notas=notas,
    )


def _producto_correo(producto: Producto) -> ProductoCorreo:
    stock_minimo = (
        producto.stock_minimo
        if producto.stock_minimo is not None
        else STOCK_BAJO
    )
    return ProductoCorreo(
        nombre=producto.nombre,
        stock=int(producto.stock or 0),
        stock_minimo=int(stock_minimo),
    )


def _estado_texto(estado: Any) -> str:
    return _texto(getattr(estado, "value", estado))


def _cotizacion_correo(
    solicitud: SolicitudDiseno,
    estado: Any | None = None,
    precio: int | None = None,
) -> CotizacionCorreo:
    precio_entidad = (
        int(solicitud.precio) if solicitud.precio is not None else None
    )
    return CotizacionCorreo(
        numero=str(solicitud.id)[:8],
        fecha=solicitud.creado_en,
        nombre=_texto(solicitud.nombre),
        email=_texto(solicitud.email),
        telefono=_texto(solicitud.telefono) or None,
        material=_texto(solicitud.material),
        alto=float(solicitud.alto) if solicitud.alto is not None else None,
        ancho=float(solicitud.ancho) if solicitud.ancho is not None else None,
        largo=float(solicitud.largo) if solicitud.largo is not None else None,
        unidad=_texto(solicitud.unidad),
        cantidad=int(solicitud.cantidad or 0),
        uso=_texto(solicitud.uso) or None,
        color=_texto(solicitud.color) or None,
        descripcion=_texto(solicitud.descripcion),
        precio=precio if precio is not None else precio_entidad,
        estado=_estado_texto(estado if estado is not None else solicitud.estado),
        material_sugerido_ia=_texto(solicitud.material_sugerido_ia) or None,
        complejidad_ia=_texto(solicitud.complejidad_ia) or None,
        gramos_estimados_ia=_numero(solicitud.gramos_estimados_ia),
        tiempo_estimado_horas_ia=_numero(solicitud.tiempo_estimado_horas_ia),
        precio_estimado_ia=_entero(solicitud.precio_estimado_ia),
    )


def _parametros_comprobante(
    pedido: Pedido, cliente_email: str, estado_pago: str
) -> dict[str, str]:
    """Campos históricos que se imprimen en modo simulación."""
    items = "\n".join(
        f"{item.cantidad}x {item.nombre}: {formatear_pesos(item.subtotal)}"
        for item in _items_correo(pedido)
    )
    return {
        "to_email": cliente_email,
        "pedido_id": str(pedido.id)[:8],
        "estado": _ETIQUETA_ESTADO_PAGO.get(estado_pago, estado_pago),
        "subtotal": formatear_pesos(pedido.subtotal),
        "descuento_productos": (
            formatear_pesos(pedido.descuento_productos)
            if pedido.descuento_productos
            else ""
        ),
        "descuento_cupon": (
            formatear_pesos(pedido.descuento_cupon)
            if pedido.descuento_cupon
            else ""
        ),
        "cupon_codigo": pedido.cupon_codigo or "",
        "descuentos": "\n".join(
            f"{descuento.etiqueta}: - {formatear_pesos(abs(descuento.monto))}"
            for descuento in _descuentos_correo(pedido)
        ),
        "total": formatear_pesos(pedido.total),
        "entrega": _ETIQUETA_ENTREGA.get(pedido.entrega, pedido.entrega or ""),
        "items": items,
        "fecha": formatear_fecha(pedido.creado_en),
    }


class ResendCorreo(ServicioCorreo):
    """Implementación de `ServicioCorreo` con Resend y modo simulación."""

    def __init__(self, config: Any) -> None:
        self._cliente = ClienteCorreo(config)
        self._admin_email = _leer_config(config, "ADMIN_EMAIL")
        self._frontend_url = _leer_config(config, "FRONTEND_URL")

    @property
    def configurado(self) -> bool:
        return self._cliente.configurado

    def enviar_comprobante_pedido(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        if not self.configurado:
            self._imprimir_en_consola(pedido, cliente_email, estado_pago)
            return
        self._cliente.enviar(
            cliente_email,
            plantillas.comprobante_pedido(
                _pedido_correo(pedido, cliente_email, estado_pago),
                self._frontend_url,
            ),
        )

    def avisar_admin_pedido_pagado(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        self._enviar_al_admin(
            plantillas.admin_pedido_pagado(
                _pedido_correo(pedido, cliente_email, estado_pago),
                self._frontend_url,
            ),
            "pedido pagado",
        )

    def avisar_admin_nueva_cotizacion(self, solicitud: SolicitudDiseno) -> None:
        self._enviar_al_admin(
            plantillas.admin_nueva_cotizacion(
                _cotizacion_correo(solicitud),
                self._frontend_url,
            ),
            "nueva cotización",
        )

    def avisar_admin_stock_bajo(self, productos: list[Producto]) -> None:
        if not productos:
            return
        self._enviar_al_admin(
            plantillas.admin_stock_bajo(
                [_producto_correo(producto) for producto in productos],
                self._frontend_url,
            ),
            "stock bajo",
        )

    def enviar_estado_cotizacion(
        self,
        solicitud: SolicitudDiseno,
        estado: str,
        precio: int | None = None,
    ) -> None:
        destino = _texto(solicitud.email)
        if not destino:
            logger.info(
                "Correo de cotización %s omitido: la solicitud no tiene email",
                solicitud.id,
            )
            return

        estado_normalizado = _estado_texto(estado).lower()
        if estado_normalizado not in {"aprobada", "rechazada"}:
            logger.warning(
                "Estado de cotización no soportado para correo: %s",
                estado_normalizado,
            )
            return

        if not self.configurado:
            logger.info(
                "Correo de cotización %s simulado (Resend sin credenciales)",
                estado_normalizado,
            )
            return

        cotizacion = _cotizacion_correo(solicitud, estado=estado, precio=precio)
        if estado_normalizado == "aprobada":
            correo = plantillas.cotizacion_aprobada(
                cotizacion, cotizacion.precio, self._frontend_url
            )
        else:
            correo = plantillas.cotizacion_rechazada(
                cotizacion, self._frontend_url
            )
        self._cliente.enviar(destino, correo)

    def _enviar_al_admin(self, correo, etiqueta: str) -> None:
        if not self._admin_email:
            logger.info(
                "Correo de %s omitido: ADMIN_EMAIL no configurado", etiqueta
            )
            return
        if not self.configurado:
            logger.info(
                "Correo de %s simulado (Resend sin credenciales)", etiqueta
            )
            return
        self._cliente.enviar(self._admin_email, correo)

    @staticmethod
    def _imprimir_en_consola(
        pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        print(
            "[correo:simulacion] Comprobante de pedido "
            "(Resend sin credenciales)"
        )
        print(f"[correo:simulacion]   para: {cliente_email}")
        for clave, valor in _parametros_comprobante(
            pedido, cliente_email, estado_pago
        ).items():
            print(f"[correo:simulacion]   {clave}: {valor}")
