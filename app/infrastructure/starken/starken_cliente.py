"""Cliente REST de seguimiento Starken (portal de desarrolladores).

Implementa la interfaz `StarkenSeguimientoCliente` del dominio. Toda la
comunicación HTTP con el proveedor queda en infraestructura; la capa de
aplicación solo conoce `SeguimientoStarken`/`EventoSeguimiento`.

Credenciales (nunca hardcodeadas) se leen de la configuración:
  STARKEN_API_URL       base del API (default https://gateway.starken.cl)
  STARKEN_API_KEY       API key de la cuenta de la PYME
  STARKEN_SEGUIMIENTO_RUTA  ruta relativa a la orden de flete
                           (default /orden-flete/of/ + codigo)
  STARKEN_TIMEOUT       timeout en segundos

Si no hay `STARKEN_API_KEY`, el cliente queda "desconectado" y `consultar()`
devuelve None: el seguimiento se muestra como no disponible sin romper el
flujo de pedidos. El contrato exacto de json se valida caso por caso con la
cuenta de Starken; el parser es tolerante y busca los campos por varios
nombres alternativos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.domain.entities.seguimiento_starken import (
    EventoSeguimiento,
    SeguimientoStarken,
)
from app.domain.interfaces.starken import ErrorStarken, StarkenSeguimientoCliente


class StarkenCliente(StarkenSeguimientoCliente):
    """Cliente real de la API de seguimiento de Starken."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._api_url = str(config.get("STARKEN_API_URL", "https://gateway.starken.cl")).rstrip("/")
        self._api_key = str(config.get("STARKEN_API_KEY", "") or "").strip()
        self._ruta = str(config.get("STARKEN_SEGUIMIENTO_RUTA", "/orden-flete/of/"))
        try:
            self._timeout = float(config.get("STARKEN_TIMEOUT", 10))
        except (TypeError, ValueError):
            self._timeout = 10.0

    def _desconectado(self) -> bool:
        return not self._api_key

    def consultar(self, codigo: str) -> SeguimientoStarken | None:
        if self._desconectado():
            return None

        url = f"{self._api_url}{self._ruta}{codigo}"
        try:
            respuesta = httpx.get(
                url,
                headers={
                    "Apikey": self._api_key,
                    "Content-Type": "application/json",
                    "Origen": "CL",
                },
                timeout=self._timeout,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
        except httpx.HTTPError as exc:
            raise ErrorStarken(f"No se pudo contactar el servicio de seguimiento: {exc}") from exc
        except ValueError as exc:
            raise ErrorStarken("El servicio de seguimiento devolvió una respuesta inválida") from exc

        return self._mapear(codigo, datos)

    @staticmethod
    def _mapear(codigo: str, datos: Any) -> SeguimientoStarken:
        if not isinstance(datos, dict):
            raise ErrorStarken("El servicio de seguimiento devolvió una respuesta inválida")

        body = datos.get("data") if isinstance(datos.get("data"), (dict, list)) else datos
        if isinstance(body, list):
            body = body[0] if body else {}
        if not isinstance(body, dict):
            body = {}

        estado = StarkenCliente._buscar(body, "estado", "macro_estado", "estado_actual", "status")
        descripcion = StarkenCliente._buscar(body, "descripcion", "descripcion_estado", "mensaje")
        historial = StarkenCliente._historial(body)

        return SeguimientoStarken(
            codigo=codigo,
            estado=str(estado).strip().upper() if estado is not None else None,
            descripcion=str(descripcion).strip() if descripcion is not None else None,
            historial=historial,
            consultado_en=datetime.utcnow(),
        )

    @staticmethod
    def _historial(datos: dict[str, Any]) -> list[EventoSeguimiento]:
        eventos: list[dict[str, Any]] = []
        for clave in ("historial", "eventos", "tracking_detalle", "detalle", "seguimiento"):
            valor = datos.get(clave)
            if isinstance(valor, list):
                eventos = valor
                break
        resultado: list[EventoSeguimiento] = []
        for item in eventos:
            if not isinstance(item, dict):
                continue
            resultado.append(
                EventoSeguimiento(
                    fecha=StarkenCliente._parsear_fecha(
                        StarkenCliente._buscar(item, "fecha", "fecha_evento", "date")
                    ),
                    descripcion=StarkenCliente._buscar(item, "descripcion", "detalle", "descripcion_evento"),
                    sucursal=StarkenCliente._buscar(item, "sucursal", "agencia"),
                    ciudad=StarkenCliente._buscar(item, "ciudad", "comuna"),
                    estado=StarkenCliente._buscar(item, "estado", "macro_estado", "status"),
                )
            )
        return resultado

    @staticmethod
    def _buscar(datos: dict[str, Any], *claves: str) -> Any:
        for clave in claves:
            valor = datos.get(clave)
            if valor is not None and str(valor).strip() != "":
                return valor
        return None

    @staticmethod
    def _parsear_fecha(valor: Any) -> datetime | None:
        if valor is None:
            return None
        texto = str(valor).strip()
        if not texto:
            return None
        for formato in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(texto[:19], formato)
            except ValueError:
                continue
        return None