"""Pruebas del reporte del dashboard de administracion.

Cubren las dos reglas que rompian las tarjetas del dashboard:

1. "Ingresos del mes" debe sumar TODOS los ingresos del mes en curso, no solo
   las ventas del local. Los pedidos de la tienda web pagados (los que devuelve
   `list_pagados`) tambien son ingreso; si se ignoran, la tarjeta muestra 0
   aunque el negocio haya vendido por internet.
2. Los cortes de dia/mes/semana son en hora de Chile, no en UTC. Un pago de las
   22:00 en Chile viaja como las 01:00 UTC del dia siguiente y, comparando en
   UTC, caeria en el dia (o el mes) equivocado.
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.reportes import gestionar_reporte as modulo
from app.application.reportes.gestionar_reporte import GestionarReporte, _fecha_chile
from app.domain.entities.pedido import Pedido
from app.domain.entities.venta_local import VentaLocal
from app.domain.enums import EstadoPedido, MedioPago


def _servicio(ventas=None, pedidos=None) -> GestionarReporte:
    ventas_repo = Mock()
    ventas_repo.listar_reportes.return_value = [Mock(id=uuid4())] if ventas else []
    ventas_repo.obtener_ventas_de_sesion.return_value = list(ventas or [])

    pedidos_repo = Mock()
    pedidos_repo.list_pagados.return_value = list(pedidos or [])

    solicitudes_repo = Mock()
    solicitudes_repo.listar_todos.return_value = []

    return GestionarReporte(ventas_repo, pedidos_repo, solicitudes_repo)


def _venta(total: int, creado_en: datetime, medio_pago: str = MedioPago.EFECTIVO.value) -> VentaLocal:
    return VentaLocal(
        sesion_id=uuid4(),
        medio_pago=medio_pago,
        items=[],
        total=total,
        creado_en=creado_en,
    )


def _pedido(
    total: int,
    creado_en: datetime,
    estado: EstadoPedido = EstadoPedido.ENVIADO,
) -> Pedido:
    return Pedido(usuario_id=uuid4(), estado=estado, total=total, creado_en=creado_en)


@pytest.fixture
def hoy_fijo(monkeypatch):
    """Fija "hoy" en Chile para que los cortes del reporte sean deterministas."""
    monkeypatch.setattr(modulo, "hoy_chile", lambda: date(2026, 10, 30))
    return date(2026, 10, 30)


def test_la_fecha_local_usa_la_zona_de_chile():
    # 2026-10-01 02:00 UTC = 2026-09-30 23:00 en Chile (UTC-3, horario de verano).
    assert _fecha_chile(datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc)) == date(2026, 9, 30)
    # Un timestamp naive se interpreta como UTC, igual que lo escriben las entidades.
    assert _fecha_chile(datetime(2026, 10, 1, 2, 0)) == date(2026, 9, 30)
    assert _fecha_chile(None) is None


def test_ingresos_del_mes_incluyen_pedidos_pagados_de_la_tienda(hoy_fijo):
    servicio = _servicio(
        ventas=[_venta(50_000, datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc))],
        pedidos=[
            _pedido(120_000, datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)),
            # Septiembre en Chile: no debe entrar al mes en curso.
            _pedido(999_000, datetime(2026, 9, 30, 2, 0, tzinfo=timezone.utc)),
            # Cancelado: no es ingreso aunque conserve el pago historico.
            _pedido(
                500_000,
                datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
                estado=EstadoPedido.CANCELADO,
            ),
            # Noviembre: tampoco.
            _pedido(700_000, datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)),
        ],
    )

    reporte = servicio.resumen()

    assert reporte["ventas"]["mes"] == {"total": 170_000.0, "n_ventas": 2}
    # `total` es el historico completo (incluye septiembre y noviembre).
    assert reporte["ventas"]["total"] == {"total": 1_869_000.0, "n_ventas": 4}


def test_ingresos_de_hoy_usan_la_fecha_local_de_chile(hoy_fijo):
    servicio = _servicio(
        ventas=[_venta(10_000, datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc))],
        pedidos=[
            # 2026-10-31 01:00 UTC = 2026-10-30 22:00 en Chile: sigue siendo "hoy".
            _pedido(5_000, datetime(2026, 10, 31, 1, 0, tzinfo=timezone.utc)),
        ],
    )

    assert servicio.resumen()["ventas"]["hoy"] == {"total": 15_000.0, "n_ventas": 2}


def test_por_medio_pago_separa_ventas_locales_y_tienda(hoy_fijo):
    servicio = _servicio(
        ventas=[_venta(10_000, datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc), MedioPago.EFECTIVO.value)],
        pedidos=[_pedido(25_000, datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc))],
    )

    medios = {m["medio_pago"]: m for m in servicio.resumen()["ventas"]["por_medio_pago"]}

    assert medios["efectivo"] == {"medio_pago": "efectivo", "total": 10_000.0, "n_ventas": 1}
    assert medios["tuu"] == {"medio_pago": "tuu", "total": 25_000.0, "n_ventas": 1}


def test_las_semanas_etiquetan_con_el_lunes_local_y_suman_ambas_fuentes(hoy_fijo):
    servicio = _servicio(
        ventas=[
            # Sabado 24/10 en Chile.
            _venta(30_000, datetime(2026, 10, 24, 15, 0, tzinfo=timezone.utc)),
            # Semana en curso (lunes 26/10).
            _venta(20_000, datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)),
        ],
        pedidos=[
            # Domingo 25/10 23:30 en Chile = lunes 26/10 02:30 UTC. Debe caer en la
            # semana del 19/10, no en la del 26/10.
            _pedido(40_000, datetime(2026, 10, 26, 2, 30, tzinfo=timezone.utc)),
        ],
    )

    semanas = servicio.resumen()["ventas"]["semanas"]

    assert [s["desde"] for s in semanas] == [
        "2026-09-28",
        "2026-10-05",
        "2026-10-12",
        "2026-10-19",
        "2026-10-26",
    ]
    assert [s["hasta"] for s in semanas][-1] == "2026-11-01"
    totales = {s["desde"]: s["total"] for s in semanas}
    assert totales["2026-10-19"] == 70_000.0
    assert totales["2026-10-26"] == 20_000.0
    # El campo `semana` se mantiene por compatibilidad, aunque el eje X ya no lo use.
    assert semanas[-1]["semana"] == date(2026, 10, 26).isocalendar()[1]


def test_el_resumen_no_falla_sin_ventas_ni_pedidos(hoy_fijo):
    reporte = _servicio().resumen()

    assert reporte["ventas"]["hoy"] == {"total": 0.0, "n_ventas": 0}
    assert reporte["ventas"]["mes"] == {"total": 0.0, "n_ventas": 0}
    assert reporte["ventas"]["por_medio_pago"] == []
    assert len(reporte["ventas"]["semanas"]) == 5
