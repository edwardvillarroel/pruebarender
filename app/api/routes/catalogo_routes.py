from io import BytesIO
from uuid import UUID

from flask import Blueprint, Response, current_app, jsonify, request, send_file

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


def _conversor_imagen():
    """Conversor de imágenes inyectado desde `create_app` (convierte RAW de
    cámara a JPEG; la capa API no depende de `infrastructure`)."""
    return current_app.config["CONVERSOR_IMAGEN"]


def _a_publico_producto(producto) -> dict:
    return {
        "id": str(producto.id),
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "stock": producto.stock,
        "imagen": producto.imagen,
        "imagen_thumb": producto.imagen_thumb,
        "activo": producto.activo,
        "categoria_id": str(producto.categoria_id),
        "specs": producto.specs,
        "descuento": producto.descuento,
        "precio_original": producto.precio_original,
        "material": producto.material,
        "tamano": producto.tamano,
        "color": producto.color,
        "nuevo_lanzamiento": bool(producto.nuevo_lanzamiento),
        # Etiqueta de la card, derivada del flag en la frontera y NO persistida:
        # la columna `badge` queda reservada para valores manuales (p.ej.
        # "Best Seller") y asi conviven "Nuevo" y "Best Seller" sin pisarse.
        # Si se guardara, apagar el flag dejaria el "Nuevo" pegado en la fila.
        "badge": "Nuevo" if producto.nuevo_lanzamiento else producto.badge,
        # La home ordena "Lanzamientos" del mas nuevo al mas viejo, asi que la
        # fecha de alta tiene que viajar en el JSON: la API ordena por nombre.
        "creado_en": producto.creado_en.isoformat() if producto.creado_en else None,
    }


def _a_publico_color(color) -> dict:
    return {
        "id": str(color.id),
        "producto_id": str(color.producto_id),
        "nombre": color.nombre,
        "orden": color.orden,
        "imagen": color.imagen_url,
        "imagen_thumb": color.imagen_thumb_url,
    }


def _a_publico_categoria(categoria) -> dict:
    return {
        "id": str(categoria.id),
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion,
    }


CACHE_IMAGENES_SEGUNDOS = 604800  # 7 dias


def _enviar_imagen(imagen) -> Response:
    """Sirve un BLOB de imagen como respuesta cacheable.

    Siete dias de cache porque una foto de producto cambia muy pocas veces, y el
    navegador deja de volver a bajarla en cada visita al catalogo. Al reemplazar
    la foto se regenera el thumbnail en el mismo alta, asi que la unica
    ventana de cache viejo es la que dura el nombre del archivo; si hace falta,
    un CDN con purge resuelve eso sin tocar estos endpoints.
    """
    respuesta = send_file(
        BytesIO(imagen.bytes),
        mimetype=imagen.content_type or "application/octet-stream",
    )
    # El `Cache-Control` se setea sobre la respuesta: `send_file` no tiene
    # parametros de cache, y ademas manda `no-cache` por defecto (Werkzeug no
    # quiere que se cachee un stream sin nombre). Hay que sacarlo de encima,
    # porque `no-cache` + `max-age` se contradicen: `no-cache` obliga al
    # navegador a revalidar en cada visita, que es justo lo que se vino a
    # evitar. `public` habilita el cache compartido (gateway/CDN): estas fotos
    # no dependen de quien las pida.
    respuesta.cache_control.max_age = CACHE_IMAGENES_SEGUNDOS
    respuesta.cache_control.no_cache = False
    respuesta.cache_control.public = True
    return respuesta


@catalogo_bp.get("/productos")
def listar_productos():
    productos = _servicio_producto().listar_con_foto_de_color()
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
    return _enviar_imagen(imagen)


@catalogo_bp.get("/productos/<uuid:producto_id>/thumb")
def thumb_producto(producto_id):
    """Thumbnail del producto para la tarjeta del catalogo.

    Se genera en la primera peticion y queda cacheado en la BD. Si no se puede
    generar (foto ya chica, Pillow ausente, archivo ilegible) se sirve la
    imagen original: es preferible descargar la foto grande que dejar la
    tarjeta rota.
    """
    servicio = _servicio_producto()
    imagen = servicio.obtener_thumb(producto_id)
    if imagen is None:
        imagen = servicio.consultar_imagen(producto_id)
    if imagen is None:
        return jsonify(mensaje="Imagen no encontrada"), 404
    return _enviar_imagen(imagen)


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
            nuevo_lanzamiento=bool(datos.get("nuevo_lanzamiento", False)),
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
            # Sin `.get(...) or False`: tiene que distinguir "no vino el campo"
            # (None = no tocar) de "vino en False" (apagar el lanzamiento).
            nuevo_lanzamiento=datos.get("nuevo_lanzamiento"),
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
    datos = archivo.read()
    try:
        datos, content_type = _conversor_imagen()(
            datos, archivo.content_type, archivo.filename
        )
    except ValueError as e:
        return jsonify(mensaje=str(e)), 400
    from app.domain.entities.producto import ImagenProducto
    imagen = ImagenProducto(bytes=datos, content_type=content_type)
    try:
        _servicio_producto().guardar_imagen(producto_id, imagen)
    except Exception as e:
        return jsonify(mensaje=f"Error al guardar imagen: {e}"), 500
    return jsonify(mensaje="Imagen subida correctamente"), 201


@catalogo_bp.get("/productos/<uuid:producto_id>/colores")
def listar_colores(producto_id):
    """Colores del producto. Lista vacia = producto de una sola foto."""
    if _servicio_producto().consultar(producto_id) is None:
        return jsonify(mensaje="Producto no encontrado"), 404
    colores = _servicio_producto().listar_colores(producto_id)
    return jsonify(colores=[_a_publico_color(c) for c in colores])


@catalogo_bp.get("/productos/colores/<uuid:color_id>/imagen")
def imagen_color(color_id):
    """Sirve la imagen de una variante de color como BLOB."""
    imagen = _servicio_producto().consultar_imagen_color(color_id)
    if imagen is None:
        return jsonify(mensaje="Imagen no encontrada"), 404
    return _enviar_imagen(imagen)


@catalogo_bp.get("/productos/colores/<uuid:color_id>/thumb")
def thumb_color(color_id):
    """Thumbnail de un color para las miniaturas del selector de color.

    Misma generacion perezosa y mismo fallback a la original que el thumbnail
    del producto.
    """
    servicio = _servicio_producto()
    imagen = servicio.obtener_thumb_color(color_id)
    if imagen is None:
        imagen = servicio.consultar_imagen_color(color_id)
    if imagen is None:
        return jsonify(mensaje="Imagen no encontrada"), 404
    return _enviar_imagen(imagen)


@catalogo_bp.post("/productos/<uuid:producto_id>/colores")
@requiere_sesion()
@rol_requerido("admin")
def guardar_color(producto_id):
    """Crea o reemplaza un color del producto con su foto (multipart).

    Campo `color`: nombre del color. Campo `imagen`: la foto (acepta RAW de
    camara, se convierte a JPEG igual que la imagen principal).
    """
    if "imagen" not in request.files:
        return jsonify(mensaje="Campo 'imagen' requerido"), 400
    archivo = request.files["imagen"]
    if not archivo.filename:
        return jsonify(mensaje="Archivo vacio"), 400
    nombre = (request.form.get("color") or "").strip()
    if not nombre:
        return jsonify(mensaje="Campo 'color' requerido"), 400
    try:
        datos, content_type = _conversor_imagen()(
            archivo.read(), archivo.content_type, archivo.filename
        )
    except ValueError as e:
        return jsonify(mensaje=str(e)), 400
    from app.domain.entities.producto import ImagenProducto

    imagen = ImagenProducto(bytes=datos, content_type=content_type)
    try:
        color = _servicio_producto().guardar_color(producto_id, nombre, imagen)
    except ValueError as e:
        mensaje = str(e)
        if "no encontrado" in mensaje.lower():
            return jsonify(mensaje=mensaje), 404
        return jsonify(mensaje=mensaje), 400
    except Exception as e:
        return jsonify(mensaje=f"Error al guardar color: {e}"), 500
    return jsonify(_a_publico_color(color)), 201


@catalogo_bp.delete("/productos/colores/<uuid:color_id>")
@requiere_sesion()
@rol_requerido("admin")
def eliminar_color(color_id):
    try:
        _servicio_producto().eliminar_color(color_id)
    except ValueError as e:
        return jsonify(mensaje=str(e)), 404
    return jsonify(mensaje="Color eliminado correctamente")
