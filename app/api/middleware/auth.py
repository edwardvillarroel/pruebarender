from functools import wraps

from flask import current_app, jsonify, request


def _es_cliente_interno_valido() -> bool:
    """Confirma que la request que manda X-User-Id/X-User-Rol viene del gateway.

    OWASP Top 10 2025 (A01: Broken Access Control): el backend no debe confiar
    ciegamente en headers que el cliente pueda enviar. Cuando `INTERNAL_SECRET`
    esta configurado, toda peticion autenticada debe traer el secreto compartido
    que el gateway agrega al proxy interno. Sin configuracion el sistema queda en
    modo fail-closed: se rechaza cualquier request que intente autenticarse.
    """
    secreto = current_app.config.get("INTERNAL_SECRET") or ""
    if not secreto:
        # Fail-closed: sin secreto compartido no se acepta identidad confiable.
        return False
    return (request.headers.get("X-Internal-Secret") or "") == secreto


def requiere_sesion():
    """Decorador: exige que el usuario esté autenticado (X-User-Id del gateway)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not request.headers.get("X-User-Id") or not _es_cliente_interno_valido():
                return jsonify(mensaje="Sesión requerida"), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def rol_requerido(*roles: str):
    """Decorador: exige uno de los roles (cabecera X-User-Rol del gateway)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not _es_cliente_interno_valido() or (
                request.headers.get("X-User-Rol") not in roles
            ):
                return jsonify(mensaje="No autorizado"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def usuario_actual():
    """Id del usuario autenticado (inyectado por el gateway)."""
    return request.headers.get("X-User-Id")
