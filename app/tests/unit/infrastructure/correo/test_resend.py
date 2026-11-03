"""El adaptador de Resend: qué hace con credenciales y qué hace sin ellas.

El contrato que importa es el modo simulación. El backend tiene que poder
arrancar y pagar en desarrollo sin que nadie haya configurado Resend, así que sin
credenciales el comprobante se imprime en la consola y no se lanza nada.

`httpx.post` se monkeypatchea en vez de usar `respx` o un servidor local: no
está la dependencia en `requirements.txt` y agregar una librería para probar una
llamada HTTP no vale el costo. Lo que se prueba es el payload que armamos y los
avisos que decidimos mandar.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import Producto
from app.domain.entities.solicitud_diseno import EstadoSolicitud, SolicitudDiseno
from app.domain.enums import EstadoPedido
from app.domain.interfaces.correo import ErrorEnvioCorreo, ServicioCorreo
from app.infrastructure.correo.resend import ResendCorreo

CREDENCIALES = {
    "RESEND_API_KEY": "re_test",
    "EMAIL_FROM": "ApoloVibes <pedidos@x.test>",
    "ADMIN_EMAIL": "admin@x.test",
    "FRONTEND_URL": "https://apolovibes3d.cl",
}


class _RespuestaFalsa:
    def __init__(self, status_code: int = 200, datos: dict | None = None):
        self.status_code = status_code
        self._datos = datos or {"id": "email_test"}

    def json(self) -> dict:
        return self._datos


class _HttpxFalso:
    """Captura el POST en vez de salir a la red."""

    def __init__(self, respuestas=None, error: Exception | None = None):
        self.llamadas: list[dict] = []
        self._respuestas = list(respuestas or [_RespuestaFalsa()])
        self._error = error

    def post(self, url, json=None, headers=None, timeout=None):
        self.llamadas.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if self._error is not None:
            raise self._error
        if len(self._respuestas) > 1:
            siguiente = self._respuestas.pop(0)
        else:
            siguiente = self._respuestas[0]
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


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


def _solicitud(**cambios) -> SolicitudDiseno:
    datos = {
        "usuario_id": uuid.uuid4(),
        "nombre": "Ana Pérez",
        "email": "ana@x.test",
        "material": "PLA",
        "descripcion": "Un llavero",
        "telefono": "+56911111111",
        "cantidad": 2,
        "estado": EstadoSolicitud.PENDIENTE,
    }
    datos.update(cambios)
    return SolicitudDiseno(**datos)


@pytest.fixture(autouse=True)
def _sin_esperas(monkeypatch):
    """Saca el `time.sleep` del reintento: los tests no esperan de verdad."""
    import shared.correo.cliente as modulo

    monkeypatch.setattr(modulo.time, "sleep", lambda _segundos: None)


def _http(monkeypatch, **kwargs) -> _HttpxFalso:
    import shared.correo.cliente as modulo

    http = _HttpxFalso(**kwargs)
    monkeypatch.setattr(modulo.httpx, "post", http.post)
    return http


# --- Modo simulación: sin credenciales no se rompe el flujo ----------------


@pytest.mark.parametrize("faltante", ["RESEND_API_KEY", "EMAIL_FROM"])
def test_sin_una_credencial_no_se_envia_nada(monkeypatch, faltante):
    """Cada credencial es obligatoria: con una sola faltante, modo simulación."""
    http = _http(monkeypatch)
    config = dict(CREDENCIALES)
    del config[faltante]

    ResendCorreo(config).enviar_comprobante_pedido(
        _pedido(), "ana@x.test", "completado"
    )

    assert http.llamadas == [], f"sin {faltante} no se puede enviar, pero se llamó a Resend"


def test_sin_credenciales_imprime_el_comprobante_en_consola(capsys):
    """El modo simulación tiene que ser útil: el contenido a la vista."""
    pedido = _pedido()

    ResendCorreo({}).enviar_comprobante_pedido(
        pedido, "ana@x.test", "completado"
    )

    salida = capsys.readouterr().out
    assert "ana@x.test" in salida, "el modo simulación tiene que mostrar el destino"
    assert "$3.500" in salida, (
        f"el total sale formateado para el cliente, no en crudo: {salida!r}"
    )
    assert str(pedido.id)[:8] in salida, "el id del pedido permite encontrar la compra"
    assert "Llavero calavera" in salida, "no se imprime el contenido del comprobante"


def test_el_modo_simulacion_no_imprime_la_direccion_de_envio(capsys):
    """`direccion_envio` es el JSON crudo del cliente: no va a un log."""
    pedido = _pedido()
    pedido.direccion_envio = '{"nombre":"Ana","direccion":"Av. Siempre Viva 742"}'

    ResendCorreo({}).enviar_comprobante_pedido(
        pedido, "ana@x.test", "completado"
    )

    salida = capsys.readouterr().out
    assert "Siempre Viva" not in salida, "se filtró la dirección del cliente al log"


def test_configurado_depende_de_las_dos_credenciales():
    assert ResendCorreo({}).configurado is False
    assert ResendCorreo(CREDENCIALES).configurado is True


# --- Con credenciales: el payload es lo que hay que revisar ----------------


def test_envia_el_payload_esperado_por_resend(monkeypatch):
    http = _http(monkeypatch)
    pedido = _pedido()

    ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
        pedido, "ana@x.test", "completado"
    )

    assert len(http.llamadas) == 1
    llamada = http.llamadas[0]
    assert llamada["url"] == "https://api.resend.com/emails"
    assert llamada["headers"]["Authorization"] == "Bearer re_test"
    assert llamada["headers"]["Content-Type"] == "application/json"
    assert llamada["headers"]["User-Agent"] == "ApoloVibes/1.0"
    payload = llamada["json"]
    assert payload["from"] == "ApoloVibes <pedidos@x.test>"
    assert payload["to"] == ["ana@x.test"]
    assert str(pedido.id)[:8] in payload["subject"]
    assert "Llavero calavera" in payload["html"]
    assert "Llavero calavera" in payload["text"]


def test_el_snapshot_del_nombre_va_al_comprobante(monkeypatch):
    """El comprobante dice lo que se compró ese día, no el nombre actual."""
    http = _http(monkeypatch)

    ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
        _pedido(), "ana@x.test", "completado"
    )

    html = http.llamadas[0]["json"]["html"]
    assert "Llavero calavera" in html


# --- Que dice el comprobante: el estado es el del PAGO ----------------------


def _payload(monkeypatch, pedido=None, estado_pago="completado") -> dict:
    http = _http(monkeypatch)
    ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
        pedido or _pedido(), "ana@x.test", estado_pago
    )
    return http.llamadas[0]["json"]


def test_el_estado_del_comprobante_es_el_del_pago(monkeypatch):
    payload = _payload(monkeypatch)

    assert "Pagado" in payload["html"]
    assert "Pagado" in payload["text"]


def test_el_estado_del_comprobante_no_depende_del_estado_del_pedido(monkeypatch):
    pedido = _pedido()
    pedido.estado = EstadoPedido.EN_PRODUCCION

    assert pedido.estado.value == "en_produccion"
    payload = _payload(monkeypatch, pedido)
    assert "Pagado" in payload["html"]


def test_un_estado_de_pago_desconocido_se_pasa_tal_cual(monkeypatch):
    payload = _payload(monkeypatch, estado_pago="reembolsado")
    assert "reembolsado" in payload["html"]


def test_el_total_llega_formateado_en_pesos_chilenos(monkeypatch):
    payload = _payload(monkeypatch)

    assert "$3.500" in payload["html"]
    assert "$2.000" in payload["html"]


def test_los_descuentos_viajan_formateados_y_vacios_si_no_hay(monkeypatch):
    pedido = _pedido()
    pedido.subtotal = 4500
    pedido.descuento_productos = 1000
    pedido.descuento_cupon = 500
    pedido.cupon_codigo = "APOLO10"

    payload = _payload(monkeypatch, pedido)
    assert "$4.500" in payload["html"]
    assert "- $1.000" in payload["html"]
    assert "Cupón (APOLO10)" in payload["html"]
    assert "- $500" in payload["html"]

    sin_descuentos = _payload(monkeypatch, _pedido())
    assert "APOLO10" not in sin_descuentos["html"]
    assert "- $" not in sin_descuentos["html"]


# --- Reintento: una insistencia, y solo cuando sirve -------------------------


def test_reintenta_una_vez_un_error_de_red(monkeypatch):
    import shared.correo.cliente as modulo

    intentos = {"n": 0}

    def post_que_falla_una_vez(url, json=None, headers=None, timeout=None):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise modulo.httpx.ConnectError("no hay internet")
        return _RespuestaFalsa()

    monkeypatch.setattr(modulo.httpx, "post", post_que_falla_una_vez)

    ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
        _pedido(), "ana@x.test", "completado"
    )

    assert intentos["n"] == 2, "un error de red tiene que reintentarse"


def test_no_reintenta_un_4xx_de_resend(monkeypatch):
    http = _http(
        monkeypatch,
        respuestas=[
            _RespuestaFalsa(
                422,
                {
                    "name": "validation_error",
                    "message": "The from address is invalid",
                },
            )
        ],
    )

    with pytest.raises(ErrorEnvioCorreo):
        ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
            _pedido(), "ana@x.test", "completado"
        )

    assert len(http.llamadas) == 1, f"un 4xx no se reintenta: hubo {len(http.llamadas)}"


def test_reintenta_y_se_recupera_de_un_5xx(monkeypatch):
    http = _http(
        monkeypatch,
        respuestas=[_RespuestaFalsa(503, {"message": "unavailable"}), _RespuestaFalsa()],
    )

    ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
        _pedido(), "ana@x.test", "completado"
    )

    assert len(http.llamadas) == 2, "un 5xx se reintenta una vez"


def test_dos_5xx_terminan_en_error_controlado(monkeypatch):
    http = _http(
        monkeypatch,
        respuestas=[
            _RespuestaFalsa(503, {"message": "unavailable"}),
            _RespuestaFalsa(503, {"message": "unavailable"}),
        ],
    )

    with pytest.raises(ErrorEnvioCorreo):
        ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
            _pedido(), "ana@x.test", "completado"
        )

    assert len(http.llamadas) == 2, "el reintento es UNO, no un bucle"


def test_despues_del_reintento_igual_falla_por_el_pago_no_se_cae(monkeypatch):
    import shared.correo.cliente as modulo

    http = _http(monkeypatch, error=modulo.httpx.ConnectError("no hay internet"))

    with pytest.raises(ErrorEnvioCorreo):
        ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
            _pedido(), "ana@x.test", "completado"
        )

    assert len(http.llamadas) == 2, "el reintento es UNO, no un bucle"


# --- Errores: se propagan como ErrorEnvioCorreo, no como http ----------------


def test_respuesta_de_error_de_resend_se_traduce(monkeypatch):
    _http(
        monkeypatch,
        respuestas=[
            _RespuestaFalsa(
                422,
                {
                    "name": "validation_error",
                    "message": "The from address is invalid",
                },
            )
        ],
    )

    with pytest.raises(ErrorEnvioCorreo) as error:
        ResendCorreo(CREDENCIALES).enviar_comprobante_pedido(
            _pedido(), "ana@x.test", "completado"
        )

    mensaje = str(error.value)
    assert "422" in mensaje, "el status de Resend va en el mensaje"
    assert "validation_error" in mensaje
    assert "re_test" not in mensaje, "la API key nunca puede aparecer en un error"


# --- Avisos internos y de cotizaciones --------------------------------------


def test_aviso_de_pedido_pagado_va_al_admin(monkeypatch):
    http = _http(monkeypatch)

    ResendCorreo(CREDENCIALES).avisar_admin_pedido_pagado(
        _pedido(), "ana@x.test", "completado"
    )

    payload = http.llamadas[0]["json"]
    assert payload["to"] == ["admin@x.test"]
    assert "Nuevo pedido pagado" in payload["subject"]
    assert "ana@x.test" in payload["html"]


def test_aviso_de_pedido_pagado_sin_admin_no_envia(monkeypatch):
    http = _http(monkeypatch)
    config = dict(CREDENCIALES)
    del config["ADMIN_EMAIL"]

    ResendCorreo(config).avisar_admin_pedido_pagado(
        _pedido(), "ana@x.test", "completado"
    )

    assert http.llamadas == []


def test_aviso_de_stock_bajo_va_al_admin(monkeypatch):
    http = _http(monkeypatch)
    productos = [
        Producto(
            nombre="Dragón",
            categoria_id=uuid.uuid4(),
            precio=1000,
            stock=0,
            stock_minimo=3,
        )
    ]

    ResendCorreo(CREDENCIALES).avisar_admin_stock_bajo(productos)

    payload = http.llamadas[0]["json"]
    assert payload["to"] == ["admin@x.test"]
    assert "Stock bajo" in payload["subject"]
    assert "Agotado" in payload["html"]


def test_aviso_de_nueva_cotizacion_va_al_admin(monkeypatch):
    http = _http(monkeypatch)
    solicitud = _solicitud()

    ResendCorreo(CREDENCIALES).avisar_admin_nueva_cotizacion(solicitud)

    payload = http.llamadas[0]["json"]
    assert payload["to"] == ["admin@x.test"]
    assert "Nueva cotización" in payload["subject"]
    assert "ana@x.test" in payload["html"]


def test_cotizacion_aprobada_va_al_cliente(monkeypatch):
    http = _http(monkeypatch)
    solicitud = _solicitud(estado=EstadoSolicitud.APROBADA, precio=Decimal("4500"))

    ResendCorreo(CREDENCIALES).enviar_estado_cotizacion(
        solicitud, "aprobada", 4500
    )

    payload = http.llamadas[0]["json"]
    assert payload["to"] == ["ana@x.test"]
    assert "aprobada" in payload["subject"]
    assert "Para pagar, revisa los detalles en nuestra página:" in payload["text"]
    assert "https://apolovibes3d.cl/mis-cotizaciones" in payload["text"]
    assert "$4.500" in payload["html"]


def test_cotizacion_rechazada_va_al_cliente(monkeypatch):
    http = _http(monkeypatch)
    solicitud = _solicitud(estado=EstadoSolicitud.RECHAZADA)

    ResendCorreo(CREDENCIALES).enviar_estado_cotizacion(
        solicitud, "rechazada"
    )

    payload = http.llamadas[0]["json"]
    assert payload["to"] == ["ana@x.test"]
    assert "rechazada" in payload["subject"]
    assert "Puedes enviarnos una nueva solicitud cuando quieras." in payload["text"]


def test_cotizacion_sin_email_no_envia(monkeypatch):
    http = _http(monkeypatch)
    solicitud = _solicitud(email="")

    ResendCorreo(CREDENCIALES).enviar_estado_cotizacion(
        solicitud, "aprobada", 4500
    )

    assert http.llamadas == []


# --- El contrato -----------------------------------------------------------


def test_es_un_servicio_correo():
    assert issubclass(ResendCorreo, ServicioCorreo)
    assert isinstance(ResendCorreo(CREDENCIALES), ServicioCorreo)
