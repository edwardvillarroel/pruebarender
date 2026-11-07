"""Almacenamiento de imágenes de cotización en Supabase Storage (F4).

Adaptador liviano sobre la Storage REST API con la service-role key
(`apikey` + `Authorization: Bearer`). El bucket es privado: para servir un
archivo se crea una URL firmada de vida corta (`SUPABASE_SIGN_TTL_SECONDS`),
nunca se expone la clave.

Todas las operaciones son best-effort: avisan con `logger.warning` (sin
imprimir jamás la clave) y devuelven `False`/`None` en vez de lanzar, porque
ninguna falla de la nube debe romper el envío de una cotización ni el serving
de los archivos locales.

El seam de red es el método privado `_request`: los tests lo stubbean y la
suite nunca toca la red.
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

# Timeout corto: una subida es ~10 MB como máximo (MAX_UPLOAD_SIZE) y el
# request del usuario no debe colgar esperando a la nube.
_TIMEOUT_SEGUNDOS = 15

# Páginas de 1000 objetos en `listar`: tope de 10 páginas por invocación para
# que un bucket gigante no cuelque la purga.
_MAX_PAGINAS_LISTADO = 10

_TIPOS_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "glb": "model/gltf-binary",
    "stl": "model/stl",
}


def tipo_mime(extension: str) -> str:
    """Content-Type real para una extensión ya validada (con o sin punto)."""
    ext = (extension or "").strip().lstrip(".").lower()
    return _TIPOS_MIME.get(ext, "application/octet-stream")


class AlmacenSupabaseStorage:
    def __init__(
        self,
        url: str,
        clave: str,
        cubeta: str,
        ttl: int = 300,
        timeout: int = _TIMEOUT_SEGUNDOS,
    ):
        self.url = (url or "").strip().rstrip("/")
        self.clave = (clave or "").strip()
        self.cubeta = (cubeta or "").strip()
        try:
            self.ttl = int(ttl) if ttl else 300
        except (TypeError, ValueError):
            self.ttl = 300
        self.timeout = timeout

    @property
    def configurado(self) -> bool:
        """True solo con URL + clave + cubeta; el resto del código ni llama."""
        return bool(self.url and self.clave and self.cubeta)

    # ------------------------------------------------------------------
    # Seam de red: única puerta a `requests`. Los tests la stubbean.
    # ------------------------------------------------------------------
    def _request(self, metodo: str, ruta: str, **kwargs) -> requests.Response:
        """Llama a `{url}/storage/v1{ruta}` con auth de service-role.

        `ruta` es relativa al prefijo `/storage/v1` (p. ej.
        `/object/Cotizaciones/cotizaciones/x.png`). La clave va SOLO en
        headers, nunca en la URL ni en los logs.
        """
        headers = kwargs.pop("headers", {})
        headers.setdefault("apikey", self.clave)
        headers.setdefault("Authorization", f"Bearer {self.clave}")
        return requests.request(
            metodo,
            f"{self.url}/storage/v1{ruta}",
            headers=headers,
            timeout=self.timeout,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    def subir(self, ruta: str, contenido: bytes, content_type: str) -> bool:
        """Sube `contenido` a `cubeta/ruta`. True solo si la API confirmó.

        `x-upsert: true` para que un reintento de la migración pise el objeto
        en vez de recibir `400 Asset Already Exists`.
        """
        if not self.configurado:
            return False
        try:
            respuesta = self._request(
                "POST",
                f"/object/{self.cubeta}/{ruta}",
                headers={
                    "Content-Type": content_type or "application/octet-stream",
                    "x-upsert": "true",
                },
                data=contenido,
            )
            if respuesta.ok:
                return True
            logger.warning(
                "[supabase-storage] no se pudo subir %s (HTTP %s): %s",
                ruta,
                respuesta.status_code,
                _resumen(respuesta),
            )
            return False
        except Exception as exc:  # noqa: BLE001 - best-effort: nada de la nube rompe al caller
            logger.warning("[supabase-storage] error subiendo %s: %s", ruta, exc)
            return False

    # ------------------------------------------------------------------
    # Existencia
    # ------------------------------------------------------------------
    def existe(self, ruta: str) -> bool:
        """True si el objeto existe en el bucket.

        Usa `GET /object/info/...` (metadatos livianos, equivalente al HEAD de
        la línea aprobada: 200 existe, 404/400 no existe; el resto se avisa y
        se responde "no existe" para caer al archivo local).
        """
        if not self.configurado:
            return False
        try:
            respuesta = self._request("GET", f"/object/info/{self.cubeta}/{ruta}")
            if respuesta.status_code == 200:
                return True
            if respuesta.status_code in (400, 404):
                return False
            logger.warning(
                "[supabase-storage] no se pudo verificar %s (HTTP %s)",
                ruta,
                respuesta.status_code,
            )
            return False
        except Exception as exc:  # noqa: BLE001 - best-effort: nada de la nube rompe al caller
            logger.warning(
                "[supabase-storage] error verificando %s: %s", ruta, exc
            )
            return False

    # ------------------------------------------------------------------
    # URL firmada
    # ------------------------------------------------------------------
    def url_firmada(self, ruta: str) -> str | None:
        """URL absoluta de descarga con TTL corto; `None` si falla.

        `POST /object/sign/...` devuelve `signedURL` relativa
        (`/object/sign/...`) o absoluta según la versión del servicio; ambas
        formas se normalizan acá.
        """
        if not self.configurado:
            return None
        try:
            respuesta = self._request(
                "POST",
                f"/object/sign/{self.cubeta}/{ruta}",
                headers={"Content-Type": "application/json"},
                json={"expiresIn": str(self.ttl)},
            )
            if not respuesta.ok:
                logger.warning(
                    "[supabase-storage] no se pudo firmar %s (HTTP %s): %s",
                    ruta,
                    respuesta.status_code,
                    _resumen(respuesta),
                )
                return None
            datos = respuesta.json() or {}
            firmada = datos.get("signedURL") or datos.get("signedUrl")
            if not firmada or not isinstance(firmada, str):
                logger.warning(
                    "[supabase-storage] respuesta de firma sin signedURL para %s",
                    ruta,
                )
                return None
            return _url_absoluta(self.url, firmada)
        except Exception as exc:  # noqa: BLE001 - best-effort: nada de la nube rompe al caller
            logger.warning("[supabase-storage] error firmando %s: %s", ruta, exc)
            return None

    # ------------------------------------------------------------------
    # Listado (purga de huérfanos del bucket)
    # ------------------------------------------------------------------
    def listar(self, prefijo: str, limite: int = 1000) -> list[dict]:
        """Objetos bajo `prefijo` con `name` y `created_at` (paginado).

        Mejor esfuerzo: ante cualquier falla devuelve lo acumulado (o `[]`) y
        avisa; la purga no debe abortar porque el listado falle.
        """
        if not self.configurado:
            return []
        objetos: list[dict] = []
        try:
            offset = 0
            for _pagina in range(_MAX_PAGINAS_LISTADO):
                respuesta = self._request(
                    "POST",
                    f"/object/list/{self.cubeta}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "prefix": prefijo,
                        "limit": limite,
                        "offset": offset,
                        "sortBy": {"column": "created_at", "order": "asc"},
                    },
                )
                if not respuesta.ok:
                    logger.warning(
                        "[supabase-storage] no se pudo listar %s (HTTP %s): %s",
                        prefijo,
                        respuesta.status_code,
                        _resumen(respuesta),
                    )
                    return objetos
                lote = respuesta.json()
                if not isinstance(lote, list):
                    logger.warning(
                        "[supabase-storage] listado de %s con forma inesperada",
                        prefijo,
                    )
                    return objetos
                objetos.extend(lote)
                if len(lote) < limite:
                    return objetos
                offset += limite
            logger.warning(
                "[supabase-storage] listado de %s truncado en %s páginas",
                prefijo,
                _MAX_PAGINAS_LISTADO,
            )
            return objetos
        except Exception as exc:  # noqa: BLE001 - best-effort: nada de la nube rompe al caller
            logger.warning("[supabase-storage] error listando %s: %s", prefijo, exc)
            return objetos

    # ------------------------------------------------------------------
    # Borrado
    # ------------------------------------------------------------------
    def eliminar(self, ruta: str) -> bool:
        """True si el objeto se borró (2xx); 404 cuenta como `False`."""
        if not self.configurado:
            return False
        try:
            respuesta = self._request("DELETE", f"/object/{self.cubeta}/{ruta}")
            if respuesta.ok:
                return True
            if respuesta.status_code == 404:
                return False
            logger.warning(
                "[supabase-storage] no se pudo borrar %s (HTTP %s): %s",
                ruta,
                respuesta.status_code,
                _resumen(respuesta),
            )
            return False
        except Exception as exc:  # noqa: BLE001 - best-effort: nada de la nube rompe al caller
            logger.warning("[supabase-storage] error borrando %s: %s", ruta, exc)
            return False


def _url_absoluta(base: str, firmada: str) -> str:
    """Normaliza `signedURL` a una URL absoluta descargable.

    Tres formas reales según la versión del servicio:
    absoluta (`https://...`), con prefijo (`/storage/v1/object/sign/...`) o
    relativa pura (`/object/sign/...`).
    """
    if firmada.startswith(("http://", "https://")):
        return firmada
    if not firmada.startswith("/"):
        firmada = "/" + firmada
    if firmada.startswith("/storage/v1"):
        return f"{base}{firmada}"
    return f"{base}/storage/v1{firmada}"


def _resumen(respuesta) -> str:
    """Extracto corto del cuerpo de error (la clave NUNCA viaja en el cuerpo)."""
    try:
        return (respuesta.text or "")[:200]
    except Exception:  # noqa: BLE001 - el logging no puede romper la operación
        return "<sin cuerpo>"


def almacen_desde_config(config=None) -> AlmacenSupabaseStorage | None:
    """Almacen listo si la config trae URL + clave + cubeta; `None` si falta algo.

    Con `config=None` lee el `current_app.config` si hay contexto de
    aplicación (los tests inyectan su config ahí) y si no los atributos de
    `Config` (CLI/scripts). `None` significa "sigue en disco local".
    """
    if config is None:
        from flask import current_app, has_app_context

        if has_app_context():
            config = current_app.config
        else:
            from app.config import Config

            config = {
                "SUPABASE_URL": getattr(Config, "SUPABASE_URL", ""),
                "SUPABASE_SERVICE_KEY": getattr(Config, "SUPABASE_SERVICE_KEY", ""),
                "SUPABASE_STORAGE_BUCKET": getattr(
                    Config, "SUPABASE_STORAGE_BUCKET", ""
                ),
                "SUPABASE_SIGN_TTL_SECONDS": getattr(
                    Config, "SUPABASE_SIGN_TTL_SECONDS", 300
                ),
            }
    almacen = AlmacenSupabaseStorage(
        url=config.get("SUPABASE_URL"),
        clave=config.get("SUPABASE_SERVICE_KEY"),
        cubeta=config.get("SUPABASE_STORAGE_BUCKET"),
        ttl=config.get("SUPABASE_SIGN_TTL_SECONDS") or 300,
    )
    return almacen if almacen.configurado else None
