from io import BytesIO
from uuid import UUID

from flask import Blueprint, Response, current_app, jsonify, request, send_file

from app.api.middleware.auth import requiere_sesion, rol_requerido
from app.application.catalogo_stock.gestionar_categoria import GestionarCategoria
from app.application.catalogo_stock.gestionar_producto import (
    PERIODO_SEMANA,
    GestionarProducto,
)
from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO
from app.domain.entities.producto import STOCK_BAJO

catalogo_bp = Blueprint("catalogo", __name__)


def _servicio_producto() -> GestionarProducto:
    return current_app.config["PRODUCTO_SERVICE"]


def _servicio_categoria() -> GestionarCategoria:
    return current_app.config["CATEGORIA_SERVICE"]


def _conversor_imagen():
    return current_app.config["CONVERSOR_IMAGEN"]


def _a_publico_producto(producto) -> dict:
    return {
        "id": str(producto.id),
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "stock": producto.stock,
        "imagen": producto.imagen,
        "imagen_url": getattr(producto, "imagen_url", None),
        "imagen_thumb": producto.imagen_thumb,
        "activo": producto.activo,
        "categoria_id": str(producto.categoria_id),
        "specs": producto.specs,
        "descuento": producto.descuento,
        "precio_original": producto.precio_original,
        "rating": float(producto.rating) if producto.rating is not None else None,
        "resenas_count": producto.resenas_count or 0,
        "material": producto.material,
        "tamano": producto.tamano,
        "color": producto.color,
        "nuevo_lanzamiento": bool(producto.nuevo_lanzamiento),
        "stock_minimo": producto.stock_minimo,
        "stock_bajo": bool(
            producto.stock
            <= (producto.stock_minimo if producto.stock_minimo is not None else STOCK_BAJO)
        ),
        "badge": "Nuevo" if producto.nuevo_lanzamiento else producto.badge,
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
        "imagen_url": getattr(categoria, "imagen_url", None),
    }


CACHE_IMAGENES_SEGUNDOS = 604800


def _enviar_imagen(imagen) -> Response:

    respuesta = send_file(
        BytesIO(imagen.bytes),
        mimetype=imagen.content_type or "application/octet-stream",
        conditional=True,
    )
    respuesta.cache_control.max_age = CACHE_IMAGENES_SEGUNDOS
    respuesta.cache_control.no_cache = False
    respuesta.cache_control.public = True
    respuesta.cache_control.immutable = True
    try:
        import hashlib

        respuesta.headers["ETag"] = f'"{hashlib.md5(imagen.bytes).hexdigest()}"'
    except Exception:
        pass
    return respuesta


@catalogo_bp.get("/productos")
def listar_productos():
    productos = _servicio_producto().listar_con_foto_de_color()
    return jsonify(productos=[_a_publico_producto(p) for p in productos])


@catalogo_bp.get("/productos/mas-vendidos")
def mas_vendidos():



    periodo = (request.args.get("periodo") or "todo").strip().lower()
    limite = request.args.get("limite", 10)
    servicio = _servicio_producto()
    metadatos: dict = {}
    try:
        if periodo == PERIODO_SEMANA:
            ranking = servicio.listar_mas_vendidos_semana(limite)
            vendidos = ranking.productos
            metadatos["semana"] = {
                "tipo": ranking.tipo,
                "desde": ranking.desde.isoformat() if ranking.desde else None,
                "hasta": ranking.hasta.isoformat() if ranking.hasta else None,
                "productos_distintos_actual": ranking.productos_distintos_semana_actual,
            }
        else:
            vendidos = servicio.listar_mas_vendidos(periodo, limite)
    except ValueError as error:
        return jsonify(mensaje=str(error)), 400
    return jsonify(
        productos=[
            {
                **_a_publico_producto(v.producto),
                "unidades_vendidas": v.unidades,
                "ingresos": v.ingresos,
            }
            for v in vendidos
        ],
        periodo=periodo,
        total=len(vendidos),
        **metadatos,
    )


@catalogo_bp.get("/productos/<uuid:producto_id>")
def detalle_producto(producto_id):
    producto = _servicio_producto().consultar(producto_id)
    if producto is None:
        return jsonify(mensaje="Producto no encontrado"), 404
    return jsonify(_a_publico_producto(producto))


@catalogo_bp.get("/productos/<uuid:producto_id>/imagen")
def imagen_producto(producto_id):
    imagen = _servicio_producto().consultar_imagen(producto_id)
    if imagen is None:
        return jsonify(mensaje="Imagen no encontrada"), 404
    return _enviar_imagen(imagen)


@catalogo_bp.get("/productos/<uuid:producto_id>/thumb")
def thumb_producto(producto_id):

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
            stock_minimo=(
                int(datos["stock_minimo"])
                if datos.get("stock_minimo") is not None
                else None
            ),
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
            nuevo_lanzamiento=datos.get("nuevo_lanzamiento"),
            stock_minimo=(
                int(datos["stock_minimo"])
                if "stock_minimo" in datos and datos.get("stock_minimo") is not None
                else None
            ),
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


def _extension_desde_mime(content_type: str | None) -> str:
    mapa = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    return mapa.get((content_type or "").lower().strip(), ".jpg")


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

    imagen_url = None
    try:
        from app.infrastructure.storage.supabase_storage import (
            almacen_catalogo_desde_config,
            url_publica_catalogo,
        )

        almacen = almacen_catalogo_desde_config(current_app.config)
        if almacen is not None:
            ext = _extension_desde_mime(content_type)
            ruta = f"productos/{producto_id}{ext}"
            if almacen.subir(ruta, datos, content_type or "application/octet-stream"):
                imagen_url = url_publica_catalogo(almacen.url, ruta)
    except Exception:
        current_app.logger.exception("No se pudo subir imagen de producto al bucket catalogo")

    try:
        _servicio_producto().guardar_imagen(producto_id, imagen, imagen_url=imagen_url)
    except Exception as e:
        return jsonify(mensaje=f"Error al guardar imagen: {e}"), 500
    return jsonify(mensaje="Imagen subida correctamente", imagen_url=imagen_url), 201


@catalogo_bp.get("/productos/<uuid:producto_id>/colores")
def listar_colores(producto_id):
    if _servicio_producto().consultar(producto_id) is None:
        return jsonify(mensaje="Producto no encontrado"), 404
    colores = _servicio_producto().listar_colores(producto_id)
    return jsonify(colores=[_a_publico_color(c) for c in colores])


@catalogo_bp.get("/productos/colores/<uuid:color_id>/imagen")
def imagen_color(color_id):
    imagen = _servicio_producto().consultar_imagen_color(color_id)
    if imagen is None:
        return jsonify(mensaje="Imagen no encontrada"), 404
    return _enviar_imagen(imagen)


@catalogo_bp.get("/productos/colores/<uuid:color_id>/thumb")
def thumb_color(color_id):

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
