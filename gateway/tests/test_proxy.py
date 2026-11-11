"""Tests de `gateway.infrastructure.proxy.reenviar`.

La whitelist de headers de `reenviar` es la unica puerta entre las respuestas
del backend y el navegador: lo que no este ahi se pierde en silencio. Eso ya
paso con `location`: los 302 de `/api/uploads` llegaban sin destino, el
navegador no podia seguir el redirect a la signed URL de Supabase y las
miniaturas de cotizacion salian en 0 bytes aunque el archivo estuviera bien en
el bucket.
"""

from flask import Flask, request

from gateway.infrastructure import proxy


class _RespuestaStub:
    def __init__(self, status_code, content, headers):
        self.status_code = status_code
        self.content = content
        self.headers = headers


class _ClienteStub:
    def __init__(self, respuesta):
        self._respuesta = respuesta
        self.llamadas = []

    def request(self, **kwargs):
        self.llamadas.append(kwargs)
        return self._respuesta


def _reenviar(monkeypatch, respuesta, ruta="uploads/cotizaciones/x.webp?exp=1&sig=2"):
    monkeypatch.setattr(proxy, "_cliente", _ClienteStub(respuesta))
    app = Flask(__name__)
    app.config["BACKEND_INTERNAL_URL"] = "http://127.0.0.1:8000"
    with app.test_request_context(f"/api/{ruta}"):
        return proxy.reenviar(ruta, request, {})


def test_reenviar_conserva_location_en_redirect(monkeypatch):
    """El 302 a la signed URL de Supabase debe llegar con su Location intacto."""
    signed = (
        "https://ejemplo.supabase.co/storage/v1/object/sign/"
        "Cotizaciones/cotizaciones/x.webp?token=abc"
    )
    respuesta = _RespuestaStub(
        302,
        b"<html>Redirecting...</html>",
        {"Location": signed, "Content-Type": "text/html; charset=utf-8"},
    )

    contenido, status, cabeceras = _reenviar(monkeypatch, respuesta)

    assert status == 302
    assert cabeceras["Location"] == signed
    assert contenido.startswith(b"<html>")


def test_reenviar_sigue_filtrando_headers_internos(monkeypatch):
    """La whitelist sigue cerrada: abrir `location` no abre todo lo demas."""
    respuesta = _RespuestaStub(
        200,
        b'{"ok": true}',
        {
            "Content-Type": "application/json; charset=utf-8",
            "X-Internal-Secret": "no-debe-pasar",
        },
    )

    contenido, status, cabeceras = _reenviar(monkeypatch, respuesta)

    assert status == 200
    assert contenido == b'{"ok": true}'
    assert "Content-Type" in cabeceras
    assert "X-Internal-Secret" not in cabeceras
