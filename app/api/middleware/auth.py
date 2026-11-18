from functools import wraps

from flask import current_app, jsonify, request


def _es_cliente_interno_valido() -> bool:

    secreto = current_app.config.get("INTERNAL_SECRET") or ""
    if not secreto:
        return False
    return (request.headers.get("X-Internal-Secret") or "") == secreto


def requiere_sesion():

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not request.headers.get("X-User-Id") or not _es_cliente_interno_valido():
                return jsonify(mensaje="Sesión requerida"), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def rol_requerido(*roles: str):

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
    return request.headers.get("X-User-Id")


def usuario_confiable():

    if not _es_cliente_interno_valido():
        return None
    return usuario_actual()


def rol_actual():
    return request.headers.get("X-User-Rol")
