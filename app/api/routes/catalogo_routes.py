from io import BytesIO

from flask import Blueprint, current_app, jsonify, send_file

from app.application.catalogo_stock.gestionar_categoria import GestionarCategoria
from app.application.catalogo_stock.gestionar_producto import GestionarProducto

catalogo_bp = Blueprint("catalogo", __name__)


def _servicio_producto() -> GestionarProducto:
    """Servicio de productos inyectado desde `create_app` (la capa API no
    depende de `infrastructure`)."""
    return current_app.config["PRODUCTO_SERVICE"]


def _servicio_categoria() -> GestionarCategoria:
    return current_app.config["CATEGORIA_SERVICE"]


def _a_publico_producto(producto) -> dict:
    return {
        "id": str(producto.id),
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "stock": producto.stock,
        "imagen": producto.imagen,
        "activo": producto.activo,
        "categoria_id": str(producto.categoria_id),
    }


def _a_publico_categoria(categoria) -> dict:
    return {
        "id": str(categoria.id),
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion,
    }


@catalogo_bp.get("/productos")
def listar_productos():
    productos = _servicio_producto().listar()
    return jsonify(productos=[_a_publico_producto(p) for p in productos])


@catalogo_bp.get("/productos/<uuid:producto_id>")
def detalle_producto(producto_id):
    producto = _servicio_producto().consultar(producto_id)
    if producto is None:
        return jsonify(mensaje="Producto no encontrado"), 404
    return jsonify(_a_publico_producto(producto))


@catalogo_bp.get("/productos/<uuid:producto_id>/imagen")
def imagen_producto(producto_id):
    """Sirve la imagen almacenada como BLOB en la base de datos."""
    imagen = _servicio_producto().consultar_imagen(producto_id)
    if imagen is None:
        return jsonify(mensaje="Imagen no encontrada"), 404
    return send_file(
        BytesIO(imagen.bytes),
        mimetype=imagen.content_type or "application/octet-stream",
    )


@catalogo_bp.post("/productos")
def crear_producto():
    # TODO: solo rol admin
    raise NotImplementedError


@catalogo_bp.get("/categorias")
def listar_categorias():
    categorias = _servicio_categoria().listar()
    return jsonify(categorias=[_a_publico_categoria(c) for c in categorias])