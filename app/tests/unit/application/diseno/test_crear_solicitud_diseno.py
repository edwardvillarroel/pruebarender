"""Estimacion IA al crear una solicitud de diseno.

El frontend estima al subir la imagen; el backend firma esa estimacion y el
alta solo la reutiliza si llega en un token valido, ligado al usuario, a la
imagen y a las especificaciones. Los precios sueltos del formulario se ignoran
siempre: el navegador no es confiable. Sin token valido (o ante cualquier fallo
del cotizador) la solicitud se crea igual y el motivo queda en `ia_origen`.
"""

import io
from decimal import Decimal
from uuid import uuid4

import pytest
import requests
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.application.diseno.crear_solicitud_diseno import (
    IA_ORIGEN_CLIENTE,
    IA_ORIGEN_SERVER,
    CrearSolicitudDiseno,
)
from app.config import Config
from app.infrastructure.cotizador.token_estimacion import (
    crear_token_estimacion,
    hash_imagen,
)

SECRETO_TEST = "secreto-de-test-para-token-de-estimacion-1234567890"
# Firma canonica que produce `firmaEspecificaciones` del frontend para
# alto/ancho/largo=5, cm, cantidad=1, Decorativo, PLA+ y Negro.
FIRMA_FRONT = "5|5|5|cm|1|Decorativo|PLA+|Negro"


@pytest.fixture(autouse=True)
def _secreto_fuerte(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", SECRETO_TEST)
    monkeypatch.setattr(Config, "ESTIMACION_TOKEN_TTL_SECONDS", 7200)


class _RepoFalso:
    def __init__(self):
        self.creadas = []

    def crear(self, entidad):
        self.creadas.append(entidad)
        return entidad


class _CotizadorFalso:
    def __init__(self, resultado=None, error=None):
        self.resultado = resultado
        self.error = error
        self.llamadas = 0

    def estimar(self, **kwargs):
        self.llamadas += 1
        if self.error is not None:
            raise self.error
        return self.resultado


def _png_bytes(tamano=(8, 8), color="white") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", tamano, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _archivo(contenido: bytes | None = None) -> FileStorage:
    return FileStorage(
        stream=io.BytesIO(contenido or _png_bytes()),
        filename="pieza.png",
        content_type="image/png",
    )


def _datos(**extra) -> dict:
    datos = {
        "nombre": "Jonathan",
        "email": "jon.caceresm@duocuc.cl",
        "telefono": "+56990778025",
        "material": "PLA+",
        "descripcion": "",
        "alto": "5",
        "ancho": "5",
        "largo": "5",
        "unidad": "cm",
        "cantidad": "1",
        "uso": "Decorativo",
        "color": "Negro",
    }
    datos.update(extra)
    return datos


def _ejecutar(servicio, datos, usuario_id=None, contenido=None):
    usuario_id = usuario_id or uuid4()
    contenido = contenido if contenido is not None else _png_bytes()
    solicitud = servicio.ejecutar(usuario_id, datos, _archivo(contenido))
    assert servicio.repositorio.creadas == [solicitud]
    return solicitud


def _resultado_cotizador(**extra) -> dict:
    resultado = {
        "precio_estimado_ia": 7000.0,
        "precio_unitario_ia": 7000.0,
        "gramos_estimados_ia": 9.3,
        "tiempo_estimado_horas_ia": 1.1,
        "material_sugerido_ia": "pla+",
        "complejidad_ia": "simple",
        "confianza_material_ia": 1.0,
        "confianza_complejidad_ia": 0.57,
    }
    resultado.update(extra)
    return resultado


def _token(usuario_id, contenido, firma=FIRMA_FRONT, estimacion=None) -> str:
    token = crear_token_estimacion(
        usuario_id=usuario_id,
        imagen_sha256=hash_imagen(contenido),
        firma=firma,
        estimacion=estimacion if estimacion is not None else _resultado_cotizador(),
        secreto=SECRETO_TEST,
    )
    assert token is not None
    return token


def _error_http(codigo: int) -> requests.HTTPError:
    respuesta = requests.Response()
    respuesta.status_code = codigo
    return requests.HTTPError(f"HTTP {codigo}", response=respuesta)


def test_reutiliza_la_estimacion_firmada_sin_llamar_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    usuario_id = uuid4()
    contenido = _png_bytes()

    solicitud = _ejecutar(
        servicio,
        _datos(estimacion_token=_token(usuario_id, contenido)),
        usuario_id=usuario_id,
        contenido=contenido,
    )

    assert cotizador.llamadas == 0
    assert solicitud.ia_origen == IA_ORIGEN_CLIENTE
    assert solicitud.ia_calculado_en is not None
    assert solicitud.ia_calculado_en.tzinfo is not None
    assert solicitud.precio_estimado_ia == Decimal("7000")
    assert solicitud.gramos_estimados_ia == Decimal("9.3")
    assert solicitud.material_sugerido_ia == "pla+"
    assert solicitud.complejidad_ia == "simple"
    assert solicitud.confianza_complejidad_ia == Decimal("0.57")


def test_ignora_los_precios_del_formulario_aunque_el_token_sea_valido():
    """El ataque clasico: token valido + precios editados en el FormData."""
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    usuario_id = uuid4()
    contenido = _png_bytes()

    solicitud = _ejecutar(
        servicio,
        _datos(
            estimacion_token=_token(usuario_id, contenido),
            precio_estimado="1",
            precio_unitario="1",
            gramos_estimados="99999",
            material_sugerido="oro",
            complejidad="trivial",
        ),
        usuario_id=usuario_id,
        contenido=contenido,
    )

    assert cotizador.llamadas == 0
    assert solicitud.precio_estimado_ia == Decimal("7000")
    assert solicitud.gramos_estimados_ia == Decimal("9.3")
    assert solicitud.material_sugerido_ia == "pla+"
    assert solicitud.complejidad_ia == "simple"


def test_sin_token_ignora_precios_del_formulario_y_llama_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)

    solicitud = _ejecutar(
        servicio,
        _datos(
            estimacion_firma=FIRMA_FRONT,
            precio_estimado="1",
            gramos_estimados="99999",
        ),
    )

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER
    assert solicitud.precio_estimado_ia == Decimal("7000")
    assert solicitud.gramos_estimados_ia == Decimal("9.3")


def test_token_adulterado_cae_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    usuario_id = uuid4()
    contenido = _png_bytes()
    token = _token(usuario_id, contenido) + "x"

    solicitud = _ejecutar(
        servicio,
        _datos(estimacion_token=token),
        usuario_id=usuario_id,
        contenido=contenido,
    )

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER


def test_token_expirado_cae_al_cotizador(monkeypatch):
    monkeypatch.setattr(Config, "ESTIMACION_TOKEN_TTL_SECONDS", -1)
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    usuario_id = uuid4()
    contenido = _png_bytes()

    solicitud = _ejecutar(
        servicio,
        _datos(estimacion_token=_token(usuario_id, contenido)),
        usuario_id=usuario_id,
        contenido=contenido,
    )

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER


def test_token_de_otro_usuario_cae_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    contenido = _png_bytes()
    token = _token(uuid4(), contenido)

    solicitud = _ejecutar(
        servicio,
        _datos(estimacion_token=token),
        usuario_id=uuid4(),
        contenido=contenido,
    )

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER


def test_token_de_otra_imagen_cae_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    usuario_id = uuid4()
    token = _token(usuario_id, _png_bytes())

    solicitud = _ejecutar(
        servicio,
        _datos(estimacion_token=token),
        usuario_id=usuario_id,
        contenido=_png_bytes(tamano=(9, 9), color="black"),
    )

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER


def test_token_de_otras_especificaciones_cae_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    usuario_id = uuid4()
    contenido = _png_bytes()
    token = _token(usuario_id, contenido, firma="6|5|5|cm|1|Decorativo|PLA+|Negro")

    solicitud = _ejecutar(
        servicio,
        _datos(estimacion_token=token),
        usuario_id=usuario_id,
        contenido=contenido,
    )

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER


def test_token_con_precio_invalido_cae_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    usuario_id = uuid4()
    contenido = _png_bytes()
    token = _token(
        usuario_id,
        contenido,
        estimacion=_resultado_cotizador(precio_estimado_ia=None),
    )

    solicitud = _ejecutar(
        servicio,
        _datos(estimacion_token=token),
        usuario_id=usuario_id,
        contenido=contenido,
    )

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER


@pytest.mark.parametrize("codigo", [401, 429])
def test_fallo_http_del_cotizador_crea_la_solicitud_y_marca_el_origen(codigo):
    cotizador = _CotizadorFalso(error=_error_http(codigo))
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)

    solicitud = _ejecutar(servicio, _datos(estimacion_token="no-es-un-token"))

    assert solicitud.ia_origen == f"cotizador-error-{codigo}"
    assert solicitud.ia_calculado_en is None
    assert solicitud.precio_estimado_ia is None
    assert solicitud.material_sugerido_ia is None


def test_timeout_del_cotizador_crea_la_solicitud_y_marca_el_origen():
    cotizador = _CotizadorFalso(error=requests.exceptions.ReadTimeout("timeout"))
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)

    solicitud = _ejecutar(servicio, _datos())

    assert solicitud.ia_origen == "cotizador-error-ReadTimeout"
    assert solicitud.ia_calculado_en is None
    assert solicitud.precio_estimado_ia is None


def test_sin_cotizador_y_sin_token_crea_la_solicitud_sin_ia():
    servicio = CrearSolicitudDiseno(_RepoFalso())

    solicitud = _ejecutar(servicio, _datos())

    assert solicitud.ia_origen is None
    assert solicitud.ia_calculado_en is None
    assert solicitud.precio_estimado_ia is None
