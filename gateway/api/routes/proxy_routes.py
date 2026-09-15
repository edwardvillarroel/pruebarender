from flask import Blueprint, Response, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError
import jwt as pyjwt
from gateway.infrastructure.proxy import reenviar

proxy_bp = Blueprint("proxy", __name__)

@proxy_bp.route("/<path:ruta>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy(ruta):
    # Verificar JWT sin abortar si el token es inválido/expirado (optional=True manual)
    claims = {}
    try:
        verify_jwt_in_request(optional=True)
        claims = get_jwt() or {}
    except (NoAuthorizationError, InvalidHeaderError, pyjwt.InvalidTokenError):
        # Token presente pero inválido/expirado: tratar como anónimo
        claims = {}

    cabeceras_internas = {}
    if claims:
        cabeceras_internas = {
            "X-User-Id": claims.get("sub") or "",
            "X-User-Rol": claims.get("rol") or "",
        }
    contenido, status = reenviar(ruta, request, cabeceras_internas)
    return Response(contenido, status=status, content_type="application/json; charset=utf-8")
