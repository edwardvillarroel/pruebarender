

from decimal import Decimal
from uuid import uuid4

from app.domain.entities.solicitud_diseno import EstadoSolicitud, SolicitudDiseno
from app.domain.time import utcnow
from app.infrastructure.repositories.pedido_repository import PedidoRepository
from app.infrastructure.repositories.solicitud_diseno_repository import (
    SolicitudDisenoRepository,
)

CABECERA_ADMIN = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "admin",
    "X-Internal-Secret": "secreto-interno-test",
}


def _cotizacion_con_ia() -> SolicitudDiseno:
    return SolicitudDiseno(
        usuario_id=uuid4(),
        nombre="Jonathan",
        email="jon.caceresm@duocuc.cl",
        material="PLA+",
        descripcion="",
        estado=EstadoSolicitud.PENDIENTE,
        material_sugerido_ia="pla+",
        complejidad_ia="simple",
        gramos_estimados_ia=Decimal("9.30"),
        tiempo_estimado_horas_ia=Decimal("1.10"),
        precio_estimado_ia=Decimal("7000"),
        confianza_material_ia=Decimal("1.00"),
        confianza_complejidad_ia=Decimal("0.57"),
        ia_calculado_en=utcnow(),
        ia_origen="cotizador-apolovibes-v2-front",
    )


def test_listado_admin_expone_la_estimacion_ia_con_sus_claves(app, client, monkeypatch):
    solicitud = _cotizacion_con_ia()
    monkeypatch.setattr(SolicitudDisenoRepository, "listar_todos", lambda self: [solicitud])
    monkeypatch.setattr(PedidoRepository, "pagos_por_cotizacion", lambda self, ids: {})

    respuesta = client.get("/api/cotizaciones", headers=CABECERA_ADMIN)

    assert respuesta.status_code == 200
    item = respuesta.get_json()[0]
    assert item["material_sugerido_ia"] == "pla+"
    assert item["complejidad_ia"] == "simple"
    assert item["gramos_estimados_ia"] == 9.3
    assert item["tiempo_estimado_horas_ia"] == 1.1
    assert item["precio_estimado_ia"] == 7000.0
    assert item["confianza_material_ia"] == 1.0
    assert item["confianza_complejidad_ia"] == 0.57
    assert item["ia_calculado_en"] is not None
    assert item["ia_origen"] == "cotizador-apolovibes-v2-front"


def test_detalle_admin_expone_la_estimacion_ia(app, client, monkeypatch):
    solicitud = _cotizacion_con_ia()
    monkeypatch.setattr(
        SolicitudDisenoRepository,
        "obtener_por_id",
        lambda self, solicitud_id: solicitud if solicitud_id == solicitud.id else None,
    )
    monkeypatch.setattr(PedidoRepository, "pagos_por_cotizacion", lambda self, ids: {})

    respuesta = client.get(f"/api/cotizaciones/{solicitud.id}", headers=CABECERA_ADMIN)

    assert respuesta.status_code == 200
    item = respuesta.get_json()
    assert item["precio_estimado_ia"] == 7000.0
    assert item["material_sugerido_ia"] == "pla+"
    assert item["ia_origen"] == "cotizador-apolovibes-v2-front"
