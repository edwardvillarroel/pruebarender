from unittest.mock import Mock
from uuid import uuid4

from app.application.catalogo_stock.gestionar_producto import (
    GestionarProducto,
    _aplicar_descuento,
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

    assert producto.precio == 4284
    assert producto.precio_original == 4760


def test_crear_sin_descuento_no_guarda_precio_original():
    repositorio = _repositorio()

    producto = GestionarProducto(repositorio).crear(_dto_creacion(4000))

    assert producto.precio == 4760
    assert producto.precio_original is None


def test_aplicar_descuento_baja_el_precio_sin_error_de_punto_flotante():
    assert _aplicar_descuento(11900, 10) == 10710
    assert _aplicar_descuento(4760, 10) == 4284
    assert _aplicar_descuento(1000, 25) == 750


def test_aplicar_descuento_devuelve_el_precio_sin_cambios_fuera_de_rango():
    assert _aplicar_descuento(4000, 0) == 4000
    assert _aplicar_descuento(4000, None) == 4000
    assert _aplicar_descuento(4000, 100) == 4000


def test_actualizar_guarda_el_precio_tal_cual_sin_volver_a_aplicar_iva():
    existente = Producto(nombre="Existente", categoria_id=uuid4(), precio=4760, stock=1)
    repositorio = _repositorio(existente)
    dto = ActualizarProductoDTO(id=existente.id, precio=5000)

    resultado = GestionarProducto(repositorio).actualizar(dto)

    assert resultado.precio == 5000
    repositorio.update.assert_called_once_with(existente)


def test_actualizar_aplica_descuento_sobre_el_precio_recibido_como_base():
    existente = Producto(nombre="Existente", categoria_id=uuid4(), precio=5000, stock=1)
    repositorio = _repositorio(existente)
    dto = ActualizarProductoDTO(id=existente.id, precio=5000, descuento=10)

    resultado = GestionarProducto(repositorio).actualizar(dto)

    assert resultado.precio == 4500
    assert resultado.precio_original == 5000


def test_actualizar_quitar_descuento_restaura_el_precio_base():
    existente = Producto(
        nombre="Existente", categoria_id=uuid4(), precio=4500, stock=1,
        descuento=10, precio_original=5000,
    )
    repositorio = _repositorio(existente)
    dto = ActualizarProductoDTO(id=existente.id, descuento=0)

    resultado = GestionarProducto(repositorio).actualizar(dto)

    assert resultado.precio == 5000
    assert resultado.precio_original is None
    assert resultado.descuento == 0


def test_actualizar_cambiar_solo_descuento_recalcula_desde_el_original():
    existente = Producto(
        nombre="Existente", categoria_id=uuid4(), precio=4500, stock=1,
        descuento=10, precio_original=5000,
    )
    repositorio = _repositorio(existente)
    dto = ActualizarProductoDTO(id=existente.id, descuento=20)

    resultado = GestionarProducto(repositorio).actualizar(dto)

    assert resultado.precio == 4000
    assert resultado.precio_original == 5000


def test_actualizar_sin_tocar_precio_ni_descuento_no_recalcula():
    existente = Producto(
        nombre="Existente", categoria_id=uuid4(), precio=4000, stock=1,
        descuento=20, precio_original=5000,
    )
    repositorio = _repositorio(existente)
    dto = ActualizarProductoDTO(id=existente.id, stock=7)

    resultado = GestionarProducto(repositorio).actualizar(dto)

    assert resultado.precio == 4000
    assert resultado.precio_original == 5000
    repositorio.update.assert_called_once_with(existente)
