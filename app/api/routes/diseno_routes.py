from uuid import UUID

from flask import Blueprint, current_app, jsonify, request

from app.api.middleware.auth import requiere_sesion, usuario_actual
from app.infrastructure.imagenes.validador_imagen_segura import ImagenInvalida

diseno_bp = Blueprint("disenos", __name__)


@diseno_bp.post("/cotizaciones/validar-imagen")
def validar_imagen_cotizacion():
    try:
        if "imagen" not in request.files:
            return jsonify({"error": "Falta la imagen de referencia."}), 400

        imagen = request.files["imagen"]
        if imagen.filename == "":
            return jsonify({"error": "Debes seleccionar una imagen."}), 400

        from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura

        validar_imagen_segura(imagen)
        return jsonify({"ok": True, "valido": True}), 200
    except ImagenInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "No pudimos validar la imagen."}), 500


@diseno_bp.post("/cotizaciones")
@requiere_sesion()
def crear_cotizacion():
    try:
        imagen = request.files.get("imagen")
        if imagen is None or imagen.filename == "":
            return jsonify({"error": "Falta la imagen de referencia."}), 400

        datos = request.form.to_dict()
        if "modeloUrl" in datos and "modelo_url" not in datos:
            datos["modelo_url"] = datos.pop("modeloUrl")

        usuario_id_str = usuario_actual()
        if not usuario_id_str:
            return jsonify({"error": "Sesión requerida"}), 401
        try:
            usuario_id = UUID(usuario_id_str)
        except Exception:
            return jsonify({"error": "Sesión requerida"}), 401

        servicio = current_app.config.get("COTIZACION_SERVICE")
        if servicio is None:
            return jsonify({"error": "No pudimos procesar la solicitud."}), 500

        solicitud = servicio.ejecutar(usuario_id, datos, imagen)
        return jsonify({"id": str(solicitud.id), "estado": solicitud.estado.value, "creado_en": solicitud.creado_en.isoformat()}), 201
    except ImagenInvalida as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "No pudimos procesar la solicitud."}), 500


@diseno_bp.get("/cotizaciones")
def listar_cotizaciones():
    raise NotImplementedError


@diseno_bp.patch("/cotizaciones/<uuid:solicitud_id>")
def evaluar_cotizacion(solicitud_id):
    raise NotImplementedError