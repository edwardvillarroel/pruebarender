from unittest.mock import Mock
from uuid import uuid4

from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.domain.entities.producto import Producto
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.repositories.producto_repository import ProductoRepository


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


def _preparar_sesion(monkeypatch, modelo: ProductoModel):
    filas = {modelo.id: modelo}
    session = Mock()
    session.get.side_effect = lambda _model, producto_id: filas.get(producto_id)
    session.delete.side_effect = lambda producto: filas.pop(producto.id)
    monkeypatch.setattr(db, "session", session)
    return filas, session


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
