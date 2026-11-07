"""Pruebas unitarias del adaptador de Supabase Storage (F4).

El seam de red es `AlmacenSupabaseStorage._request`: aca se stubbea y la suite
nunca toca la red. Fijan el contrato del adaptador: parseo de `signedURL`
(relativa y absoluta), ruta y `contentType` de la subida, existencia, borrado,
listado y que nada de esto lance hacia el caller (best-effort con warning).
"""

from __future__ import annotations

import pytest

from app.infrastructure.storage.supabase_storage import (
    AlmacenSupabaseStorage,
    almacen_desde_config,
    tipo_mime,
)


class _Respuesta:
    """Doble liviano de `requests.Response`."""

    def __init__(self, status_code: int = 200, json_datos=None, texto: str = ""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._json = json_datos
        self.text = texto

    def json(self):
        if self._json is None:
            raise ValueError("respuesta sin cuerpo JSON")
        return self._json


class _RedCaida(Exception):
    """Simula un fallo de red del tipo que `requests` lanza."""


def _almacen() -> AlmacenSupabaseStorage:
    return AlmacenSupabaseStorage(
        url="https://ejemplo.supabase.co",
        clave="sb_secret_de_prueba",
        cubeta="Cotizaciones",
        ttl=300,
    )


def _stub(monkeypatch, almacen, respuesta_o_error):
    """Reemplaza `_request` en `almacen` y devuelve la lista de llamadas."""
    llamadas = []

    def _request(metodo, ruta, **kwargs):
        llamadas.append((metodo, ruta, kwargs))
        if isinstance(respuesta_o_error, Exception):
            raise respuesta_o_error
        if callable(respuesta_o_error):
            return respuesta_o_error(metodo, ruta, kwargs)
        return respuesta_o_error

    monkeypatch.setattr(almacen, "_request", _request)
    return llamadas


# --------------------------------------------------------------------------
# URL firmada
# --------------------------------------------------------------------------


def test_url_firmada_parsea_signed_url_relativa(monkeypatch):
    almacen = _almacen()
    _stub(
        monkeypatch,
        almacen,
        _Respuesta(
            200,
            {
                "signedURL": "/object/sign/Cotizaciones/cotizaciones/abc.png?token=t1"
            },
        ),
    )

    url = almacen.url_firmada("cotizaciones/abc.png")

    assert url == (
        "https://ejemplo.supabase.co/storage/v1"
        "/object/sign/Cotizaciones/cotizaciones/abc.png?token=t1"
    )


def test_url_firmada_respuesta_absoluta_se_usa_tal_cual(monkeypatch):
    almacen = _almacen()
    absoluta = "https://ejemplo.supabase.co/storage/v1/object/sign/c/abc.png?token=x"
    _stub(monkeypatch, almacen, _Respuesta(200, {"signedURL": absoluta}))

    assert almacen.url_firmada("cotizaciones/abc.png") == absoluta


def test_url_firmada_usa_el_ttl_configurado(monkeypatch):
    almacen = _almacen()
    capturado = {}

    def _request(metodo, ruta, **kwargs):
        capturado.update(kwargs)
        return _Respuesta(200, {"signedURL": "/object/sign/c/abc.png?token=x"})

    monkeypatch.setattr(almacen, "_request", _request)

    almacen.url_firmada("cotizaciones/abc.png")

    assert capturado["json"] == {"expiresIn": "300"}


def test_url_firmada_error_http_devuelve_none(monkeypatch):
    almacen = _almacen()
    _stub(monkeypatch, almacen, _Respuesta(403, texto="denegado"))

    assert almacen.url_firmada("cotizaciones/abc.png") is None


def test_url_firmada_sin_red_caida_devuelve_none(monkeypatch):
    almacen = _almacen()
    _stub(monkeypatch, almacen, _RedCaida())

    assert almacen.url_firmada("cotizaciones/abc.png") is None


# --------------------------------------------------------------------------
# Subida
# --------------------------------------------------------------------------


def test_subir_usa_ruta_bucket_content_type_y_auth(monkeypatch):
    almacen = _almacen()
    llamadas = _stub(monkeypatch, almacen, _Respuesta(200, {}))

    ok = almacen.subir("cotizaciones/abc.png", b"PNG", "image/png")

    assert ok is True
    metodo, ruta, kwargs = llamadas[0]
    assert metodo == "POST"
    assert ruta == "/object/Cotizaciones/cotizaciones/abc.png"
    assert kwargs["headers"]["Content-Type"] == "image/png"
    assert kwargs["headers"]["x-upsert"] == "true"
    # La clave SOLO viaja en los headers del seam (apikey + Bearer).
    assert kwargs["data"] == b"PNG"


def test_subir_error_http_devuelve_false_sin_lanzar(monkeypatch):
    almacen = _almacen()
    _stub(monkeypatch, almacen, _Respuesta(413, texto="muy grande"))

    assert almacen.subir("cotizaciones/abc.png", b"x", "image/png") is False


def test_subir_red_caida_devuelve_false_sin_lanzar(monkeypatch):
    almacen = _almacen()
    llamadas = _stub(monkeypatch, almacen, _RedCaida("sin conexion"))

    assert almacen.subir("cotizaciones/abc.png", b"x", "image/png") is False
    assert len(llamadas) == 1


def test_sin_configurar_no_toca_la_red(monkeypatch):
    almacen = AlmacenSupabaseStorage(url="", clave="", cubeta="")

    def _request(*_args, **_kwargs):  # pragma: no cover - no debe llegar
        raise AssertionError("no deberia llamar a la red sin configurar")

    monkeypatch.setattr(almacen, "_request", _request)

    assert almacen.configurado is False
    assert almacen.subir("cotizaciones/a.png", b"x", "image/png") is False
    assert almacen.existe("cotizaciones/a.png") is False
    assert almacen.url_firmada("cotizaciones/a.png") is None
    assert almacen.eliminar("cotizaciones/a.png") is False
    assert almacen.listar("cotizaciones/") == []


# --------------------------------------------------------------------------
# Existencia y borrado
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,esperado",
    [(200, True), (404, False), (400, False), (500, False)],
)
def test_existe_según_el_status(monkeypatch, status, esperado):
    almacen = _almacen()
    _stub(monkeypatch, almacen, _Respuesta(status))

    assert almacen.existe("cotizaciones/abc.png") is esperado


def test_existe_llama_a_object_info(monkeypatch):
    almacen = _almacen()
    llamadas = _stub(monkeypatch, almacen, _Respuesta(404))

    almacen.existe("cotizaciones/abc.png")

    assert llamadas[0] == ("GET", "/object/info/Cotizaciones/cotizaciones/abc.png", {})


def test_eliminar_200_es_true_y_404_es_false(monkeypatch):
    almacen = _almacen()
    _stub(monkeypatch, almacen, _Respuesta(200, {}))
    assert almacen.eliminar("cotizaciones/abc.png") is True

    _stub(monkeypatch, almacen, _Respuesta(404, texto="no existe"))
    assert almacen.eliminar("cotizaciones/abc.png") is False


def test_eliminar_red_caida_devuelve_false_sin_lanzar(monkeypatch):
    almacen = _almacen()
    _stub(monkeypatch, almacen, _RedCaida())

    assert almacen.eliminar("cotizaciones/abc.png") is False


# --------------------------------------------------------------------------
# Listado
# --------------------------------------------------------------------------


def test_listar_devuelve_los_objetos_con_created_at(monkeypatch):
    almacen = _almacen()
    objetos = [
        {"name": "cotizaciones/a.png", "created_at": "2024-01-01T00:00:00+00:00"},
        {"name": "cotizaciones/b.png", "created_at": "2024-02-01T00:00:00+00:00"},
    ]
    llamadas = _stub(monkeypatch, almacen, _Respuesta(200, objetos))

    assert almacen.listar("cotizaciones/") == objetos
    metodo, ruta, kwargs = llamadas[0]
    assert metodo == "POST"
    assert ruta == "/object/list/Cotizaciones"
    assert kwargs["json"]["prefix"] == "cotizaciones/"


def test_listar_error_http_devuelve_vacio(monkeypatch):
    almacen = _almacen()
    _stub(monkeypatch, almacen, _Respuesta(500, texto="boom"))

    assert almacen.listar("cotizaciones/") == []


# --------------------------------------------------------------------------
# Fábrica desde configuración
# --------------------------------------------------------------------------


def test_almacen_desde_config_completo_devuelve_almacen():
    almacen = almacen_desde_config(
        {
            "SUPABASE_URL": "https://otro.supabase.co/",
            "SUPABASE_SERVICE_KEY": "sb_secret",
            "SUPABASE_STORAGE_BUCKET": "Cotizaciones",
            "SUPABASE_SIGN_TTL_SECONDS": 120,
        }
    )

    assert almacen is not None
    assert almacen.url == "https://otro.supabase.co"  # barra final normalizada
    assert almacen.cubeta == "Cotizaciones"
    assert almacen.ttl == 120


@pytest.mark.parametrize(
    "faltante",
    ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_STORAGE_BUCKET"],
)
def test_almacen_desde_config_incompleto_devuelve_none(faltante):
    config = {
        "SUPABASE_URL": "https://x.supabase.co",
        "SUPABASE_SERVICE_KEY": "sb_secret",
        "SUPABASE_STORAGE_BUCKET": "Cotizaciones",
        "SUPABASE_SIGN_TTL_SECONDS": 300,
    }
    config[faltante] = ""

    assert almacen_desde_config(config) is None


# --------------------------------------------------------------------------
# Content-Type por extensión
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extension,esperado",
    [
        (".png", "image/png"),
        ("png", "image/png"),
        ("jpg", "image/jpeg"),
        ("JPEG", "image/jpeg"),
        ("glb", "model/gltf-binary"),
        ("stl", "model/stl"),
        ("weird", "application/octet-stream"),
        ("", "application/octet-stream"),
    ],
)
def test_tipo_mime_por_extension(extension, esperado):
    assert tipo_mime(extension) == esperado
