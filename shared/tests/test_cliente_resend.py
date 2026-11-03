"""Contrato del cliente HTTP de Resend y de sus modos de fallo."""

from __future__ import annotations

import httpx
import pytest

from shared.correo.cliente import ClienteCorreo, ErrorEnvioCorreo
from shared.correo.modelos import Correo

CREDENCIALES = {
    "RESEND_API_KEY": "re_test",
    "EMAIL_FROM": "ApoloVibes <pedidos@x.test>",
}
CORREO = Correo(
    asunto="Asunto de prueba",
    html="<p>Hola</p>",
    texto="Hola",
)


class _RespuestaFalsa:
    def __init__(self, status_code: int = 200, datos: dict | None = None):
        self.status_code = status_code
        self._datos = datos or {"id": "email_test"}

    def json(self) -> dict:
        return self._datos


class _HttpxFalso:
    def __init__(self, respuestas=None, error: Exception | None = None):
        self.llamadas: list[dict] = []
        self._respuestas = list(respuestas or [_RespuestaFalsa()])
        self._error = error

    def post(self, url, json=None, headers=None, timeout=None):
        self.llamadas.append(
            {"url": url, "json": json, "headers": headers, "timeout": timeout}
        )
        if self._error is not None:
            raise self._error
        if len(self._respuestas) > 1:
            siguiente = self._respuestas.pop(0)
        else:
            siguiente = self._respuestas[0]
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


@pytest.fixture(autouse=True)
def _sin_esperas(monkeypatch):
    import shared.correo.cliente as modulo

    monkeypatch.setattr(modulo.time, "sleep", lambda _segundos: None)


def _http(monkeypatch, **kwargs) -> _HttpxFalso:
    import shared.correo.cliente as modulo

    http = _HttpxFalso(**kwargs)
    monkeypatch.setattr(modulo.httpx, "post", http.post)
    return http


@pytest.mark.parametrize("faltante", ["RESEND_API_KEY", "EMAIL_FROM"])
def test_sin_credenciales_simula_sin_http(monkeypatch, faltante):
    http = _http(monkeypatch)
    config = dict(CREDENCIALES)
    del config[faltante]

    assert ClienteCorreo(config).enviar("ana@x.test", CORREO) is False
    assert http.llamadas == []


def test_payload_y_cabeceras_esperadas(monkeypatch):
    http = _http(monkeypatch)

    assert ClienteCorreo(CREDENCIALES).enviar("ana@x.test", CORREO) is True

    llamada = http.llamadas[0]
    assert llamada["url"] == "https://api.resend.com/emails"
    assert llamada["headers"] == {
        "Authorization": "Bearer re_test",
        "Content-Type": "application/json",
        "User-Agent": "ApoloVibes/1.0",
    }
    assert llamada["json"] == {
        "from": "ApoloVibes <pedidos@x.test>",
        "to": ["ana@x.test"],
        "subject": "Asunto de prueba",
        "html": "<p>Hola</p>",
        "text": "Hola",
    }
    assert llamada["timeout"] == 15


def test_un_4xx_no_se_reintenta_y_no_expone_la_key(monkeypatch):
    http = _http(
        monkeypatch,
        respuestas=[
            _RespuestaFalsa(
                422,
                {
                    "name": "validation_error",
                    "message": "The from address is invalid",
                },
            )
        ],
    )

    with pytest.raises(ErrorEnvioCorreo) as error:
        ClienteCorreo(CREDENCIALES).enviar("ana@x.test", CORREO)

    assert len(http.llamadas) == 1
    assert "422" in str(error.value)
    assert "validation_error" in str(error.value)
    assert "re_test" not in str(error.value)


def test_un_5xx_se_reintenta_y_luego_sigue(monkeypatch):
    http = _http(
        monkeypatch,
        respuestas=[_RespuestaFalsa(503), _RespuestaFalsa()],
    )

    assert ClienteCorreo(CREDENCIALES).enviar("ana@x.test", CORREO) is True
    assert len(http.llamadas) == 2


def test_dos_5xx_terminan_en_error_controlado(monkeypatch):
    http = _http(
        monkeypatch,
        respuestas=[_RespuestaFalsa(503), _RespuestaFalsa(503)],
    )

    with pytest.raises(ErrorEnvioCorreo):
        ClienteCorreo(CREDENCIALES).enviar("ana@x.test", CORREO)
    assert len(http.llamadas) == 2


def test_timeout_se_reintenta(monkeypatch):
    import shared.correo.cliente as modulo

    http = _http(
        monkeypatch,
        respuestas=[httpx.TimeoutException("timeout"), _RespuestaFalsa()],
    )

    assert ClienteCorreo(CREDENCIALES).enviar("ana@x.test", CORREO) is True
    assert len(http.llamadas) == 2


def test_error_de_transporte_dos_veces_no_revienta_como_httpx(monkeypatch):
    http = _http(
        monkeypatch,
        error=httpx.TransportError("sin red"),
    )

    with pytest.raises(ErrorEnvioCorreo):
        ClienteCorreo(CREDENCIALES).enviar("ana@x.test", CORREO)
    assert len(http.llamadas) == 2
