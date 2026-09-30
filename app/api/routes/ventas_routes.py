from uuid import UUID

from flask import Blueprint, current_app, jsonify, request

from app.api.middleware.auth import requiere_sesion, rol_requerido, usuario_actual
from app.application.venta_local.gestionar_venta_local import GestionarVentaLocal
from app.domain.enums import MedioPago

venta_bp = Blueprint("ventas", __name__)


def _servicio() -> GestionarVentaLocal:
    """Servicio de venta local inyectado desde el punto de composición
    (`create_app`), para que esta capa no dependa de `infrastructure`."""
    return current_app.config["VENTA_SERVICE"]


def _usuario_uuid() -> UUID:
    """Convierte el X-User-Id (str) del gateway a UUID para el caso de uso."""
    return UUID(usuario_actual())


def _a_publico_sesion(sesion) -> dict:
    return {
        "id": str(sesion.id),
        "lugar": sesion.lugar,
        "fecha": sesion.fecha.isoformat(),
        "estado": sesion.estado,
        "creado_en": sesion.creado_en,
        "cerrada_en": sesion.cerrada_en,
    }


def _a_publico_venta(venta) -> dict:
    return {
        "id": str(venta.id),
        "sesion_id": str(venta.sesion_id),
        "medio_pago": venta.medio_pago,
        "total": venta.total,
        "creado_en": venta.creado_en,
        "items": [
            {
                "id": str(item.id),
                "producto_id": str(item.producto_id),
                "nombre": item.nombre,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "subtotal": item.cantidad * item.precio_unitario,
            }
            for item in venta.items
        ],
    }


def _a_publico_reporte(sesion, ventas) -> dict:
    """Reporte con los campos de la sesión al nivel raíz (contrato del frontend)."""
    total_efectivo = sum(
        v.total for v in ventas if v.medio_pago == MedioPago.EFECTIVO.value
    )
    total_tuu = sum(v.total for v in ventas if v.medio_pago == MedioPago.TUU.value)
    return {
        **_a_publico_sesion(sesion),
        "ventas": [_a_publico_venta(v) for v in ventas],
        "total": sum(v.total for v in ventas),
        "total_efectivo": total_efectivo,
        "total_tuu": total_tuu,
        "n_ventas": len(ventas),
    }


def _error(mensaje: str, codigo: int):
    return jsonify(mensaje=mensaje), codigo


def _traducir_error(exc: ValueError):
    """Traduce un ValueError del caso de uso: 409 para conflictos de negocio
    (stock, sesión cerrada) y 400 para errores de validación."""
    mensaje = str(exc)
    if "stock" in mensaje or "cerrada" in mensaje:
        return _error(mensaje, 409)
    return _error(mensaje, 400)


@venta_bp.post("/ventas/sesiones")
@requiere_sesion()
@rol_requerido("admin")
def abrir_sesion_venta():
    datos = request.get_json(silent=True) or {}
    try:
        sesion = _servicio().abrir_sesion(
            lugar=datos.get("lugar"),
            usuario_id=_usuario_uuid(),
        )
    except ValueError as exc:
        return _traducir_error(exc)
    return jsonify(sesion=_a_publico_sesion(sesion)), 201


@venta_bp.get("/ventas/sesiones/actual")
@requiere_sesion()
@rol_requerido("admin")
def sesion_venta_actual():
    sesion = _servicio().obtener_sesion_abierta(_usuario_uuid())
    if sesion is None:
        return jsonify(sesion=None, ventas=[])
    ventas = _servicio().obtener_ventas_de_sesion(sesion.id)
    return jsonify(
        sesion=_a_publico_sesion(sesion),
        ventas=[_a_publico_venta(v) for v in ventas],
    )


@venta_bp.post("/ventas/sesiones/<uuid:sesion_id>/ventas")
@requiere_sesion()
@rol_requerido("admin")
def registrar_venta_local(sesion_id):
    datos = request.get_json(silent=True) or {}
    medio_pago = datos.get("medio_pago")
    items = []
    for item in datos.get("items") or []:
        try:
            producto_id = UUID(str(item["producto_id"]))
            cantidad = int(item.get("cantidad", 0))
        except (KeyError, TypeError, ValueError):
            return _error("producto_id y cantidad son obligatorios y válidos", 400)
        items.append((producto_id, cantidad))
    try:
        venta = _servicio().registrar_venta(
            sesion_id,
            medio_pago,
            items,
            _usuario_uuid(),
        )
    except ValueError as exc:
        return _traducir_error(exc)
    return jsonify(venta=_a_publico_venta(venta)), 201


@venta_bp.post("/ventas/sesiones/<uuid:sesion_id>/cierre")
@requiere_sesion()
@rol_requerido("admin")
def cerrar_sesion_venta(sesion_id):
    try:
        sesion = _servicio().cerrar_sesion(sesion_id)
        ventas = _servicio().obtener_ventas_de_sesion(sesion_id)
    except ValueError as exc:
        return _traducir_error(exc)
    return jsonify(reporte=_a_publico_reporte(sesion, ventas))


@venta_bp.get("/ventas/reportes")
@requiere_sesion()
@rol_requerido("admin")
def listar_reportes_venta():
    sesiones = _servicio().listar_reportes()
    reportes = [
        _a_publico_reporte(sesion, _servicio().obtener_ventas_de_sesion(sesion.id))
        for sesion in sesiones
    ]
    return jsonify(reportes=reportes)


@venta_bp.get("/ventas/reportes/<uuid:sesion_id>")
@requiere_sesion()
@rol_requerido("admin")
def detalle_reporte_venta(sesion_id):
    sesion = _servicio().obtener_reporte(sesion_id)
    if sesion is None:
        return _error("Sesión no encontrada", 404)
    ventas = _servicio().obtener_ventas_de_sesion(sesion_id)
    return jsonify(reporte=_a_publico_reporte(sesion, ventas))