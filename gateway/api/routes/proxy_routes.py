from flask import Blueprint, Response, request
from flask_jwt_extended import get_jwt, jwt_required
from gateway.infrastructure.proxy import reenviar

proxy_bp = Blueprint("proxy", __name__)

@proxy_bp.route("/<path:ruta>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@jwt_required(optional=True)
def proxy(ruta):
    claims = get_jwt() or {}
    cabeceras_internas = {}
    if claims:
        cabeceras_internas = {
            "X-User-Id": claims.get("sub") or "",
            "X-User-Rol": claims.get("rol") or "",
        }
    contenido, status = reenviar(ruta, request, cabeceras_internas)
    return Response(contenido, status=status, content_type="application/json; charset=utf-8")
    