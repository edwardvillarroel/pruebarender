"""Gestion de usuarios del panel de administracion.

Incluye el listado con metricas (solo lectura) y las acciones de alta,
eliminacion logica, cambio de rol y bloqueo/desbloqueo.

Las contrasenas se hashean con la misma funcion que usa el gateway
(`app.infrastructure.security.passwords.crear_hash`, bcrypt) y las reglas de
longitud son las mismas que las de `gateway/application/auth.py`: si cambian
alla, hay que cambiarlas aca.
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID

from app.domain.entities.usuario import Usuario, UsuarioMetricas
from app.domain.enums import Rol
from app.domain.interfaces.repositories import UsuarioRepository
from app.domain.time import utcnow

MIN_PASSWORD = 8
MAX_PASSWORD = 72
ROLES_VALIDOS = {Rol.ADMIN.value, Rol.CLIENTE.value}


class UsuarioNoEncontrado(Exception):
    """El id no existe o la cuenta ya fue eliminada."""


class CorreoEnUso(Exception):
    """Ya hay una cuenta (viva o eliminada) con ese correo."""


class DatosUsuarioInvalidos(Exception):
    """Datos del formulario que no cumplen las reglas del proyecto."""


class OperacionNoPermitida(Exception):
    """La accion dejaria el sistema sin administradores o se aplica a uno mismo."""


class GestionarUsuarios:
    """Casos de uso del apartado Usuarios del panel de administracion.

    El repositorio agrega las metricas en SQL; aca solo se arman los DTO que
    consume el frontend, sin exponer datos sensibles (hash de contrasena, MFA,
    google_sub).
    """

    def __init__(
        self,
        usuarios: UsuarioRepository,
        hasher: Callable[[str], str],
    ) -> None:
        self._usuarios = usuarios
        self._hasher = hasher

    # ------------------------------ lectura ------------------------------

    def listar(self) -> list[dict[str, Any]]:
        return [self._a_publico_metricas(u) for u in self._usuarios.listar_con_metricas()]

    # ------------------------------ alta ------------------------------

    def crear(self, datos: dict[str, Any], actor_id: str | None = None) -> dict[str, Any]:
        """Crea un usuario con contrasena local y rol inicial.

        El correo se guarda en minusculas (igual que el login del gateway) y la
        contrasena se valida con las mismas reglas que el registro publico.
        """
        email = _texto(datos.get("email")).lower()
        nombre = _texto(datos.get("nombre"))
        apellido = _texto(datos.get("apellido"))
        rol = _texto(datos.get("rol")).lower() or Rol.CLIENTE.value
        telefono = _texto(datos.get("telefono")) or None
        password = datos.get("password")

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise DatosUsuarioInvalidos("El correo electrónico no es válido")
        if not nombre:
            raise DatosUsuarioInvalidos("El nombre es obligatorio")
        if rol not in ROLES_VALIDOS:
            raise DatosUsuarioInvalidos("El rol debe ser «admin» o «cliente»")
        if rol == Rol.CLIENTE.value and not apellido:
            # La base exige apellido para los clientes (CK_USUARIOS_APELLIDO).
            raise DatosUsuarioInvalidos("El apellido es obligatorio para un cliente")
        _validar_password(password)

        if self._usuarios.correo_en_uso(email):
            raise CorreoEnUso("Ya existe una cuenta con ese correo electrónico")

        usuario = Usuario(
            email=email,
            password_hash=self._hasher(password),
            nombre=nombre,
            apellido=apellido or None,
            rol=Rol(rol),
            telefono=telefono,
        )
        creado = self._usuarios.crear(usuario)
        return self._a_publico(creado)

    # ------------------------------ permisos ------------------------------

    def cambiar_rol(
        self, usuario_id: UUID, rol: str, actor_id: str | None
    ) -> dict[str, Any]:
        usuario = self._buscar(usuario_id)
        nuevo_rol = _texto(rol).lower()
        if nuevo_rol not in ROLES_VALIDOS:
            raise DatosUsuarioInvalidos("El rol debe ser «admin» o «cliente»")

        if usuario.rol.value == nuevo_rol:
            return self._a_publico(usuario)

        if _es_mismo_usuario(usuario, actor_id):
            raise OperacionNoPermitida(
                "No puedes quitarte tu propio rol de administrador"
            )
        if nuevo_rol == Rol.CLIENTE.value and not usuario.apellido:
            raise DatosUsuarioInvalidos(
                "Ese usuario no tiene apellido registrado y no puede pasar a cliente"
            )

        self._exigir_otro_admin(usuario)
        usuario.rol = Rol(nuevo_rol)
        return self._a_publico(self._usuarios.actualizar(usuario))

    # ------------------------------ bloqueo ------------------------------

    def cambiar_estado(
        self, usuario_id: UUID, activo: bool, actor_id: str | None
    ) -> dict[str, Any]:
        """Bloquea (`activo=False`) o desbloquea (`activo=True`) una cuenta.

        El bloqueo es reversible y no borra nada: el gateway rechaza el login de
        las cuentas con `activo=False`.
        """
        usuario = self._buscar(usuario_id)
        if not isinstance(activo, bool):
            raise DatosUsuarioInvalidos("El estado debe ser verdadero o falso")

        if usuario.activo == activo:
            return self._a_publico(usuario)

        if not activo:
            if _es_mismo_usuario(usuario, actor_id):
                raise OperacionNoPermitida("No puedes bloquear tu propia cuenta")
            self._exigir_otro_admin(usuario)

        usuario.activo = activo
        return self._a_publico(self._usuarios.actualizar(usuario))

    # ------------------------------ eliminacion ------------------------------

    def eliminar(self, usuario_id: UUID, actor_id: str | None) -> None:
        """Soft delete: marca `eliminado_en` y bloquea la cuenta.

        No se borra la fila porque pedidos, cotizaciones, resenas y cupones la
        referencian. La cuenta desaparece del listado y ya no puede iniciar
        sesion.
        """
        usuario = self._buscar(usuario_id)
        if _es_mismo_usuario(usuario, actor_id):
            raise OperacionNoPermitida("No puedes eliminar tu propia cuenta")
        self._exigir_otro_admin(usuario)

        usuario.activo = False
        usuario.eliminado_en = utcnow()
        self._usuarios.actualizar(usuario)

    # ------------------------------ helpers ------------------------------

    def _buscar(self, usuario_id: UUID) -> Usuario:
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None or usuario.eliminado_en is not None:
            raise UsuarioNoEncontrado("Usuario no encontrado")
        return usuario

    def _exigir_otro_admin(self, usuario: Usuario) -> None:
        """Impide que la accion deje el sistema sin un administrador activo."""
        es_admin_activo = (
            usuario.rol == Rol.ADMIN
            and usuario.activo
            and usuario.eliminado_en is None
        )
        if es_admin_activo and self._usuarios.contar_admins_activos() <= 1:
            raise OperacionNoPermitida(
                "Debe quedar al menos un administrador activo en el sistema"
            )

    @staticmethod
    def _a_publico(usuario: Usuario) -> dict[str, Any]:
        return {
            "id": str(usuario.id),
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "nombre_completo": _nombre_completo(usuario.nombre, usuario.apellido),
            "email": usuario.email,
            "rol": usuario.rol.value,
            "activo": usuario.activo,
            "eliminado": usuario.eliminado_en is not None,
            "creado_en": usuario.creado_en.isoformat() if usuario.creado_en else None,
        }

    @staticmethod
    def _a_publico_metricas(usuario: UsuarioMetricas) -> dict[str, Any]:
        return {
            "id": str(usuario.id),
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "nombre_completo": usuario.nombre_completo,
            "email": usuario.email,
            "rol": usuario.rol,
            "activo": usuario.activo,
            "productos_comprados": usuario.productos_comprados,
            "pedidos_pagados": usuario.pedidos_pagados,
            "cotizaciones_pedidas": usuario.cotizaciones_pedidas,
            "cotizaciones_aprobadas": usuario.cotizaciones_aprobadas,
            "cotizaciones_rechazadas": usuario.cotizaciones_rechazadas,
        }


def _texto(valor: Any) -> str:
    """Normaliza un valor de JSON a texto sin espacios (None -> "")."""
    if valor is None:
        return ""
    return str(valor).strip()


def _nombre_completo(nombre: str, apellido: str | None) -> str:
    return " ".join(parte for parte in (nombre, apellido) if parte).strip()


def _es_mismo_usuario(usuario: Usuario, actor_id: str | None) -> bool:
    return actor_id is not None and str(usuario.id) == str(actor_id)


def _validar_password(password: Any) -> None:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise DatosUsuarioInvalidos(
            f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres"
        )
    if len(password) > MAX_PASSWORD:
        raise DatosUsuarioInvalidos(
            f"La contraseña no puede superar los {MAX_PASSWORD} caracteres"
        )
