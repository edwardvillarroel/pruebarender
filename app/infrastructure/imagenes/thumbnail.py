



from __future__ import annotations

import io

try:
    from PIL import Image
except Exception:  # pragma: no cover - dependencia opcional ausente
    Image = None

LADO_MAXIMO = 600

CALIDAD_JPEG = 82

TAMANIO_MINIMO_BYTES = 16 * 1024


def _convertir_a_rgb(imagen: "Image.Image") -> "Image.Image":

    if imagen.mode in ("RGB", "L"):
        return imagen
    if imagen.mode in ("RGBA", "LA", "P"):
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        if imagen.mode != "P":
            imagen = imagen.convert("RGBA")
        fondo.paste(imagen, mask=imagen.split()[-1])
        return fondo
    return imagen.convert("RGB")


def generar_thumbnail(
    datos: bytes,
    content_type: str,
    lado_maximo: int = LADO_MAXIMO,
) -> tuple[bytes, str] | None:


    if Image is None or not datos:
        return None

    if len(datos) <= TAMANIO_MINIMO_BYTES:
        return None

    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            imagen.load()
            if max(imagen.size) <= lado_maximo:
                return None
            imagen.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)
            salida = io.BytesIO()
            _convertir_a_rgb(imagen).save(
                salida, format="JPEG", quality=CALIDAD_JPEG, optimize=True
            )
            return salida.getvalue(), "image/jpeg"
    except Exception:
        return None
