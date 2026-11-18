



from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_TIMEOUT_SEGUNDOS = 15

_MAX_PAGINAS_LISTADO = 10

_TIPOS_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "glb": "model/gltf-binary",
    "stl": "model/stl",
}


def tipo_mime(extension: str) -> str:
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
        return bool(self.url and self.clave and self.cubeta)

    def _request(self, metodo: str, ruta: str, **kwargs) -> requests.Response:

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

    def subir(self, ruta: str, contenido: bytes, content_type: str) -> bool:

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

    def existe(self, ruta: str) -> bool:

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

    def descargar(self, ruta: str) -> bytes | None:

        if not self.configurado:
            return None
        try:
            respuesta = self._request("GET", f"/object/{self.cubeta}/{ruta}")
            if respuesta.ok:
                return respuesta.content
            if respuesta.status_code not in (400, 404):
                logger.warning(
                    "[supabase-storage] no se pudo descargar %s (HTTP %s): %s",
                    ruta,
                    respuesta.status_code,
                    _resumen(respuesta),
                )
            return None
        except Exception as exc:  # noqa: BLE001 - best-effort: nada de la nube rompe al caller
            logger.warning("[supabase-storage] error descargando %s: %s", ruta, exc)
            return None

    def url_firmada(self, ruta: str) -> str | None:

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

    def listar(self, prefijo: str, limite: int = 1000) -> list[dict]:

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

    def eliminar(self, ruta: str) -> bool:
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

    if firmada.startswith(("http://", "https://")):
        return firmada
    if not firmada.startswith("/"):
        firmada = "/" + firmada
    if firmada.startswith("/storage/v1"):
        return f"{base}{firmada}"
    return f"{base}/storage/v1{firmada}"


def _resumen(respuesta) -> str:
    try:
        return (respuesta.text or "")[:200]
    except Exception:  # noqa: BLE001 - el logging no puede romper la operación
        return "<sin cuerpo>"


def almacen_desde_config(config=None) -> AlmacenSupabaseStorage | None:

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
