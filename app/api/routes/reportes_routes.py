from flask import Blueprint, current_app, jsonify

from app.api.middleware.auth import requiere_sesion, rol_requerido
from app.application.reportes.gestionar_reporte import GestionarReporte

reportes_bp = Blueprint("reportes", __name__)


def _servicio() -> GestionarReporte:
    return current_app.config["REPORTE_SERVICE"]


@reportes_bp.get("/reportes")
@requiere_sesion()
@rol_requerido("admin")
def reporte_general():

    return jsonify(reporte=_servicio().resumen())
