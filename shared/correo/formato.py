"""Formato y utilidades de presentación para los correos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    ZONA_CHILE = ZoneInfo("America/Santiago")
except Exception:  # pragma: no cover - depende del sistema operativo
    ZONA_CHILE = timezone(timedelta(hours=-4))


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


def envolver(titulo: str, cuerpo_html: str) -> str:
    """Envuelve el cuerpo del correo en un contenedor simple y legible."""
    return (
        '<div style="max-width:600px;margin:0 auto;padding:24px;'
        'font-family:Arial,Helvetica,sans-serif;color:#1f2937;'
        'font-size:15px;line-height:1.6">'
        f'<h1 style="font-size:20px;margin:0 0 16px">{escapar(titulo)}</h1>'
        f"{cuerpo_html}"
        '<p style="margin-top:24px;color:#6b7280;font-size:12px">'
        "ApoloVibes · Impresión 3D</p>"
        "</div>"
    )


def tabla_items(items) -> str:
    """Tabla HTML con los productos del pedido."""
    filas = []
    for item in items:
        filas.append(
            "<tr>"
            f'<td style="padding:6px 0">{escapar(item.nombre)}</td>'
            f'<td style="padding:6px 0;text-align:center">{item.cantidad}</td>'
            f'<td style="padding:6px 0;text-align:right">'
            f"{formatear_pesos(item.subtotal)}</td>"
            "</tr>"
        )
    return (
        '<table style="width:100%;border-collapse:collapse;margin:12px 0">'
        '<thead><tr style="border-bottom:1px solid #e5e7eb">'
        '<th style="text-align:left;padding:6px 0">Producto</th>'
        '<th style="text-align:center;padding:6px 0">Cantidad</th>'
        '<th style="text-align:right;padding:6px 0">Subtotal</th>'
        "</tr></thead>"
        f"<tbody>{''.join(filas)}</tbody>"
        "</table>"
    )


def tabla_descuentos(descuentos) -> str:
    """Tabla HTML con los descuentos aplicados, o vacío si no hay."""
    if not descuentos:
        return ""
    filas = []
    for descuento in descuentos:
        filas.append(
            "<tr>"
            f'<td style="padding:4px 0">{escapar(descuento.etiqueta)}</td>'
            f'<td style="padding:4px 0;text-align:right">'
            f"- {formatear_pesos(abs(descuento.monto))}</td>"
            "</tr>"
        )
    return (
        '<table style="width:100%;border-collapse:collapse;margin:8px 0">'
        f"<tbody>{''.join(filas)}</tbody>"
        "</table>"
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
