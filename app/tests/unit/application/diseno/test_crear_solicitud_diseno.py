"""Estimacion IA al crear una solicitud de diseno.

El frontend estima al subir la imagen y manda el resultado junto con
`estimacion_firma`. El backend debe reutilizar esa estimacion (una sola llamada
al cotizador, que permite 1 request/minuto) y solo llamar al cotizador si no
hay una estimacion valida. Ante cualquier fallo del cotizador la solicitud se
crea igual, con los campos IA en NULL y el motivo visible en `ia_origen`.
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


def _imagen_png() -> FileStorage:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    buffer.seek(0)
    return FileStorage(stream=buffer, filename="pieza.png", content_type="image/png")


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


def _ejecutar(servicio, datos):
    repo = servicio.repositorio
    solicitud = servicio.ejecutar(uuid4(), datos, _imagen_png())
    assert repo.creadas == [solicitud]
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


def _error_http(codigo: int) -> requests.HTTPError:
    respuesta = requests.Response()
    respuesta.status_code = codigo
    return requests.HTTPError(f"HTTP {codigo}", response=respuesta)


# Firma canonica que produce `firmaEspecificaciones` del frontend para
# alto/ancho/largo=5, cm, cantidad=1, Decorativo, PLA+ y Negro.
FIRMA_FRONT = "5|5|5|cm|1|Decorativo|PLA+|Negro"


def test_reutiliza_la_estimacion_del_cliente_sin_llamar_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    datos = _datos(
        estimacion_firma=FIRMA_FRONT,
        precio_estimado="7000",
        precio_unitario="7000",
        gramos_estimados="9.3",
        tiempo_estimado_horas="1.1",
        material_sugerido="pla+",
        complejidad="simple",
        confianza_material="1",
        confianza_complejidad="0.57",
    )

    solicitud = _ejecutar(servicio, datos)

    assert cotizador.llamadas == 0
    assert solicitud.ia_origen == IA_ORIGEN_CLIENTE
    assert solicitud.ia_calculado_en is not None
    assert solicitud.ia_calculado_en.tzinfo is not None
    assert solicitud.precio_estimado_ia == Decimal("7000")
    assert solicitud.gramos_estimados_ia == Decimal("9.3")
    assert solicitud.material_sugerido_ia == "pla+"
    assert solicitud.complejidad_ia == "simple"
    assert solicitud.confianza_complejidad_ia == Decimal("0.57")


def test_ignora_estimacion_del_cliente_si_la_firma_no_coincide():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    datos = _datos(
        estimacion_firma="5|5|5|cm|1|Decorativo|PLA+|Negro|otra-cosa",
        precio_estimado="7000",
    )

    solicitud = _ejecutar(servicio, datos)

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER
    assert solicitud.precio_estimado_ia == Decimal("7000")
    assert solicitud.material_sugerido_ia == "pla+"


def test_estimacion_del_cliente_con_valores_undefined_cae_al_cotizador():
    cotizador = _CotizadorFalso(resultado=_resultado_cotizador())
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    datos = _datos(
        estimacion_firma=FIRMA_FRONT,
        precio_estimado="undefined",
        gramos_estimados="undefined",
    )

    solicitud = _ejecutar(servicio, datos)

    assert cotizador.llamadas == 1
    assert solicitud.ia_origen == IA_ORIGEN_SERVER
    assert solicitud.precio_estimado_ia == Decimal("7000")


@pytest.mark.parametrize("codigo", [401, 429])
def test_fallo_http_del_cotizador_crea_la_solicitud_y_marca_el_origen(codigo):
    cotizador = _CotizadorFalso(error=_error_http(codigo))
    servicio = CrearSolicitudDiseno(_RepoFalso(), cotizador_ia=cotizador)
    datos = _datos(estimacion_firma="firma-invalida", precio_estimado="7000")

    solicitud = _ejecutar(servicio, datos)

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


def test_sin_cotizador_y_sin_estimacion_del_cliente_crea_la_solicitud_sin_ia():
    servicio = CrearSolicitudDiseno(_RepoFalso())

    solicitud = _ejecutar(servicio, _datos())

    assert solicitud.ia_origen is None
    assert solicitud.ia_calculado_en is None
    assert solicitud.precio_estimado_ia is None
