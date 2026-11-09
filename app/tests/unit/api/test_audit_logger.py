"""Middleware de auditoría de acciones sensibles (OWASP Top 10 2025, A09).

`auditar` registra la acción sensible (p. ej. `crear_pedido`) sobre el
endpoint que la ejecuta y persiste el evento via el caso de uso inyectado
(`AUDITORIA_SERVICE`). El guard de uso real vive en las rutas; acá se
blindan el mecanismo de registro y la persistencia para que una acción
sensible no pueda dejarse fuera por omisión.
"""

from unittest.mock import Mock

from app.api.middleware.audit_logger import ACTIONS_SENSIBLES, auditar
from app.api.routes import pedido_routes, usuarios_routes


def test_auditar_registra_la_accion_de_la_funcion_endpoint():
    def _endpoint():
        return None

    auditar("crear_pedido")(_endpoint)

    assert _endpoint in ACTIONS_SENSIBLES
    assert ACTIONS_SENSIBLES[_endpoint] == "crear_pedido"


def test_auditar_devuelve_un_wrapper_que_ejecuta():
    def _endpoint():
        return "ok"

    decorada = auditar("procesar_pago")(_endpoint)

    assert decorada is not _endpoint
    assert decorada() == "ok"


# ---------------------------------------------------------------------------
# Endpoints de acciones sensibles quedan registrados para auditoria (A09)
# ---------------------------------------------------------------------------


def test_acciones_de_pedido_registradas_para_auditoria():
    registradas = {fn.__name__: accion for fn, accion in ACTIONS_SENSIBLES.items()}
    assert registradas["crear_pedido"] == "crear_pedido"
    assert registradas["cancelar_pedido"] == "cancelar_pedido"
    assert registradas["reintentar_pago"] == "reintentar_pago"
    assert registradas["eliminar_pedido"] == "eliminar_pedido"
    assert registradas["cambiar_estado_pedido"] == "cambiar_estado_pedido"
    assert (
        registradas["avisar_cancelacion_cliente"] == "avisar_cancelacion_cliente"
    )


def test_acciones_de_gestion_de_usuarios_registradas_para_auditoria():
    acciones = set(ACTIONS_SENSIBLES.values())
    assert "crear_usuario" in acciones
    assert "cambiar_rol" in acciones
    assert "cambiar_estado_usuario" in acciones
    assert "eliminar_usuario" in acciones


def test_endpoint_de_cambio_de_rol_registra_en_el_servicio_de_auditoria(app, client):
    """La accion auditada persiste via `AUDITORIA_SERVICE` (mock, sin BD)."""
    app.config["AUDITORIA_SERVICE"] = Mock()
    app.config["USUARIOS_SERVICE"] = Mock()
    app.config["USUARIOS_SERVICE"].cambiar_rol.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "rol": "cliente",
    }

    respuesta = client.patch(
        "/api/usuarios/11111111-1111-1111-1111-111111111111/rol",
        json={"rol": "cliente"},
        headers={
            "X-User-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Rol": "admin",
            "X-Internal-Secret": "secreto-interno-test",
        },
    )
    assert respuesta.status_code == 200

    app.config["AUDITORIA_SERVICE"].registrar.assert_called_once()
    args, kwargs = app.config["AUDITORIA_SERVICE"].registrar.call_args
    assert args[0] == "cambiar_rol"
    assert kwargs["entidad_tipo"] == "cambiar_rol"
