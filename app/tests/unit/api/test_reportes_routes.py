"""Tests del reporte general de ventas y pedidos (panel de administracion).

`GET /api/reportes` agrega ventas de sesiones locales cerradas, pedidos y
cotizaciones para el dashboard admin. Aqui se cubren los guard de acceso y el
shape del payload que consume el frontend.
"""
from unittest.mock import Mock

CABECERA_ADMIN = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "admin",
}


def _servicio_con_datos() -> Mock:
    servicio = Mock()
    servicio.resumen.return_value = {
        "ventas": {
            "total": {"total": 250000.0, "n_ventas": 2},
            "hoy": {"total": 100000.0, "n_ventas": 1},
            "mes": {"total": 250000.0, "n_ventas": 2},
            "por_medio_pago": [
                {"medio_pago": "efectivo", "total": 100000.0, "n_ventas": 1},
                {"medio_pago": "tuu", "total": 150000.0, "n_ventas": 1},
            ],
            "semanas": [
                {"semana": 40, "desde": "2026-09-28", "hasta": "2026-10-04", "total": 100000.0},
                {"semana": 41, "desde": "2026-10-05", "hasta": "2026-10-11", "total": 150000.0},
            ],
        },
        "pedidos": {
            "recientes": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "estado": "enviado",
                    "total": 150000.0,
                    "fecha": "2026-10-30T10:00:00",
                    "cliente": "Maria Torres",
                    "entrega": "envio",
                }
            ],
            "pendientes": [],
            "por_estado": [{"estado": "enviado", "total": 1}],
        },
        "cotizaciones": {
            "sin_revisar": [
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "nombre": "Cliente S.A.",
                    "email": "cliente@s.com",
                    "estado": "pendiente",
                    "creado_en": "2026-10-30T09:00:00",
                    "precio": None,
                }
            ],
            "total": 1,
        },
    }
    return servicio


def test_el_reporte_requiere_sesion(app, client):
    respuesta = client.get("/api/reportes")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


def test_el_reporte_rechaza_a_clientes(app, client):
    respuesta = client.get(
        "/api/reportes", headers={"X-User-Id": "11111111-1111-1111-1111-111111111111", "X-User-Rol": "cliente"}
    )
    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


def test_el_reporte_admin_devuelve_el_resumen(app, client):
    app.config["REPORTE_SERVICE"] = _servicio_con_datos()
    respuesta = client.get("/api/reportes", headers=CABECERA_ADMIN)
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["reporte"]["ventas"]["total"] == {"total": 250000.0, "n_ventas": 2}
    assert cuerpo["reporte"]["ventas"]["hoy"]["n_ventas"] == 1
    assert cuerpo["reporte"]["ventas"]["por_medio_pago"][0]["medio_pago"] == "efectivo"
    assert cuerpo["reporte"]["pedidos"]["recientes"][0]["id"] == (
        "22222222-2222-2222-2222-222222222222"
    )
    assert cuerpo["reporte"]["cotizaciones"]["total"] == 1
