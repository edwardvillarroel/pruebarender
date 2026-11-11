"""Cliente TUU: sin `TUU_SECRET_KEY` no se firma ni se valida (fail-closed).

El secreto embebido se elimino del codigo (OWASP A04): la key real viene del
entorno. Estos tests blindan que un secreto vacio no se use para cobrar ni
para aceptar callbacks (una firma HMAC con clave vacia es forjable).
"""

import hashlib
import hmac

import pytest

from app.domain.interfaces.pasarela_pago import ErrorPasarela, SolicitudPago
from app.infrastructure.pagos.tuu_client import TuuCliente


def _config(secret_key: str) -> dict:
    return {
        "TUU_ACCOUNT_ID": "62224230",
        "TUU_SECRET_KEY": secret_key,
        "TUU_API_URL": "https://example.test/payment",
        "TUU_SHOP_NAME": "ApoloVibes",
        "TUU_URL_CALLBACK": "http://localhost:3000/api/pago/callback",
        "TUU_URL_COMPLETE": "http://localhost:5173/pago/retorno",
        "TUU_URL_CANCEL": "http://localhost:5173/checkout",
    }


def _solicitud() -> SolicitudPago:
    return SolicitudPago(
        monto=1000,
        referencia="abc123",
        descripcion="Pedido",
        nombre_cliente="Ana",
        email_cliente="ana@example.com",
        telefono_cliente="+56911111111",
        apellido_cliente="Perez",
    )


def test_crear_intento_sin_secret_key_falla_sin_llamar_a_la_pasarela():
    cliente = TuuCliente(_config(""))

    with pytest.raises(ErrorPasarela, match="TUU_SECRET_KEY"):
        cliente.crear_intento(_solicitud())


def test_verificar_firma_sin_secret_key_rechaza_todo():
    """Un secreto vacio permitiria forjar la firma: se rechaza siempre."""
    cliente = TuuCliente(_config(""))

    # Firma calculada con clave vacia (lo que un atacante podria producir).
    cadena = "x_amount1000x_referenceabc123"
    firma_forjada = hmac.new(b"", cadena.encode(), hashlib.sha256).hexdigest()

    assert (
        cliente.verificar_firma(
            {"x_amount": "1000", "x_reference": "abc123", "x_signature": firma_forjada}
        )
        is False
    )


def test_verificar_firma_con_secret_key_valida_la_firma_correcta():
    cliente = TuuCliente(_config("secreto-real"))
    parametros = {"x_amount": "1000", "x_reference": "abc123"}
    cadena = "x_amount1000x_referenceabc123"
    firma = hmac.new(b"secreto-real", cadena.encode(), hashlib.sha256).hexdigest()

    assert cliente.verificar_firma({**parametros, "x_signature": firma}) is True


def test_verificar_firma_con_secret_key_rechaza_firma_incorrecta():
    cliente = TuuCliente(_config("secreto-real"))

    assert (
        cliente.verificar_firma({"x_amount": "1000", "x_signature": "no-valida"})
        is False
    )
