"""Pruebas unitarias de las firmas HMAC de las URLs de cotización.

`GET /api/uploads/<path>` dejó de ser público: cada ruta se publica con
`?exp=&sig=` y el endpoint exige una firma vigente. Estos tests fijan el
contrato de `firmar`/`verificar`: roundtrip, expiración, firma alterada,
parámetros no numéricos, URLs absolutas que pasan sin firmar y la
normalización de barras invertidas de las filas legacy.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qs, urlparse

import pytest

from app.infrastructure.imagenes.firmas_upload import firmar, verificar


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield app


def _firma_expirada(app, ruta: str, exp: int) -> tuple[str, str]:
    """Firma manual con un `exp` arbitrario (para simular vencimiento)."""
    normalizada = ruta.replace("\\", "/")
    secreto = str(app.config["UPLOAD_SIGN_SECRET"])
    sig = hmac.new(
        secreto.encode(),
        f"{normalizada}|{exp}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return str(exp), sig


def test_roundtrip_firmar_verificar(ctx):
    app = ctx
    firmada = firmar("cotizaciones/abc123.png")

    assert firmada is not None
    assert firmada.startswith("cotizaciones/abc123.png?")
    partes = urlparse(firmada)
    args = parse_qs(partes.query)
    assert "exp" in args and "sig" in args

    assert verificar("cotizaciones/abc123.png", args["exp"][0], args["sig"][0]) is True


def test_firma_expirada_devuelve_false(ctx):
    app = ctx
    exp, sig = _firma_expirada(app, "cotizaciones/abc.png", int(time.time()) - 60)

    assert verificar("cotizaciones/abc.png", exp, sig) is False


def test_firma_alterada_devuelve_false(ctx):
    firmada = firmar("cotizaciones/abc.png")
    args = parse_qs(urlparse(firmada).query)
    sig_alterada = ("0" if args["sig"][0][0] != "0" else "1") + args["sig"][0][1:]

    assert verificar("cotizaciones/abc.png", args["exp"][0], sig_alterada) is False


def test_exp_no_numerico_devuelve_false(ctx):
    firmada = firmar("cotizaciones/abc.png")
    args = parse_qs(urlparse(firmada).query)

    assert verificar("cotizaciones/abc.png", "mañana", args["sig"][0]) is False
    assert verificar("cotizaciones/abc.png", "", args["sig"][0]) is False


def test_falta_parametro_devuelve_false(ctx):
    firmada = firmar("cotizaciones/abc.png")
    args = parse_qs(urlparse(firmada).query)

    assert verificar("cotizaciones/abc.png", None, args["sig"][0]) is False
    assert verificar("cotizaciones/abc.png", args["exp"][0], None) is False


def test_url_absoluta_se_pasa_sin_firmar(ctx):
    abs_url = "https://cdn.ejemplo.cl/imagen.png"

    assert firmar(abs_url) == abs_url
    assert firmar("http://cdn.ejemplo.cl/imagen.png") == (
        "http://cdn.ejemplo.cl/imagen.png"
    )
    assert firmar(None) is None


def test_backslashes_se_normalizan_al_firmar(ctx):
    firmada = firmar("cotizaciones\\legacy.png")

    assert firmada.startswith("cotizaciones/legacy.png?")
    partes = urlparse(firmada)
    args = parse_qs(partes.query)

    # La fila legacy con `\` y la URL servida con `/` deben verificar igual.
    assert verificar("cotizaciones\\legacy.png", args["exp"][0], args["sig"][0]) is True
    assert verificar("cotizaciones/legacy.png", args["exp"][0], args["sig"][0]) is True
