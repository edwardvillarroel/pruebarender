from flask import Blueprint, current_app, jsonify

from app.api.middleware.auth import requiere_sesion, rol_requerido
from app.application.reportes.gestionar_reporte import GestionarReporte

reportes_bp = Blueprint("reportes", __name__)


def _servicio() -> GestionarReporte:
    """Reporte general inyectado desde el punto de composición
    (`create_app`), para que esta capa no dependa de `infrastructure`."""
    return current_app.config["REPORTE_SERVICE"]


@reportes_bp.get("/reportes")
@requiere_sesion()
@rol_requerido("admin")
def reporte_general():
    """Reporte general de ventas y pedidos para el panel de administracion.

    Suma como ingresos las ventas de las sesiones locales cerradas y los pedidos
    pagados de la tienda web, y ademas resume los pedidos (con estado) y las
    cotizaciones pendientes. Solo lectura: no modifica datos existentes.
    """
    return jsonify(reporte=_servicio().resumen())
