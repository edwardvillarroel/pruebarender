"""Pruebas del escritor de imágenes de cotización (F4).

Fijan el contrato de `guardar_imagen_cotizacion_supabase`: siempre devuelve
`cotizaciones/<uuid><ext>`, sube al bucket solo si la config está completa,
no toca el disco cuando la subida sale bien y DEGRADA a disco con el MISMO
nombre cuando la nube falla. La red se stubbea en `_request` o en la
fábrica `almacen_desde_config`; la suite nunca toca la red.
"""

from __future__ import annotations

import logging

from app.infrastructure.imagenes.almacen_cotizaciones import (
    guardar_imagen_cotizacion,
    guardar_imagen_cotizacion_supabase,
)
from app.infrastructure.storage.supabase_storage import AlmacenSupabaseStorage


class _AlmacenFalso:
    """Doble de `AlmacenSupabaseStorage` que no toca la red."""

    def __init__(self, sube: bool = True):
        self.sube = sube
        self.llamadas: list[tuple[str, bytes, str]] = []

    @property
    def configurado(self) -> bool:
        return True

    def subir(self, ruta: str, contenido: bytes, content_type: str) -> bool:
        self.llamadas.append((ruta, contenido, content_type))
        return self.sube


class _Respuesta:
    def __init__(self, status_code: int = 200, json_datos=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._json = json_datos

    def json(self):
        return self._json


def _configurar_supabase(app) -> None:
    app.config.update(
        SUPABASE_URL="https://ejemplo.supabase.co",
        SUPABASE_SERVICE_KEY="sb_secret_de_prueba",
        SUPABASE_STORAGE_BUCKET="Cotizaciones",
        SUPABASE_SIGN_TTL_SECONDS=300,
    )


# --------------------------------------------------------------------------
# Sin Supabase: el contrato de siempre (disco local)
# --------------------------------------------------------------------------


def test_sin_supabase_escribe_en_disco_local(app, tmp_path):
    # TestingConfig trae SUPABASE_* vacío: dentro del contexto la fábrica
    # devuelve None y el escritor hace lo de siempre.
    with app.app_context():
        ruta = guardar_imagen_cotizacion_supabase(b"PNG", "png", tmp_path)

    assert ruta.startswith("cotizaciones/")
    assert ruta.endswith(".png")
    archivo = tmp_path / ruta
    assert archivo.is_file()
    assert archivo.read_bytes() == b"PNG"


def test_escritor_local_base_sigue_intacto(tmp_path):
    ruta = guardar_imagen_cotizacion(b"PNG", "png", tmp_path)

    assert ruta.startswith("cotizaciones/")
    assert ruta.endswith(".png")
    assert (tmp_path / ruta).read_bytes() == b"PNG"


# --------------------------------------------------------------------------
# Con Supabase configurado: sube al bucket
# --------------------------------------------------------------------------


def test_con_supabase_sube_al_bucket_sin_tocar_el_disco(
    app, tmp_path, monkeypatch
):
    falso = _AlmacenFalso(sube=True)
    monkeypatch.setattr(
        "app.infrastructure.storage.supabase_storage.almacen_desde_config",
        lambda config=None: falso,
    )

    with app.app_context():
        ruta = guardar_imagen_cotizacion_supabase(b"PNG", "png", tmp_path)

    assert falso.llamadas == [(ruta, b"PNG", "image/png")]
    assert ruta.startswith("cotizaciones/")
    assert ruta.endswith(".png")
    # Éxito en la nube: NO se crea nada en disco.
    assert not (tmp_path / "cotizaciones").exists()


def test_el_content_type_sale_de_la_extension(app, tmp_path, monkeypatch):
    falso = _AlmacenFalso(sube=True)
    monkeypatch.setattr(
        "app.infrastructure.storage.supabase_storage.almacen_desde_config",
        lambda config=None: falso,
    )

    with app.app_context():
        ruta = guardar_imagen_cotizacion_supabase(b"GLB", "glb", tmp_path)

    assert ruta.endswith(".glb")
    assert falso.llamadas[0][2] == "model/gltf-binary"


def test_dos_llamadas_generan_rutas_distintas(app, tmp_path, monkeypatch):
    falso = _AlmacenFalso(sube=True)
    monkeypatch.setattr(
        "app.infrastructure.storage.supabase_storage.almacen_desde_config",
        lambda config=None: falso,
    )

    with app.app_context():
        ruta1 = guardar_imagen_cotizacion_supabase(b"A", "png", tmp_path)
        ruta2 = guardar_imagen_cotizacion_supabase(b"B", "png", tmp_path)

    assert ruta1 != ruta2


def test_extension_con_punto_o_sin_punto_da_el_mismo_resultado(
    app, tmp_path, monkeypatch
):
    falso = _AlmacenFalso(sube=True)
    monkeypatch.setattr(
        "app.infrastructure.storage.supabase_storage.almacen_desde_config",
        lambda config=None: falso,
    )

    with app.app_context():
        con_punto = guardar_imagen_cotizacion_supabase(b"A", ".png", tmp_path)
        sin_punto = guardar_imagen_cotizacion_supabase(b"B", "png", tmp_path)

    assert con_punto.endswith(".png")
    assert sin_punto.endswith(".png")


# --------------------------------------------------------------------------
# Falla de la nube: degradación a disco con el MISMO nombre
# --------------------------------------------------------------------------


def test_si_falla_la_nube_escribe_en_disco_con_el_mismo_nombre(
    app, tmp_path, monkeypatch, caplog
):
    falso = _AlmacenFalso(sube=False)
    monkeypatch.setattr(
        "app.infrastructure.storage.supabase_storage.almacen_desde_config",
        lambda config=None: falso,
    )

    with app.app_context(), caplog.at_level(logging.WARNING):
        ruta = guardar_imagen_cotizacion_supabase(b"PNG", "png", tmp_path)

    archivo = tmp_path / ruta
    assert archivo.is_file()
    assert archivo.read_bytes() == b"PNG"
    assert "no aceptó" in caplog.text


# --------------------------------------------------------------------------
# La fábrica real lee la config de la aplicación en uso
# --------------------------------------------------------------------------


def test_config_de_app_config_usa_el_almacen_real(app, tmp_path, monkeypatch):
    _configurar_supabase(app)
    llamadas = []

    def _request(self, metodo, ruta, **kwargs):
        llamadas.append((metodo, ruta, kwargs))
        return _Respuesta(200, {})

    monkeypatch.setattr(AlmacenSupabaseStorage, "_request", _request)

    with app.app_context():
        ruta = guardar_imagen_cotizacion_supabase(b"PNG", "png", tmp_path)

    metodo, ruta_http, kwargs = llamadas[0]
    assert metodo == "POST"
    assert ruta_http == f"/object/Cotizaciones/{ruta}"
    assert kwargs["headers"]["Content-Type"] == "image/png"
    assert kwargs["headers"]["x-upsert"] == "true"
    assert kwargs["data"] == b"PNG"
    # Éxito en la nube: nada en disco.
    assert not (tmp_path / "cotizaciones").exists()
