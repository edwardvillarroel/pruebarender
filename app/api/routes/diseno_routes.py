from flask import Blueprint, jsonify, request

from app.infrastructure.imagenes.validador_imagen_segura import ImagenInvalida, validar_imagen_segura

diseno_bp = Blueprint("disenos", __name__)


@diseno_bp.post("/cotizaciones/validar-imagen")
def validar_imagen_cotizacion():
    try:
        if "imagen" not in request.files:
            return jsonify({"error": "Falta la imagen de referencia."}), 400

        imagen = request.files["imagen"]
        if imagen.filename == "":
            return jsonify({"error": "Debes seleccionar una imagen."}), 400

        validar_imagen_segura(imagen)
        return jsonify({"ok": True, "valido": True}), 200
    except ImagenInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "No pudimos validar la imagen."}), 500


@diseno_bp.post("/cotizaciones")
def crear_cotizacion():
    try:
        if "imagen" not in request.files:
            return jsonify({"error": "Falta la imagen de referencia."}), 400

        imagen = request.files["imagen"]
        if imagen.filename == "":
            return jsonify({"error": "Debes seleccionar una imagen."}), 400

        validar_imagen_segura(imagen)
        return jsonify({"error": "Endpoint en desarrollo."}), 501
    except ImagenInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "No pudimos procesar la solicitud."}), 500


@diseno_bp.get("/cotizaciones")
def listar_cotizaciones():
    raise NotImplementedError


@diseno_bp.patch("/cotizaciones/<uuid:solicitud_id>")
def evaluar_cotizacion(solicitud_id):
    raise NotImplementedError