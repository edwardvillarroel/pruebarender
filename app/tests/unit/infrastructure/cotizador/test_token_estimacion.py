
from uuid import uuid4

from app.infrastructure.cotizador.token_estimacion import (
    crear_token_estimacion,
    hash_imagen,
    verificar_token_estimacion,
)

SECRETO = "secreto-de-test-para-token-de-estimacion-1234567890"
ESTIMACION = {
    "precio_estimado_ia": 7000.0,
    "precio_unitario_ia": 7000.0,
    "gramos_estimados_ia": 9.3,
    "tiempo_estimado_horas_ia": 1.1,
    "material_sugerido_ia": "pla+",
    "complejidad_ia": "simple",
    "confianza_material_ia": 1.0,
    "confianza_complejidad_ia": 0.57,
}


def _token(usuario_id=None, contenido=b"imagen", firma="5|5|5|cm|1|Decorativo|PLA+|Negro"):
    return crear_token_estimacion(
        usuario_id=usuario_id or uuid4(),
        imagen_sha256=hash_imagen(contenido),
        firma=firma,
        estimacion=ESTIMACION,
        secreto=SECRETO,
    )


def _verificar(token, usuario_id, contenido=b"imagen", firma="5|5|5|cm|1|Decorativo|PLA+|Negro", max_age=60):
    return verificar_token_estimacion(
        token,
        usuario_id=usuario_id,
        imagen_sha256=hash_imagen(contenido),
        firma=firma,
        secreto=SECRETO,
        max_age=max_age,
    )


def test_hash_imagen_distingue_contenido():
    assert hash_imagen(b"a") != hash_imagen(b"b")
    assert hash_imagen(b"a") == hash_imagen(b"a")


def test_roundtrip_devuelve_solo_los_campos_de_estimacion():
    usuario_id = uuid4()
    token = _token(usuario_id)

    estimacion = _verificar(token, usuario_id)

    assert estimacion == ESTIMACION


def test_token_adulterado_no_verifica():
    usuario_id = uuid4()
    assert _verificar(_token(usuario_id) + "x", usuario_id) is None


def test_token_con_otro_usuario_no_verifica():
    assert _verificar(_token(uuid4()), uuid4()) is None


def test_token_con_otra_imagen_no_verifica():
    usuario_id = uuid4()
    assert _verificar(_token(usuario_id), usuario_id, contenido=b"otra") is None


def test_token_con_otras_especificaciones_no_verifica():
    usuario_id = uuid4()
    assert _verificar(_token(usuario_id), usuario_id, firma="6|5|5|cm|1|Decorativo|PLA+|Negro") is None


def test_token_expirado_no_verifica():
    usuario_id = uuid4()
    assert _verificar(_token(usuario_id), usuario_id, max_age=-1) is None


def test_no_firma_con_secreto_inseguro():
    assert (
        crear_token_estimacion(
            usuario_id=uuid4(),
            imagen_sha256=hash_imagen(b"imagen"),
            firma="x",
            estimacion=ESTIMACION,
            secreto="dev-secret-change-me",
        )
        is None
    )


def test_no_verifica_con_secreto_inseguro():
    usuario_id = uuid4()
    token = _token(usuario_id)
    assert (
        verificar_token_estimacion(
            token,
            usuario_id=usuario_id,
            imagen_sha256=hash_imagen(b"imagen"),
            firma="5|5|5|cm|1|Decorativo|PLA+|Negro",
            secreto="dev-secret-change-me",
            max_age=60,
        )
        is None
    )
