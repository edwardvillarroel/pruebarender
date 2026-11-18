



import io
import os

import pytest

from app.infrastructure.imagenes import conversor_raw
from app.infrastructure.imagenes.conversor_raw import (
    CALIDAD_JPEG_OPTIMIZADO,
    LADO_MAXIMO_ORIGINAL,
    TAMANIO_MAXIMO_INTACTO,
    es_raw,
    normalizar_imagen,
    optimizar_imagen,
)


def _jpeg_minimo() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_minimo() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(0, 255, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


def _ruido(ancho: int, alto: int, modo: str = "RGB"):

    from PIL import Image

    return Image.frombytes(modo, (ancho, alto), os.urandom(ancho * alto * len(modo)))


def _serializar(imagen, formato: str, **opciones) -> bytes:
    buffer = io.BytesIO()
    imagen.save(buffer, format=formato, **opciones)
    return buffer.getvalue()


def _tamanio(datos: bytes) -> tuple[int, int]:
    from PIL import Image

    with Image.open(io.BytesIO(datos)) as imagen:
        return imagen.size


def _modo(datos: bytes) -> str:
    from PIL import Image

    with Image.open(io.BytesIO(datos)) as imagen:
        return imagen.mode


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


def test_normalizar_imagen_pasa_jpeg_chico_tal_cual():
    datos = _jpeg_minimo()

    assert normalizar_imagen(datos, "image/jpeg", "foto.jpg") == (datos, "image/jpeg")


def test_normalizar_imagen_pasa_png_chico_tal_cual():
    datos = _png_minimo()

    assert normalizar_imagen(datos, "image/png", "foto.png") == (datos, "image/png")


def test_normalizar_imagen_corrige_content_type_no_navegable_de_jpeg():
    datos = _jpeg_minimo()

    bytes_ok, mime = normalizar_imagen(datos, "application/octet-stream", "foto")

    assert bytes_ok == datos
    assert mime == "image/jpeg"




def test_una_foto_grande_se_reescala_a_1600px():
    datos = _serializar(_ruido(2400, 1800), "JPEG", quality=90)

    bytes_ok, mime = normalizar_imagen(datos, "image/jpeg", "camara.jpg")

    assert mime == "image/jpeg"
    assert max(_tamanio(bytes_ok)) == LADO_MAXIMO_ORIGINAL
    assert _tamanio(bytes_ok) == (LADO_MAXIMO_ORIGINAL, 1200)
    assert len(bytes_ok) < len(datos) / 3


def test_una_foto_pesada_se_recomprime_aunque_entre_en_pixels():
    datos = _serializar(_ruido(1500, 1500), "JPEG", quality=95)
    assert len(datos) > TAMANIO_MAXIMO_INTACTO

    bytes_ok, mime = normalizar_imagen(datos, "image/jpeg", "pesada.jpg")

    assert mime == "image/jpeg"
    assert _tamanio(bytes_ok) == (1500, 1500)
    assert len(bytes_ok) < len(datos) * 0.75


def test_una_imagen_chica_pero_grande_en_pixels_no_crece(monkeypatch):


    from PIL import Image

    monkeypatch.setattr(conversor_raw, "TAMANIO_MAXIMO_INTACTO", 1)
    degradado = Image.new("RGB", (2000, 2000))
    degradado.putdata(
        [((i + j) % 256, (i * 2) % 256, (j * 2) % 256) for i in range(2000) for j in range(2000)]
    )
    datos = _serializar(degradado, "PNG")

    bytes_ok, mime = optimizar_imagen(datos, "image/png")

    assert bytes_ok is datos
    assert mime == "image/png"

    with Image.open(io.BytesIO(datos)) as imagen:
        imagen.thumbnail((LADO_MAXIMO_ORIGINAL, LADO_MAXIMO_ORIGINAL), Image.LANCZOS)
        como_jpeg = _serializar(imagen, "JPEG", quality=85, optimize=True)
    assert len(como_jpeg) > len(datos) * 10


def test_una_foto_chica_no_se_toca():
    datos = _jpeg_minimo()

    bytes_ok, _ = optimizar_imagen(datos, "image/jpeg")

    assert bytes_ok is datos


def test_un_png_con_alfa_chico_se_mantiene_png():
    from PIL import Image

    datos = _serializar(Image.new("RGBA", (600, 600), (255, 0, 0, 128)), "PNG")

    bytes_ok, mime = normalizar_imagen(datos, "image/png", "logo.png")

    assert (bytes_ok, mime) == (datos, "image/png")


def test_un_png_con_alfa_grande_se_reescala_pero_sigue_siendo_png():
    from PIL import Image

    pixeles = [
        (10, 20, 30, 0 if i < 20 else 255) for i in range(2000) for _ in range(2000)
    ]
    imagen = Image.new("RGBA", (2000, 2000))
    imagen.putdata(pixeles)
    datos = _serializar(imagen, "PNG")

    bytes_ok, mime = normalizar_imagen(datos, "image/png", "logo.png")

    assert mime == "image/png"
    assert max(_tamanio(bytes_ok)) == LADO_MAXIMO_ORIGINAL
    assert _modo(bytes_ok) == "RGBA"


def test_un_png_paletizado_sin_alfa_pasa_a_jpeg():
    from PIL import Image

    datos = _serializar(
        _ruido(1800, 1800).convert("P", palette=Image.ADAPTIVE, colors=256), "PNG"
    )
    assert len(datos) > TAMANIO_MAXIMO_INTACTO

    bytes_ok, mime = normalizar_imagen(datos, "image/png", "paleta.png")

    assert mime == "image/jpeg"
    assert _modo(bytes_ok) == "RGB"


def test_un_png_paletizado_con_alfa_se_mantiene_png():
    from PIL import Image

    imagen = _ruido(1800, 1800).convert("P", palette=Image.ADAPTIVE, colors=256)
    imagen.info["transparency"] = 0
    datos = _serializar(imagen, "PNG")

    bytes_ok, mime = normalizar_imagen(datos, "image/png", "paleta.png")

    assert mime == "image/png"
    assert max(_tamanio(bytes_ok)) == LADO_MAXIMO_ORIGINAL


def test_un_webp_con_alpa_se_queda_en_webp():
    datos = _serializar(_ruido(2000, 2000, "RGBA"), "WEBP", quality=95)

    bytes_ok, mime = normalizar_imagen(datos, "image/webp", "logo.webp")

    assert mime == "image/webp"
    assert max(_tamanio(bytes_ok)) == LADO_MAXIMO_ORIGINAL
    assert _modo(bytes_ok) in ("RGBA", "RGB")


def test_un_webp_sin_alfa_pasa_a_jpeg():
    datos = _serializar(_ruido(2000, 2000), "WEBP", quality=95)

    bytes_ok, mime = normalizar_imagen(datos, "image/webp", "foto.webp")

    assert mime == "image/jpeg"
    assert max(_tamanio(bytes_ok)) == LADO_MAXIMO_ORIGINAL


def test_un_gif_animado_no_se_toca(monkeypatch):
    from PIL import Image

    monkeypatch.setattr(conversor_raw, "TAMANIO_MAXIMO_INTACTO", 1)

    primero = _ruido(64, 64)
    datos = _serializar(
        primero, "GIF", save_all=True, append_images=[_ruido(64, 64)], duration=100
    )

    assert optimizar_imagen(datos, "image/gif") == (datos, "image/gif")

    solo = _serializar(primero, "GIF")
    assert optimizar_imagen(solo, "image/gif")[1] == "image/jpeg"


def test_sin_pillow_se_guarda_la_foto_tal_cual(monkeypatch):
    monkeypatch.setattr(conversor_raw, "Image", None)
    datos = _jpeg_minimo()

    assert normalizar_imagen(datos, "image/jpeg", "foto.jpg") == (datos, "image/jpeg")


def test_una_foto_ilegible_no_rompe_el_ingreso():
    datos = b"esto no es una imagen" * 200

    assert optimizar_imagen(datos, "image/jpeg") == (datos, "image/jpeg")


def test_el_raw_convertido_tambien_pasa_por_el_optimizador(monkeypatch):
    datos = _serializar(_ruido(3000, 2000), "JPEG", quality=90)
    monkeypatch.setattr(
        conversor_raw, "convertir_raw_a_jpeg", lambda _datos: datos
    )

    bytes_ok, mime = normalizar_imagen(b"raw-falso", "image/x-canon-cr2", "foto.CR2")

    assert mime == "image/jpeg"
    assert max(_tamanio(bytes_ok)) == LADO_MAXIMO_ORIGINAL


def test_los_parametros_de_optimizacion_estan_expuestos():
    assert LADO_MAXIMO_ORIGINAL == 1600
    assert CALIDAD_JPEG_OPTIMIZADO == 85
    assert TAMANIO_MAXIMO_INTACTO == 2 * 1024 * 1024


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
