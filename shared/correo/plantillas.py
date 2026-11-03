"""Plantillas de correo transaccional de ApoloVibes.

Todas las funciones devuelven un `Correo` con asunto, HTML y texto plano.
Los textos visibles están en español neutro.
"""

from __future__ import annotations

from dataclasses import replace

from shared.correo.formato import (
    descuentos_texto,
    envolver,
    escapar,
    formatear_fecha,
    formatear_pesos,
    items_texto,
    tabla_descuentos,
    tabla_items,
)
from shared.correo.modelos import (
    Correo,
    CotizacionCorreo,
    PedidoCorreo,
    ProductoCorreo,
)

FRONTEND_URL_POR_DEFECTO = "https://apolovibes3d.cl"


def _base(frontend_url: str | None) -> str:
    return (frontend_url or FRONTEND_URL_POR_DEFECTO).rstrip("/")


def _enlace_cotizaciones(frontend_url: str | None) -> str:
    return f"{_base(frontend_url)}/mis-cotizaciones"


def _fila_html(etiqueta: str, valor: object) -> str:
    if valor is None or valor == "":
        return ""
    return (
        "<tr>"
        f'<td style="padding:4px 8px 4px 0;color:#6b7280;vertical-align:top">'
        f"{escapar(etiqueta)}</td>"
        f'<td style="padding:4px 0">{escapar(valor)}</td>'
        "</tr>"
    )


def _tabla_html(filas: str) -> str:
    return (
        '<table style="width:100%;border-collapse:collapse;margin:12px 0">'
        f"<tbody>{filas}</tbody></table>"
    )


def _fila_texto(etiqueta: str, valor: object) -> str:
    if valor is None or valor == "":
        return ""
    return f"{etiqueta}: {valor}"


def _lineas(*lineas: str) -> str:
    return "\n".join(linea for linea in lineas if linea)


def _medidas(cotizacion: CotizacionCorreo) -> str:
    medidas = [
        medida
        for medida in (cotizacion.alto, cotizacion.ancho, cotizacion.largo)
        if medida is not None
    ]
    if not medidas:
        return ""
    return " x ".join(f"{medida:g}" for medida in medidas) + f" {cotizacion.unidad}"


def _detalle_cotizacion_html(
    cotizacion: CotizacionCorreo,
    *,
    incluir_contacto: bool = False,
    incluir_estado: bool = False,
) -> str:
    filas = "".join(
        [
            _fila_html("Material", cotizacion.material),
            _fila_html("Medidas", _medidas(cotizacion)),
            _fila_html("Cantidad", cotizacion.cantidad),
            _fila_html("Uso", cotizacion.uso),
            _fila_html("Color", cotizacion.color),
            _fila_html("Descripción", cotizacion.descripcion),
            _fila_html(
                "Precio",
                formatear_pesos(cotizacion.precio)
                if cotizacion.precio is not None
                else "",
            ),
            _fila_html("Email", cotizacion.email if incluir_contacto else ""),
            _fila_html("Teléfono", cotizacion.telefono if incluir_contacto else ""),
            _fila_html("Estado", cotizacion.estado if incluir_estado else ""),
        ]
    )
    return _tabla_html(filas)


def _detalle_cotizacion_texto(
    cotizacion: CotizacionCorreo,
    *,
    incluir_contacto: bool = False,
    incluir_estado: bool = False,
) -> str:
    return _lineas(
        _fila_texto("Material", cotizacion.material),
        _fila_texto("Medidas", _medidas(cotizacion)),
        _fila_texto("Cantidad", cotizacion.cantidad),
        _fila_texto("Uso", cotizacion.uso),
        _fila_texto("Color", cotizacion.color),
        _fila_texto("Descripción", cotizacion.descripcion),
        _fila_texto(
            "Precio",
            formatear_pesos(cotizacion.precio)
            if cotizacion.precio is not None
            else "",
        ),
        _fila_texto("Email", cotizacion.email if incluir_contacto else ""),
        _fila_texto("Teléfono", cotizacion.telefono if incluir_contacto else ""),
        _fila_texto("Estado", cotizacion.estado if incluir_estado else ""),
    )


def _totales_html(pedido: PedidoCorreo) -> str:
    filas = [
        _fila_html("Subtotal", formatear_pesos(pedido.subtotal)),
        _fila_html(
            "Descuentos",
            formatear_pesos(abs(pedido.descuento_total))
            if pedido.descuento_total
            else "",
        ),
    ]
    if pedido.costo_envio > 0:
        filas.append(_fila_html("Envío", formatear_pesos(pedido.costo_envio)))
    elif pedido.tipo_entrega == "Envío a domicilio":
        filas.append(_fila_html("Envío", "Gratis"))
    filas.append(
        "<tr>"
        '<td style="padding:8px 8px 8px 0;font-weight:bold">Total</td>'
        f'<td style="padding:8px 0;font-weight:bold;text-align:right">'
        f"{formatear_pesos(pedido.total)}</td>"
        "</tr>"
    )
    return _tabla_html("".join(filas))


def _totales_texto(pedido: PedidoCorreo) -> str:
    envio = ""
    if pedido.costo_envio > 0:
        envio = _fila_texto("Envío", formatear_pesos(pedido.costo_envio))
    elif pedido.tipo_entrega == "Envío a domicilio":
        envio = _fila_texto("Envío", "Gratis")
    return _lineas(
        _fila_texto("Subtotal", formatear_pesos(pedido.subtotal)),
        _fila_texto(
            "Descuentos",
            formatear_pesos(abs(pedido.descuento_total))
            if pedido.descuento_total
            else "",
        ),
        envio,
        _fila_texto("Total", formatear_pesos(pedido.total)),
    )


def comprobante_pedido(pedido: PedidoCorreo, frontend_url: str | None = None) -> Correo:
    """Comprobante que recibe el cliente cuando se confirma su pago."""
    asunto = f"Comprobante de tu pedido #{pedido.numero} — ApoloVibes"

    cuerpo_html = (
        "<p>Gracias por tu compra en ApoloVibes. "
        f"Este es el comprobante del pedido <strong>#{escapar(pedido.numero)}</strong>."
        "</p>"
        + _tabla_html(
            _fila_html("Fecha", formatear_fecha(pedido.fecha))
            + _fila_html("Estado del pago", pedido.estado_pago)
            + _fila_html("Tipo de entrega", pedido.tipo_entrega)
            + _fila_html("Dirección", pedido.direccion)
            + _fila_html("Notas", pedido.notas)
        )
        + tabla_items(pedido.items)
        + tabla_descuentos(pedido.descuentos)
        + _totales_html(pedido)
    )
    html = envolver(f"Pedido #{pedido.numero}", cuerpo_html)

    texto = _lineas(
        "Gracias por tu compra en ApoloVibes.",
        f"Comprobante del pedido #{pedido.numero}",
        "",
        _fila_texto("Fecha", formatear_fecha(pedido.fecha)),
        _fila_texto("Estado del pago", pedido.estado_pago),
        _fila_texto("Tipo de entrega", pedido.tipo_entrega),
        _fila_texto("Dirección", pedido.direccion),
        _fila_texto("Notas", pedido.notas),
        "",
        items_texto(pedido.items),
        "",
        descuentos_texto(pedido.descuentos),
        "",
        _totales_texto(pedido),
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def admin_pedido_pagado(
    pedido: PedidoCorreo, frontend_url: str | None = None
) -> Correo:
    """Aviso interno cuando se confirma el pago de un pedido."""
    asunto = (
        f"Nuevo pedido pagado #{pedido.numero} — {formatear_pesos(pedido.total)}"
    )
    enlace = f"{_base(frontend_url)}/admin/pedidos"

    cuerpo_html = (
        f"<p>Se confirmó el pago del pedido <strong>#{escapar(pedido.numero)}</strong>."
        "</p>"
        + _tabla_html(
            _fila_html("Cliente", pedido.email_cliente)
            + _fila_html("Total", formatear_pesos(pedido.total))
            + _fila_html("Estado del pago", pedido.estado_pago)
            + _fila_html("Tipo de entrega", pedido.tipo_entrega)
            + _fila_html("Dirección", pedido.direccion)
        )
        + tabla_items(pedido.items)
        + f'<p><a href="{escapar(enlace)}">Ver pedido en el panel</a></p>'
    )
    html = envolver(f"Pedido pagado #{pedido.numero}", cuerpo_html)

    texto = _lineas(
        f"Se confirmó el pago del pedido #{pedido.numero}.",
        _fila_texto("Cliente", pedido.email_cliente),
        _fila_texto("Total", formatear_pesos(pedido.total)),
        _fila_texto("Estado del pago", pedido.estado_pago),
        _fila_texto("Tipo de entrega", pedido.tipo_entrega),
        _fila_texto("Dirección", pedido.direccion),
        "",
        items_texto(pedido.items),
        "",
        f"Ver pedido en el panel: {enlace}",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def admin_nueva_cotizacion(
    cotizacion: CotizacionCorreo, frontend_url: str | None = None
) -> Correo:
    """Aviso interno cuando ingresa una solicitud de diseño."""
    asunto = f"Nueva cotización #{cotizacion.numero} — {cotizacion.nombre}"
    enlace = f"{_base(frontend_url)}/admin/cotizaciones"

    cuerpo_html = (
        "<p>Ingresó una nueva solicitud de cotización.</p>"
        + _detalle_cotizacion_html(
            cotizacion, incluir_contacto=True, incluir_estado=True
        )
        + f'<p><a href="{escapar(enlace)}">Ver cotización en el panel</a></p>'
    )
    html = envolver(f"Nueva cotización #{cotizacion.numero}", cuerpo_html)

    texto = _lineas(
        "Ingresó una nueva solicitud de cotización.",
        "",
        _detalle_cotizacion_texto(
            cotizacion, incluir_contacto=True, incluir_estado=True
        ),
        "",
        f"Ver cotización en el panel: {enlace}",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def _detalle_producto_html(producto: ProductoCorreo) -> str:
    if producto.stock <= 0:
        return f"{escapar(producto.nombre)}: Agotado"
    return (
        f"{escapar(producto.nombre)}: stock {producto.stock} "
        f"(mínimo {producto.stock_minimo})"
    )


def _detalle_producto_texto(producto: ProductoCorreo) -> str:
    if producto.stock <= 0:
        return f"{producto.nombre}: Agotado"
    return (
        f"{producto.nombre}: stock {producto.stock} "
        f"(mínimo {producto.stock_minimo})"
    )


def admin_stock_bajo(
    productos: list[ProductoCorreo], frontend_url: str | None = None
) -> Correo:
    """Aviso interno cuando uno o más productos quedan en stock bajo."""
    cantidad = len(productos)
    sustantivo = "producto" if cantidad == 1 else "productos"
    asunto = f"Stock bajo en ApoloVibes ({cantidad} {sustantivo})"
    enlace = f"{_base(frontend_url)}/admin/inventario"

    lista_html = "".join(
        f"<li>{_detalle_producto_html(producto)}</li>" for producto in productos
    )
    cuerpo_html = (
        "<p>Estos productos quedaron en stock bajo o agotado:</p>"
        f"<ul>{lista_html}</ul>"
        f'<p><a href="{escapar(enlace)}">Revisar inventario</a></p>'
    )
    html = envolver("Stock bajo", cuerpo_html)

    lista_texto = "\n".join(
        f"- {_detalle_producto_texto(producto)}" for producto in productos
    )
    texto = _lineas(
        "Estos productos quedaron en stock bajo o agotado:",
        "",
        lista_texto,
        "",
        f"Revisar inventario: {enlace}",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def cotizacion_aprobada(
    cotizacion: CotizacionCorreo, precio: int | None, frontend_url: str | None
) -> Correo:
    """Correo al cliente cuando su cotización pasa a aprobada."""
    asunto = f"Tu cotización #{cotizacion.numero} fue aprobada"
    enlace = _enlace_cotizaciones(frontend_url)
    monto = precio if precio is not None else cotizacion.precio
    cotizacion = replace(cotizacion, precio=monto)

    cuerpo_html = (
        f"<p>Hola {escapar(cotizacion.nombre)},</p>"
        f"<p>Tu cotización <strong>#{escapar(cotizacion.numero)}</strong> "
        "fue aprobada.</p>"
        + _detalle_cotizacion_html(cotizacion)
        + "<p>Para pagar, revisa los detalles en nuestra página:</p>"
        f'<p><a href="{escapar(enlace)}">{escapar(enlace)}</a></p>'
        "<p>Si tienes dudas, responde este correo.</p>"
    )
    html = envolver("Cotización aprobada", cuerpo_html)

    detalle = _detalle_cotizacion_texto(cotizacion)
    texto = _lineas(
        f"Hola {cotizacion.nombre},",
        "",
        f"Tu cotización #{cotizacion.numero} fue aprobada.",
        "",
        detalle,
        "",
        "Para pagar, revisa los detalles en nuestra página:",
        enlace,
        "",
        "Si tienes dudas, responde este correo.",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def cotizacion_rechazada(
    cotizacion: CotizacionCorreo, frontend_url: str | None = None
) -> Correo:
    """Correo al cliente cuando su cotización pasa a rechazada."""
    asunto = f"Tu cotización #{cotizacion.numero} fue rechazada"

    cuerpo_html = (
        f"<p>Hola {escapar(cotizacion.nombre)},</p>"
        f"<p>Tu cotización <strong>#{escapar(cotizacion.numero)}</strong> "
        "fue rechazada.</p>"
        "<p>Puedes enviarnos una nueva solicitud cuando quieras.</p>"
    )
    html = envolver("Cotización rechazada", cuerpo_html)

    texto = _lineas(
        f"Hola {cotizacion.nombre},",
        "",
        f"Tu cotización #{cotizacion.numero} fue rechazada.",
        "Puedes enviarnos una nueva solicitud cuando quieras.",
        "",
        "— Equipo ApoloVibes",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def codigo_verificacion(codigo: str) -> Correo:
    """Código de un solo uso para el gateway."""
    asunto = "Tu código de verificación — ApoloVibes"

    cuerpo_html = (
        f"<p>Tu código de verificación es <strong>{escapar(codigo)}</strong>.</p>"
        "<p>Este código tiene una vigencia limitada.</p>"
        "<p>Si no solicitaste este código, ignora este mensaje.</p>"
    )
    html = envolver("Código de verificación", cuerpo_html)

    texto = _lineas(
        f"Tu código de verificación es {codigo}.",
        "Este código tiene una vigencia limitada.",
        "Si no solicitaste este código, ignora este mensaje.",
        "",
        "— Equipo ApoloVibes",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def alerta_seguridad(detalle: str) -> Correo:
    """Aviso de inicio de sesión para el gateway."""
    asunto = "Alerta de seguridad — ApoloVibes"

    cuerpo_html = (
        "<p>Detectamos actividad de seguridad en tu cuenta.</p>"
        f"<p>{escapar(detalle)}</p>"
        "<p>Si no fuiste tú, cambia tu contraseña de inmediato.</p>"
    )
    html = envolver("Alerta de seguridad", cuerpo_html)

    texto = _lineas(
        "Detectamos actividad de seguridad en tu cuenta.",
        detalle,
        "Si no fuiste tú, cambia tu contraseña de inmediato.",
        "",
        "— Equipo ApoloVibes",
    )
    return Correo(asunto=asunto, html=html, texto=texto)
