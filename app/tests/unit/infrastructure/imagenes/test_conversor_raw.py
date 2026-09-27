"""Pruebas unitarias del conversor de imágenes RAW de cámara.

Nota de cobertura conocida: la decodificación RAW real (rawpy sobre un
archivo de cámara genuino, p.ej. `.CR2`/`.NEF`) NO se puede probar sin un
archivo de muestra real; fabricar un `.dng` falso haría fallar libraw de
formas no representativas. Ese camino queda como vacío de cobertura, a cubrir
con un RAW de muestra si se decide agregar uno al repositorio.
"""

import io

import pytest

from app.infrastructure.imagenes import conversor_raw
from app.infrastructure.imagenes.conversor_raw import (
    es_raw,
    normalizar_imagen,
)


def _jpeg_minimo() -> bytes:
    """JPEG mínimo generado con Pillow para usarlo como bytes válidos."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_minimo() -> bytes:
    """PNG mínimo generado con Pillow para usarlo como bytes válidos."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(0, 255, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "nombre",
    ["foto.CR2", "imagen.nef", "escaneo.raw", "IMG_1234.RW2", "toma.ARW"],
)
def test_es_raw_reconoce_extensiones_de_camara(nombre):
    assert es_raw(nombre) is True


@pytest.mark.parametrize(
    "nombre",
    ["foto.jpg", "captura.PNG", "documento.pdf", "", "fotografia", "sin_extension"],
)
def test_es_raw_rechaza_lo_que_no_es_raw(nombre):
    assert es_raw(nombre) is False


def test_normalizar_imagen_pasa_jpeg_tal_cual():
    datos = _jpeg_minimo()

    assert normalizar_imagen(datos, "image/jpeg", "foto.jpg") == (datos, "image/jpeg")


def test_normalizar_imagen_pasa_png_tal_cual():
    datos = _png_minimo()

    assert normalizar_imagen(datos, "image/png", "foto.png") == (datos, "image/png")


def test_normalizar_imagen_corrige_content_type_no_navegable_de_jpeg():
    datos = _jpeg_minimo()

    bytes_ok, mime = normalizar_imagen(datos, "application/octet-stream", "foto")

    assert bytes_ok == datos
    assert mime == "image/jpeg"


def test_normalizar_imagen_rechaza_archivo_que_no_es_imagen():
    with pytest.raises(ValueError) as excinfo:
        normalizar_imagen(b"esto no es una imagen", "application/octet-stream", "datos.bin")

    assert "Formato de imagen no soportado" in str(excinfo.value)


def test_normalizar_imagen_raw_sin_dependencias_lanza_error_en_espanol(monkeypatch):
    monkeypatch.setattr(conversor_raw, "rawpy", None)

    with pytest.raises(ValueError) as excinfo:
        normalizar_imagen(b"\x00\x01", "application/octet-stream", "foto.cr2")

    mensaje = str(excinfo.value)
    assert "RAW" in mensaje
    assert "disponible" in mensaje


def test_normalizar_imagen_raw_que_falla_lanza_error_en_espanol(monkeypatch):
    class _RawpyRoto:
        @staticmethod
        def imread(_fuente):
            raise RuntimeError("archivo corrupto")

    monkeypatch.setattr(conversor_raw, "rawpy", _RawpyRoto())

    with pytest.raises(ValueError) as excinfo:
        normalizar_imagen(b"\x00\x01", "image/x-canon-cr2", "IMG_0001.CR2")

    mensaje = str(excinfo.value)
    assert "convertir" in mensaje
    assert "camara" in mensaje or "danado" in mensaje
