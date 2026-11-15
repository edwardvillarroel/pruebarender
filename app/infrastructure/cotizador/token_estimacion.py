"""Token firmado para reutilizar la estimacion del cotizador IA.

El navegador no es una fuente confiable de precios: cualquiera puede editar el
`FormData` de `POST /cotizaciones` y mandar el precio que quiera. Por eso
`POST /cotizaciones/estimar` firma la estimacion (HMAC via itsdangerous) y el
alta solo reutiliza valores que vengan dentro de un token valido, ligado al
usuario, a la imagen y a las especificaciones de la pieza.

El contenido del token es legible (base64), pero no modificable sin el secreto.
Eso es suficiente: el cliente ya ve su propia estimacion; lo que se protege es
la integridad de lo que se persiste en la base de datos.
"""

from __future__ import annotations

import hashlib

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SAL = "estimacion-ia-apolovibes"
VERSION = 1

# Campos que el alta puede tomar del token. Cualquier otra clave se descarta.
CAMPOS_ESTIMACION: tuple[str, ...] = (
    "precio_estimado_ia",
    "precio_unitario_ia",
    "gramos_estimados_ia",
    "tiempo_estimado_horas_ia",
    "material_sugerido_ia",
    "complejidad_ia",
    "confianza_material_ia",
    "confianza_complejidad_ia",
)

# Secretos conocidos/debiles con los que NO se firma ni se acepta un token.
# El default de `Config` no protege nada si llega a produccion, asi que es
# preferible caer al cotizador del backend antes que confiar en el navegador.
_SECRETOS_INSEGUROS = {"", "dev-secret-change-me"}


def hash_imagen(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def crear_token_estimacion(
    *,
    usuario_id,
    imagen_sha256: str,
    firma: str,
    estimacion: dict,
    secreto: str | None,
) -> str | None:
    """Firma la estimacion para un usuario, imagen y firma de especificaciones.

    Devuelve `None` si no hay un secreto seguro configurado: en ese caso el alta
    volvera a estimar en el backend en vez de confiar en el navegador.
    """
    if not _secreto_valido(secreto):
        return None
    payload = {
        "v": VERSION,
        "usuario_id": str(usuario_id),
        "imagen_sha256": imagen_sha256,
        "firma": firma,
        "estimacion": {k: estimacion.get(k) for k in CAMPOS_ESTIMACION},
    }
    return _serializer(secreto).dumps(payload)


def verificar_token_estimacion(
    token: str | None,
    *,
    usuario_id,
    imagen_sha256: str,
    firma: str,
    secreto: str | None,
    max_age: int,
) -> dict | None:
    """Devuelve la estimacion firmada solo si el token es valido y corresponde
    al usuario, la imagen y las especificaciones actuales."""
    if not token or not _secreto_valido(secreto):
        return None
    try:
        payload = _serializer(secreto).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict) or payload.get("v") != VERSION:
        return None
    if str(payload.get("usuario_id") or "") != str(usuario_id):
        return None
    if not imagen_sha256 or payload.get("imagen_sha256") != imagen_sha256:
        return None
    if not firma or payload.get("firma") != firma:
        return None
    estimacion = payload.get("estimacion")
    if not isinstance(estimacion, dict):
        return None
    return {k: estimacion.get(k) for k in CAMPOS_ESTIMACION}


def _serializer(secreto: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secreto, salt=SAL)


def _secreto_valido(secreto: str | None) -> bool:
    return str(secreto or "").strip() not in _SECRETOS_INSEGUROS
