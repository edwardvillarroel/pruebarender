from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def rol_requerido(*roles: str):
    """Decorador: exige un JWT válido y uno de los roles indicados."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("rol") not in roles:
                return jsonify(mensaje="No autorizado"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator