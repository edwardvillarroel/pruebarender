"""Las plantillas generan el asunto y el contenido que prometemos."""

from __future__ import annotations

from datetime import datetime, timezone

from shared.correo.formato import formatear_pesos
from shared.correo.modelos import (
    CotizacionCorreo,
    DescuentoCorreo,
    ItemCorreo,
    PedidoCorreo,
    ProductoCorreo,
)
from shared.correo import plantillas

FRONTEND = "https://apolovibes3d.cl"


def _pedido() -> PedidoCorreo:
    return PedidoCorreo(
        numero="abc12345",
        fecha=datetime(2026, 11, 2, 15, 30, tzinfo=timezone.utc),
        email_cliente="ana@x.test",
        estado_pago="Pagado",
        items=[
            ItemCorreo(
                nombre="Llavero calavera",
                cantidad=2,
                precio_unitario=1000,
                subtotal=2000,
            )
        ],
        descuentos=[DescuentoCorreo(etiqueta="Cupón (APOLO10)", monto=500)],
        subtotal=2500,
        descuento_total=500,
        costo_envio=0,
        total=2000,
        tipo_entrega="Envío a domicilio",
        direccion="Av. Siempre Viva 742, Providencia",
        notas=None,
    )


def _cotizacion() -> CotizacionCorreo:
    return CotizacionCorreo(
        numero="cot12345",
        fecha=datetime(2026, 11, 2, 15, 30, tzinfo=timezone.utc),
        nombre="Ana Pérez",
        email="ana@x.test",
        telefono="+56911111111",
        material="PLA",
        alto=10.0,
        ancho=5.0,
        largo=2.0,
        unidad="cm",
        cantidad=2,
        uso="Decorativo",
        color="Negro",
        descripcion="Un llavero",
        precio=4500,
        estado="aprobada",
    )


def test_formatear_pesos_chilenos():
    assert formatear_pesos(3500) == "$3.500"
    assert formatear_pesos(-500) == "-$500"
    assert formatear_pesos(None) == ""


def test_comprobante_incluye_numero_total_e_items():
    correo = plantillas.comprobante_pedido(_pedido(), FRONTEND)

    assert "abc12345" in correo.asunto
    assert "abc12345" in correo.html
    assert "Llavero calavera" in correo.texto
    assert "$2.000" in correo.html
    assert "$2.000" in correo.texto


def test_aviso_admin_de_pedido_pagado_enlaza_al_panel():
    correo = plantillas.admin_pedido_pagado(_pedido(), FRONTEND)

    assert "Nuevo pedido pagado" in correo.asunto
    assert "ana@x.test" in correo.html
    assert f"{FRONTEND}/admin/pedidos" in correo.texto


def test_aviso_de_stock_bajo_lista_agotados_y_bajos():
    correo = plantillas.admin_stock_bajo(
        [
            ProductoCorreo(nombre="Dragón", stock=0, stock_minimo=3),
            ProductoCorreo(nombre="Llavero", stock=2, stock_minimo=3),
        ],
        FRONTEND,
    )

    assert "Stock bajo" in correo.asunto
    assert "Dragón: Agotado" in correo.texto
    assert "Llavero: stock 2 (mínimo 3)" in correo.texto


def test_cotizacion_aprobada_tiene_el_copy_y_el_enlace():
    correo = plantillas.cotizacion_aprobada(_cotizacion(), 4500, FRONTEND)

    assert correo.asunto == "Tu cotización #cot12345 fue aprobada"
    assert "Tu cotización #cot12345 fue aprobada." in correo.texto
    assert "Para pagar, revisa los detalles en nuestra página:" in correo.texto
    assert f"{FRONTEND}/mis-cotizaciones" in correo.texto
    assert "$4.500" in correo.html


def test_cotizacion_rechazada_tiene_el_copy_exacto():
    correo = plantillas.cotizacion_rechazada(_cotizacion(), FRONTEND)

    assert correo.asunto == "Tu cotización #cot12345 fue rechazada"
    assert "Tu cotización #cot12345 fue rechazada." in correo.texto
    assert "Puedes enviarnos una nueva solicitud cuando quieras." in correo.texto


def test_codigo_y_alerta_de_seguridad():
    codigo = plantillas.codigo_verificacion("123456")
    assert codigo.asunto == "Tu código de verificación — ApoloVibes"
    assert "Tu código de verificación es 123456." in codigo.texto
    assert "Este código tiene una vigencia limitada." in codigo.texto

    alerta = plantillas.alerta_seguridad("Se detectaron intentos fallidos.")
    assert alerta.asunto == "Alerta de seguridad — ApoloVibes"
    assert "Detectamos actividad de seguridad en tu cuenta." in alerta.texto
    assert "Si no fuiste tú, cambia tu contraseña de inmediato." in alerta.texto


def test_el_html_escapa_datos_del_cliente():
    cotizacion = _cotizacion()
    cotizacion = CotizacionCorreo(
        **{**cotizacion.__dict__, "nombre": "<script>alert(1)</script>"}
    )

    correo = plantillas.cotizacion_aprobada(cotizacion, 4500, FRONTEND)

    assert "<script>" not in correo.html
    assert "&lt;script&gt;" in correo.html
