"""Envío de correos del backend vía la REST API de EmailJS.

Espejo de `gateway/infrastructure/correo.py`, con una diferencia DELIBERADA: el
gateway, sin credenciales, no hace nada (sus correos son de seguridad y el
simulacion imprime el codigo por consola); acá, sin credenciales, el contenido
se imprime en consola del backend. El comprobante de un pedido es un correo que
el cliente ya le prometimos ("Te enviamos el comprobante a tu correo"), asi que
en desarrollo tiene que quedar a la vista para poder verificarlo.

Aun asi, la ausencia de credenciales NO es un error: el flujo de pago no puede
depender de que haya un proveedor de correo configurado.

Para pasar de MODO SIMULACION a envio real, completar en `.env`:
    EMAILJS_PUBLIC_KEY, EMAILJS_PRIVATE_KEY, EMAILJS_SERVICE_ID,
    EMAILJS_TEMPLATE_COMPROBANTE

Y en el dashboard de EmailJS:
- La plantilla usa las variables `{{to_email}}`, `{{pedido_id}}`, `{{estado}}`,
  `{{total}}`, `{{entrega}}`, `{{items}}` y `{{fecha}}`.
- Activar "Allow API for non-browser applications" (llamadas desde el servidor).
- Si esta habilitado "Use Private Key", el campo `accessToken` es obligatorio.
- `{{estado}}` es el estado del PAGO ("Pagado"), NO `pedido.estado`. Mandar el
  estado del envío ahí producia un comprobante que decía "Estado: pendiente"
  debajo de "¡Gracias por tu compra!", que se lee como "mi pago quedo pendiente".
"""

from __future__ import annotations
import time
from typing import Any
import httpx

from app.domain.entities.pedido import Pedido
from app.domain.interfaces.correo import ErrorEnvioCorreo, ServicioCorreo

EMAILJS_URL = "https://api.emailjs.com/api/v1.0/email/send"
TIMEOUT_SEGUNDOS = 15
# Un solo reintento, con espera corta. El pago YA esta confirmado cuando se
# manda este correo, asi que la red caida es el unico motivo realista de fallo
# y vale la pena insistir una vez. Mas reintentos se traduce en minutos de
# latencia en un request que la pasarela espera de forma sincronica.
REINTENTOS = 1
ESPERA_REINTENTO_SEGUNDOS = 0.4

# Etiquetas legibles del estado del pago. `{{estado}}` va escrito a mano porque
# la plantilla es HTML y no interpola operadores: no hay forma de que "pagado"
# se vea solo.
_ETIQUETA_ESTADO_PAGO = {
    "completado": "Pagado",
}


class EmailJsCorreo(ServicioCorreo):
    """Envía el comprobante de un pedido con la plantilla de EmailJS.

    Recibe la configuracion ya resuelta (un dict) en vez de leer `app.config`:
    el `Config` del backend es el de `app/config.py` y asi el adaptador queda
    testeable sin levantar la app.
    """

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
                # Un error de red se reintenta; un 4xx de EmailJS (credencial
                # mala, plantilla inexistente) no mejora con otra llamada, asi
                # que sale temprano en vez de gastar el reintento.
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
        """MODO SIMULACION: deja el comprobante a la vista sin enviarlo.

        Imprime el destino y los datos, nunca la `direccion_envio` completa: esa
        columna es texto crudo con datos personales del cliente y no tiene por
        que aparecer en un log.
        """
        print("[correo:simulacion] Comprobante de pedido (EmailJS sin credenciales)")
        print(f"[correo:simulacion]   para: {cliente_email}")
        for linea in _parametros_comprobante(pedido, cliente_email, estado_pago).items():
            print(f"[correo:simulacion]   {linea[0]}: {linea[1]}")


def _parametros_comprobante(
    pedido: Pedido, cliente_email: str, estado_pago: str
) -> dict[str, str]:
    """Arma las variables de la plantilla del comprobante.

    `items` va como texto plano porque EmailJS solo interpola strings. Usa el
    `nombre` snapshot de la linea: para eso existe, y un comprobante que cambia
    de texto si el admin renombra el producto no es un comprobante.

    `estado` es el estado del PAGO. El del pedido (`pedido.estado`) describe el
    envio y va a "Mis pedidos"/panel admin; en un comprobante de compra es
    informacion que confunde. Un estado desconocido se pasa tal cual en vez de
    inventar una etiqueta: si mañana llega `reembolsado`, el correo lo dice.
    """
    items = "\n".join(
        f"{d.nombre or 'producto'} x{d.cantidad} @ {_formatear_pesos(d.precio_unitario)}"
        for d in pedido.detalles
    )
    fecha = pedido.creado_en.isoformat() if pedido.creado_en else ""
    return {
        "to_email": cliente_email,
        "pedido_id": str(pedido.id),
        "estado": _ETIQUETA_ESTADO_PAGO.get(estado_pago, estado_pago),
        "total": _formatear_pesos(pedido.total),
        "entrega": pedido.entrega,
        "items": items,
        "fecha": fecha,
    }


def _formatear_pesos(monto: int | float | str | None) -> str:
    """`10990` -> `"$10.990"`.

    El formato va en el backend y no en la plantilla por dos razones: la
    plantilla es HTML y no puede hacer aritmetica, y el separador de miles
    chileno (".") es ambiguo para quien lea la plantilla sin contexto. Mandar
    `"10990"` pelado obligaba a la plantilla a saber de formato chileno.
    """
    try:
        entero = int(monto)
    except (TypeError, ValueError):
        return str(monto) if monto is not None else ""
    return f"${entero:,}".replace(",", ".")