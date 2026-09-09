"""Sanitización de inputs de diseño personalizado.

Paso obligatorio antes de que cualquier texto del usuario llegue al LLM,
para mitigar prompt injection (RNF-05).
"""

MAX_LONGITUD = 2000
CAMPOS_PERMITIDOS = {"nombre", "email", "telefono", "material", "descripcion"}


def sanitizar_texto(texto: str | None) -> str:
    if texto is None:
        return ""
    texto = texto.strip()
    texto = texto.replace("\x00", "")
    return texto[:MAX_LONGITUD]


def sanitizar_input(datos: dict) -> dict:
    sanitizados = {}
    for campo, valor in datos.items():
        if campo not in CAMPOS_PERMITIDOS:
            continue
        if isinstance(valor, str):
            sanitizados[campo] = sanitizar_texto(valor)
        else:
            sanitizados[campo] = valor
    return sanitizados