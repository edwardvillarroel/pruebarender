from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    ZONA_CHILE = ZoneInfo("America/Santiago")
except Exception:  
    ZONA_CHILE = timezone(timedelta(hours=-4))

FRONTEND_URL_POR_DEFECTO = "https://apolovibes3d.cl"


COLOR_SURFACE = "#121212"
COLOR_ACCENT = "#E8863E"
COLOR_WHITE = "#ffffff"
COLOR_PAGE = "#f6f7f9"
COLOR_PANEL = "#f6f7f9"
COLOR_TEXT = "#121212"
COLOR_MUTED = "#6b7280"
COLOR_BORDER = "#e5e7eb"
COLOR_GREEN = "#1fa855"
COLOR_RED = "#df1a0c"

# Color del borde del círculo por ícono: siempre coincide con el glifo.
ICONO_COLORES = {
    "check": COLOR_GREEN,
    "campana": COLOR_ACCENT,
    "lapiz": COLOR_ACCENT,
    "alerta": COLOR_ACCENT,
    "equis": COLOR_RED,
    "escudo": COLOR_ACCENT,
    "escudo-alerta": COLOR_ACCENT,
    "cubo": "#9ca3af",
}

FUENTE = "Arial,Helvetica,sans-serif"


def formatear_pesos(monto: int | float | None) -> str:
    if monto is None:
        return ""
    try:
        entero = int(monto)
    except (TypeError, ValueError):
        return str(monto)
    signo = "-" if entero < 0 else ""
    return f"{signo}${abs(entero):,}".replace(",", ".")


def formatear_fecha(fecha: datetime | None) -> str:
    if fecha is None:
        return ""
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(ZONA_CHILE).strftime("%d-%m-%Y %H:%M")


def escapar(valor: object) -> str:
    texto = "" if valor is None else str(valor)
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def base_url(frontend_url: str | None = None) -> str:
    return (frontend_url or FRONTEND_URL_POR_DEFECTO).rstrip("/")


def logo_html(frontend_url: str | None = None) -> str:
    """Bloque de marca del encabezado: wordmark y tagline."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'border="0" style="border-collapse:collapse;">'
        "<tr>"
        '<td align="left" style="text-align:left;'
        f'font-family:{FUENTE};font-size:27px;line-height:1.1;'
        'font-weight:800;color:#ffffff;letter-spacing:-0.02em;">'
        'ApoloVibes <span style="color:#E8863E;">3D</span>'
        "</td>"
        "</tr>"
        "<tr>"
        '<td align="left" style="padding-top:8px;text-align:left;'
        f'font-family:{FUENTE};font-size:11px;line-height:1.4;'
        'color:#d4d4d4;letter-spacing:0.03em;">'
        "Impulsando la creatividad con cada impresión."
        "</td>"
        "</tr>"
        "</table>"
    )


def icono_html(nombre: str, frontend_url: str | None = None) -> str:
    """Círculo blanco con el ícono del correo; el borde usa el color del glifo."""
    color = ICONO_COLORES.get(nombre, COLOR_ACCENT)
    imagen = f"{base_url(frontend_url)}/media/correo-icono-{nombre}.png"
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'border="0" align="center" '
        'style="border-collapse:separate;margin:24px auto 0;">'
        "<tr>"
        '<td width="56" height="56" align="center" valign="middle" '
        f'bgcolor="{COLOR_WHITE}" '
        'style="width:56px;height:56px;text-align:center;'
        'vertical-align:middle;padding:0;'
        f'background-color:{COLOR_WHITE};border:4px solid {color};'
        'border-radius:50%;">'
        f'<img src="{escapar(imagen)}" width="32" height="32" alt="" '
        'style="display:block;border:0;margin:0 auto;">'
        "</td>"
        "</tr>"
        "</table>"
    )


@dataclass
class FilaDetalle:
    etiqueta: str
    valor: object
    html: bool = False


def tabla_detalle(filas) -> str:
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
                    '<td width="48" valign="middle" '
                    f'style="width:48px;padding:12px 12px 12px 0;{separacion}">'
                    f'<img src="{escapar(imagen)}" alt="{escapar(item.nombre)}" '
                    'width="48" height="48" '
                    'style="display:block;width:48px;height:48px;border:0;'
                    'border-radius:8px;object-fit:cover;" />'
                    "</td>"
                )
            else:
                celdas.append(
                    '<td width="48" valign="middle" '
                    f'style="width:48px;padding:12px 12px 12px 0;{separacion}">'
                    "&nbsp;</td>"
                )
        celdas.append(
            '<td valign="middle" '
            f'style="padding:12px 0;{separacion}font-family:{FUENTE};">'
            f'<div style="font-size:14px;line-height:1.4;font-weight:bold;'
            f'color:{COLOR_TEXT};">{escapar(item.nombre)}</div>'
            "</td>"
        )
        celdas.append(
            '<td valign="middle" '
            f'style="padding:12px 8px;{separacion}font-family:{FUENTE};'
            f'font-size:13px;line-height:1.4;color:{COLOR_MUTED};'
            'white-space:nowrap;">'
            f"x{escapar(item.cantidad)}"
            "</td>"
        )
        celdas.append(
            '<td align="right" valign="middle" '
            f'style="padding:12px 0;text-align:right;{separacion}'
            f'font-family:{FUENTE};font-size:14px;line-height:1.4;'
            f'font-weight:bold;color:{COLOR_TEXT};">'
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


def seccion(titulo: str) -> str:
    """Etiqueta en negrita que separa bloques dentro del cuerpo."""
    return (
        '<div style="margin:18px 0 8px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:13px;line-height:1.4;font-weight:bold;color:{COLOR_TEXT};">'
        f"{escapar(titulo)}</div>"
    )


def tabla_stock(productos, frontend_url: str | None = None) -> str:
    """Lista de productos con su stock, con miniatura de cubo."""
    productos = list(productos)
    if not productos:
        return ""

    icono = f"{base_url(frontend_url)}/media/correo-icono-cubo.png"
    filas = []
    for indice, producto in enumerate(productos):
        separacion = (
            ""
            if indice == len(productos) - 1
            else f"border-bottom:1px solid {COLOR_BORDER};"
        )
        if producto.stock <= 0:
            stock = (
                '<div style="margin-top:2px;font-size:12px;line-height:1.4;'
                f'font-weight:bold;color:{COLOR_RED};">Agotado</div>'
            )
        else:
            stock = (
                '<div style="margin-top:2px;font-size:12px;line-height:1.4;'
                f'color:{COLOR_MUTED};">Stock: {escapar(producto.stock)} '
                f"(mín. {escapar(producto.stock_minimo)})</div>"
            )
        filas.append(
            "<tr>"
            '<td width="40" valign="middle" '
            f'style="width:40px;padding:10px 10px 10px 0;{separacion}">'
            '<table role="presentation" width="40" height="40" cellpadding="0" '
            'cellspacing="0" border="0" align="center" '
            f'bgcolor="{COLOR_PANEL}" '
            'style="width:40px;height:40px;border-collapse:separate;'
            f'background-color:{COLOR_PANEL};border-radius:8px;">'
            "<tr>"
            '<td align="center" valign="middle" '
            'style="width:40px;height:40px;text-align:center;'
            'vertical-align:middle;padding:0;">'
            f'<img src="{escapar(icono)}" width="22" height="22" alt="" '
            'style="display:block;border:0;">'
            "</td>"
            "</tr>"
            "</table>"
            "</td>"
            '<td valign="middle" '
            f'style="padding:10px 0;{separacion}font-family:{FUENTE};">'
            '<div style="font-size:14px;line-height:1.4;font-weight:bold;'
            f'color:{COLOR_TEXT};">{escapar(producto.nombre)}</div>'
            f"{stock}"
            "</td>"
            "</tr>"
        )

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;border-collapse:collapse;margin:4px 0 8px;">'
        f"<tbody>{''.join(filas)}</tbody>"
        "</table>"
    )


def tabla_totales(pedido) -> str:
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
            f'color:#9ca3af;letter-spacing:.04em;">{marca}</div>'
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
    pie: str = "Equipo ApoloVibes",
) -> str:
    base = base_url(frontend_url)
    mascota = f"{base}/media/apolo-vibes-logo.png"
    onda_header = f"{base}/media/correo-onda-header.png"
    onda_footer = f"{base}/media/correo-onda-footer.png"

    titulo_html = escapar(titulo)
    subtitulo_html = escapar(subtitulo) if subtitulo else ""
    bloque_icono = icono or ""
    bloque_subtitulo = (
        f'<p style="margin:8px 0 0;text-align:center;font-family:{FUENTE};'
        f'font-size:14px;line-height:1.5;color:{COLOR_MUTED};">'
        f"{subtitulo_html}</p>"
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
        f'background-color:{COLOR_WHITE};border-radius:18px;overflow:hidden;">'
        "<tr>"
        '<td '
        f'bgcolor="{COLOR_SURFACE}" '
        f'style="padding:0;background-color:{COLOR_SURFACE};">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;border-collapse:collapse;">'
        "<tr>"
        '<td align="left" valign="top" '
        'style="padding:34px 0 16px 32px;text-align:left;vertical-align:top;">'
        f"{logo_html(frontend_url)}"
        "</td>"
        '<td align="right" valign="bottom" '
        'style="padding:16px 32px 0 0;text-align:right;vertical-align:bottom;">'
        f'<img src="{escapar(mascota)}" width="96" height="110" '
        'alt="ApoloVibes" '
        'style="display:block;width:96px;height:110px;border:0;">'
        "</td>"
        "</tr>"
        "</table>"
        "</td>"
        "</tr>"
        "<tr>"
        '<td '
        f'bgcolor="{COLOR_SURFACE}" '
        'style="padding:0;font-size:0;line-height:0;'
        f'background-color:{COLOR_SURFACE};">'
        f'<img src="{escapar(onda_header)}" width="600" height="36" alt="" '
        'style="display:block;width:100%;height:36px;border:0;">'
        "</td>"
        "</tr>"
        "<tr>"
        '<td style="padding:0 32px 30px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;line-height:1.5;color:{COLOR_TEXT};">'
        f"{bloque_icono}"
        '<h1 style="margin:18px 0 0;text-align:center;font-family:Arial,'
        f'Helvetica,sans-serif;font-size:24px;line-height:1.25;'
        f'font-weight:800;color:{COLOR_TEXT};">{titulo_html}</h1>'
        f"{bloque_subtitulo}"
        f"{cuerpo_html}"
        "</td>"
        "</tr>"
        "<tr>"
        '<td '
        f'bgcolor="{COLOR_SURFACE}" '
        'style="padding:0;font-size:0;line-height:0;'
        f'background-color:{COLOR_SURFACE};">'
        f'<img src="{escapar(onda_footer)}" width="600" height="36" alt="" '
        'style="display:block;width:100%;height:36px;border:0;">'
        "</td>"
        "</tr>"
        "<tr>"
        '<td align="center" '
        f'bgcolor="{COLOR_SURFACE}" '
        f'style="padding:20px 24px 26px;background-color:{COLOR_SURFACE};'
        'text-align:center;">'
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
    return "\n".join(
        f"{item.cantidad}x {item.nombre}: {formatear_pesos(item.subtotal)}"
        for item in items
    )


def descuentos_texto(descuentos) -> str:
    return "\n".join(
        f"{descuento.etiqueta}: - {formatear_pesos(abs(descuento.monto))}"
        for descuento in descuentos
    )
