import httpx
from flask import current_app

_cliente = httpx.Client(timeout=30)

_WHITELIST = (
    "content-type",
    "cache-control",
    "etag",
    "last-modified",
    "expires",
    "vary",
    "accept-ranges",
    "content-disposition",
)

def reenviar(ruta, datos_metodo, cabeceras_internas):
    url = f"{current_app.config['BACKEND_INTERNAL_URL']}/api/{ruta}"
    cabeceras = {
        "Content-Type": datos_metodo.headers.get("Content-Type", ""),
        "Accept": datos_metodo.headers.get("Accept", "*/*"),
        "X-User-Id": cabeceras_internas.get("X-User-Id", ""),
        "X-User-Rol": cabeceras_internas.get("X-User-Rol", ""),
    }
    try:
        respuesta = _cliente.request(
            method=datos_metodo.method,
            url=url,
            params=datos_metodo.args,
            content=datos_metodo.get_data(),
            headers=cabeceras,
        )
    except httpx.RequestError:
        return (
            b'{"mensaje": "backend no disponible"}',
            502,
            {"Content-Type": "application/json; charset=utf-8"},
        )
    cabeceras_out = {}
    for clave, valor in respuesta.headers.items():
        if clave.lower() in _WHITELIST:
            cabeceras_out[clave] = valor
    return respuesta.content, respuesta.status_code, cabeceras_out

