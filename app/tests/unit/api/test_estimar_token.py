
import io
from uuid import uuid4

from PIL import Image

from app.infrastructure.cotizador import ClienteCotizadorIA
from app.infrastructure.cotizador.token_estimacion import (
    hash_imagen,
    verificar_token_estimacion,
)

SECRETO = "secreto-de-test-para-token-de-estimacion-1234567890"
FIRMA = "5|5|5|cm|1|Decorativo|PLA+|Negro"

RESULTADO = {
    "precio_estimado_ia": 7000.0,
    "precio_unitario_ia": 7000.0,
    "gramos_estimados_ia": 9.3,
    "tiempo_estimado_horas_ia": 1.1,
    "material_sugerido_ia": "pla+",
    "complejidad_ia": "simple",
    "confianza_material_ia": 1.0,
    "confianza_complejidad_ia": 0.57,
}


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _post_estimar(client, contenido, headers):
    return client.post(
        "/api/cotizaciones/estimar",
        data={
            "imagen": (io.BytesIO(contenido), "pieza.png"),
            "alto": "5",
            "ancho": "5",
            "largo": "5",
            "unidad": "cm",
            "cantidad": "1",
            "uso": "Decorativo",
            "material_usuario": "PLA+",
            "color": "Negro",
        },
        headers=headers,
        content_type="multipart/form-data",
    )


def test_estimar_emite_token_ligado_al_usuario_y_a_la_imagen(app, client, monkeypatch):
    app.config["SECRET_KEY"] = SECRETO
    monkeypatch.setattr(ClienteCotizadorIA, "estimar", lambda self, **kwargs: RESULTADO)
    usuario_id = str(uuid4())
    contenido = _png_bytes()

    respuesta = _post_estimar(
        client,
        contenido,
        {"X-User-Id": usuario_id, "X-Internal-Secret": "secreto-interno-test"},
    )

    assert respuesta.status_code == 200
    body = respuesta.get_json()
    assert body["firma"] == FIRMA
    assert body["token"]

    estimacion = verificar_token_estimacion(
        body["token"],
        usuario_id=usuario_id,
        imagen_sha256=hash_imagen(contenido),
        firma=FIRMA,
        secreto=SECRETO,
        max_age=60,
    )
    assert estimacion["precio_estimado_ia"] == 7000.0
    assert estimacion["gramos_estimados_ia"] == 9.3


def test_estimar_sin_sesion_requiere_autenticacion(app, client, monkeypatch):
    app.config["SECRET_KEY"] = SECRETO
    monkeypatch.setattr(ClienteCotizadorIA, "estimar", lambda self, **kwargs: RESULTADO)

    respuesta = _post_estimar(client, _png_bytes(), {})

    assert respuesta.status_code == 401


def test_estimar_sin_secreto_seguro_no_emite_token(app, client, monkeypatch):
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    monkeypatch.setattr(ClienteCotizadorIA, "estimar", lambda self, **kwargs: RESULTADO)
    usuario_id = str(uuid4())

    respuesta = _post_estimar(
        client,
        _png_bytes(),
        {"X-User-Id": usuario_id, "X-Internal-Secret": "secreto-interno-test"},
    )

    assert respuesta.status_code == 200
    assert "token" not in respuesta.get_json()
