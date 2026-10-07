from typing import Any, Callable
from uuid import UUID

from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO
from app.domain.entities.producto import (
    ColorProducto,
    ImagenProducto,
    Producto,
)
from app.domain.interfaces.repositories import ProductoRepository


IVA_PORCENTAJE = 19


def _aplicar_descuento(precio: int, descuento: int | None) -> int:
    """Precio final restando el descuento sobre el precio base.

    El descuento BAJA lo que paga el cliente: `precio * (1 - descuento/100)`.
    Se usa aritmetica de enteros (como `_aplicar_iva`) para evitar errores de
    punto flotante: `ceil(11900 * 90/100)` con floats daria 10711, no 10710.
    """
    if not descuento or descuento >= 100:
        return precio
    return (precio * (100 - descuento) + 99) // 100


def _aplicar_iva(precio_neto: int) -> int:
    """Precio final con IVA incluido, redondeado hacia arriba a pesos enteros."""
    if precio_neto <= 0:
        return precio_neto
    return (precio_neto * (100 + IVA_PORCENTAJE) + 99) // 100


class GestionarProducto:
    """Caso de uso: CRUD de productos del catálogo.

    `generador_thumb` es la funcion de infraestructura que reduce una foto a un
    thumbnail (Pillow). Se recibe inyectada porque `application` no puede
    importar `infrastructure`; si es `None` no hay thumbnails y las rutas
    sirven siempre la imagen original.
    """

    def __init__(
        self,
        repositorio: ProductoRepository,
        generador_thumb: Callable[[bytes, str], tuple[bytes, str] | None] | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._generador_thumb = generador_thumb

    def crear(self, dto: CrearProductoDTO) -> Producto:
        precio_base = _aplicar_iva(dto.precio)
        precio_final = _aplicar_descuento(precio_base, dto.descuento)
        precio_original = precio_base if dto.descuento and dto.descuento > 0 else None
        producto = Producto(
            nombre=dto.nombre,
            categoria_id=dto.categoria_id,
            precio=precio_final,
            stock=dto.stock,
            descripcion=dto.descripcion,
            imagen=dto.imagen,
            material=dto.material,
            tamano=dto.tamano,
            color=dto.color,
            specs=dto.specs,
            descuento=dto.descuento,
            precio_original=precio_original,
            nuevo_lanzamiento=dto.nuevo_lanzamiento,
            stock_minimo=dto.stock_minimo,
        )
        return self._repositorio.add(producto)

    def consultar(self, producto_id: UUID) -> Producto | None:
        return self._repositorio.get_by_id(producto_id)

    def consultar_imagen(self, producto_id: UUID) -> ImagenProducto | None:
        return self._repositorio.get_imagen_by_id(producto_id)

    def obtener_thumb(self, producto_id: UUID) -> ImagenProducto | None:
        """Thumbnail del producto, generandolo la primera vez.

        El catalogo pedia 43 MB para 18 productos porque cada tarjeta
        descargaba la foto completa. Aqui se devuelve la version reducida: si ya
        esta cacheada se lee de la BD, y si no se genera desde el original y se
        guarda para las proximas peticiones.

        Devuelve `None` cuando el producto no tiene foto, cuando no hay
        generador (Pillow ausente), cuando Pillow no puede decodificar la foto o
        cuando la original ya es chica. En todos esos casos la ruta debe servir
        la imagen original.
        """
        thumb = self._repositorio.get_thumb_by_id(producto_id)
        if thumb is not None:
            return thumb

        if self._generador_thumb is None:
            return None

        original = self._repositorio.get_imagen_by_id(producto_id)
        if original is None or not original.bytes:
            return None

        generado = self._generador_thumb(original.bytes, original.content_type)
        if generado is None:
            return None

        thumb = ImagenProducto(bytes=generado[0], content_type=generado[1])
        self._repositorio.guardar_thumb(producto_id, thumb)
        return thumb

    def obtener_thumb_color(self, color_id: UUID) -> ImagenProducto | None:
        """Thumbnail de un color, con la misma generacion perezosa y cache."""
        thumb = self._repositorio.get_color_thumb_by_id(color_id)
        if thumb is not None:
            return thumb

        if self._generador_thumb is None:
            return None

        original = self._repositorio.get_color_imagen_by_id(color_id)
        if original is None or not original.bytes:
            return None

        generado = self._generador_thumb(original.bytes, original.content_type)
        if generado is None:
            return None

        thumb = ImagenProducto(bytes=generado[0], content_type=generado[1])
        self._repositorio.guardar_color_thumb(color_id, thumb)
        return thumb

    def listar(self) -> list[Producto]:
        return self._repositorio.list_activos()

    def listar_con_foto_de_color(self) -> list[Producto]:
        """Catalogo para el listado, con una foto garantizada por producto.

        Un producto puede no tener foto principal y tener solo fotos de color
        (por ejemplo al crearlo con variantes y sin foto general). En ese caso
        se completa con la del primer color para que la tarjeta no quede vacia,
        junto con su thumbnail si ya fue generado.
        """
        productos = self._repositorio.list_activos()
        sin_foto = [p for p in productos if not p.imagen]
        if not sin_foto:
            return productos

        por_producto = self._repositorio.primera_imagen_color_por_producto(
            [p.id for p in sin_foto]
        )
        for producto in sin_foto:
            foto = por_producto.get(producto.id)
            if foto:
                producto.imagen = foto.imagen_url
                # Solo si ese color ya tiene thumbnail cacheado: la URL se
                # expone para que la tarjeta no baje la foto completa.
                producto.imagen_thumb = foto.imagen_thumb_url
        return productos

    def actualizar(self, dto: ActualizarProductoDTO) -> Producto:
        producto = self._repositorio.get_by_id(dto.id)
        if producto is None:
            raise ValueError("Producto no encontrado")
        if dto.nombre is not None:
            producto.nombre = dto.nombre
        if dto.categoria_id is not None:
            producto.categoria_id = dto.categoria_id
        if dto.precio is not None:
            producto.precio = dto.precio
        if dto.stock is not None:
            producto.stock = dto.stock
        if dto.descripcion is not None:
            producto.descripcion = dto.descripcion
        if dto.activo is not None:
            producto.activo = dto.activo
        if dto.material is not None:
            producto.material = dto.material
        if dto.tamano is not None:
            producto.tamano = dto.tamano
        if dto.color is not None:
            producto.color = dto.color
        if dto.specs is not None:
            producto.specs = dto.specs
        if dto.descuento is not None:
            producto.descuento = dto.descuento
        if dto.precio is not None or dto.descuento is not None:
            # El precio que se guarda es la base (final con IVA). Con
            # descuento, lo que paga el cliente BAJA y `precio_original`
            # guarda la base como "antes de la oferta". Si llega solo el
            # descuento, la base se recupera de `precio_original` (nunca del
            # precio ya rebajado, o el descuento se aplicaria dos veces).
            base = dto.precio if dto.precio is not None else (
                producto.precio_original or producto.precio
            )
            if producto.descuento and producto.descuento > 0:
                producto.precio_original = base
                producto.precio = _aplicar_descuento(base, producto.descuento)
            else:
                producto.precio = base
                producto.precio_original = None
        # `is not None` y no truthy: apagar un lanzamiento manda `False`, y con
        # un if truthy el producto quedaria marcado para siempre.
        if dto.nuevo_lanzamiento is not None:
            producto.nuevo_lanzamiento = dto.nuevo_lanzamiento
        if dto.stock_minimo is not None:
            producto.stock_minimo = dto.stock_minimo
        return self._repositorio.update(producto)

    def eliminar(self, producto_id: UUID) -> None:
        producto = self._repositorio.get_by_id(producto_id)
        if producto is None:
            raise ValueError("Producto no encontrado")
        self._repositorio.delete(producto)

    def guardar_imagen(self, producto_id: UUID, imagen: ImagenProducto) -> None:
        """Guarda la foto del producto y genera su thumbnail en el mismo acto.

        El repositorio invalida el thumbnail cacheado al reemplazar la foto
        (la vieja ya no corresponde). Aprovechar que los bytes de la nueva foto
        estan ahi para generarlo ahora evita que el primer `GET /thumb` que
        llegue pague el trabajo de Pillow en la respuesta: la tarjeta del
        catalogo ya sale con su `imagen_thumb` desde el primer listado.
        """
        self._repositorio.guardar_imagen(producto_id, imagen)
        self._regenerar_thumb(producto_id, imagen, self._repositorio.guardar_thumb)

    def _regenerar_thumb(
        self,
        imagen_id: UUID,
        imagen: ImagenProducto,
        guardar: Callable[[UUID, ImagenProducto], None],
    ) -> None:
        """Genera y persiste el thumbnail de la foto que se acaba de guardar.

        `guardar` es inyectado para no repetir el codigo entre producto y
        color, cuyos metodos del repositorio se llaman distinto. Un `None` del
        generador no es un error (foto ya chica, Pillow ausente, archivo
        ilegible): en ese caso no se guarda nada y las rutas siguen cayendo a la
        imagen original.
        """
        if self._generador_thumb is None or not imagen.bytes:
            return

        generado = self._generador_thumb(imagen.bytes, imagen.content_type)
        if generado is None:
            return

        guardar(
            imagen_id,
            ImagenProducto(bytes=generado[0], content_type=generado[1]),
        )

    def listar_colores(self, producto_id: UUID) -> list[ColorProducto]:
        """Colores del producto. Lista vacia = producto de una sola foto."""
        return self._repositorio.list_colores(producto_id)

    def consultar_color(self, color_id: UUID) -> ColorProducto | None:
        return self._repositorio.get_color_by_id(color_id)

    def consultar_imagen_color(self, color_id: UUID) -> ImagenProducto | None:
        return self._repositorio.get_color_imagen_by_id(color_id)

    def guardar_color(
        self, producto_id: UUID, nombre: str, imagen: ImagenProducto
    ) -> ColorProducto:
        """Crea o reemplaza un color del producto con su foto.

        Igual que la foto principal, el thumbnail se genera en el acto: el
        selector de color lo muestra en swatches de 24px y asi no espera a que
        alguien pida `GET /productos/colores/<id>/thumb`.
        """
        producto = self._repositorio.get_by_id(producto_id)
        if producto is None:
            raise ValueError("Producto no encontrado")
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre del color es obligatorio")
        color = self._repositorio.guardar_color(producto_id, nombre, imagen)
        self._regenerar_thumb(color.id, imagen, self._repositorio.guardar_color_thumb)
        return color

    def eliminar_color(self, color_id: UUID) -> None:
        self._repositorio.eliminar_color(color_id)
