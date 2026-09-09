from flask import Blueprint, jsonify

diseno_bp = Blueprint("disenos", __name__)


@diseno_bp.post("/cotizaciones")
def crear_cotizacion():
    # TODO: multipart (nombre, email, telefono, material, descripcion,
    #       imagen, modeloUrl) -> sanitizar antes de persistir/LLM (RNF-05)
    raise NotImplementedError


@diseno_bp.get("/cotizaciones")
def listar_cotizaciones():
    # TODO: solo rol admin
    raise NotImplementedError


@diseno_bp.patch("/cotizaciones/<uuid:solicitud_id>")
def evaluar_cotizacion(solicitud_id):
    # TODO: {estado: aprobada, precio}; solo rol admin
    raise NotImplementedError