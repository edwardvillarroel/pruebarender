


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
    monkeypatch.setattr(modulo, "hoy_chile", lambda: date(2026, 10, 30))
    return date(2026, 10, 30)


def test_la_fecha_local_usa_la_zona_de_chile():
    assert _fecha_chile(datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc)) == date(2026, 9, 30)
    assert _fecha_chile(datetime(2026, 10, 1, 2, 0)) == date(2026, 9, 30)
    assert _fecha_chile(None) is None


def test_ingresos_del_mes_incluyen_pedidos_pagados_de_la_tienda(hoy_fijo):
    servicio = _servicio(
        ventas=[_venta(50_000, datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc))],
        pedidos=[
            _pedido(120_000, datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)),
            _pedido(999_000, datetime(2026, 9, 30, 2, 0, tzinfo=timezone.utc)),
            _pedido(
                500_000,
                datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
                estado=EstadoPedido.CANCELADO,
            ),
            _pedido(700_000, datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)),
        ],
    )

    reporte = servicio.resumen()

    assert reporte["ventas"]["mes"] == {"total": 170_000.0, "n_ventas": 2}
    assert reporte["ventas"]["total"] == {"total": 1_869_000.0, "n_ventas": 4}


def test_ingresos_de_hoy_usan_la_fecha_local_de_chile(hoy_fijo):
    servicio = _servicio(
        ventas=[_venta(10_000, datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc))],
        pedidos=[
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
            _venta(30_000, datetime(2026, 10, 24, 15, 0, tzinfo=timezone.utc)),
            _venta(20_000, datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)),
        ],
        pedidos=[
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
    assert semanas[-1]["semana"] == date(2026, 10, 26).isocalendar()[1]


def test_el_resumen_no_falla_sin_ventas_ni_pedidos(hoy_fijo):
    reporte = _servicio().resumen()

    assert reporte["ventas"]["hoy"] == {"total": 0.0, "n_ventas": 0}
    assert reporte["ventas"]["mes"] == {"total": 0.0, "n_ventas": 0}
    assert reporte["ventas"]["por_medio_pago"] == []
    assert len(reporte["ventas"]["semanas"]) == 5
