"""Plantillas de correo transaccional de ApoloVibes.

Todas las funciones devuelven un `Correo` con asunto, HTML y texto plano.
Los textos visibles están en español neutro.
"""

from __future__ import annotations

from dataclasses import replace

from shared.correo.formato import (
    COLOR_ACCENT,
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_RED,
    COLOR_TEXT,
    FilaDetalle,
    base_url,
    boton,
    caja_codigo,
    descuentos_texto,
    envolver,
    escapar,
    formatear_fecha,
    formatear_pesos,
    icono_html,
    items_texto,
    tabla_detalle,
    tabla_items,
    tabla_totales,
)
from shared.correo.modelos import (
    Correo,
    CotizacionCorreo,
    PedidoCorreo,
    ProductoCorreo,
)


def _base(frontend_url: str | None) -> str:
    return base_url(frontend_url)


def _enlace_cotizaciones(frontend_url: str | None) -> str:
    return f"{_base(frontend_url)}/mis-cotizaciones"


def _parrafo(
    contenido_html: str,
    *,
    color: str = COLOR_TEXT,
    tamano: int = 15,
    margen: str = "0 0 14px",
) -> str:
    return (
        f'<p style="margin:{margen};font-family:Arial,Helvetica,sans-serif;'
        f'font-size:{tamano}px;line-height:1.6;color:{color};">'
        f"{contenido_html}</p>"
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


def _estado_pago_html(estado: str | None) -> str:
    texto = "" if estado is None else str(estado)
    afirmativos = {"Pagado", "Completado", "Aprobado", "Confirmado"}
    if texto in afirmativos:
        return (
            f'<span style="color:{COLOR_GREEN};font-weight:bold;">✓</span> '
            f"{escapar(texto)}"
        )
    return escapar(texto)


def _detalle_cotizacion_html(
    cotizacion: CotizacionCorreo,
    *,
    incluir_contacto: bool = False,
    incluir_estado: bool = False,
    etiqueta_precio: str = "Precio",
) -> str:
    filas = [
        FilaDetalle("Material", cotizacion.material),
        FilaDetalle("Medidas", _medidas(cotizacion)),
        FilaDetalle("Cantidad", cotizacion.cantidad),
        FilaDetalle("Uso", cotizacion.uso),
        FilaDetalle("Color", cotizacion.color),
        FilaDetalle("Descripción", cotizacion.descripcion),
        FilaDetalle(
            etiqueta_precio,
            formatear_pesos(cotizacion.precio)
            if cotizacion.precio is not None
            else "",
        ),
    ]
    if incluir_contacto:
        filas.append(FilaDetalle("Email", cotizacion.email))
        filas.append(FilaDetalle("Teléfono", cotizacion.telefono))
    if incluir_estado:
        filas.append(FilaDetalle("Estado", cotizacion.estado))
    return tabla_detalle(filas)


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
        tabla_detalle(
            [
                FilaDetalle("Fecha", formatear_fecha(pedido.fecha)),
                FilaDetalle(
                    "Estado del pago",
                    _estado_pago_html(pedido.estado_pago),
                    html=True,
                ),
                FilaDetalle("Tipo de entrega", pedido.tipo_entrega),
                FilaDetalle("Dirección", pedido.direccion),
                FilaDetalle("Notas", pedido.notas),
            ]
        )
        + tabla_items(pedido.items, frontend_url)
        + tabla_totales(pedido)
    )
    html = envolver(
        f"Pedido #{pedido.numero}",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("✓", COLOR_GREEN),
        subtitulo=(
            "Gracias por tu compra en ApoloVibes. "
            f"Este es el comprobante del pedido #{pedido.numero}."
        ),
    )

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
        tabla_detalle(
            [
                FilaDetalle("Cliente", pedido.email_cliente),
                FilaDetalle("Total", formatear_pesos(pedido.total)),
                FilaDetalle(
                    "Estado del pago",
                    _estado_pago_html(pedido.estado_pago),
                    html=True,
                ),
                FilaDetalle("Tipo de entrega", pedido.tipo_entrega),
                FilaDetalle("Dirección", pedido.direccion),
            ]
        )
        + tabla_items(pedido.items, frontend_url)
        + boton("Ver pedido en el panel", enlace)
    )
    html = envolver(
        f"Pedido pagado #{pedido.numero}",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("✓", COLOR_GREEN),
        subtitulo=f"Se ha confirmado el pago del pedido #{pedido.numero}.",
        pie="",
    )

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

    cuerpo_html = _detalle_cotizacion_html(
        cotizacion,
        incluir_contacto=True,
        incluir_estado=True,
        etiqueta_precio="Precio estimado",
    ) + boton("Ver cotización en el panel", enlace)
    html = envolver(
        "Nueva cotización",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("✦", COLOR_ACCENT),
        subtitulo=(
            "Ingresó una nueva solicitud de cotización "
            f"#{cotizacion.numero}."
        ),
        pie="",
    )

    texto = _lineas(
        f"Ingresó una nueva solicitud de cotización #{cotizacion.numero}.",
        "",
        _detalle_cotizacion_texto(
            cotizacion, incluir_contacto=True, incluir_estado=True
        ),
        "",
        f"Ver cotización en el panel: {enlace}",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def _estado_stock_html(producto: ProductoCorreo) -> str:
    if producto.stock <= 0:
        return f'<span style="color:{COLOR_RED};font-weight:bold;">Agotado</span>'
    return escapar(
        f"stock {producto.stock} (mínimo {producto.stock_minimo})"
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

    cuerpo_html = tabla_detalle(
        [
            FilaDetalle(
                producto.nombre,
                _estado_stock_html(producto),
                html=True,
            )
            for producto in productos
        ]
    ) + boton("Revisar inventario", enlace)
    html = envolver(
        "Stock bajo",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("!", COLOR_ACCENT),
        subtitulo="Estos productos quedaron en stock bajo o agotado:",
        pie="",
    )

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
        _parrafo(f"Hola {escapar(cotizacion.nombre)},")
        + _detalle_cotizacion_html(cotizacion)
        + _parrafo("Para pagar, revisa los detalles en nuestra página:")
        + boton("Mis Cotizaciones", enlace)
        + _parrafo("Si tienes dudas, responde este correo.", margen="0")
    )
    html = envolver(
        "Cotización aprobada",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("✓", COLOR_GREEN),
        subtitulo=f"Tu cotización #{cotizacion.numero} fue aprobada.",
    )

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

    cuerpo_html = _parrafo(
        "Puedes enviarnos una nueva solicitud cuando quieras.", margen="0"
    )
    html = envolver(
        "Cotización rechazada",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("✕", COLOR_RED),
        subtitulo=f"Tu cotización #{cotizacion.numero} fue rechazada.",
    )

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
        caja_codigo(codigo)
        + _parrafo("Este código tiene una vigencia limitada.", margen="0 0 8px")
        + _parrafo(
            "Si no solicitaste este código, ignora este mensaje.",
            color=COLOR_MUTED,
            tamano=13,
            margen="0",
        )
    )
    html = envolver(
        "Código de verificación",
        cuerpo_html,
        icono=icono_html("#", COLOR_ACCENT),
        subtitulo="Tu código de verificación es:",
        pie="Equipo de seguridad",
    )

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

    # El frontend abre la recuperación de contraseña desde el modal de inicio
    # de sesión; por eso el botón apunta a la raíz y no a una ruta dedicada.
    enlace = f"{base_url()}/"

    cuerpo_html = (
        _parrafo(escapar(detalle))
        + _parrafo("Si no fuiste tú, cambia tu contraseña de inmediato.")
        + boton("Cambiar contraseña", enlace)
    )
    html = envolver(
        "Alerta de seguridad",
        cuerpo_html,
        icono=icono_html("!", COLOR_ACCENT),
        subtitulo="Detectamos actividad de seguridad en tu cuenta.",
        pie="Equipo de seguridad",
    )

    texto = _lineas(
        "Detectamos actividad de seguridad en tu cuenta.",
        detalle,
        "Si no fuiste tú, cambia tu contraseña de inmediato.",
        "",
        "— Equipo ApoloVibes",
    )
    return Correo(asunto=asunto, html=html, texto=texto)
