"""Fase 0: verifica que la organizacion puede emitir DTE contra OpenFactura.

No es un smoke test de la app: es el pre-requisito de la integracion de
facturacion electronica. Contesta tres preguntas, en orden de bloqueo:

  1. La API key existe y es valida?          -> GET /v2/dte/organization/document
  2. Hay folios autorizados para 39 y 33?    -> mismo endpoint (campo `documentos`)
  3. Que datos tiene el emisor en el SII?    -> GET /v2/dte/taxpayer/{rut}

Las dos primeras son de lectura. La tercera tambien. La emision de prueba
(`--emitir`) ESCRIBE un documento real, asi que va apagada por defecto y hay
que pedirla explicitamente: sin eso, correr el script emite boletas de prueba
en la contabilidad real.

Como obtener la API key
-----------------------
En la plataforma OpenFactura (https://openfactura.haulmer.com), con la cuenta
del titular del servicio:

  1. Entrar a "Configuracion".
  2. Bajar hasta el modulo "API".
  3. Boton "GENERAR API KEY". La key queda disponible en pantalla.

La key queda atada a la organizacion (empresa) del usuario que la genera, asi
que hay que generarla con la cuenta del RUT emisor, no con un integrador.
Es la misma key para dev y produccion: lo que cambia es la URL base
(`dev-api.haulmer.com` usa un CAF simulado, por lo que el timbre no valida).

Uso
---
    python tools/verificar_openfactura.py
    python tools/verificar_openfactura.py --ambiente dev
    python tools/verificar_openfactura.py --emitir boleta --monto 1000
    python tools/verificar_openfactura.py --pdf <TOKEN>
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import httpx
from dotenv import load_dotenv

REPO = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")

BASE_PROD = "https://api.haulmer.com"
BASE_DEV = "https://dev-api.haulmer.com"

# RUT de "Apolo Vibes SPA" segun los terminos legales (LegalModal.jsx).
RUT_EMISOR_POR_DEFECTO = "78064166-5"

# Codigos de tipo de documento del SII que nos interesan.
TIPO_BOLETA = 39
TIPO_FACTURA = 33
NOMBRES_TIPO = {
    30: "Factura de venta",
    33: "Factura de venta electronica",
    34: "Factura exenta electronica",
    39: "Boleta de venta electronica",
    41: "Boleta exenta electronica",
    43: "Nota de debito de liquidacion factura",
    48: "Comprobante de pago electronico",
    52: "Guia de despacho electronica",
    56: "Nota de debito electronica",
    61: "Nota de credito electronica",
}


def _titulo(texto: str) -> None:
    print()
    print("=" * 72)
    print(texto)
    print("=" * 72)


def _api_key() -> str:
    clave = (os.getenv("OPENFACTURA_API_KEY") or "").strip()
    if not clave:
        print(
            "FALTA OPENFACTURA_API_KEY.\n"
            "  1. Entra a https://openfactura.haulmer.com con la cuenta titular.\n"
            "  2. Configuracion -> modulo API -> GENERAR API KEY.\n"
            "  3. Pegala en el .env de la raiz como OPENFACTURA_API_KEY=<la key>.\n"
        )
        sys.exit(2)
    return clave


def _cliente(base: str, key: str) -> httpx.Client:
    return httpx.Client(
        base_url=base,
        headers={"apikey": key, "Content-Type": "application/json"},
        timeout=30.0,
    )


def _cuerpo(respuesta: httpx.Response) -> str:
    try:
        return json.dumps(respuesta.json(), ensure_ascii=False, indent=2)
    except ValueError:
        return respuesta.text.strip()


def verificar_autorizacion(cliente: httpx.Client, rut_emisor: str) -> dict:
    """Tipos de documento autorizados y folios disponibles de la organizacion."""
    _titulo("1. Organizacion: tipos autorizados y folios disponibles")

    # El endpoint aparece documentado como GET y como POST con el RUT en el
    # cuerpo. Se prueba el GET y, si no responde, el POST.
    respuesta = cliente.get("/v2/dte/organization/document")
    if respuesta.status_code == 404:
        respuesta = cliente.post("/v2/dte/organization/document", json={"rut": rut_emisor})
    elif respuesta.status_code in (400, 405):
        respuesta = cliente.post("/v2/dte/organization/document", json={"rut": rut_emisor})

    if respuesta.status_code != 200:
        print(f"HTTP {respuesta.status_code}")
        print(_cuerpo(respuesta))
        print(
            "\nSi es 401, la API key es invalida o no pertenece a la organizacion\n"
            "certificada. Si es 404, la organizacion no tiene el modulo de\n"
            "Documentos electronicos habilitado."
        )
        return {}

    datos = respuesta.json()
    documentos = datos.get("documentos") or []
    print(f"RUT emisor: {datos.get('rut', rut_emisor)}")
    print(f"{'DTE':<6}{'Tipo':<34}{'Folios disp.':>14}{'Vence':>14}")
    for documento in sorted(documentos, key=lambda d: d.get("dte", 0)):
        codigo = documento.get("dte")
        print(
            f"{codigo:<6}{NOMBRES_TIPO.get(codigo, '?'):<34}"
            f"{documento.get('disponibles', 0):>14}{documento.get('vencimiento', ''):>14}"
        )

    por_codigo = {d.get("dte"): d for d in documentos}
    print()
    for codigo, etiqueta in ((TIPO_BOLETA, "boleta"), (TIPO_FACTURA, "factura")):
        documento = por_codigo.get(codigo)
        if documento is None:
            print(f"[FALTA] DTE {codigo} ({etiqueta}) no esta autorizado.")
        elif not documento.get("disponibles"):
            print(
                f"[FALTA] DTE {codigo} ({etiqueta}) autorizado pero sin folios "
                f"disponibles (vencen {documento.get('vencimiento')})."
            )
        else:
            print(f"[OK]    DTE {codigo} ({etiqueta}) con {documento['disponibles']} folios.")
    return datos


def verificar_emisor(cliente: httpx.Client, rut_emisor: str) -> dict:
    """Datos del emisor tal como los tiene el SII: base del bloque `Emisor`."""
    _titulo(f"2. Emisor {rut_emisor} segun el SII")
    respuesta = cliente.get(f"/v2/dte/taxpayer/{rut_emisor}")
    if respuesta.status_code != 200:
        print(f"HTTP {respuesta.status_code}")
        print(_cuerpo(respuesta))
        return {}

    datos = respuesta.json()
    print(f"Razon social : {datos.get('razonSocial')}")
    print(f"Email       : {datos.get('email')}")
    print(f"Telefono    : {datos.get('telefono')}")
    print(f"Direccion   : {datos.get('direccion')}")
    print(f"Comuna      : {datos.get('comuna')}")
    for actividad in datos.get("actividades") or []:
        marca = "*" if actividad.get("actividadPrincipal") else " "
        print(
            f" Actividad{marca} {actividad.get('codigoActividadEconomica')}"
            f"  {actividad.get('actividadEconomica')}"
        )
        print(f"            giro: {actividad.get('giro')}")
    for sucursal in datos.get("sucursales") or []:
        print(
            f" Sucursal   : cdgSIISucur={sucursal.get('cdgSIISucur')} "
            f"comuna={sucursal.get('comuna')} direccion={sucursal.get('direccion')}"
        )

    print()
    print("Bloque `Emisor` que usaria la API (copiar a .env / app/config.py):")
    principal = next(
        (a for a in datos.get("actividades") or [] if a.get("actividadPrincipal")),
        (datos.get("actividades") or [{}])[0],
    )
    sucursal = (datos.get("sucursales") or [{}])[0]
    bloque = {
        "RUTEmisor": rut_emisor,
        "RznSoc": datos.get("razonSocial"),
        "GiroEmis": principal.get("giro"),
        "Acteco": principal.get("codigoActividadEconomica"),
        "DirOrigen": datos.get("direccion"),
        "CmnaOrigen": datos.get("comuna"),
        "CdgSIISucur": sucursal.get("cdgSIISucur"),
    }
    print(json.dumps(bloque, ensure_ascii=False, indent=2))
    return datos


def _payload_prueba(
    tipo_dte: int, emisor: dict, monto: int, nombre: str, rut_receptor: str
) -> dict:
    """Arma un DTE minimo de 1 linea para probar la forma del payload.

    Los precios del repo son IVA incluido, asi que el neto se calcula aqui
    (bruto / 1.19) y el IVA es la diferencia. Asi `MntNeto + IVA = MntTotal`
    cierra al peso, que es lo que el SII exige.
    """
    neto = round(monto / 1.19)
    iva = monto - neto
    return {
        "response": ["XML", "PDF", "FOLIO", "TIMBRE", "LOGO", "RESOLUCION"],
        "dte": {
            "Encabezado": {
                "IdDoc": {
                    "TipoDTE": tipo_dte,
                    "Folio": 0,
                    "FchEmis": _hoy(),
                    "TpoTranVenta": 1,
                    "FmaPago": 2,
                },
                "Emisor": emisor,
                "Receptor": {"RUTRecep": rut_receptor},
                "Totales": {
                    "MntNeto": neto,
                    "TasaIVA": "19",
                    "IVA": iva,
                    "MntTotal": monto,
                    "VlrPagar": monto,
                },
            },
            "Detalle": [
                {
                    "NroLinDet": 1,
                    "NmbItem": nombre,
                    "QtyItem": 1,
                    "PrcItem": neto,
                    "MontoItem": neto,
                }
            ],
        },
    }


def _hoy() -> str:
    from datetime import date

    return date.today().isoformat()


def emitir_prueba(
    cliente: httpx.Client,
    tipo_dte: int,
    emisor: dict,
    monto: int,
    rut_receptor: str,
    idempotency_key: str,
) -> dict:
    """Emite un DTE de prueba. ESCRIBE en la contabilidad: usar con cuidado."""
    etiqueta = "boleta" if tipo_dte == TIPO_BOLETA else "factura"
    _titulo(f"3. Emision de prueba: {etiqueta} (DTE {tipo_dte}) por ${monto}")

    payload = _payload_prueba(
        tipo_dte,
        emisor,
        monto,
        f"Prueba de emision {etiqueta} - no es una compra real",
        rut_receptor,
    )
    print("Payload enviado:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()

    respuesta = cliente.post(
        "/v2/dte/document",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )
    print(f"HTTP {respuesta.status_code}")
    print(_cuerpo(respuesta))

    if respuesta.status_code not in (200, 201):
        print()
        print(
            "Si el error menciona un nombre de campo, ese es el nombre que la\n"
            "API espera (la doc oficial y los ejemplos usan `RznSoc`/`GiroEmis`\n"
            "en v2 y `RznSocEmisor`/`GiroEmisor` en v1: hay que usar el que pida)."
        )
        return {}
    return respuesta.json()


def descargar_pdf(cliente: httpx.Client, token: str, salida: pathlib.Path) -> None:
    _titulo(f"4. PDF del documento {token}")
    respuesta = cliente.get(f"/v2/dte/document/{token}/pdf")
    if respuesta.status_code != 200:
        print(f"HTTP {respuesta.status_code}")
        print(_cuerpo(respuesta))
        return
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(respuesta.content)
    print(f"PDF guardado en {salida} ({len(respuesta.content)} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ambiente",
        choices=("prod", "dev"),
        default=os.getenv("OPENFACTURA_AMBIENTE", "prod"),
        help="prod = api.haulmer.com (real). dev = dev-api.haulmer.com (CAF simulado).",
    )
    parser.add_argument(
        "--rut-emisor",
        default=os.getenv("EMISOR_RUT", RUT_EMISOR_POR_DEFECTO),
    )
    parser.add_argument(
        "--emitir",
        choices=("boleta", "factura"),
        help="Emite un documento de PRUEBA (escribe). Opcional a proposito.",
    )
    parser.add_argument("--monto", type=int, default=1000)
    parser.add_argument(
        "--receptor",
        default=os.getenv("RECEPTOR_PRUEBA_RUT", "66666666-6"),
        help="RUT receptor del documento de prueba (66666666-6 = consumidor final).",
    )
    parser.add_argument("--idempotency-key", default="apolvibes-fase0-prueba")
    parser.add_argument("--pdf-token", help="Descarga el PDF de un TOKEN ya emitido.")
    parser.add_argument(
        "--pdf-salida",
        default=str(REPO / "tmp" / "openfactura_prueba.pdf"),
    )
    args = parser.parse_args()

    key = _api_key()
    base = BASE_DEV if args.ambiente == "dev" else BASE_PROD
    print(f"Ambiente: {args.ambiente} ({base})")
    print(f"API key : {key[:4]}...{key[-4:]} (oculta)")

    with _cliente(base, key) as cliente:
        if args.pdf_token:
            descargar_pdf(cliente, args.pdf_token, pathlib.Path(args.pdf_salida))
            return 0

        verificar_autorizacion(cliente, args.rut_emisor)
        emisor = verificar_emisor(cliente, args.rut_emisor)

        if args.emitir:
            bloque = {
                "RUTEmisor": args.rut_emisor,
                "RznSoc": emisor.get("razonSocial") or "APOLO VIBES SPA",
                "GiroEmis": (
                    (emisor.get("actividades") or [{}])[0].get("giro")
                    or "VENTA AL POR MENOR POR INTERNET"
                ),
                "Acteco": (
                    (emisor.get("actividades") or [{}])[0].get("codigoActividadEconomica")
                    or 523999
                ),
                "DirOrigen": emisor.get("direccion") or "PASAJE EL BOLDO N 33",
                "CmnaOrigen": emisor.get("comuna") or "VIÑA DEL MAR",
                "CdgSIISucur": (emisor.get("sucursales") or [{}])[0].get("cdgSIISucur"),
            }
            tipo = TIPO_BOLETA if args.emitir == "boleta" else TIPO_FACTURA
            emitir_prueba(
                cliente, tipo, bloque, args.monto, args.receptor, args.idempotency_key
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
