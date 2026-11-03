"""Formato y utilidades de presentación para los correos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    ZONA_CHILE = ZoneInfo("America/Santiago")
except Exception:  # pragma: no cover - depende del sistema operativo
    ZONA_CHILE = timezone(timedelta(hours=-4))

FRONTEND_URL_POR_DEFECTO = "https://apolovibes3d.cl"

# Reflejo de --surface y --accent del frontend (ApoloVibes-frontend/src/styles/global.css)
COLOR_SURFACE = "#002A5E"
COLOR_ACCENT = "#E8863E"
COLOR_WHITE = "#ffffff"
COLOR_PAGE = "#f3f4f6"
COLOR_PANEL = "#f6f7f9"
COLOR_TEXT = "#1f2937"
COLOR_MUTED = "#6b7280"
COLOR_BORDER = "#e5e7eb"
COLOR_GREEN = "#1fa855"
COLOR_RED = "#df1a0c"

FUENTE = "Arial,Helvetica,sans-serif"


def formatear_pesos(monto: int | float | None) -> str:
    """Devuelve un monto en pesos chilenos, por ejemplo ``$3.500``."""
    if monto is None:
        return ""
    try:
        entero = int(monto)
    except (TypeError, ValueError):
        return str(monto)
    signo = "-" if entero < 0 else ""
    return f"{signo}${abs(entero):,}".replace(",", ".")


def formatear_fecha(fecha: datetime | None) -> str:
    """Formatea una fecha en horario de Chile con formato ``dd-mm-AAAA HH:MM``."""
    if fecha is None:
        return ""
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(ZONA_CHILE).strftime("%d-%m-%Y %H:%M")


def escapar(valor: object) -> str:
    """Escapa texto para insertarlo en HTML."""
    texto = "" if valor is None else str(valor)
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def base_url(frontend_url: str | None = None) -> str:
    """Devuelve la URL base del frontend, sin barra final."""
    return (frontend_url or FRONTEND_URL_POR_DEFECTO).rstrip("/")


def logo_html(frontend_url: str | None = None) -> str:
    """Logo dentro de un círculo blanco con anillo accent.

    Usa el PNG como ``src`` para Outlook y el WebP como ``srcset`` para los
    clientes modernos.
    """
    base = base_url(frontend_url)
    webp = f"{base}/media/apolo-vibes-logo.webp"
    png = f"{base}/media/apolo-vibes-logo.png"
    return (
        '<table role="presentation" width="96" cellpadding="0" cellspacing="0" '
        'border="0" align="center" style="border-collapse:collapse;">'
        "<tr>"
        '<td width="96" height="96" align="center" valign="middle" '
        f'bgcolor="{COLOR_WHITE}" '
        f'style="width:96px;height:96px;background-color:{COLOR_WHITE};'
        f'border:3px solid {COLOR_ACCENT};border-radius:48px;'
        'text-align:center;vertical-align:middle;">'
        f'<img src="{escapar(png)}" srcset="{escapar(webp)}" '
        'alt="ApoloVibes" width="64" height="72" '
        'style="display:block;width:64px;height:72px;border:0;'
        'outline:none;text-decoration:none;" />'
        "</td>"
        "</tr>"
        "</table>"
    )


def icono_html(simbolo: str, color: str, borde: str = COLOR_ACCENT) -> str:
    """Círculo blanco con un glifo de texto centrado."""
    return (
        '<table role="presentation" width="56" cellpadding="0" cellspacing="0" '
        'border="0" align="center" style="border-collapse:collapse;">'
        "<tr>"
        '<td width="56" height="56" align="center" valign="middle" '
        f'bgcolor="{COLOR_WHITE}" '
        f'style="width:56px;height:56px;background-color:{COLOR_WHITE};'
        f'border:2px solid {borde};border-radius:28px;'
        f'text-align:center;vertical-align:middle;font-family:{FUENTE};'
        f'font-size:26px;font-weight:bold;line-height:52px;color:{color};">'
        f"{escapar(simbolo)}"
        "</td>"
        "</tr>"
        "</table>"
    )


@dataclass
class FilaDetalle:
    """Una fila de la tabla de detalles."""

    etiqueta: str
    valor: object
    html: bool = False


def tabla_detalle(filas) -> str:
    """Tabla de filas grises redondeadas con etiqueta a la izquierda."""
    visibles = [
        fila
        for fila in filas
        if fila is not None and fila.valor is not None and fila.valor != ""
    ]
    if not visibles:
        return ""

    celdas = []
    for indice, fila in enumerate(visibles):
        valor = fila.valor if fila.html else escapar(fila.valor)
        separacion = "" if indice == len(visibles) - 1 else "padding-bottom:6px;"
        celdas.append(
            f'<tr><td style="{separacion}">'
            '<table role="presentation" width="100%" cellpadding="0" '
            'cellspacing="0" border="0" '
            f'bgcolor="{COLOR_PANEL}" '
            f'style="width:100%;border-collapse:collapse;'
            f'background-color:{COLOR_PANEL};border-radius:8px;">'
            "<tr>"
            '<td width="46%" valign="top" '
            'style="padding:10px 14px;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:13px;line-height:1.5;font-weight:bold;color:{COLOR_TEXT};">'
            f"{escapar(fila.etiqueta)}"
            "</td>"
            '<td align="right" valign="top" '
            'style="padding:10px 14px;font-family:Arial,Helvetica,sans-serif;'
            'font-size:13px;line-height:1.5;'
            f'color:{COLOR_TEXT};text-align:right;word-break:break-word;">'
            f"{valor}"
            "</td>"
            "</tr>"
            "</table>"
            "</td></tr>"
        )

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;border-collapse:collapse;margin:4px 0 12px;">'
        f"<tbody>{''.join(celdas)}</tbody>"
        "</table>"
    )


def _url_imagen(valor: object, frontend_url: str | None) -> str:
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        return ""
    if texto.startswith("//"):
        return f"https:{texto}"
    if texto.startswith(("http://", "https://")):
        return texto
    return f"{base_url(frontend_url)}/{texto.lstrip('/')}"


def tabla_items(items, frontend_url: str | None = None) -> str:
    """Tabla de productos con miniatura opcional y subtotal alineado a la derecha."""
    items = list(items)
    if not items:
        return ""

    imagenes = [_url_imagen(getattr(item, "imagen", None), frontend_url) for item in items]
    hay_imagenes = any(imagenes)

    filas = []
    for indice, (item, imagen) in enumerate(zip(items, imagenes)):
        separacion = (
            "" if indice == len(items) - 1 else f"border-bottom:1px solid {COLOR_BORDER};"
        )
        celdas = []
        if hay_imagenes:
            if imagen:
                celdas.append(
                    '<td width="48" valign="top" '
                    f'style="width:48px;padding:12px 12px 12px 0;{separacion}">'
                    f'<img src="{escapar(imagen)}" alt="{escapar(item.nombre)}" '
                    'width="48" height="48" '
                    'style="display:block;width:48px;height:48px;border:0;'
                    'border-radius:8px;object-fit:cover;" />'
                    "</td>"
                )
            else:
                celdas.append(
                    '<td width="48" valign="top" '
                    f'style="width:48px;padding:12px 12px 12px 0;{separacion}">'
                    "&nbsp;</td>"
                )
        celdas.append(
            '<td valign="top" '
            f'style="padding:12px 0;{separacion}'
            'font-family:Arial,Helvetica,sans-serif;">'
            f'<div style="font-size:14px;line-height:1.5;font-weight:bold;'
            f'color:{COLOR_TEXT};">{escapar(item.nombre)}</div>'
            f'<div style="font-size:12px;line-height:1.5;color:{COLOR_MUTED};">'
            f"Cantidad: {escapar(item.cantidad)}</div>"
            "</td>"
        )
        celdas.append(
            '<td align="right" valign="top" '
            f'style="padding:12px 0;text-align:right;{separacion}'
            'font-family:Arial,Helvetica,sans-serif;font-size:14px;'
            f'line-height:1.5;font-weight:bold;color:{COLOR_TEXT};">'
            f"{escapar(formatear_pesos(item.subtotal))}"
            "</td>"
        )
        filas.append(f"<tr>{''.join(celdas)}</tr>")

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;border-collapse:collapse;margin:4px 0 8px;">'
        f"<tbody>{''.join(filas)}</tbody>"
        "</table>"
    )


def tabla_totales(pedido) -> str:
    """Caja gris redondeada con subtotal, descuentos, envío y total."""
    filas = [
        (
            "Subtotal",
            formatear_pesos(pedido.subtotal),
        )
    ]

    descuentos = list(getattr(pedido, "descuentos", None) or [])
    if descuentos:
        for descuento in descuentos:
            filas.append(
                (
                    descuento.etiqueta,
                    f"- {formatear_pesos(abs(descuento.monto))}",
                )
            )
    elif pedido.descuento_total:
        filas.append(
            (
                "Descuentos",
                f"- {formatear_pesos(abs(pedido.descuento_total))}",
            )
        )

    if pedido.costo_envio > 0:
        filas.append(("Envío", formatear_pesos(pedido.costo_envio)))
    elif pedido.tipo_entrega == "Envío a domicilio":
        filas.append(("Envío", "Gratis"))

    celdas = "".join(
        "<tr>"
        '<td style="padding:9px 16px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:14px;line-height:1.5;color:{COLOR_MUTED};">'
        f"{escapar(etiqueta)}"
        "</td>"
        '<td align="right" style="padding:9px 16px;'
        'font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;'
        f'font-weight:bold;color:{COLOR_TEXT};text-align:right;">'
        f"{escapar(valor)}"
        "</td>"
        "</tr>"
        for etiqueta, valor in filas
    )

    total = (
        "<tr>"
        f'<td colspan="2" bgcolor="{COLOR_ACCENT}" '
        f'style="padding:0;background-color:{COLOR_ACCENT};'
        'border-radius:0 0 12px 12px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;border-collapse:collapse;">'
        "<tr>"
        '<td style="padding:13px 16px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;line-height:1.5;font-weight:bold;color:{COLOR_WHITE};">'
        "Total"
        "</td>"
        '<td align="right" style="padding:13px 16px;'
        'font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;'
        f'font-weight:bold;color:{COLOR_WHITE};text-align:right;">'
        f"{escapar(formatear_pesos(pedido.total))}"
        "</td>"
        "</tr>"
        "</table>"
        "</td>"
        "</tr>"
    )

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" '
        f'bgcolor="{COLOR_PANEL}" '
        f'style="width:100%;border-collapse:collapse;background-color:{COLOR_PANEL};'
        'border-radius:12px;margin:12px 0 0;">'
        f"<tbody>{celdas}{total}</tbody>"
        "</table>"
    )


def tabla_descuentos(descuentos) -> str:
    """Tabla HTML con los descuentos aplicados, o vacío si no hay."""
    if not descuentos:
        return ""
    filas = "".join(
        "<tr>"
        '<td style="padding:9px 16px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:14px;line-height:1.5;color:{COLOR_MUTED};">'
        f"{escapar(descuento.etiqueta)}"
        "</td>"
        '<td align="right" style="padding:9px 16px;'
        'font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;'
        f'font-weight:bold;color:{COLOR_TEXT};text-align:right;">'
        f"- {escapar(formatear_pesos(abs(descuento.monto)))}"
        "</td>"
        "</tr>"
        for descuento in descuentos
    )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" '
        f'bgcolor="{COLOR_PANEL}" '
        f'style="width:100%;border-collapse:collapse;background-color:{COLOR_PANEL};'
        'border-radius:12px;margin:8px 0;">'
        f"<tbody>{filas}</tbody>"
        "</table>"
    )


def boton(texto: str, url: str) -> str:
    """Botón redondeado accent con texto blanco y flecha."""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;border-collapse:collapse;margin:8px 0 18px;">'
        '<tr><td align="center" style="text-align:center;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'align="center" style="border-collapse:collapse;">'
        "<tr>"
        f'<td align="center" bgcolor="{COLOR_ACCENT}" '
        f'style="background-color:{COLOR_ACCENT};border-radius:10px;'
        'text-align:center;">'
        f'<a href="{escapar(url)}" '
        'style="display:inline-block;padding:14px 28px;'
        f'font-family:{FUENTE};font-size:15px;line-height:1.2;font-weight:bold;'
        f'color:{COLOR_WHITE};text-decoration:none;border-radius:10px;'
        'mso-padding-alt:14px 28px;">'
        f"{escapar(texto)} →"
        "</a>"
        "</td>"
        "</tr>"
        "</table>"
        "</td></tr>"
        "</table>"
    )


def caja_codigo(codigo: str) -> str:
    """Caja grande y centrada para mostrar un código."""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" '
        f'bgcolor="{COLOR_PANEL}" '
        f'style="width:100%;border-collapse:collapse;background-color:{COLOR_PANEL};'
        'border-radius:10px;margin:8px 0 16px;">'
        "<tr>"
        '<td align="center" style="padding:20px 16px;text-align:center;'
        "font-family:'Courier New',Courier,monospace;font-size:32px;"
        f'line-height:1.3;font-weight:bold;letter-spacing:8px;color:{COLOR_SURFACE};'
        'word-break:break-all;">'
        f"{escapar(codigo)}"
        "</td>"
        "</tr>"
        "</table>"
    )


def _pie_html(pie: str) -> str:
    marca = "ApoloVibes 3D"
    pie_texto = "" if pie is None else str(pie)
    lineas = []
    if pie_texto and pie_texto != marca:
        lineas.append(
            f'<div style="font-family:{FUENTE};font-size:13px;line-height:1.5;'
            f'font-weight:bold;color:{COLOR_WHITE};margin:0 0 4px;">'
            f"{escapar(pie_texto)}</div>"
        )
        lineas.append(
            f'<div style="font-family:{FUENTE};font-size:11px;line-height:1.5;'
            f'color:#dbe3ef;letter-spacing:.04em;">{marca}</div>'
        )
    else:
        lineas.append(
            f'<div style="font-family:{FUENTE};font-size:13px;line-height:1.5;'
            f'font-weight:bold;color:{COLOR_WHITE};letter-spacing:.04em;">'
            f"{marca}</div>"
        )
    return "".join(lineas)


def envolver(
    titulo: str,
    cuerpo_html: str,
    *,
    frontend_url: str | None = None,
    icono: str | None = None,
    subtitulo: str = "",
    pie: str = "Equipo ApoloVibes ♥",
) -> str:
    """Envuelve el cuerpo en la tarjeta de correo transaccional."""
    titulo_html = escapar(titulo)
    subtitulo_html = escapar(subtitulo) if subtitulo else ""
    bloque_icono = (
        f'<tr><td align="center" style="padding:16px 24px 0;">{icono}</td></tr>'
        if icono
        else ""
    )
    bloque_subtitulo = (
        f'<p style="margin:8px 0 0;font-family:{FUENTE};font-size:15px;'
        f'line-height:1.6;color:{COLOR_MUTED};">{subtitulo_html}</p>'
        if subtitulo_html
        else ""
    )

    return (
        "<!DOCTYPE html>"
        '<html lang="es">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        f"<title>{titulo_html}</title>"
        "</head>"
        f'<body bgcolor="{COLOR_PAGE}" style="margin:0;padding:0;'
        f'background-color:{COLOR_PAGE};font-family:{FUENTE};color:{COLOR_TEXT};">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" '
        f'bgcolor="{COLOR_PAGE}" '
        f'style="width:100%;border-collapse:collapse;background-color:{COLOR_PAGE};">'
        "<tr>"
        '<td align="center" style="padding:32px 12px;">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'border="0" align="center" '
        'style="width:100%;max-width:600px;border-collapse:separate;'
        f'background-color:{COLOR_WHITE};border-radius:16px;">'
        "<tr>"
        '<td align="center" '
        f'bgcolor="{COLOR_SURFACE}" '
        f'style="padding:30px 24px 22px;background-color:{COLOR_SURFACE};'
        'border-radius:16px 16px 0 0;text-align:center;">'
        f"{logo_html(frontend_url)}"
        "</td>"
        "</tr>"
        "<tr>"
        '<td height="14" '
        f'bgcolor="{COLOR_ACCENT}" '
        f'style="height:14px;line-height:14px;font-size:0;'
        f'background-color:{COLOR_ACCENT};border-radius:0 0 14px 14px;">'
        "&nbsp;</td>"
        "</tr>"
        '<tr><td height="8" style="height:8px;line-height:8px;font-size:0;">'
        "&nbsp;</td></tr>"
        f"{bloque_icono}"
        "<tr>"
        '<td align="center" style="padding:18px 40px 0;text-align:center;">'
        f'<h1 style="margin:0;font-family:{FUENTE};font-size:24px;line-height:1.3;'
        f'font-weight:bold;color:{COLOR_TEXT};">{titulo_html}</h1>'
        f"{bloque_subtitulo}"
        "</td>"
        "</tr>"
        "<tr>"
        '<td style="padding:20px 40px 32px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;line-height:1.6;color:{COLOR_TEXT};">'
        f"{cuerpo_html}"
        "</td>"
        "</tr>"
        '<tr><td height="28" style="height:28px;line-height:28px;font-size:0;">'
        "&nbsp;</td></tr>"
        "<tr>"
        '<td height="14" '
        f'bgcolor="{COLOR_SURFACE}" '
        f'style="height:14px;line-height:14px;font-size:0;'
        f'background-color:{COLOR_SURFACE};border-radius:14px 14px 0 0;">'
        "&nbsp;</td>"
        "</tr>"
        "<tr>"
        '<td align="center" '
        f'bgcolor="{COLOR_SURFACE}" '
        f'style="padding:18px 24px 24px;background-color:{COLOR_SURFACE};'
        'border-radius:0 0 16px 16px;text-align:center;">'
        f"{_pie_html(pie)}"
        "</td>"
        "</tr>"
        "</table>"
        "</td>"
        "</tr>"
        "</table>"
        "</body>"
        "</html>"
    )


def items_texto(items) -> str:
    """Lista de productos en texto plano."""
    return "\n".join(
        f"{item.cantidad}x {item.nombre}: {formatear_pesos(item.subtotal)}"
        for item in items
    )


def descuentos_texto(descuentos) -> str:
    """Lista de descuentos en texto plano."""
    return "\n".join(
        f"{descuento.etiqueta}: - {formatear_pesos(abs(descuento.monto))}"
        for descuento in descuentos
    )
