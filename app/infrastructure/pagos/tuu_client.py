"""Cliente de la pasarela TUU (Pago Online de Haulmer).

Implementa la interfaz `PasarelaPago` del dominio. Toda la comunicación con el
proveedor externo (HTTP más firma HMAC-SHA256) queda en infraestructura; la
capa de aplicación solo conoce `SolicitudPago`/`ResultadoIntentoPago`.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

from app.domain.interfaces.pasarela_pago import (
    ErrorPasarela,
    PasarelaPago,
    ResultadoIntentoPago,
    SolicitudPago,
)


class TuuCliente(PasarelaPago):
    """Cliente real de TUU. Se configura desde el punto de composición."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._account_id = config["TUU_ACCOUNT_ID"]
        self._secret_key = config["TUU_SECRET_KEY"]
        self._api_url = config["TUU_API_URL"]
        self._shop_name = config["TUU_SHOP_NAME"]
        self._url_callback = config["TUU_URL_CALLBACK"]
        self._url_complete = config["TUU_URL_COMPLETE"]
        self._url_cancel = config["TUU_URL_CANCEL"]
        self._timeout = config.get("TUU_TIMEOUT", 15)

    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        parametros = self._construir_payload(solicitud)
        try:
            respuesta = httpx.post(
                self._api_url,
                json=parametros,
                headers={
                    "X-REDIRECT": "false",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
        except httpx.HTTPError as exc:
            raise ErrorPasarela(
                f"No se pudo contactar a la pasarela de pagos: {exc}"
            ) from exc
        except ValueError:
            datos = None
        url = self._extraer_url(datos)
        if not url:
            cuerpo = respuesta.text.strip()
            if cuerpo.startswith("http://") or cuerpo.startswith("https://"):
                url = cuerpo
        if not url:
            raise ErrorPasarela("La pasarela no devolvió una URL de pago")
        token = self._extraer_token(datos) or solicitud.referencia
        return ResultadoIntentoPago(url=url, token=token)

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        esperada = self._firmar({k: v for k, v in parametros.items() if k != "x_signature"})
        recibida = str(parametros.get("x_signature") or "")
        return hmac.compare_digest(esperada, recibida)

    def _construir_payload(self, solicitud: SolicitudPago) -> dict[str, Any]:
        parametros: dict[str, Any] = {
            "x_account_id": self._account_id,
            "x_amount": solicitud.monto,
            "x_currency": "CLP",
            "x_customer_email": solicitud.email_cliente,
            "x_customer_first_name": solicitud.nombre_cliente,
            "x_customer_last_name": solicitud.apellido_cliente,
            "x_customer_phone": solicitud.telefono_cliente,
            "x_description": solicitud.descripcion,
            "x_reference": solicitud.referencia,
            "x_shop_name": self._shop_name,
            "x_url_callback": self._url_callback,
            "x_url_cancel": self._url_cancel,
            "x_url_complete": self._url_complete,
        }
        parametros["x_signature"] = self._firmar(parametros)
        return parametros

    def _firmar(self, parametros: dict[str, Any]) -> str:
        """Firma HMAC-SHA256 (hex) sobre los campos x_* ordenados alfabéticamente.

        TUU concatena `clave` + `valor` (sin separadores) de cada campo `x_*`
        (excluyendo la propia firma), ordenados por nombre de parámetro.
        """
        cadena = "".join(
            f"{k}{v}"
            for k, v in sorted(parametros.items())
            if k.startswith("x_") and k != "x_signature"
        )
        digest = hmac.new(
            self._secret_key.encode(), cadena.encode(), hashlib.sha256
        ).hexdigest()
        return digest

    @staticmethod
    def _extraer_url(datos: Any) -> str | None:
        if not isinstance(datos, dict):
            return None
        for clave in ("url", "redirect_url", "payment_url"):
            valor = datos.get(clave)
            if isinstance(valor, str) and valor:
                return valor
        anidado = datos.get("data")
        if isinstance(anidado, dict):
            return TuuCliente._extraer_url(anidado)
        return None

    @staticmethod
    def _extraer_token(datos: Any) -> str | None:
        if not isinstance(datos, dict):
            return None
        for clave in ("token", "reference", "x_reference"):
            valor = datos.get(clave)
            if isinstance(valor, str) and valor:
                return valor
        anidado = datos.get("data")
        if isinstance(anidado, dict):
            return TuuCliente._extraer_token(anidado)
        return None