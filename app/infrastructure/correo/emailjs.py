
from __future__ import annotations
import html
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any
import httpx

from app.domain.entities.pedido import Pedido
from app.domain.interfaces.correo import ErrorEnvioCorreo, ServicioCorreo

EMAILJS_URL = "https://api.emailjs.com/api/v1.0/email/send"
TIMEOUT_SEGUNDOS = 15
REINTENTOS = 1
ESPERA_REINTENTO_SEGUNDOS = 0.4
_ETIQUETA_ESTADO_PAGO = {
    "completado": "Pagado",
}

_ETIQUETA_ENTREGA = {
    "envio": "Envío a domicilio",
    "retiro": "Retiro",
}

_ZONA_CHILE = ZoneInfo("America/Santiago")


class EmailJsCorreo(ServicioCorreo):
    def __init__(self, config: dict[str, Any]) -> None:
        self._public_key = str(config.get("EMAILJS_PUBLIC_KEY") or "").strip()
        self._private_key = str(config.get("EMAILJS_PRIVATE_KEY") or "").strip()
        self._service_id = str(config.get("EMAILJS_SERVICE_ID") or "").strip()
        self._template_id = str(config.get("EMAILJS_TEMPLATE_COMPROBANTE") or "").strip()

    @property
    def configurado(self) -> bool:
        """True cuando hay credenciales suficientes para un envio real."""
        return bool(self._public_key and self._private_key and self._service_id and self._template_id)

    def enviar_comprobante_pedido(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        """Envia el comprobante, o lo imprime en consola si no hay credenciales."""
        if not self.configurado:
            self._imprimir_en_consola(pedido, cliente_email, estado_pago)
            return

        payload = {
            "service_id": self._service_id,
            "template_id": self._template_id,
            "user_id": self._public_key,
            "accessToken": self._private_key,
            "template_params": _parametros_comprobante(pedido, cliente_email, estado_pago),
        }

        for intento in range(REINTENTOS + 1):
            try:
                respuesta = httpx.post(EMAILJS_URL, json=payload, timeout=TIMEOUT_SEGUNDOS)
            except httpx.HTTPError as error:
                if intento < REINTENTOS:
                    time.sleep(ESPERA_REINTENTO_SEGUNDOS)
                    continue
                raise ErrorEnvioCorreo(
                    f"Error de red al enviar el comprobante: {error}"
                ) from error

            if respuesta.status_code < 400:
                return

            if 400 <= respuesta.status_code < 500 or intento >= REINTENTOS:
                raise ErrorEnvioCorreo(
                    f"EmailJS respondió {respuesta.status_code}: {respuesta.text[:300]}"
                )
            time.sleep(ESPERA_REINTENTO_SEGUNDOS)

    @staticmethod
    def _imprimir_en_consola(pedido: Pedido, cliente_email: str, estado_pago: str) -> None:
        print("[correo:simulacion] Comprobante de pedido (EmailJS sin credenciales)")
        print(f"[correo:simulacion]   para: {cliente_email}")
        for linea in _parametros_comprobante(pedido, cliente_email, estado_pago).items():
            print(f"[correo:simulacion]   {linea[0]}: {linea[1]}")


def _parametros_comprobante(
    pedido: Pedido, cliente_email: str, estado_pago: str
) -> dict[str, str]:
    items = _items_en_tabla(pedido)
    fecha = _formatear_fecha(pedido.creado_en)
    return {
        "to_email": cliente_email,
        "pedido_id": str(pedido.id)[:8],
        "estado": _ETIQUETA_ESTADO_PAGO.get(estado_pago, estado_pago),
        "total": _formatear_pesos(pedido.total),
        "entrega": _ETIQUETA_ENTREGA.get(pedido.entrega, pedido.entrega),
        "items": items,
        "fecha": fecha,
    }


def _items_en_tabla(pedido: Pedido) -> str:
    borde = "border-bottom:1px solid #e8eef4;"
    encabezado = (
        "<tr>"
        f'<th align="left" style="padding:4px 0;{borde}color:#888;font-weight:normal;">Nombre</th>'
        f'<th align="center" style="padding:4px 8px;{borde}color:#888;font-weight:normal;">Cant.</th>'
        f'<th align="right" style="padding:4px 0;{borde}color:#888;font-weight:normal;">Subtotal</th>'
        "</tr>"
    )
    filas = "".join(
        "<tr>"
        f'<td style="padding:7px 0;{borde}">'
        f'{html.escape(d.nombre or "Producto")}</td>'
        f'<td align="center" style="padding:7px 8px;{borde}">{d.cantidad}</td>'
        f'<td align="right" style="padding:7px 0;{borde}">'
        f"{_formatear_pesos(d.precio_unitario * d.cantidad)}</td>"
        "</tr>"
        for d in pedido.detalles
    )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;font-size:13px;color:#2c3e50;">'
        f"{encabezado}{filas}</table>"
    )


def _formatear_fecha(creado_en: datetime | None) -> str:
    """`pedido.creado_en` llega en UTC; el comprobante lo muestra en hora de Chile."""
    if creado_en is None:
        return ""
    if creado_en.tzinfo is None:
        creado_en = creado_en.replace(tzinfo=timezone.utc)
    return creado_en.astimezone(_ZONA_CHILE).strftime("%d/%m/%Y %H:%M")


def _formatear_pesos(monto: int | float | str | None) -> str:
    try:
        entero = int(monto)
    except (TypeError, ValueError):
        return str(monto) if monto is not None else ""
    return f"${entero:,}".replace(",", ".")