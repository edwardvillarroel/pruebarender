


from __future__ import annotations

import uuid as _uuid
from datetime import date, timedelta

import pytest

from app.application.venta_local.gestionar_venta_local import (
    GestionarVentaLocal,
    SesionNoAutorizada,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.usuario_model import UsuarioModel
from app.infrastructure.repositories.producto_repository import ProductoRepository
from app.infrastructure.repositories.venta_local_repository import VentaLocalRepository


@pytest.fixture
def venta_local(db_sesion, usuario):
    return GestionarVentaLocal(VentaLocalRepository(), ProductoRepository())


def _stock(producto) -> int:
    return db.session.execute(
        db.text("SELECT stock FROM productos WHERE id = :i"), {"i": producto.id}
    ).scalar_one()


def _otro_usuario(db_sesion) -> UsuarioModel:
    otro = UsuarioModel(
        email=f"r0-{_uuid.uuid4().hex[:12]}@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="Otro vendedor",
        apellido="Prueba",
    )
    db_sesion.add(otro)
    db_sesion.commit()
    return otro


def test_venta_exitosa_descuenta_stock_y_persiste_items(
    venta_local, usuario, producto
):
    p = producto(stock=10, precio=2500)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)

    venta = venta_local.registrar_venta(s.id, "efectivo", [(p.id, 3)], usuario.id)

    assert venta.total == 3 * 2500
    assert len(venta.items) == 1
    assert venta.items[0].cantidad == 3
    assert venta.items[0].precio_unitario == 2500
    assert _stock(p) == 7, "el stock no se desconto"


def test_no_se_puede_vender_mas_del_stock(venta_local, usuario, producto):
    p = producto(stock=2, precio=1000)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)

    with pytest.raises(ValueError, match="stock suficiente"):
        venta_local.registrar_venta(s.id, "efectivo", [(p.id, 3)], usuario.id)

    assert _stock(p) == 2, "un rechazo no puede alterar el stock"


def test_stock_en_cero_no_permite_venta(venta_local, usuario, producto):
    p = producto(stock=0, precio=1000)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)

    with pytest.raises(ValueError, match="stock suficiente"):
        venta_local.registrar_venta(s.id, "efectivo", [(p.id, 1)], usuario.id)
    assert _stock(p) == 0


def test_reabastecimiento_permite_vender_despues_de_agotarse(
    venta_local, usuario, producto, db_sesion
):
    p = producto(stock=1, precio=1000)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)

    venta_local.registrar_venta(s.id, "efectivo", [(p.id, 1)], usuario.id)
    assert _stock(p) == 0

    with pytest.raises(ValueError, match="stock suficiente"):
        venta_local.registrar_venta(s.id, "efectivo", [(p.id, 1)], usuario.id)

    db_sesion.execute(
        db.text("UPDATE productos SET stock = 10 WHERE id = :i"), {"i": p.id}
    )
    db_sesion.commit()

    venta = venta_local.registrar_venta(s.id, "efectivo", [(p.id, 4)], usuario.id)
    assert venta.total == 4000
    assert _stock(p) == 6


def test_venta_parcial_por_items_no_deja_stock_negativo(
    venta_local, usuario, producto
):

    p_ok = producto(stock=10, precio=1000, nombre="r0-ok")
    p_falta = producto(stock=1, precio=1000, nombre="r0-falta")
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)

    with pytest.raises(ValueError, match="stock suficiente"):
        venta_local.registrar_venta(
            s.id, "efectivo", [(p_ok.id, 5), (p_falta.id, 9)], usuario.id
        )

    assert _stock(p_ok) == 10, "el descuento del primer item no debe quedar aplicado"
    assert _stock(p_falta) == 1


def test_no_se_puede_vender_en_sesion_cerrada(venta_local, usuario, producto):
    p = producto(stock=10)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    venta_local.cerrar_sesion(s.id, usuario.id, "empleado")

    with pytest.raises(ValueError, match="cerrada"):
        venta_local.registrar_venta(s.id, "efectivo", [(p.id, 1)], usuario.id)
    assert _stock(p) == 10


def test_una_sesion_abierta_por_usuario_a_la_vez(venta_local, usuario):
    venta_local.abrir_sesion("Feria Uno", usuario.id)
    with pytest.raises(ValueError, match="venta abierta"):
        venta_local.abrir_sesion("Feria Dos", usuario.id)


def test_no_se_puede_abrir_otra_sesion_el_mismo_dia(venta_local, usuario):
    s = venta_local.abrir_sesion("Feria Uno", usuario.id)
    venta_local.cerrar_sesion(s.id, usuario.id, "empleado")

    with pytest.raises(ValueError, match="una sesión por día"):
        venta_local.abrir_sesion("Feria Dos", usuario.id)


def test_si_se_puede_abrir_sesion_otro_dia(venta_local, usuario):
    ayer = date.today() - timedelta(days=1)
    anterior = venta_local.abrir_sesion("Feria Uno", usuario.id, fecha=ayer)
    venta_local.cerrar_sesion(anterior.id, usuario.id, "empleado")
    s2 = venta_local.abrir_sesion("Feria Dos", usuario.id)
    assert s2.fecha == date.today()


def test_lugar_vacio_se_rechaza(venta_local, usuario):
    with pytest.raises(ValueError, match="lugar es obligatorio"):
        venta_local.abrir_sesion("   ", usuario.id)


@pytest.mark.parametrize("medio", ["tarjeta", "", "EFECTIVO"])
def test_medio_de_pago_invalido_se_rechaza(venta_local, usuario, producto, medio):
    p = producto(stock=5)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    with pytest.raises(ValueError, match="inv"):
        venta_local.registrar_venta(s.id, medio, [(p.id, 1)], usuario.id)


def test_venta_sin_items_se_rechaza(venta_local, usuario):
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    with pytest.raises(ValueError, match="al menos un producto"):
        venta_local.registrar_venta(s.id, "efectivo", [], usuario.id)


@pytest.mark.parametrize("cantidad", [0, -3])
def test_cantidad_no_positiva_se_rechaza(venta_local, usuario, producto, cantidad):
    p = producto(stock=10)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    with pytest.raises(ValueError, match="mayor a cero"):
        venta_local.registrar_venta(s.id, "efectivo", [(p.id, cantidad)], usuario.id)


def test_producto_inexistente_se_rechaza(venta_local, usuario):
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    with pytest.raises(ValueError, match="no encontrado"):
        venta_local.registrar_venta(s.id, "efectivo", [(_uuid.uuid4(), 1)], usuario.id)


def test_creado_en_viene_con_zona_horaria(venta_local, usuario, producto):
    p = producto(stock=5)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    venta = venta_local.registrar_venta(s.id, "efectivo", [(p.id, 1)], usuario.id)

    assert venta.creado_en is not None
    assert venta.creado_en.tzinfo is not None, (
        "creado_en volvio naive: en la migracion DATE paso a timestamptz y el "
        "modelo debe declarar timezone=True"
    )


def test_la_venta_registra_quien_la_hizo(venta_local, usuario, producto):
    p = producto(stock=5)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)

    venta = venta_local.registrar_venta(s.id, "efectivo", [(p.id, 1)], usuario.id)

    assert venta.usuario_id == usuario.id


@pytest.mark.parametrize("cantidad", [1.5, "2.5", True])
def test_cantidad_decimal_o_no_entera_se_rechaza(
    venta_local, usuario, producto, cantidad
):
    p = producto(stock=10)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)

    with pytest.raises(ValueError, match="entero mayor a cero"):
        venta_local.registrar_venta(s.id, "efectivo", [(p.id, cantidad)], usuario.id)
    assert _stock(p) == 10


def test_otro_empleado_no_puede_vender_en_la_sesion(
    venta_local, usuario, producto, db_sesion
):
    p = producto(stock=10)
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    otro = _otro_usuario(db_sesion)

    with pytest.raises(SesionNoAutorizada, match="no es tuya"):
        venta_local.registrar_venta(s.id, "efectivo", [(p.id, 1)], otro.id)
    assert _stock(p) == 10


def test_otro_empleado_no_puede_cerrar_la_sesion(
    venta_local, usuario, db_sesion
):
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    otro = _otro_usuario(db_sesion)

    with pytest.raises(SesionNoAutorizada, match="dueño"):
        venta_local.cerrar_sesion(s.id, otro.id, "empleado")

    assert venta_local.obtener_sesion_abierta(usuario.id).id == s.id


def test_admin_puede_cerrar_sesion_olvidada(venta_local, usuario, db_sesion):
    s = venta_local.abrir_sesion("Feria de prueba", usuario.id)
    admin = _otro_usuario(db_sesion)

    cerrada = venta_local.cerrar_sesion(s.id, admin.id, "admin")

    assert cerrada.estado == "cerrada"
    assert venta_local.obtener_sesion_abierta(usuario.id) is None