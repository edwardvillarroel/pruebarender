

import io

import pytest

from app.infrastructure.imagenes import thumbnail
from app.infrastructure.imagenes.thumbnail import (
    CALIDAD_JPEG,
    LADO_MAXIMO,
    TAMANIO_MINIMO_BYTES,
    generar_thumbnail,
)

pytest.importorskip("PIL.Image", reason="Pillow no instalado")


def _imagen(ancho: int, alto: int, modo: str = "RGB") -> bytes:
    import random

    from PIL import Image

    random.seed(ancho * 1000 + alto)
    pixeles = [
        (
            (i * 37 + j * 11) % 256,
            (i * 17 + j * 53) % 256,
            (i * 91 + j * 7) % 256,
        )
        for i in range(alto)
        for j in range(ancho)
    ]
    imagen = Image.new("RGB", (ancho, alto))
    imagen.putdata(pixeles)
    if modo != "RGB":
        imagen = imagen.convert(modo)

    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def test_reduce_la_imagen_al_lado_maximo():
    datos = _imagen(2400, 1800)

    resultado = generar_thumbnail(datos, "image/png")

    assert resultado is not None
    bytes_thumb, content_type = resultado
    assert content_type == "image/jpeg"

    from PIL import Image

    with Image.open(io.BytesIO(bytes_thumb)) as imagen:
        assert max(imagen.size) == LADO_MAXIMO
        assert imagen.size == (LADO_MAXIMO, 450)


def test_el_thumbnail_es_mas_chico_que_la_original():
    datos = _imagen(3000, 3000)

    resultado = generar_thumbnail(datos, "image/png")

    assert resultado is not None
    assert len(resultado[0]) < len(datos) / 4


def test_png_con_canal_alfa_se_compone_sobre_blanco():
    import random

    from PIL import Image

    random.seed(7)
    ancho = alto = 1200
    pixeles = []
    for i in range(alto):
        for j in range(ancho):
            alfa = 0 if i < 50 else 255
            pixeles.append(((i * 31) % 256, (j * 19) % 256, (i * j) % 256, alfa))
    imagen = Image.new("RGBA", (ancho, alto))
    imagen.putdata(pixeles)

    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")

    resultado = generar_thumbnail(buffer.getvalue(), "image/png")

    assert resultado is not None
    with Image.open(io.BytesIO(resultado[0])) as thumb:
        assert thumb.mode == "RGB"
        assert thumb.getpixel((10, 10)) == (255, 255, 255)


def test_imagen_ya_chica_no_se_recomprime():
    datos = _imagen(60, 60)

    assert generar_thumbnail(datos, "image/png") is None


def test_bytes_por_debajo_del_minimo_no_se_tocan():
    assert generar_thumbnail(b"x" * 100, "image/png") is None


def test_archivo_ilegible_devuelve_none_y_no_explota():
    assert generar_thumbnail(b"esto no es una imagen" * 100, "image/png") is None


def test_entrada_vacia_devuelve_none():
    assert generar_thumbnail(b"", "image/jpeg") is None


def test_sin_pillow_devuelve_none_en_vez_de_romper(monkeypatch):
    monkeypatch.setattr(thumbnail, "Image", None)

    datos = _imagen(1200, 1200)
    assert generar_thumbnail(datos, "image/png") is None


def test_calidad_y_lado_estan_expuestos_para_documentar_el_contrato():
    assert LADO_MAXIMO == 600
    assert CALIDAD_JPEG == 82
    assert TAMANIO_MINIMO_BYTES == 16 * 1024
