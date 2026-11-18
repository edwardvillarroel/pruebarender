
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from app.api.routes.catalogo_routes import (
    CACHE_IMAGENES_SEGUNDOS,
    _a_publico_producto,
)
from app.application.catalogo_stock.gestionar_producto import RankingSemana
from app.domain.entities.producto import ImagenProducto, Producto, ProductoVendido


def _producto(**cambios) -> Producto:
    base = dict(
        nombre="Producto de prueba",
        categoria_id=uuid4(),
        precio=1000,
        stock=3,
    )
    base.update(cambios)
    return Producto(**base)




def test_un_lanzamiento_viaja_con_la_etiqueta_nuevo():
    publico = _a_publico_producto(_producto(nuevo_lanzamiento=True))

    assert publico["badge"] == "Nuevo"
    assert publico["nuevo_lanzamiento"] is True


def test_un_producto_normal_no_viaja_con_etiqueta():
    publico = _a_publico_producto(_producto())

    assert publico["badge"] is None
    assert publico["nuevo_lanzamiento"] is False


def test_un_badge_manual_no_se_pisa_cuando_no_es_lanzamiento():

    publico = _a_publico_producto(_producto(badge="Best Seller"))

    assert publico["badge"] == "Best Seller"


def test_la_etiqueta_nuevo_tiene_prioridad_sobre_el_badge_manual():

    publico = _a_publico_producto(_producto(badge="Best Seller", nuevo_lanzamiento=True))

    assert publico["badge"] == "Nuevo"




def test_la_fecha_de_alta_viaja_en_iso():
    fecha = datetime(2026, 9, 26, 3, 0, 28)

    publico = _a_publico_producto(_producto(creado_en=fecha))

    assert publico["creado_en"] == "2026-09-26T03:00:28"


def test_un_producto_sin_fecha_no_rompe_el_json():
    publico = _a_publico_producto(_producto(creado_en=None))

    assert publico["creado_en"] is None


def test_el_flag_siempre_viaja_como_booleano():

    publico = _a_publico_producto(_producto())

    assert publico["nuevo_lanzamiento"] is False
    assert isinstance(publico["nuevo_lanzamiento"], bool)




def test_un_producto_bajo_stock_viaja_con_el_flag_prendido():
    publico = _a_publico_producto(_producto(stock=3))

    assert publico["stock_bajo"] is True
    assert isinstance(publico["stock_bajo"], bool)
    assert publico["stock_minimo"] is None


def test_un_producto_con_stock_de_sobra_no_es_stock_bajo():
    publico = _a_publico_producto(_producto(stock=10))

    assert publico["stock_bajo"] is False


def test_el_stock_minimo_propio_manda_sobre_el_global():
    publico = _a_publico_producto(_producto(stock=5, stock_minimo=6))

    assert publico["stock_bajo"] is True
    assert publico["stock_minimo"] == 6




def _servicio_con_ranking(vendidos=None) -> Mock:
    servicio = Mock()
    servicio.listar_mas_vendidos.return_value = vendidos or []
    return servicio


def _vendido(nombre: str = "Figura", unidades: int = 3, ingresos: int = 9000):
    producto = Producto(nombre=nombre, categoria_id=uuid4(), precio=3000, stock=2)
    return ProductoVendido(producto=producto, unidades=unidades, ingresos=ingresos)


def test_el_ranking_de_mas_vendidos_es_publico(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking([_vendido()])

    respuesta = client.get("/api/productos/mas-vendidos")

    assert respuesta.status_code == 200


def test_el_ranking_devuelve_las_unidades_y_los_ingresos(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking(
        [_vendido(unidades=7, ingresos=21000)]
    )

    cuerpo = client.get("/api/productos/mas-vendidos").get_json()

    assert cuerpo["total"] == 1
    assert cuerpo["productos"][0]["unidades_vendidas"] == 7
    assert cuerpo["productos"][0]["ingresos"] == 21000


def test_el_ranking_trae_los_mismos_campos_que_el_catalogo(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking([_vendido()])

    cuerpo = client.get("/api/productos/mas-vendidos").get_json()

    producto = cuerpo["productos"][0]
    for campo in ("id", "nombre", "precio", "imagen", "imagen_thumb", "badge"):
        assert campo in producto


def test_el_ranking_devuelve_el_periodo_que_se_pidio(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking()

    cuerpo = client.get("/api/productos/mas-vendidos?periodo=7d").get_json()

    assert cuerpo["periodo"] == "7d"


def test_sin_periodo_el_ranking_cubre_el_historico_completo(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking()

    cuerpo = client.get("/api/productos/mas-vendidos").get_json()

    assert cuerpo["periodo"] == "todo"


def test_un_ranking_sin_ventas_devuelve_una_lista_vacia(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking([])

    respuesta = client.get("/api/productos/mas-vendidos")

    assert respuesta.status_code == 200
    assert respuesta.get_json()["productos"] == []
    assert respuesta.get_json()["total"] == 0


def test_un_periodo_invalido_devuelve_400_con_el_mensaje(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking()
    app.config["PRODUCTO_SERVICE"].listar_mas_vendidos.side_effect = ValueError(
        "Periodo no valido: 7-semanas"
    )

    respuesta = client.get("/api/productos/mas-vendidos?periodo=7-semanas")

    assert respuesta.status_code == 400
    assert respuesta.get_json()["mensaje"] == "Periodo no valido: 7-semanas"


def test_el_limite_viaja_al_servicio(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_ranking()

    client.get("/api/productos/mas-vendidos?limite=5")

    _periodo, limite = app.config["PRODUCTO_SERVICE"].listar_mas_vendidos.call_args[0]
    assert limite == "5"




def _servicio_semana(tipo: str = "actual", distintos: int = 5) -> Mock:
    servicio = Mock()
    servicio.listar_mas_vendidos_semana.return_value = RankingSemana(
        productos=[_vendido()],
        tipo=tipo,
        desde=datetime(2026, 10, 19, tzinfo=timezone.utc),
        hasta=datetime(2026, 10, 26, tzinfo=timezone.utc),
        productos_distintos_semana_actual=distintos,
    )
    return servicio


def test_el_periodo_semana_usa_el_servicio_con_fallback(app, client):
    servicio = _servicio_semana(tipo="anterior", distintos=3)
    app.config["PRODUCTO_SERVICE"] = servicio

    cuerpo = client.get("/api/productos/mas-vendidos?periodo=semana").get_json()

    servicio.listar_mas_vendidos_semana.assert_called_once()
    servicio.listar_mas_vendidos.assert_not_called()
    assert cuerpo["periodo"] == "semana"
    assert cuerpo["total"] == 1
    assert cuerpo["semana"] == {
        "tipo": "anterior",
        "desde": "2026-10-19T00:00:00+00:00",
        "hasta": "2026-10-26T00:00:00+00:00",
        "productos_distintos_actual": 3,
    }


def test_el_periodo_semana_cae_al_historico_cuando_la_anterior_tambien_es_pobre(
    app, client
):
    servicio = Mock()
    servicio.listar_mas_vendidos_semana.return_value = RankingSemana(
        productos=[_vendido()],
        tipo="historico",
        desde=None,
        hasta=None,
        productos_distintos_semana_actual=2,
    )
    app.config["PRODUCTO_SERVICE"] = servicio

    cuerpo = client.get("/api/productos/mas-vendidos?periodo=semana").get_json()

    servicio.listar_mas_vendidos_semana.assert_called_once()
    servicio.listar_mas_vendidos.assert_not_called()
    assert cuerpo["periodo"] == "semana"
    assert cuerpo["total"] == 1
    assert cuerpo["semana"] == {
        "tipo": "historico",
        "desde": None,
        "hasta": None,
        "productos_distintos_actual": 2,
    }


def test_el_limite_semanal_viaja_crudo_al_servicio(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_semana()

    client.get("/api/productos/mas-vendidos?periodo=semana&limite=5")

    app.config["PRODUCTO_SERVICE"].listar_mas_vendidos_semana.assert_called_once_with("5")


def test_el_ranking_semanal_trae_los_mismos_campos_que_el_catalogo(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_semana()

    producto = client.get("/api/productos/mas-vendidos?periodo=semana").get_json()[
        "productos"
    ][0]

    for campo in ("id", "nombre", "precio", "imagen", "imagen_thumb", "badge"):
        assert campo in producto




def _servicio_con_foto() -> Mock:
    foto = ImagenProducto(bytes=b"x" * 64, content_type="image/jpeg")
    thumb = ImagenProducto(bytes=b"y" * 32, content_type="image/jpeg")
    servicio = Mock()
    servicio.consultar_imagen.return_value = foto
    servicio.obtener_thumb.return_value = thumb
    servicio.consultar_imagen_color.return_value = foto
    servicio.obtener_thumb_color.return_value = thumb
    return servicio


def _assert_cacheable(respuesta) -> None:

    cache = respuesta.cache_control
    assert cache.max_age == CACHE_IMAGENES_SEGUNDOS
    assert not cache.no_cache
    assert cache.public


def test_la_imagen_del_producto_se_sirve_cacheada(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_foto()

    respuesta = client.get(f"/api/productos/{uuid4()}/imagen")

    assert respuesta.status_code == 200
    assert respuesta.mimetype == "image/jpeg"
    _assert_cacheable(respuesta)


def test_el_thumbnail_del_producto_tambien_se_sirve_cacheado(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_foto()

    respuesta = client.get(f"/api/productos/{uuid4()}/thumb")

    assert respuesta.status_code == 200
    _assert_cacheable(respuesta)


def test_las_fotos_de_color_se_sirven_cacheadas(app, client):
    app.config["PRODUCTO_SERVICE"] = _servicio_con_foto()

    color_id = uuid4()
    for ruta in (
        f"/api/productos/colores/{color_id}/imagen",
        f"/api/productos/colores/{color_id}/thumb",
    ):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200
        _assert_cacheable(respuesta)


def test_una_foto_inexistente_sigue_dando_404(app, client):
    servicio = _servicio_con_foto()
    servicio.consultar_imagen.return_value = None
    app.config["PRODUCTO_SERVICE"] = servicio

    respuesta = client.get(f"/api/productos/{uuid4()}/imagen")

    assert respuesta.status_code == 404
    assert respuesta.get_json()["mensaje"] == "Imagen no encontrada"


def test_la_cache_de_imagenes_dura_una_semana():
    assert CACHE_IMAGENES_SEGUNDOS == 604800
