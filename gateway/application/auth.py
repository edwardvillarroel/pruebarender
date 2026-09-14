from typing import Protocol

from gateway.domain.seguridad import (
    verificar_password,
    nuevo_jti,
    calcular_expiracion,
    esta_expirado,
    es_reuso,
)
from gateway.infrastructure import repositorios


class FabricaTokens(Protocol):
    def crear_par(self, *, user_id, rol, email, refresh_jti, refresh_expira) -> dict:
        ...


class CredencialesInvalidas(Exception):
    pass


class ReusoDetectado(Exception):
    pass


class SesionExpirada(Exception):
    pass


DURACION_ACCESS_MINUTOS = 15
DURACION_REFRESH_MINUTOS = 7 * 24 * 60


def _usuario_a_publico(usuario: dict) -> dict:
    return {
        "id": usuario["id"],
        "email": usuario["email"],
        "nombre": usuario["nombre"],
        "apellido": usuario["apellido"],
        "rol": usuario["rol"],
    }


def iniciar_sesion(email, password, ip, user_agent, fabrica_tokens):
    usuario = repositorios.buscar_usuario_por_email(email)
    uid = None if usuario is None else usuario["id"]

    if usuario is None or not usuario["activo"]:
        repositorios.registrar_log("login_fail", uid, ip, "email inexistente o inactivo")
        raise CredencialesInvalidas()

    if not verificar_password(password, usuario["password_hash"]):
        repositorios.registrar_log("login_fail", uid, ip, "password incorrecta")
        raise CredencialesInvalidas()

    jti = nuevo_jti()
    expira_en = calcular_expiracion(DURACION_REFRESH_MINUTOS)
    tokens = fabrica_tokens.crear_par(
        user_id=usuario["id"],
        rol=usuario["rol"],
        email=usuario["email"],
        refresh_jti=jti,
        refresh_expira=expira_en,
    )
    repositorios.guardar_refresh(jti, usuario["id"], expira_en, ip, user_agent)
    repositorios.registrar_log("login_ok", usuario["id"], ip, "")
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user": _usuario_a_publico(usuario),
    }


def rotar_refresh(jti, ip, fabrica_tokens):
    registro = repositorios.buscar_refresh(jti)
    if registro is None:
        raise CredencialesInvalidas()

    if es_reuso(registro):
        user_id = registro["user_id"]
        repositorios.revocar_tokens_de_usuario(user_id)
        repositorios.registrar_log(
            "reuso", user_id, ip, "refresh revocado usado -> se revoca toda la sesion"
        )
        raise ReusoDetectado(user_id)

    if esta_expirado(registro["expira_en"]):
        repositorios.registrar_log("refresh_expirado", registro["user_id"], ip, "")
        raise SesionExpirada()

    usuario = repositorios.buscar_usuario_por_id(registro["user_id"])
    if usuario is None:
        raise CredencialesInvalidas()

    repositorios.revocar_refresh(jti)

    nuevo_jti_valor = nuevo_jti()
    expira_en = calcular_expiracion(DURACION_REFRESH_MINUTOS)
    tokens = fabrica_tokens.crear_par(
        user_id=usuario["id"],
        rol=usuario["rol"],
        email=usuario["email"],
        refresh_jti=nuevo_jti_valor,
        refresh_expira=expira_en,
    )
    repositorios.guardar_refresh(nuevo_jti_valor, usuario["id"], expira_en, ip, "rotacion")
    repositorios.registrar_log("refresh_ok", usuario["id"], ip, "token rotado")
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user": _usuario_a_publico(usuario),
    }


def cerrar_sesion(jti, ip):
    if jti is None:
        return
    registro = repositorios.buscar_refresh(jti)
    if registro is not None:
        repositorios.revocar_refresh(jti)
        repositorios.registrar_log("logout", registro["user_id"], ip, "")


def obtener_perfil(user_id):
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None:
        raise CredencialesInvalidas()
    return _usuario_a_publico(usuario)