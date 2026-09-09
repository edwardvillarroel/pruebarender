from flask import Blueprint, jsonify

catalogo_bp = Blueprint("catalogo", __name__)


@catalogo_bp.get("/productos")
def listar_productos():
    raise NotImplementedError


@catalogo_bp.get("/productos/<uuid:producto_id>")
def detalle_producto(producto_id):
    raise NotImplementedError


@catalogo_bp.post("/productos")
def crear_producto():
    # TODO: solo rol admin
    raise NotImplementedError


@catalogo_bp.get("/categorias")
def listar_categorias():
    raise NotImplementedError