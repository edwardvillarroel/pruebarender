"""Validación de prompts antes de ser enviados al proveedor LLM.

Segunda barrera (después de sanitizar_input) para mitigar prompt
injection (RNF-05): solo se envía el prompt del sistema más los campos
permitidos y ya saneados.
"""

MAX_PROMPT = 500


def validar_prompt(prompt: str) -> str:
    if not prompt or not prompt.strip():
        raise ValueError("El prompt no puede estar vacío")
    if len(prompt) > MAX_PROMPT:
        raise ValueError(f"El prompt excede los {MAX_PROMPT} caracteres")
    if "\x00" in prompt:
        raise ValueError("El prompt contiene caracteres no permitidos")
    return prompt.strip()