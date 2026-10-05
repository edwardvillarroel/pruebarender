"""Harnes de caracterizacion (R0) contra la base real.

Estos tests congelan el comportamiento que la migracion a PostgreSQL no puede
cambiar. Corren identicos contra Oracle y Supabase: el motor se elige con
`TEST_DB_BACKEND` y la `TestingConfig` resuelve la DSN.

Por que NO se usa SQLite: el punto de la caracterizacion es comparar motores.
Un test que pasa en SQLite no dice nada sobre si el `NULLS NOT DISTINCT` de
PostgreSQL se comporta como el unico de Oracle, ni sobre `timestamptz`.

Aislamiento
-----------
Cada test crea filas con un centinela unico (`r0-<uuid>`) y las borra al
terminar. Un `session` de sesion toma un conteo de las tablas que se tocan y el
teardown final falla si el numero no volvio al inicial. Si un test deja basura,
la suite se da cuenta en lugar de contaminar la base silenciosamente.
"""

from __future__ import annotations

import os
import uuid

import pytest

os.environ.setdefault("TEST_DB_BACKEND", "postgres")

from app import create_app  # noqa: E402
from app.config import TestingConfig  # noqa: E402
from app.infrastructure.database.connection import db  # noqa: E402
from app.infrastructure.database.models.categoria_model import CategoriaModel  # noqa: E402
from app.infrastructure.database.models.producto_model import ProductoModel  # noqa: E402
from app.infrastructure.database.models.usuario_model import UsuarioModel  # noqa: E402

TABLAS_SENSIBLES = (
    "carrito_items",
    "carrito",
    "venta_local_items",
    "ventas_local",
    "sesiones_venta",
    "detalle_pedidos",
    "pagos",
    "pedidos",
    "productos",
    "categorias",
    "usuarios",
)


@pytest.fixture(scope="session")
def app():
    """App contra la base de tests.

    Si la base no esta disponible o falta el esquema, esto FALLA, no se saltea.
    Una suite que se salta entera sin decir nada reporta verde con cero
    cobertura, que es peor que un rojo: es la forma tipica de dar por buena una
    migracion que no se probo. Para correr sin base (por ejemplo en un lint)
    hay que pedirlo explicitamente con `R0_PERMITIR_SIN_BASE=1`.
    """
    try:
        aplicacion = create_app(TestingConfig)
        with aplicacion.app_context():
            db.session.execute(db.text("SELECT 1"))
            db.session.remove()
    except Exception as exc:  # noqa: BLE001
        if os.getenv("R0_PERMITIR_SIN_BASE") == "1":
            pytest.skip(f"base de tests no disponible: {exc}")
        pytest.fail(
            "la base de tests no esta disponible, asi que R0 no verifico nada. "
            f"Causa: {exc}\n"
            "Revisar TEST_DATABASE_URL, o poner R0_PERMITIR_SIN_BASE=1 si "
            "realmente se quiere correr sin base."
        )

    with aplicacion.app_context():
        falta = _tablas_faltantes()
        if falta:
            pytest.fail(
                "faltan tablas en la base de tests: "
                f"{falta}. Aplicar migrations/postgres/schema_completo.sql"
            )
        _asserpar_aislamiento_baseline()
        yield aplicacion
        _verificar_sin_residuos()


def _tablas_faltantes() -> list[str]:
    from sqlalchemy import inspect

    existentes = set(inspect(db.engine).get_table_names())
    return [t for t in TABLAS_SENSIBLES if t not in existentes]


def _conteos() -> dict[str, int]:
    from sqlalchemy import func, select

    from app.infrastructure.database.models.carrito_model import (  # noqa: F401
        CarritoItemModel,
        CarritoModel,
    )
    from app.infrastructure.database.models.detalle_pedido_model import (  # noqa: F401
        DetallePedidoModel,
    )
    from app.infrastructure.database.models.pago_model import PagoModel  # noqa: F401
    from app.infrastructure.database.models.pedido_model import PedidoModel  # noqa: F401
    from app.infrastructure.database.models.venta_local_model import (  # noqa: F401
        SesionVentaModel,
        VentaLocalItemModel,
        VentaLocalModel,
    )

    modelos = {
        "carrito_items": CarritoItemModel,
        "carrito": CarritoModel,
        "venta_local_items": VentaLocalItemModel,
        "ventas_local": VentaLocalModel,
        "sesiones_venta": SesionVentaModel,
        "detalle_pedidos": DetallePedidoModel,
        "pagos": PagoModel,
        "pedidos": PedidoModel,
        "productos": ProductoModel,
        "categorias": CategoriaModel,
        "usuarios": UsuarioModel,
    }
    return {
        tabla: db.session.execute(select(func.count()).select_from(modelo)).scalar_one()
        for tabla, modelo in modelos.items()
    }


def _asserpar_aislamiento_baseline() -> None:
    db.session.rollback()
    global _CONTEO_INICIAL
    _CONTEO_INICIAL = _conteos()


def _verificar_sin_residuos() -> None:
    db.session.rollback()
    final = _conteos()
    db.session.remove()
    if _CONTEO_INICIAL is None:
        return
    diff = {t: (i, final[t]) for t, i in _CONTEO_INICIAL.items() if final[t] != i}
    if diff:
        pytest.fail(f"la suite dejo residuos en la base: {diff}")


_CONTEO_INICIAL: dict[str, int] | None = None

# Marca de todas las filas que crea la suite. La limpieza es centralizada y en
# orden de FK, en vez de por fixture: los tests crean usuarios y carritos
# auxiliar en el camino, y un teardown por fixture se olvidaba de ellos y
# reventaba con violaciones de clave foranea.
_LIMPIEZA = [
    ("carrito_items", "carrito_id IN (SELECT id FROM carrito WHERE usuario_id IN "
     "(SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test'))"),
    ("carrito", "usuario_id IN (SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test')"),
    ("venta_local_items", "venta_id IN (SELECT v.id FROM ventas_local v WHERE v.sesion_id IN "
     "(SELECT id FROM sesiones_venta WHERE usuario_id IN "
     "(SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test')))"),
    ("ventas_local", "sesion_id IN (SELECT id FROM sesiones_venta WHERE usuario_id IN "
     "(SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test'))"),
    ("sesiones_venta", "usuario_id IN (SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test')"),
    # Antes que `pedidos`: `pagos.pedido_id` es FK a `pedidos`, asi que borrar
    # el pedido con el pago vivo viola la FK. Los tests de `/pago/crear` son los
    # primeros que dejan filas en `pagos`.
    ("pagos", "pedido_id IN (SELECT id FROM pedidos WHERE usuario_id IN "
     "(SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test'))"),
    ("detalle_pedidos", "pedido_id IN (SELECT id FROM pedidos WHERE usuario_id IN "
     "(SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test'))"),
    ("pedidos", "usuario_id IN (SELECT id FROM usuarios WHERE email LIKE '%@caracterizacion.test')"),
    ("usuarios", "email LIKE '%@caracterizacion.test'"),
    # Va antes de `productos`: `producto_colores.producto_id` es FK a
    # `productos`, asi que borrar el producto con colores vivos viola la FK.
    ("producto_colores", "producto_id IN (SELECT id FROM productos WHERE nombre LIKE 'r0-%')"),
    ("productos", "nombre LIKE 'r0-%'"),
    ("categorias", "nombre LIKE 'r0-%'"),
]


def _limpiar_filas_r0() -> None:
    from sqlalchemy import text

    for tabla, condicion in _LIMPIEZA:
        db.session.execute(text(f"DELETE FROM {tabla} WHERE {condicion}"))
    db.session.commit()


@pytest.fixture(autouse=True)
def _limpiar_tras_cada_test(app):
    """Guaranteiza que ningun test deje filas propias en la base."""
    yield
    with app.app_context():
        db.session.rollback()
        _limpiar_filas_r0()


@pytest.fixture
def db_sesion(app):
    """Sesion de BD dentro de contexto de app, limpia al final."""
    with app.app_context():
        yield db.session
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def centinela() -> str:
    """Marca unica por test, para identificar y borrar filas propias."""
    return "r0-" + uuid.uuid4().hex[:12]


@pytest.fixture
def usuario(db_sesion, centinela):
    # `apellido` es obligatorio para rol cliente: lo exige el CHECK
    # ck_usuarios_apellido del esquema.
    u = UsuarioModel(
        email=f"{centinela}@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="R0 Caracterizacion",
        apellido="Prueba",
    )
    db_sesion.add(u)
    db_sesion.commit()
    return u


@pytest.fixture
def categoria(db_sesion, centinela):
    c = CategoriaModel(nombre=f"{centinela}-cat")
    db_sesion.add(c)
    db_sesion.commit()
    return c


@pytest.fixture
def producto(db_sesion, categoria, centinela):
    def _crear(stock: int = 10, nombre: str | None = None, precio: int = 5000):
        p = ProductoModel(
            categoria_id=categoria.id,
            nombre=nombre or f"{centinela}-prod",
            precio=precio,
            stock=stock,
        )
        db_sesion.add(p)
        db_sesion.commit()
        return p

    return _crear