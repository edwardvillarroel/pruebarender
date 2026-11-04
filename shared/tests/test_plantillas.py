"""Las plantillas generan el asunto y el contenido que prometemos."""

from __future__ import annotations

from datetime import datetime, timezone

from shared.correo.formato import ICONO_COLORES, formatear_pesos, icono_html
from shared.correo.modelos import (
    CotizacionCorreo,
    DescuentoCorreo,
    ItemCorreo,
    PedidoCorreo,
    ProductoCorreo,
)
from shared.correo import plantillas

FRONTEND = "https://apolovibes3d.cl"


def _asset(nombre: str) -> str:
    return f"{FRONTEND}/media/{nombre}"


def _assert_marco(html: str) -> None:
    assert _asset("correo-onda-header.png") in html
    assert _asset("correo-onda-footer.png") in html


def _assert_icono(html: str, nombre: str) -> None:
    assert _asset(f"correo-icono-{nombre}.png") in html
    assert f"border:4px solid {ICONO_COLORES[nombre]}" in html


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
    assert "¡Gracias por tu compra!" in correo.html
    assert "Este es el comprobante de tu pedido #abc12345." in correo.html
    assert "Tus productos" in correo.html
    assert "Llavero calavera" in correo.texto
    assert "x2" in correo.html
    assert "$2.000" in correo.html
    assert "$2.000" in correo.texto
    assert "¡Impulsando la creatividad con cada impresión!" in correo.texto
    _assert_marco(correo.html)
    _assert_icono(correo.html, "check")


def test_aviso_admin_de_pedido_pagado_enlaza_al_panel():
    correo = plantillas.admin_pedido_pagado(_pedido(), FRONTEND)

    assert "Nuevo pedido pagado" in correo.asunto
    assert "Nuevo pedido pagado" in correo.html
    assert "ana@x.test" in correo.html
    assert "Productos" in correo.html
    assert f"{FRONTEND}/admin/pedidos" in correo.texto
    _assert_icono(correo.html, "campana")


def test_aviso_admin_de_nueva_cotizacion_con_los_datos_clave():
    correo = plantillas.admin_nueva_cotizacion(_cotizacion(), FRONTEND)

    assert "Nueva cotización #cot12345" in correo.html
    assert "Ingresó una nueva solicitud de cotización." in correo.html
    assert "Cliente: Ana Pérez" in correo.texto
    assert "Teléfono: +56911111111" in correo.texto
    assert "Material: PLA" in correo.texto
    assert "Precio estimado: $4.500" in correo.texto
    assert "Email:" not in correo.texto
    assert "Estimación IA" not in correo.html
    assert f"{FRONTEND}/admin/cotizaciones" in correo.texto
    _assert_icono(correo.html, "lapiz")


def test_aviso_de_stock_bajo_lista_agotados_y_bajos():
    correo = plantillas.admin_stock_bajo(
        [
            ProductoCorreo(nombre="Dragón", stock=0, stock_minimo=3),
            ProductoCorreo(nombre="Llavero", stock=2, stock_minimo=3),
        ],
        FRONTEND,
    )

    assert "Stock bajo en ApoloVibes" in correo.asunto
    assert "Dragón: Agotado" in correo.texto
    assert "Llavero: Stock 2 (mín. 3)" in correo.texto
    assert "Agotado" in correo.html
    assert "Stock: 2 (mín. 3)" in correo.html
    assert _asset("correo-icono-cubo.png") in correo.html
    _assert_icono(correo.html, "alerta")


def test_cotizacion_aprobada_tiene_el_copy_y_el_enlace():
    correo = plantillas.cotizacion_aprobada(_cotizacion(), 4500, FRONTEND)

    assert correo.asunto == "Tu cotización #cot12345 fue aprobada"
    assert "Hola Ana Pérez," in correo.texto
    assert "Tu cotización #cot12345 fue aprobada." in correo.texto
    assert "Material: PLA" in correo.texto
    assert "Cantidad" not in correo.texto
    assert "Descripción" not in correo.texto
    assert "Para pagar, revisa los detalles en nuestra página:" in correo.texto
    assert f"{FRONTEND}/mis-cotizaciones" in correo.texto
    assert "$4.500" in correo.html
    assert "Estimación IA" not in correo.html
    _assert_icono(correo.html, "check")


def test_cotizacion_rechazada_tiene_el_copy_exacto():
    correo = plantillas.cotizacion_rechazada(_cotizacion(), FRONTEND)

    assert correo.asunto == "Tu cotización #cot12345 fue rechazada"
    assert "Hola Ana Pérez," in correo.texto
    assert "Tu cotización #cot12345 fue rechazada." in correo.texto
    assert "Puedes enviarnos una nueva solicitud cuando quieras." in correo.texto
    assert "Puedes enviarnos una nueva solicitud cuando quieras." in correo.html
    assert "Estimación IA" not in correo.html
    _assert_icono(correo.html, "equis")


def test_codigo_y_alerta_de_seguridad():
    codigo = plantillas.codigo_verificacion("123456")
    assert codigo.asunto == "Tu código de verificación — ApoloVibes"
    assert "Tu código de verificación es:" in codigo.texto
    assert "123456" in codigo.texto
    assert "Este código tiene una vigencia de 5 minutos." in codigo.texto
    assert "Si no solicitaste este código, ignora este mensaje." in codigo.texto
    _assert_marco(codigo.html)
    _assert_icono(codigo.html, "escudo")

    alerta = plantillas.alerta_seguridad("Se detectaron intentos fallidos.")
    assert alerta.asunto == "Alerta de seguridad — ApoloVibes"
    assert "Detectamos actividad de seguridad en tu cuenta." in alerta.texto
    assert "Se detectaron intentos fallidos." in alerta.texto
    assert "Si no fuiste tú, cambia tu contraseña de inmediato." in alerta.texto
    _assert_icono(alerta.html, "escudo-alerta")


def test_codigo_de_registro_declara_su_vigencia_real():
    codigo = plantillas.codigo_verificacion("123456", minutos=10)

    assert "Este código tiene una vigencia de 10 minutos." in codigo.html
    assert "Este código tiene una vigencia de 10 minutos." in codigo.texto
    assert "5 minutos" not in codigo.texto


def test_icono_html_usa_el_color_del_glifo():
    html = icono_html("equis", FRONTEND)

    assert _asset("correo-icono-equis.png") in html
    assert f"border:4px solid {ICONO_COLORES['equis']}" in html
    assert 'width="32" height="32"' in html


def test_el_html_escapa_datos_del_cliente():
    cotizacion = _cotizacion()
    cotizacion = CotizacionCorreo(
        **{**cotizacion.__dict__, "nombre": "<script>alert(1)</script>"}
    )

    correo = plantillas.cotizacion_aprobada(cotizacion, 4500, FRONTEND)

    assert "<script>" not in correo.html
    assert "&lt;script&gt;" in correo.html


def test_descripcion_heredada_muestra_solo_lo_que_escribio_el_usuario():
    cotizacion = CotizacionCorreo(
        **{
            **_cotizacion().__dict__,
            "descripcion": (
                "Tamaño: 10 x 5 x 2 cm\n"
                "Cantidad: 2\n"
                "Uso: Decorativo\n"
                "Color: Negro\n"
                "Detalles: Quiero el nombre Ana en la base\n"
                "Precio estimado IA: $4.500\n"
                "Material IA: PLA\n"
                "Complejidad IA: Baja"
            ),
        }
    )

    correo = plantillas.admin_nueva_cotizacion(cotizacion, FRONTEND)

    assert "Quiero el nombre Ana en la base" in correo.html
    assert "Tamaño:" not in correo.html
    assert "Precio estimado IA: $4.500" not in correo.html
    assert "Quiero el nombre Ana en la base" in correo.texto
    assert "Tamaño:" not in correo.texto


def test_descripcion_heredada_en_una_sola_linea():
    cotizacion = CotizacionCorreo(
        **{
            **_cotizacion().__dict__,
            "descripcion": (
                "Tamaño: 10x5x3 cm / Cantidad: 2 / Uso: prototipo / "
                "Color: Rojo / Detalles: prueba"
            ),
        }
    )

    correo = plantillas.admin_nueva_cotizacion(cotizacion, FRONTEND)

    assert "prueba" in correo.html
    assert "Tamaño:" not in correo.html


def test_sin_descripcion_no_se_muestra_la_fila():
    cotizacion = CotizacionCorreo(**{**_cotizacion().__dict__, "descripcion": ""})

    correo = plantillas.admin_nueva_cotizacion(cotizacion, FRONTEND)

    assert "Descripción:" not in correo.texto
    assert ">Descripción<" not in correo.html
    assert "Estimación IA" not in correo.html
