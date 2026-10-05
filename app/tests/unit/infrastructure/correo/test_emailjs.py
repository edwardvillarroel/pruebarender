"""El adaptador de EmailJS: qué hace con credenciales y qué hace sin ellas.

El contrato que importa es el modo simulacion. El backend tiene que poder
arrancar y pagar en desarrollo sin que nadie haya configurado una plantilla de
EmailJS, asi que sin credenciales el comprobante se imprime en la consola y no
se lanza nada.

La razon de que degrade en vez de fallar es la misma que en el gateway pero con
un matiz importante: los correos del gateway son codigos de seguridad y sin
credenciales no se envia nada; el comprobante de un pedido se le prometio al
cliente, asi que en desarrollo tiene que quedar a la vista para poder
verificarlo. Ver `gateway/infrastructure/correo.py` para el contraste.

`httpx.post` se monkeypatchea en vez de usar `respx` o un servidor local: no
esta la dependencia en `requirements.txt` y agregar una libreria para probar una
llamada HTTP no vale el costo. Lo que se prueba es el payload que armamos, que
es la parte que es nuestra.
"""

from __future__ import annotations

import uuid

import pytest

from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido
from app.domain.interfaces.correo import ErrorEnvioCorreo, ServicioCorreo
from app.infrastructure.correo.emailjs import EmailJsCorreo

CREDENCIALES = {
    "EMAILJS_PUBLIC_KEY": "pub_test",
    "EMAILJS_PRIVATE_KEY": "priv_test",
    "EMAILJS_SERVICE_ID": "service_test",
    "EMAILJS_TEMPLATE_COMPROBANTE": "template_test",
}


class _RespuestaFalsa:
    def __init__(self, status_code: int = 200, texto: str = '{"status":"ok"}'):
        self.status_code = status_code
        self.text = texto


class _HttpxFalso:
    """Captura el POST en vez de salir a la red."""

    def __init__(self, respuesta=None, error: Exception | None = None):
        self.llamadas: list[dict] = []
        self._respuesta = respuesta or _RespuestaFalsa()
        self._error = error

    def post(self, url, json=None, timeout=None):
        self.llamadas.append({"url": url, "json": json, "timeout": timeout})
        if self._error is not None:
            raise self._error
        return self._respuesta


def _pedido() -> Pedido:
    pedido = Pedido(usuario_id=uuid.uuid4(), entrega="envio", total=3500)
    pedido.detalles.append(
        DetallePedido(
            pedido_id=pedido.id,
            producto_id=uuid.uuid4(),
            cantidad=2,
            precio_unitario=1000,
            nombre="Llavero calavera",
            color="Rojo",
        )
    )
    return pedido


@pytest.fixture(autouse=True)
def _sin_esperas(monkeypatch):
    """Saca el `time.sleep` del reintento: los tests no esperan de verdad."""
    import app.infrastructure.correo.emailjs as modulo

    monkeypatch.setattr(modulo.time, "sleep", lambda _segundos: None)


# --- Modo simulacion: sin credenciales no se rompe el flujo ----------------


@pytest.mark.parametrize(
    "faltante",
    [
        "EMAILJS_PUBLIC_KEY",
        "EMAILJS_PRIVATE_KEY",
        "EMAILJS_SERVICE_ID",
        "EMAILJS_TEMPLATE_COMPROBANTE",
    ],
)
def test_sin_una_credencial_no_se_envia_nada(monkeypatch, faltante):
    """Cada credencial es obligatoria: con una sola faltante, modo simulacion."""
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso()
    monkeypatch.setattr(modulo.httpx, "post", http.post)
    config = dict(CREDENCIALES)
    del config[faltante]

    EmailJsCorreo(config).enviar_comprobante_pedido(_pedido(), "ana@x.test", "completado")

    assert http.llamadas == [], f"sin {faltante} no se puede enviar, pero se llamo a EmailJS"


def test_sin_credenciales_imprime_el_comprobante_en_consola(capsys):
    """El modo simulacion tiene que ser util: el contenido a la vista.

    Si solo se imprimiera "modo simulacion", en desarrollo habria que adivinar
    que se mando. La razon por la que el comprobante SI se imprime (y el codigo
    de verificacion del gateway no) es que el cliente lo espera.
    """
    pedido = _pedido()

    EmailJsCorreo({}).enviar_comprobante_pedido(pedido, "ana@x.test", "completado")

    salida = capsys.readouterr().out
    assert "ana@x.test" in salida, "el modo simulacion tiene que mostrar el destino"
    assert "$3.500" in salida, (
        f"el total sale formateado para el cliente, no en crudo: {salida!r}"
    )
    assert str(pedido.id) in salida, "el id del pedido permite encontrar la compra"
    assert "Llavero calavera" in salida, "no se imprime el contenido del comprobante"


def test_el_modo_simulacion_no_imprime_la_direccion_de_envio(capsys):
    """`direccion_envio` es el JSON crudo del cliente: no va a un log."""
    pedido = _pedido()
    pedido.direccion_envio = '{"nombre":"Ana","direccion":"Av. Siempre Viva 742"}'

    EmailJsCorreo({}).enviar_comprobante_pedido(pedido, "ana@x.test", "completado")

    salida = capsys.readouterr().out
    assert "Siempre Viva" not in salida, "se filtró la direccion del cliente al log"


def test_configurado_es_falso_sin_credenciales():
    assert EmailJsCorreo({}).configurado is False
    assert EmailJsCorreo(CREDENCIALES).configurado is True


# --- Con credenciales: el payload es lo que hay que revisar ----------------


def test_envia_el_payload_esperado_por_emailjs(monkeypatch):
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso()
    monkeypatch.setattr(modulo.httpx, "post", http.post)
    pedido = _pedido()

    EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(pedido, "ana@x.test", "completado")

    assert len(http.llamadas) == 1
    llamada = http.llamadas[0]
    assert llamada["url"].startswith("https://api.emailjs.com/api/")
    payload = llamada["json"]
    assert payload["service_id"] == "service_test"
    assert payload["template_id"] == "template_test", (
        "el comprobante tiene que usar la plantilla PROPIA, no la de "
        "verificacion del gateway"
    )
    assert payload["user_id"] == "pub_test"
    assert payload["accessToken"] == "priv_test", (
        "con 'Use Private Key' de EmailJS, accessToken es obligatorio"
    )
    assert payload["template_params"]["to_email"] == "ana@x.test"
    assert payload["template_params"]["pedido_id"] == str(pedido.id)


def test_el_snapshot_del_nombre_va_al_comprobante(monkeypatch):
    """El comprobante dice lo que se compró ese día, no el nombre actual.

    Mismo motivo que el snapshot del pedido: si el admin renombra el producto,
    un comprobante que cambia solo es un comprobante que miente.
    """
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso()
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(_pedido(), "ana@x.test", "completado")

    items = http.llamadas[0]["json"]["template_params"]["items"]
    assert "Llavero calavera" in items, items
    assert "producto" not in items, "un item sin nombre no puede caer en 'producto'"


def test_items_texto_plano_porque_emailjs_no_interpola_listas(monkeypatch):
    """Todo `template_params` va como string; una lista llega vacia a la plantilla."""
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso()
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(_pedido(), "ana@x.test", "completado")

    for clave, valor in http.llamadas[0]["json"]["template_params"].items():
        assert isinstance(valor, str), f"{clave} no es string: {type(valor)}"


# --- Que dice el comprobante: el estado es el del PAGO ----------------------


def _params(monkeypatch, pedido=None, estado_pago="completado") -> dict:
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso()
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(
        pedido or _pedido(), "ana@x.test", estado_pago
    )
    return http.llamadas[0]["json"]["template_params"]


def test_el_estado_del_comprobante_es_el_del_pago(monkeypatch):
    """El bug que se reporto: el comprobante decia "Estado: pendiente".

    `pedido.estado` describe el envio y recien va a cambiar cuando el admin
    marque "en produccion". En un comprobante de una compra recien pagada,
    mandar ese valor pone "Estado: pendiente" debajo de "¡Gracias por tu
    compra!", que el cliente lee como "mi pago quedo pendiente".
    """
    params = _params(monkeypatch)

    assert params["estado"] == "Pagado", (
        "el comprobante de una compra pagada tiene que decir 'Pagado'"
    )


def test_el_estado_del_comprobante_no_depende_del_estado_del_pedido(monkeypatch):
    """Se fija el invariante: el pedido va 'pendiente' y el comprobante 'Pagado'."""
    pedido = _pedido()
    pedido.estado = EstadoPedido.EN_PRODUCCION

    assert pedido.estado.value == "en_produccion"
    assert _params(monkeypatch, pedido)["estado"] == "Pagado", (
        "el estado del envio no tiene que filtrarse al comprobante de pago"
    )


def test_un_estado_de_pago_desconocido_se_pasa_tal_cual(monkeypatch):
    """Si mañana aparece 'reembolsado', el correo lo dice en vez de mentir."""
    assert _params(monkeypatch, estado_pago="reembolsado")["estado"] == "reembolsado"


def test_el_total_llega_formateado_en_pesos_chilenos(monkeypatch):
    """`3500` -> `"$3.500"`.

    La plantilla es HTML y no puede hacer aritmetica, y el separador de miles
    chileno (".") es ambiguo fuera de Chile. Que el backend lo mande listo
    evita que cada plantilla invente su propio formato.
    """
    params = _params(monkeypatch)

    assert params["total"] == "$3.500"
    assert params["items"].endswith("@ $1.000"), params["items"]


# --- Reintento: una insistencia, y solo cuando sirve -------------------------


def test_reintenta_una_vez_un_error_de_red(monkeypatch):
    """La red caida es el motivo realista de fallo, y se insistiere una vez."""
    import app.infrastructure.correo.emailjs as modulo

    intentos = {"n": 0}

    def post_que_falla_una_vez(url, json=None, timeout=None):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise modulo.httpx.ConnectError("no hay internet")
        return _RespuestaFalsa()

    monkeypatch.setattr(modulo.httpx, "post", post_que_falla_una_vez)

    EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(_pedido(), "ana@x.test", "completado")

    assert intentos["n"] == 2, "un error de red tiene que reintentarse"


def test_no_reintenta_un_4xx_de_emailjs(monkeypatch):
    """Con la credencial mala, repetir el mismo POST no arregla nada.

    Solo suma latencia a un request que la pasarela espera de forma sincronica.
    """
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso(respuesta=_RespuestaFalsa(400, "The template ID is invalid"))
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    with pytest.raises(ErrorEnvioCorreo):
        EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(
            _pedido(), "ana@x.test", "completado"
        )

    assert len(http.llamadas) == 1, f"un 4xx no se reintenta: hubo {len(http.llamadas)}"


def test_reintenta_un_5xx_de_emailjs(monkeypatch):
    """Un 5xx es del lado de EmailJS: puede ser transitorio, se reintenta."""
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso(respuesta=_RespuestaFalsa(503, "Service unavailable"))
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    with pytest.raises(ErrorEnvioCorreo):
        EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(
            _pedido(), "ana@x.test", "completado"
        )

    assert len(http.llamadas) == 2, f"un 5xx se reintenta una vez: hubo {len(http.llamadas)}"


def test_despues_del_reintento_igual_falla_por_el_pago_no_se_cae(monkeypatch):
    """Dos fallos y levanta `ErrorEnvioCorreo`, que el caso de uso traga."""
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso(error=modulo.httpx.ConnectError("no hay internet"))
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    with pytest.raises(ErrorEnvioCorreo):
        EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(
            _pedido(), "ana@x.test", "completado"
        )

    assert len(http.llamadas) == 2, "el reintento es UNO, no un bucle"


# --- Errores: se propagan como ErrorEnvioCorreo, no como http ----------------


def test_error_de_red_se_traduce_a_error_de_envio(monkeypatch):
    """El dominio no debe conocer `httpx`: la traduccion es del adaptador."""
    import httpx as modulo_httpx

    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso(error=modulo_httpx.ConnectError("no hay internet"))
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    with pytest.raises(ErrorEnvioCorreo):
        EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(_pedido(), "ana@x.test", "completado")


def test_respuesta_de_error_de_emailjs_se_traduce(monkeypatch):
    import app.infrastructure.correo.emailjs as modulo

    http = _HttpxFalso(respuesta=_RespuestaFalsa(400, "The template ID is invalid"))
    monkeypatch.setattr(modulo.httpx, "post", http.post)

    with pytest.raises(ErrorEnvioCorreo) as error:
        EmailJsCorreo(CREDENCIALES).enviar_comprobante_pedido(_pedido(), "ana@x.test", "completado")

    assert "400" in str(error.value), (
        "el status de EmailJS va en el mensaje: es la unica pista de por que fallo"
    )


# --- El contrato ----------------------------------------------------------


def test_es_un_servicio_correo():
    assert issubclass(EmailJsCorreo, ServicioCorreo)
    assert isinstance(EmailJsCorreo(CREDENCIALES), ServicioCorreo)