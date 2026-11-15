"""Pruebas de las miniaturas de cotización.

El listado muestra cada referencia en una caja de 96×96. Estos tests fijan las
dos piezas que hacen que eso no descargue la foto completa: la convención de
ruta (`cotizaciones/<uuid>.<ext>` → `miniaturas/cotizaciones/<uuid>.jpg`) y la
reducción con Pillow, incluyendo el `None` que obliga al llamador a servir el
original.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.infrastructure.imagenes.miniaturas_cotizacion import (
    LADO_MAXIMO_MINIATURA,
    crear_miniatura,
    ruta_miniatura,
)


def _imagen_bytes(lado: int, formato: str = "PNG", ruido: bool = False) -> bytes:
    """Imagen de prueba; con `ruido` comprime mal y supera el mínimo de bytes."""
    if ruido:
        imagen = Image.effect_noise((lado, lado), 90).convert("RGB")
    else:
        imagen = Image.new("RGB", (lado, lado), (30, 90, 200))
    salida = io.BytesIO()
    imagen.save(salida, format=formato)
    return salida.getvalue()


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("cotizaciones/abc.png", "miniaturas/cotizaciones/abc.jpg"),
        ("cotizaciones/abc.jpeg", "miniaturas/cotizaciones/abc.jpg"),
        ("cotizaciones\\abc.png", "miniaturas/cotizaciones/abc.jpg"),
        ("cotizaciones/sin-extension", "miniaturas/cotizaciones/sin-extension.jpg"),
    ],
)
def test_ruta_miniatura_traduce_la_ruta_de_cotizacion(entrada, esperado):
    assert ruta_miniatura(entrada) == esperado


@pytest.mark.parametrize(
    "entrada",
    [
        None,
        "",
        "https://cdn.ejemplo.cl/foto.png",
        "/absoluta/foto.png",
        "productos/foto.png",
        "cotizaciones/sub/foto.png",
        "cotizaciones/../secreto.png",
    ],
)
def test_ruta_miniatura_ignora_lo_que_no_es_una_imagen_de_cotizacion(entrada):
    assert ruta_miniatura(entrada) is None


def test_crear_miniatura_reduce_y_devuelve_jpeg():
    original = _imagen_bytes(1200, ruido=True)

    miniatura = crear_miniatura(original)

    assert miniatura is not None
    assert miniatura.startswith(b"\xff\xd8")  # firma JPEG
    assert len(miniatura) < len(original)
    with Image.open(io.BytesIO(miniatura)) as imagen:
        assert max(imagen.size) <= LADO_MAXIMO_MINIATURA


def test_crear_miniatura_no_recomprime_una_foto_que_ya_es_chica():
    assert crear_miniatura(_imagen_bytes(120, ruido=True)) is None


def test_crear_miniatura_devuelve_none_si_no_hay_datos():
    assert crear_miniatura(None) is None
    assert crear_miniatura(b"") is None


def test_crear_miniatura_devuelve_none_si_no_puede_decodificar():
    assert crear_miniatura(b"esto no es una imagen" * 2000) is None
