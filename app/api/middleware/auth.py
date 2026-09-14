from functools import wraps

from flask import jsonify, request


def rol_requerido(*roles: str):
    """Decorador: exige uno de los roles (cabecera X-User-Rol del gateway)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.headers.get("X-User-Rol") not in roles:
                return jsonify(mensaje="No autorizado"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def usuario_actual():
    """Id del usuario autenticado (inyectado por el gateway)."""
    return request.headers.get("X-User-Id")