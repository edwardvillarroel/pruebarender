"""Caso de uso de auditoria (OWASP Top 10 2025, A09 / RNF-06).

`GestionAuditoria.registrar` arma el `LogAuditoria` y lo persiste por el
puerto inyectado. Aca se blinda el contrato con el repositorio (`add`, no
`guardar`) y la conversion del `X-User-Id` (string) a UUID.
"""

from unittest.mock import Mock
from uuid import UUID

from app.application.auditoria.gestionar_auditoria import GestionAuditoria


def test_registrar_persiste_por_el_puerto_add():
    repositorio = Mock()
    servicio = GestionAuditoria(repositorio)

    servicio.registrar(
        "crear_pedido",
        entidad_tipo="pedido",
        entidad_id="123",
        usuario_id="11111111-1111-1111-1111-111111111111",
        detalle="detalle",
        ip="127.0.0.1",
    )

    repositorio.add.assert_called_once()
    log = repositorio.add.call_args.args[0]
    assert log.accion == "crear_pedido"
    assert log.entidad_tipo == "pedido"
    assert log.entidad_id == "123"
    assert log.usuario_id == UUID("11111111-1111-1111-1111-111111111111")
    assert log.detalle == "detalle"
    assert log.ip == "127.0.0.1"


def test_registrar_sin_usuario_deja_usuario_id_en_none():
    repositorio = Mock()

    GestionAuditoria(repositorio).registrar("crear_pedido", entidad_tipo="pedido")

    log = repositorio.add.call_args.args[0]
    assert log.usuario_id is None


def test_registrar_con_usuario_invalido_no_rompe():
    """Un header corrupto no debe impedir registrar la accion."""
    repositorio = Mock()

    GestionAuditoria(repositorio).registrar(
        "crear_pedido", entidad_tipo="pedido", usuario_id="no-es-uuid"
    )

    log = repositorio.add.call_args.args[0]
    assert log.usuario_id is None
