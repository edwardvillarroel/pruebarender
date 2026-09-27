from unittest.mock import Mock
from uuid import uuid4

from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.domain.entities.producto import ImagenProducto, Producto
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_color_model import ProductoColorModel
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.repositories.producto_repository import ProductoRepository

FOTO_NUEVA = ImagenProducto(bytes=b"n" * 9000, content_type="image/jpeg")


class _FilaProducto:
    """Fila de resultado que se lee por posición y por atributo.

    `get_by_id`/`list_activos` reciben la tupla
    `(modelo, tiene_thumb, tiene_imagen)`, mientras que `get_thumb_by_id` lee
    `fila.imagen_thumb_bytes`. Delegar en el modelo hace que las dos lecturas
    reflejen el mismo estado, que es justo lo que necesita un test de
    invalidación: tras borrar la foto hay que ver el thumbnail como `None` y no
    como el valor viejo cacheado.
    """

    def __init__(
        self,
        modelo,
        tiene_thumb: bool = False,
        tiene_imagen: bool | None = None,
    ):
        self.modelo = modelo
        self.tiene_thumb = tiene_thumb
        # Sin valor explicito se deduce del modelo, igual que hace el SELECT con
        # `imagen_bytes.isnot(None)`.
        self.tiene_imagen = (
            tiene_imagen
            if tiene_imagen is not None
            else getattr(modelo, "imagen_bytes", None) is not None
        )

    def __getitem__(self, indice):
        return (self.modelo, self.tiene_thumb, self.tiene_imagen)[indice]

    def __getattr__(self, nombre):
        return getattr(self.modelo, nombre)


def _preparar_producto(activo: bool) -> tuple[Producto, ProductoModel]:
    producto = Producto(
        nombre="Producto de prueba",
        categoria_id=uuid4(),
        precio=100,
        stock=2,
    )
    modelo = ProductoModel()
    modelo.id = producto.id
    modelo.nombre = producto.nombre
    modelo.categoria_id = producto.categoria_id
    modelo.precio = producto.precio
    modelo.stock = producto.stock
    modelo.activo = activo
    return producto, modelo


def _preparar_sesion(monkeypatch, modelo: ProductoModel, color=None):
    filas = {modelo.id: modelo}
    if color is not None:
        filas[color.id] = color
    session = Mock()
    session.get.side_effect = lambda _model, clave: filas.get(clave)
    session.delete.side_effect = lambda producto: filas.pop(producto.id)

    # `get_by_id`/`list_activos` piden el modelo y, en el mismo SELECT, si ya
    # existe el thumbnail (`imagen_thumb_bytes.isnot(None)`) y la foto
    # (`imagen_bytes.isnot(None)`). El resultado de SQLAlchemy es una tupla
    # `(modelo, tiene_thumb, tiene_imagen)`, no el modelo solo.
    # `guardar_color` usa el mismo `execute` con `scalar_one_or_none()` (¿el
    # color existe ya?) y `scalar_one()` (siguiente `orden`).
    resultado = Mock()
    resultado.first.return_value = _FilaProducto(modelo, False)
    resultado.all.return_value = [_FilaProducto(modelo, False)]
    resultado.scalar_one_or_none.return_value = color
    resultado.scalar_one.return_value = 0
    session.execute.return_value = resultado

    monkeypatch.setattr(db, "session", session)
    return filas, session


def _preparar_color(producto_id, thumb_cacheado: bytes = b"t" * 300) -> ProductoColorModel:
    """Color de prueba con un thumbnail ya cacheado."""
    color = ProductoColorModel()
    color.id = uuid4()
    color.producto_id = producto_id
    color.nombre = "Rojo"
    color.orden = 0
    color.imagen_bytes = b"f" * 5000
    color.imagen_content_type = "image/jpeg"
    color.imagen_thumb_bytes = thumb_cacheado
    color.imagen_thumb_content_type = "image/jpeg"
    return color


def test_eliminar_archiva_producto_sin_borrar_fila(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    filas, session = _preparar_sesion(monkeypatch, modelo)

    GestionarProducto(ProductoRepository()).eliminar(producto.id)

    assert modelo.activo is False
    assert filas[producto.id] is modelo
    session.delete.assert_not_called()
    session.commit.assert_called_once_with()


def test_eliminar_es_idempotente_para_producto_inactivo(monkeypatch):
    producto, modelo = _preparar_producto(activo=False)
    filas, session = _preparar_sesion(monkeypatch, modelo)

    GestionarProducto(ProductoRepository()).eliminar(producto.id)

    assert modelo.activo is False
    assert filas[producto.id] is modelo
    session.delete.assert_not_called()
    session.commit.assert_called_once_with()


# --- Invalidación del thumbnail al reemplazar la foto -------------------------
#
# El thumbnail es un caché derivado del BLOB original. Si se reemplaza la foto y
# el caché sobrevive, la tarjeta del catálogo sigue mostrando la foto anterior y
# no hay ningún error visible: la imagen sale bien, solo que vieja. Por eso la
# invalidación va dentro del propio `guardar_imagen`/`guardar_color` (es un
# invariante de persistencia) y por eso tiene cobertura acá.
#
# Estas pruebas usan el repositorio real contra una sesión `Mock` en vez de una
# BD: el paso que hay que verificar es que las columnas `imagen_thumb_*` queden
# en `None` y que la escritura confirme. Un `UPDATE` sin `commit` no fallaría
# contra una BD falsa que no transacciona, así que el `commit` se afirma
# explícitamente en cada caso.


def test_reemplazar_la_foto_borra_el_thumbnail_cacheado(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen_bytes = b"vieja" * 1000
    modelo.imagen_content_type = "image/png"
    modelo.imagen_thumb_bytes = b"thumb-viejo"
    modelo.imagen_thumb_content_type = "image/jpeg"
    _preparar_sesion(monkeypatch, modelo)

    ProductoRepository().guardar_imagen(producto.id, FOTO_NUEVA)

    assert modelo.imagen_thumb_bytes is None
    assert modelo.imagen_thumb_content_type is None
    # La original sí se reemplaza: el thumbnail se borra, la foto no.
    assert modelo.imagen_bytes == FOTO_NUEVA.bytes
    assert modelo.imagen_content_type == FOTO_NUEVA.content_type


def test_reemplazar_la_foto_confirma_el_borrado_del_thumbnail(monkeypatch):
    # Sin `commit` el `None` queda solo en la sesión y se pierde: es el bug que
    # tenía el `invalidar_thumb` que se eliminó por código muerto.
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen_thumb_bytes = b"thumb-viejo"
    _, session = _preparar_sesion(monkeypatch, modelo)

    ProductoRepository().guardar_imagen(producto.id, FOTO_NUEVA)

    session.commit.assert_called_once_with()


def test_tras_reemplazar_la_foto_el_thumbnail_se_regenera(monkeypatch):
    """Comportamiento observable: la tarjeta deja de mostrar la foto vieja.

    No alcanza con afirmar que la columna quedó en `None`: lo que importa es que
    el caso de uso, al pedir el thumbnail de nuevo, no sirva el caché anterior
    sino que lo regenere desde la foto nueva.
    """
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen_bytes = b"vieja" * 1000
    modelo.imagen_content_type = "image/png"
    modelo.imagen_thumb_bytes = b"thumb-viejo"
    modelo.imagen_thumb_content_type = "image/jpeg"
    _preparar_sesion(monkeypatch, modelo)

    repositorio = ProductoRepository()
    servicio = GestionarProducto(
        repositorio, generador_thumb=Mock(return_value=(b"thumb-nuevo", "image/jpeg"))
    )
    repositorio.guardar_imagen(producto.id, FOTO_NUEVA)

    resultado = servicio.obtener_thumb(producto.id)

    assert resultado is not None
    assert resultado.bytes == b"thumb-nuevo"


def test_reemplazar_la_foto_de_un_color_borra_su_thumbnail(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    color = _preparar_color(producto.id)
    _preparar_sesion(monkeypatch, modelo, color=color)

    ProductoRepository().guardar_color(producto.id, "Rojo", FOTO_NUEVA)

    assert color.imagen_thumb_bytes is None
    assert color.imagen_thumb_content_type is None
    assert color.imagen_bytes == FOTO_NUEVA.bytes


def test_guardar_el_thumbnail_confirma_la_escritura(monkeypatch):
    # Contraparte del borrado: escribir el caché también tiene que commitear, o
    # se regeneraría en cada request (2,4 MB de Pillow por visita al catálogo).
    producto, modelo = _preparar_producto(activo=True)
    _, session = _preparar_sesion(monkeypatch, modelo)

    ProductoRepository().guardar_thumb(
        producto.id, ImagenProducto(bytes=b"t" * 300, content_type="image/jpeg")
    )

    session.commit.assert_called_once_with()


# --- La foto es el BLOB, no la URL de `productos.imagen` ----------------------
#
# `guardar_imagen` escribe la URL en la columna de texto `imagen` la primera vez
# y nunca la vuelve a validar. Si el BLOB se borra o nunca se guardo, la URL
# sigue ahi y el repositorio reportaba un producto "con foto": la tarjeta pedia
# una imagen que responde 404 y, peor, `listar_con_foto_de_color` lo excluia de
# la busqueda, asi que las fotos de color del producto nunca se usaban.
#
# La foto real es `imagen_bytes`. El SELECT la consulta con `isnot(None)` en la
# misma consulta (igual que el thumbnail) para no disparar un SELECT por
# producto, que es el N+1 que este listado ya tuvo que arreglar.


def test_listar_activos_no_reporta_foto_si_solo_queda_la_url(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    # URL persistida de una subida anterior, sin BLOB que la respalde.
    modelo.imagen = f"/api/productos/{producto.id}/imagen"
    _preparar_sesion(monkeypatch, modelo)

    listado = ProductoRepository().list_activos()

    assert [p.imagen for p in listado] == [None]


def test_listar_activos_expone_la_ruta_de_imagen_cuando_hay_blob(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen_bytes = b"foto" * 1000
    modelo.imagen_content_type = "image/png"
    _preparar_sesion(monkeypatch, modelo)

    listado = ProductoRepository().list_activos()

    assert [p.imagen for p in listado] == [f"/api/productos/{producto.id}/imagen"]


def test_listar_activos_omite_el_thumbnail_sin_blob_de_thumb(monkeypatch):
    # La foto y el thumbnail son caches distintos: tener foto no implica tener
    # thumbnail cacheado, y por eso `imagen_thumb` sale en `None`.
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen_bytes = b"foto" * 1000
    _preparar_sesion(monkeypatch, modelo)

    listado = ProductoRepository().list_activos()

    assert listado[0].imagen_thumb is None


def test_obtener_producto_tambien_ignora_la_url_sin_blob(monkeypatch):
    # `get_by_id` alimenta el detalle: la URL rota se repetía ahí también.
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen = f"/api/productos/{producto.id}/imagen"
    _preparar_sesion(monkeypatch, modelo)

    resultado = ProductoRepository().get_by_id(producto.id)

    assert resultado is not None
    assert resultado.imagen is None
