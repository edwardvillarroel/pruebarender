from flask import Blueprint, jsonify, request

from app.api.middleware.auth import requiere_sesion, rol_requerido
from app.domain.entities.cupon import Cupon
from app.infrastructure.repositories.cupon_repository import CuponRepository

cupon_bp = Blueprint("cupones", __name__)
_repo = CuponRepository()


@cupon_bp.get("/admin/cupones")
@requiere_sesion()
@rol_requerido("admin")
def listar_cupones():
    cupones = _repo.listar()
    return jsonify({
        "cupones": [
            {
                "id": str(c.id),
                "codigo": c.codigo,
                "tipo": c.tipo,
                "valor": c.valor,
                "activo": c.activo,
                "uso_unico": c.uso_unico,
                "usado": c.usado,
                "usado_por": str(c.usado_por) if c.usado_por else None,
                "usado_en": c.usado_en.isoformat() if c.usado_en else None,
                "creado_en": c.creado_en.isoformat() if c.creado_en else None,
                "descripcion": c.descripcion,
            }
            for c in cupones
        ]
    })


@cupon_bp.post("/admin/cupones")
@requiere_sesion()
@rol_requerido("admin")
def crear_cupon():
    datos = request.get_json(silent=True) or {}
    codigo = str(datos.get("codigo") or "").strip().upper()
    tipo = str(datos.get("tipo") or "porcentaje").strip().lower()
    valor = datos.get("valor")
    uso_unico = bool(datos.get("uso_unico"))
    descripcion = datos.get("descripcion")

    if not codigo:
        return jsonify({"error": "El código es obligatorio"}), 400
    if tipo not in ("porcentaje", "monto"):
        return jsonify({"error": "Tipo inválido"}), 400
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return jsonify({"error": "Valor inválido"}), 400
    if valor <= 0:
        return jsonify({"error": "El valor debe ser mayor a 0"}), 400
    if tipo == "porcentaje" and valor > 100:
        return jsonify({"error": "El porcentaje no puede ser mayor a 100"}), 400

    existente = _repo.get_by_codigo(codigo)
    if existente:
        return jsonify({"error": "Ya existe un cupón con ese código"}), 409

    from flask import g
    creado_por = getattr(g, "usuario_id", None)

    cupon = Cupon(
        codigo=codigo,
        tipo=tipo,
        valor=valor,
        activo=True,
        uso_unico=uso_unico,
        descripcion=descripcion,
        creado_por=creado_por,
    )
    creado = _repo.crear(cupon)
    return jsonify({
        "cupon": {
            "id": str(creado.id),
            "codigo": creado.codigo,
            "tipo": creado.tipo,
            "valor": creado.valor,
            "activo": creado.activo,
            "uso_unico": creado.uso_unico,
            "usado": creado.usado,
            "descripcion": creado.descripcion,
            "creado_en": creado.creado_en.isoformat() if creado.creado_en else None,
        }
    }), 201


@cupon_bp.delete("/admin/cupones/<uuid:cupon_id>")
@requiere_sesion()
@rol_requerido("admin")
def eliminar_cupon(cupon_id):
    try:
        _repo.eliminar(cupon_id)
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@cupon_bp.post("/cupones/validar")
@requiere_sesion()
def validar_cupon():
    datos = request.get_json(silent=True) or {}
    codigo = str(datos.get("codigo") or "").strip().upper()
    if not codigo:
        return jsonify({"error": "Ingresa un código"}), 400

    cupon = _repo.get_by_codigo(codigo)
    if not cupon or not cupon.activo or cupon.usado:
        return jsonify({"error": "Cupón inválido o ya utilizado"}), 400

    return jsonify({
        "valido": True,
        "cupon": {
            "codigo": cupon.codigo,
            "tipo": cupon.tipo,
            "valor": cupon.valor,
        }
    })
