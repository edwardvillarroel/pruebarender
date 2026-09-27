from unittest.mock import Mock
from uuid import uuid4

from app.application.catalogo_stock.gestionar_producto import (
    GestionarProducto,
    _aplicar_iva,
)
from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO
from app.domain.entities.producto import Producto


def _repositorio(producto_existente: Producto | None = None) -> Mock:
    repositorio = Mock()
    repositorio.add.side_effect = lambda producto: producto
    repositorio.update.side_effect = lambda producto: producto
    repositorio.get_by_id.return_value = producto_existente
    return repositorio


def _dto_creacion(precio: int, descuento: int | None = None) -> CrearProductoDTO:
    return CrearProductoDTO(
        nombre="Producto de prueba",
        categoria_id=uuid4(),
        precio=precio,
        stock=2,
        descuento=descuento,
    )


def test_aplicar_iva_suma_19_por_ciento_y_redondea_hacia_arriba():
    assert _aplicar_iva(4000) == 4760
    assert _aplicar_iva(100) == 119
    assert _aplicar_iva(1) == 2
    assert _aplicar_iva(99) == 118


def test_aplicar_iva_devuelve_sin_cambiar_precios_no_positivos():
    assert _aplicar_iva(0) == 0
    assert _aplicar_iva(-4000) == -4000


def test_crear_almacena_el_precio_final_con_iva():
    repositorio = _repositorio()
    dto = _dto_creacion(4000)

    producto = GestionarProducto(repositorio).crear(dto)

    assert producto.precio == 4760
    assert producto.precio_original is None
    assert dto.precio == 4000
    repositorio.add.assert_called_once_with(producto)


def test_crear_calcula_el_precio_original_sobre_el_precio_con_iva():
    repositorio = _repositorio()

    producto = GestionarProducto(repositorio).crear(_dto_creacion(4000, descuento=10))

    assert producto.precio == 4760
    assert producto.precio_original == 5289


def test_actualizar_guarda_el_precio_tal_cual_sin_volver_a_aplicar_iva():
    existente = Producto(nombre="Existente", categoria_id=uuid4(), precio=4760, stock=1)
    repositorio = _repositorio(existente)
    dto = ActualizarProductoDTO(id=existente.id, precio=5000)

    resultado = GestionarProducto(repositorio).actualizar(dto)

    assert resultado.precio == 5000
    repositorio.update.assert_called_once_with(existente)
