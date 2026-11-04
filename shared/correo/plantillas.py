"""Plantillas de correo transaccional de ApoloVibes.

Todas las funciones devuelven un `Correo` con asunto, HTML y texto plano.
Los textos visibles están en español neutro.
"""

from __future__ import annotations

import re
from dataclasses import replace

from shared.correo.formato import (
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_PANEL,
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
    seccion,
    tabla_detalle,
    tabla_items,
    tabla_stock,
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
    centrado: bool = False,
) -> str:
    alineacion = "text-align:center;" if centrado else ""
    return (
        f'<p style="margin:{margen};{alineacion}'
        f'font-family:Arial,Helvetica,sans-serif;'
        f'font-size:{tamano}px;line-height:1.5;color:{color};">'
        f"{contenido_html}</p>"
    )


def _caja_panel(contenido_html: str) -> str:
    """Bloque gris redondeado para mensajes destacados sin botón."""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" '
        f'bgcolor="{COLOR_PANEL}" '
        f'style="width:100%;border-collapse:collapse;background-color:{COLOR_PANEL};'
        'border-radius:12px;margin:18px 0 0;">'
        "<tr>"
        '<td align="center" style="padding:20px 18px;text-align:center;'
        'font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;'
        f'color:{COLOR_TEXT};">'
        f"{contenido_html}"
        "</td>"
        "</tr>"
        "</table>"
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


def _descripcion_usuario(descripcion: str | None) -> str:
    """Devuelve solo el texto que escribió el usuario.

    Las solicitudes antiguas guardaban el resumen completo dentro de
    `descripcion` ("Tamaño: ...", "Cantidad: ...", "Detalles: ..."). Cuando
    detectamos ese formato devolvemos únicamente la línea de "Detalles" para
    no repetir datos que ya tienen su propia fila en el correo.
    """
    texto = "" if descripcion is None else str(descripcion).strip()
    if not texto:
        return ""
    if not re.match(r"^Tamaño:\s*", texto, re.IGNORECASE):
        return texto
    etiquetas = re.findall(
        r"(?:^|\n|/)\s*"
        r"(Tamaño|Cantidad|Uso|Color|Detalles|Precio estimado IA|"
        r"Material IA|Complejidad IA):",
        texto,
        re.IGNORECASE,
    )
    if len({etiqueta.lower() for etiqueta in etiquetas}) < 2:
        return texto
    partes = re.split(r"Detalles:\s*", texto, maxsplit=1, flags=re.IGNORECASE)
    if len(partes) < 2:
        return ""
    return re.split(
        r"\n|/\s*(?:Tamaño|Cantidad|Uso|Color|Precio estimado IA|"
        r"Material IA|Complejidad IA):",
        partes[1],
        maxsplit=1,
    )[0].strip()


def _estado_pago_html(estado: str | None) -> str:
    texto = "" if estado is None else str(estado)
    afirmativos = {"Pagado", "Completado", "Aprobado", "Confirmado"}
    if texto in afirmativos:
        return (
            f'<span style="color:{COLOR_GREEN};font-weight:bold;">✓</span> '
            f"{escapar(texto)}"
        )
    return escapar(texto)


def _detalle_producto_texto(producto: ProductoCorreo) -> str:
    if producto.stock <= 0:
        return f"{producto.nombre}: Agotado"
    return (
        f"{producto.nombre}: Stock {producto.stock} "
        f"(mín. {producto.stock_minimo})"
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
        + seccion("Tus productos")
        + tabla_items(pedido.items, frontend_url)
        + tabla_totales(pedido)
        + _parrafo("¡Seguimos creando contigo!", margen="18px 0 0", centrado=True)
    )
    html = envolver(
        "¡Gracias por tu compra!",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("check", frontend_url),
        subtitulo=f"Este es el comprobante de tu pedido #{pedido.numero}.",
        pie="Equipo ApoloVibes",
    )

    texto = _lineas(
        "¡Gracias por tu compra!",
        f"Este es el comprobante de tu pedido #{pedido.numero}.",
        "",
        _fila_texto("Fecha", formatear_fecha(pedido.fecha)),
        _fila_texto("Estado del pago", pedido.estado_pago),
        _fila_texto("Tipo de entrega", pedido.tipo_entrega),
        _fila_texto("Dirección", pedido.direccion),
        _fila_texto("Notas", pedido.notas),
        "",
        "Tus productos",
        items_texto(pedido.items),
        "",
        descuentos_texto(pedido.descuentos),
        "",
        _totales_texto(pedido),
        "",
        "¡Seguimos creando contigo!",
        "",
        "Equipo ApoloVibes",
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
        + seccion("Productos")
        + tabla_items(pedido.items, frontend_url)
        + boton("Ver pedido en el panel", enlace)
    )
    html = envolver(
        "Nuevo pedido pagado",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("campana", frontend_url),
        subtitulo=f"Se ha confirmado el pago del pedido #{pedido.numero}.",
        pie="Equipo de administración",
    )

    texto = _lineas(
        "Nuevo pedido pagado",
        f"Se ha confirmado el pago del pedido #{pedido.numero}.",
        "",
        _fila_texto("Cliente", pedido.email_cliente),
        _fila_texto("Total", formatear_pesos(pedido.total)),
        _fila_texto("Estado del pago", pedido.estado_pago),
        _fila_texto("Tipo de entrega", pedido.tipo_entrega),
        _fila_texto("Dirección", pedido.direccion),
        "",
        "Productos",
        items_texto(pedido.items),
        "",
        f"Ver pedido en el panel: {enlace}",
        "",
        "Equipo de administración",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def admin_nueva_cotizacion(
    cotizacion: CotizacionCorreo, frontend_url: str | None = None
) -> Correo:
    """Aviso interno cuando ingresa una solicitud de diseño."""
    asunto = f"Nueva cotización #{cotizacion.numero} — {cotizacion.nombre}"
    enlace = f"{_base(frontend_url)}/admin/cotizaciones"
    precio = (
        cotizacion.precio
        if cotizacion.precio is not None
        else cotizacion.precio_estimado_ia
    )

    cuerpo_html = (
        tabla_detalle(
            [
                FilaDetalle("Cliente", cotizacion.nombre),
                FilaDetalle("Teléfono", cotizacion.telefono),
                FilaDetalle("Material", cotizacion.material),
                FilaDetalle("Medidas", _medidas(cotizacion)),
                FilaDetalle("Cantidad", cotizacion.cantidad),
                FilaDetalle("Uso", cotizacion.uso),
                FilaDetalle("Color", cotizacion.color),
                FilaDetalle(
                    "Descripción", _descripcion_usuario(cotizacion.descripcion)
                ),
                FilaDetalle("Precio estimado", formatear_pesos(precio)),
                FilaDetalle("Estado", cotizacion.estado),
            ]
        )
        + boton("Ver cotización en el panel", enlace)
    )
    html = envolver(
        f"Nueva cotización #{cotizacion.numero}",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("lapiz", frontend_url),
        subtitulo="Ingresó una nueva solicitud de cotización.",
        pie="Equipo de administración",
    )

    texto = _lineas(
        f"Nueva cotización #{cotizacion.numero}",
        "Ingresó una nueva solicitud de cotización.",
        "",
        _fila_texto("Cliente", cotizacion.nombre),
        _fila_texto("Teléfono", cotizacion.telefono),
        _fila_texto("Material", cotizacion.material),
        _fila_texto("Medidas", _medidas(cotizacion)),
        _fila_texto("Cantidad", cotizacion.cantidad),
        _fila_texto("Uso", cotizacion.uso),
        _fila_texto("Color", cotizacion.color),
        _fila_texto(
            "Descripción", _descripcion_usuario(cotizacion.descripcion)
        ),
        _fila_texto("Precio estimado", formatear_pesos(precio)),
        _fila_texto("Estado", cotizacion.estado),
        "",
        f"Ver cotización en el panel: {enlace}",
        "",
        "Equipo de administración",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def admin_stock_bajo(
    productos: list[ProductoCorreo], frontend_url: str | None = None
) -> Correo:
    """Aviso interno cuando uno o más productos quedan en stock bajo."""
    cantidad = len(productos)
    sustantivo = "producto" if cantidad == 1 else "productos"
    asunto = f"Stock bajo en ApoloVibes ({cantidad} {sustantivo})"
    enlace = f"{_base(frontend_url)}/admin/inventario"

    cuerpo_html = tabla_stock(productos, frontend_url) + boton(
        "Revisar inventario", enlace
    )
    html = envolver(
        "Stock bajo en ApoloVibes",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("alerta", frontend_url),
        subtitulo="Estos productos quedaron en stock bajo o agotado:",
        pie="Equipo de administración",
    )

    lista_texto = "\n".join(
        f"- {_detalle_producto_texto(producto)}" for producto in productos
    )
    texto = _lineas(
        "Stock bajo en ApoloVibes",
        "Estos productos quedaron en stock bajo o agotado:",
        "",
        lista_texto,
        "",
        f"Revisar inventario: {enlace}",
        "",
        "Equipo de administración",
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
        + _parrafo(
            f"Tu cotización #{escapar(cotizacion.numero)} fue aprobada."
        )
        + tabla_detalle(
            [
                FilaDetalle("Material", cotizacion.material),
                FilaDetalle("Medidas", _medidas(cotizacion)),
                FilaDetalle("Uso", cotizacion.uso),
                FilaDetalle("Color", cotizacion.color),
                FilaDetalle(
                    "Precio",
                    formatear_pesos(cotizacion.precio)
                    if cotizacion.precio is not None
                    else "",
                ),
            ]
        )
        + _parrafo(
            "Para pagar, revisa los detalles en nuestra página:",
            centrado=True,
        )
        + boton("Mis Cotizaciones", enlace)
        + _parrafo(
            "Si tienes dudas, responde este correo.",
            margen="0",
            centrado=True,
        )
    )
    html = envolver(
        "¡Tu cotización fue aprobada!",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("check", frontend_url),
        pie="Equipo ApoloVibes",
    )

    texto = _lineas(
        f"Hola {cotizacion.nombre},",
        "",
        f"Tu cotización #{cotizacion.numero} fue aprobada.",
        "",
        _fila_texto("Material", cotizacion.material),
        _fila_texto("Medidas", _medidas(cotizacion)),
        _fila_texto("Uso", cotizacion.uso),
        _fila_texto("Color", cotizacion.color),
        _fila_texto(
            "Precio",
            formatear_pesos(cotizacion.precio)
            if cotizacion.precio is not None
            else "",
        ),
        "",
        "Para pagar, revisa los detalles en nuestra página:",
        enlace,
        "",
        "Si tienes dudas, responde este correo.",
        "",
        "Equipo ApoloVibes",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def cotizacion_rechazada(
    cotizacion: CotizacionCorreo, frontend_url: str | None = None
) -> Correo:
    """Correo al cliente cuando su cotización pasa a rechazada."""
    asunto = f"Tu cotización #{cotizacion.numero} fue rechazada"

    cuerpo_html = (
        _parrafo(f"Hola {escapar(cotizacion.nombre)},")
        + _parrafo(
            f"Tu cotización #{escapar(cotizacion.numero)} fue rechazada."
        )
        + _caja_panel(
            escapar("Puedes enviarnos una nueva solicitud cuando quieras.")
        )
    )
    html = envolver(
        "Tu cotización fue rechazada",
        cuerpo_html,
        frontend_url=frontend_url,
        icono=icono_html("equis", frontend_url),
        pie="Equipo ApoloVibes",
    )

    texto = _lineas(
        f"Hola {cotizacion.nombre},",
        "",
        f"Tu cotización #{cotizacion.numero} fue rechazada.",
        "",
        "Puedes enviarnos una nueva solicitud cuando quieras.",
        "",
        "Equipo ApoloVibes",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def codigo_verificacion(codigo: str) -> Correo:
    """Código de un solo uso para el gateway."""
    asunto = "Tu código de verificación — ApoloVibes"

    cuerpo_html = (
        caja_codigo(codigo)
        + _parrafo(
            "Este código tiene una vigencia limitada.",
            margen="0 0 8px",
            centrado=True,
        )
        + _parrafo(
            "Si no solicitaste este código, ignora este mensaje.",
            color=COLOR_MUTED,
            tamano=12,
            margen="0",
            centrado=True,
        )
    )
    html = envolver(
        "Tu código de verificación",
        cuerpo_html,
        icono=icono_html("escudo"),
        subtitulo="Tu código de verificación es:",
        pie="Equipo de seguridad",
    )

    texto = _lineas(
        "Tu código de verificación",
        "Tu código de verificación es:",
        codigo,
        "",
        "Este código tiene una vigencia limitada.",
        "Si no solicitaste este código, ignora este mensaje.",
        "",
        "Equipo de seguridad",
    )
    return Correo(asunto=asunto, html=html, texto=texto)


def alerta_seguridad(detalle: str) -> Correo:
    """Aviso de inicio de sesión para el gateway."""
    asunto = "Alerta de seguridad — ApoloVibes"

    enlace = f"{base_url()}/"

    cuerpo_html = (
        _parrafo(escapar(detalle), centrado=True)
        + _parrafo(
            "Si no fuiste tú, cambia tu contraseña de inmediato.",
            centrado=True,
        )
        + boton("Cambiar contraseña", enlace)
    )
    html = envolver(
        "Alerta de seguridad",
        cuerpo_html,
        icono=icono_html("escudo-alerta"),
        subtitulo="Detectamos actividad de seguridad en tu cuenta.",
        pie="Equipo de seguridad",
    )

    texto = _lineas(
        "Alerta de seguridad",
        "Detectamos actividad de seguridad en tu cuenta.",
        detalle,
        "Si no fuiste tú, cambia tu contraseña de inmediato.",
        "",
        "Equipo de seguridad",
    )
    return Correo(asunto=asunto, html=html, texto=texto)
