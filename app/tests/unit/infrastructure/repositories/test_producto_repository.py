from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO
from app.domain.entities.producto import ImagenProducto, Producto
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_color_model import ProductoColorModel
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.repositories.producto_repository import ProductoRepository

FOTO_NUEVA = ImagenProducto(bytes=b"n" * 9000, content_type="image/jpeg")


class _FilaProducto:


    def __init__(
        self,
        modelo,
        tiene_thumb: bool = False,
        tiene_imagen: bool | None = None,
    ):
        self.modelo = modelo
        self.tiene_thumb = tiene_thumb
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

    resultado = Mock()
    resultado.first.return_value = _FilaProducto(modelo, False)
    resultado.all.return_value = [_FilaProducto(modelo, False)]
    resultado.scalar_one_or_none.return_value = color
    resultado.scalar_one.return_value = 0
    session.execute.return_value = resultado

    monkeypatch.setattr(db, "session", session)
    return filas, session


def _preparar_color(producto_id, thumb_cacheado: bytes = b"t" * 300) -> ProductoColorModel:
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
    assert modelo.imagen_bytes == FOTO_NUEVA.bytes
    assert modelo.imagen_content_type == FOTO_NUEVA.content_type


def test_reemplazar_la_foto_confirma_el_borrado_del_thumbnail(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen_thumb_bytes = b"thumb-viejo"
    _, session = _preparar_sesion(monkeypatch, modelo)

    ProductoRepository().guardar_imagen(producto.id, FOTO_NUEVA)

    session.commit.assert_called_once_with()


def test_tras_reemplazar_la_foto_el_thumbnail_se_regenera(monkeypatch):

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
    producto, modelo = _preparar_producto(activo=True)
    _, session = _preparar_sesion(monkeypatch, modelo)

    ProductoRepository().guardar_thumb(
        producto.id, ImagenProducto(bytes=b"t" * 300, content_type="image/jpeg")
    )

    session.commit.assert_called_once_with()




def test_listar_activos_no_reporta_foto_si_solo_queda_la_url(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
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
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen_bytes = b"foto" * 1000
    _preparar_sesion(monkeypatch, modelo)

    listado = ProductoRepository().list_activos()

    assert listado[0].imagen_thumb is None


def test_obtener_producto_tambien_ignora_la_url_sin_blob(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.imagen = f"/api/productos/{producto.id}/imagen"
    _preparar_sesion(monkeypatch, modelo)

    resultado = ProductoRepository().get_by_id(producto.id)

    assert resultado is not None
    assert resultado.imagen is None




def test_el_flag_de_lanzamiento_llega_del_modelo_a_la_entidad(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.nuevo_lanzamiento = True
    _preparar_sesion(monkeypatch, modelo)

    resultado = ProductoRepository().get_by_id(producto.id)

    assert resultado.nuevo_lanzamiento is True


def test_el_flag_de_lanzamiento_se_persiste_al_actualizar(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    _preparar_sesion(monkeypatch, modelo)
    producto.nuevo_lanzamiento = True

    GestionarProducto(ProductoRepository()).actualizar(
        ActualizarProductoDTO(id=producto.id, nuevo_lanzamiento=True)
    )

    assert modelo.nuevo_lanzamiento is True


def test_se_puede_apagar_el_flag_de_lanzamiento(monkeypatch):

    producto, modelo = _preparar_producto(activo=True)
    modelo.nuevo_lanzamiento = True
    _preparar_sesion(monkeypatch, modelo)

    GestionarProducto(ProductoRepository()).actualizar(
        ActualizarProductoDTO(id=producto.id, nuevo_lanzamiento=False)
    )

    assert modelo.nuevo_lanzamiento is False


def test_un_update_sin_el_flag_no_lo_toca(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.nuevo_lanzamiento = True
    _preparar_sesion(monkeypatch, modelo)

    GestionarProducto(ProductoRepository()).actualizar(
        ActualizarProductoDTO(id=producto.id, stock=7)
    )

    assert modelo.nuevo_lanzamiento is True


def test_crear_honora_el_flag_de_lanzamiento(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.nuevo_lanzamiento = True
    _preparar_sesion(monkeypatch, modelo)

    GestionarProducto(ProductoRepository()).crear(
        CrearProductoDTO(
            nombre="Producto nuevo",
            categoria_id=producto.categoria_id,
            precio=100,
            nuevo_lanzamiento=True,
        )
    )

    agregado = db.session.add.call_args[0][0]
    assert agregado.nuevo_lanzamiento is True




def test_el_stock_minimo_llega_del_modelo_a_la_entidad(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.stock_minimo = 5
    _preparar_sesion(monkeypatch, modelo)

    resultado = ProductoRepository().get_by_id(producto.id)

    assert resultado.stock_minimo == 5


def test_un_producto_sin_stock_minimo_no_inventa_umbral(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    modelo.stock_minimo = None
    _preparar_sesion(monkeypatch, modelo)

    resultado = ProductoRepository().get_by_id(producto.id)

    assert resultado.stock_minimo is None


def test_el_stock_minimo_se_persiste_al_actualizar(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    _preparar_sesion(monkeypatch, modelo)

    GestionarProducto(ProductoRepository()).actualizar(
        ActualizarProductoDTO(id=producto.id, stock_minimo=4)
    )

    assert modelo.stock_minimo == 4


def test_reponer_por_arriba_del_umbral_limpia_el_aviso(monkeypatch):
    producto, modelo = _preparar_producto(activo=False)
    modelo.stock_minimo = 3
    modelo.aviso_stock_enviado = True
    _preparar_sesion(monkeypatch, modelo)
    producto.stock = 20

    ProductoRepository().update(producto)

    assert modelo.aviso_stock_enviado is False


def test_reponer_sin_salir_del_umbral_mantiene_el_aviso(monkeypatch):
    producto, modelo = _preparar_producto(activo=False)
    modelo.stock_minimo = 3
    modelo.aviso_stock_enviado = True
    _preparar_sesion(monkeypatch, modelo)
    producto.stock = 3

    ProductoRepository().update(producto)

    assert modelo.aviso_stock_enviado is True
    assert producto.stock <= 3




class _FilaAgregacion:

    def __init__(self, producto_id, unidades: int, ingresos: int):
        self.producto_id = producto_id
        self.unidades = unidades
        self.ingresos = ingresos


def _preparar_sesion_ranking(monkeypatch, agregacion, productos):
    session = Mock()
    primero, segundo = Mock(), Mock()
    primero.all.return_value = agregacion
    segundo.all.return_value = productos
    session.execute.side_effect = [primero, segundo]
    monkeypatch.setattr(db, "session", session)
    return session


def _sql_de(consulta, literal_binds: bool = False) -> str:
    return str(
        consulta.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True} if literal_binds else {},
        )
    )


def test_el_ranking_solo_cuenta_pagos_completados(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    session = _preparar_sesion_ranking(
        monkeypatch,
        [_FilaAgregacion(producto.id, 3, 9000)],
        [_FilaProducto(modelo, False, True)],
    )

    ProductoRepository().listar_mas_vendidos(None, 10)

    sql = _sql_de(session.execute.call_args_list[0][0][0], literal_binds=True)
    assert "EXISTS" in sql
    assert "pagos.estado = 'completado'" in sql


def test_el_ranking_no_hace_join_con_pagos_para_no_multiplicar_lineas(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    session = _preparar_sesion_ranking(
        monkeypatch,
        [_FilaAgregacion(producto.id, 3, 9000)],
        [_FilaProducto(modelo, False, True)],
    )

    ProductoRepository().listar_mas_vendidos(None, 10)

    sql = _sql_de(session.execute.call_args_list[0][0][0])
    assert "JOIN pagos" not in sql


def test_el_ranking_solo_muestra_productos_activos(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    session = _preparar_sesion_ranking(
        monkeypatch,
        [_FilaAgregacion(producto.id, 3, 9000)],
        [_FilaProducto(modelo, False, True)],
    )

    ProductoRepository().listar_mas_vendidos(None, 10)

    sql = _sql_de(session.execute.call_args_list[0][0][0])
    assert "productos.activo IS true" in sql


def test_la_ventana_de_venta_filtra_por_la_fecha_del_pago(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    session = _preparar_sesion_ranking(
        monkeypatch,
        [_FilaAgregacion(producto.id, 3, 9000)],
        [_FilaProducto(modelo, False, True)],
    )

    ProductoRepository().listar_mas_vendidos(
        datetime(2026, 1, 1, tzinfo=timezone.utc), 10
    )

    sql = _sql_de(session.execute.call_args_list[0][0][0])
    assert "pagos.creado_en >=" in sql


def test_sin_ventana_de_venta_no_se_filtra_por_fecha(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    session = _preparar_sesion_ranking(
        monkeypatch,
        [_FilaAgregacion(producto.id, 3, 9000)],
        [_FilaProducto(modelo, False, True)],
    )

    ProductoRepository().listar_mas_vendidos(None, 10)

    sql = _sql_de(session.execute.call_args_list[0][0][0])
    assert "pagos.creado_en" not in sql


def test_el_ranking_pide_solo_el_limite_de_productos(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    session = _preparar_sesion_ranking(
        monkeypatch,
        [_FilaAgregacion(producto.id, 3, 9000)],
        [_FilaProducto(modelo, False, True)],
    )

    ProductoRepository().listar_mas_vendidos(None, 5)

    sql = _sql_de(session.execute.call_args_list[0][0][0], literal_binds=True)
    assert "LIMIT 5" in sql


def test_el_ranking_conserva_el_orden_de_la_agregacion(monkeypatch):
    primero, modelo_primero = _preparar_producto(activo=True)
    segundo, modelo_segundo = _preparar_producto(activo=True)
    _preparar_sesion_ranking(
        monkeypatch,
        [
            _FilaAgregacion(primero.id, 9, 9000),
            _FilaAgregacion(segundo.id, 4, 4000),
        ],
        [
            _FilaProducto(modelo_segundo, False, True),
            _FilaProducto(modelo_primero, False, True),
        ],
    )

    resultado = ProductoRepository().listar_mas_vendidos(None, 10)

    assert [v.producto.id for v in resultado] == [primero.id, segundo.id]
    assert [v.unidades for v in resultado] == [9, 4]
    assert [v.ingresos for v in resultado] == [9000, 4000]


def test_el_ranking_devuelve_los_ingresos_como_entero(monkeypatch):
    producto, modelo = _preparar_producto(activo=True)
    _preparar_sesion_ranking(
        monkeypatch,
        [_FilaAgregacion(producto.id, 3, 9000)],
        [_FilaProducto(modelo, False, True)],
    )

    resultado = ProductoRepository().listar_mas_vendidos(None, 10)

    assert isinstance(resultado[0].ingresos, int)
    assert isinstance(resultado[0].unidades, int)


def test_el_ranking_devuelve_lista_vacia_sin_ventas(monkeypatch):
    session = _preparar_sesion_ranking(monkeypatch, [], [])

    resultado = ProductoRepository().listar_mas_vendidos(None, 10)

    assert resultado == []
    assert session.execute.call_count == 1




def test_la_ventana_semanal_filtra_por_desde_y_hasta(monkeypatch):
    session = _preparar_sesion_ranking(monkeypatch, [], [])

    ProductoRepository().listar_mas_vendidos_en_ventana(
        datetime(2026, 10, 19, tzinfo=timezone.utc),
        datetime(2026, 10, 26, tzinfo=timezone.utc),
        10,
    )

    sql = _sql_de(session.execute.call_args_list[0][0][0], literal_binds=True)
    assert "pagos.creado_en >=" in sql
    assert "pagos.creado_en <" in sql


def test_contar_productos_distintos_cuenta_solo_pagos_completados(monkeypatch):
    session = Mock()
    session.execute.return_value.scalar.return_value = 3
    monkeypatch.setattr(db, "session", session)

    total = ProductoRepository().contar_productos_distintos(
        datetime(2026, 10, 19, tzinfo=timezone.utc),
        datetime(2026, 10, 26, tzinfo=timezone.utc),
    )

    assert total == 3
    sql = _sql_de(session.execute.call_args[0][0], literal_binds=True)
    assert "count(distinct(" in sql.lower()
    assert "pagos.estado = 'completado'" in sql
    assert "pagos.creado_en >=" in sql
    assert "pagos.creado_en <" in sql


def test_contar_productos_distintos_sin_ventas_devuelve_cero(monkeypatch):
    session = Mock()
    session.execute.return_value.scalar.return_value = None
    monkeypatch.setattr(db, "session", session)

    total = ProductoRepository().contar_productos_distintos(
        datetime(2026, 10, 19, tzinfo=timezone.utc),
        datetime(2026, 10, 26, tzinfo=timezone.utc),
    )

    assert total == 0

