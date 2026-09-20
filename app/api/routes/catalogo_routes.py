from io import BytesIO
from uuid import UUID

from flask import Blueprint, current_app, jsonify, request, send_file

from app.api.middleware.auth import requiere_sesion, rol_requerido
from app.application.catalogo_stock.gestionar_categoria import GestionarCategoria
from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO

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
        "specs": producto.specs,
        "descuento": producto.descuento,
        "precio_original": producto.precio_original,
        "material": producto.material,
        "tamano": producto.tamano,
        "color": producto.color,
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
@requiere_sesion()
@rol_requerido("admin")
def crear_producto():
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify(mensaje="Body JSON requerido"), 400
    try:
        dto = CrearProductoDTO(
            nombre=datos["nombre"],
            categoria_id=UUID(datos["categoria_id"]),
            precio=int(datos["precio"]),
            stock=int(datos.get("stock", 0)),
            descripcion=datos.get("descripcion"),
            imagen=datos.get("imagen"),
            material=datos.get("material"),
            tamano=datos.get("tamano"),
            color=datos.get("color"),
            specs=datos.get("specs"),
            descuento=datos.get("descuento"),
        )
    except (KeyError, ValueError) as e:
        return jsonify(mensaje=f"Datos invalidos: {e}"), 400
    producto = _servicio_producto().crear(dto)
    return jsonify(_a_publico_producto(producto)), 201


@catalogo_bp.patch("/productos/<uuid:producto_id>")
@requiere_sesion()
@rol_requerido("admin")
def actualizar_producto(producto_id):
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify(mensaje="Body JSON requerido"), 400
    try:
        dto = ActualizarProductoDTO(
            id=producto_id,
            nombre=datos.get("nombre"),
            categoria_id=UUID(datos["categoria_id"]) if "categoria_id" in datos else None,
            precio=int(datos["precio"]) if "precio" in datos else None,
            stock=int(datos["stock"]) if "stock" in datos else None,
            descripcion=datos.get("descripcion"),
            activo=datos.get("activo"),
            material=datos.get("material"),
            tamano=datos.get("tamano"),
            color=datos.get("color"),
            specs=datos.get("specs"),
            descuento=datos.get("descuento"),
        )
    except (ValueError) as e:
        return jsonify(mensaje=f"Datos invalidos: {e}"), 400
    try:
        producto = _servicio_producto().actualizar(dto)
    except ValueError as e:
        return jsonify(mensaje=str(e)), 404
    return jsonify(_a_publico_producto(producto))


@catalogo_bp.delete("/productos/<uuid:producto_id>")
@requiere_sesion()
@rol_requerido("admin")
def eliminar_producto(producto_id):
    try:
        _servicio_producto().eliminar(producto_id)
    except ValueError as e:
        mensaje = str(e)
        if "no encontrado" in mensaje.lower():
            return jsonify(mensaje=mensaje), 404
        return jsonify(mensaje=mensaje), 409
    return jsonify(mensaje="Producto eliminado correctamente")


@catalogo_bp.get("/categorias")
def listar_categorias():
    categorias = _servicio_categoria().listar()
    return jsonify(categorias=[_a_publico_categoria(c) for c in categorias])


@catalogo_bp.post("/productos/<uuid:producto_id>/imagen")
@requiere_sesion()
@rol_requerido("admin")
def subir_imagen(producto_id):
    if 'imagen' not in request.files:
        return jsonify(mensaje="Campo 'imagen' requerido"), 400
    archivo = request.files['imagen']
    if not archivo.filename:
        return jsonify(mensaje="Archivo vacio"), 400
    from app.domain.entities.producto import ImagenProducto
    imagen = ImagenProducto(bytes=archivo.read(), content_type=archivo.content_type)
    try:
        _servicio_producto().guardar_imagen(producto_id, imagen)
    except Exception as e:
        return jsonify(mensaje=f"Error al guardar imagen: {e}"), 500
    return jsonify(mensaje="Imagen subida correctamente"), 201
