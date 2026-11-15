from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.application.diseno.firma_especificaciones import firma_especificaciones
from app.domain.entities.solicitud_diseno import EstadoSolicitud, SolicitudDiseno
from app.domain.time import utcnow
from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura
from app.infrastructure.cotizador import ClienteCotizadorIA
from app.infrastructure.cotizador.token_estimacion import (
    hash_imagen,
    verificar_token_estimacion,
)

logger = logging.getLogger(__name__)

MATERIALES_PERMITIDOS = {"PLA", "PLA+", "ABS+", "ABS", "PETG", "Resina", "No estoy seguro"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IA_ORIGEN_SERVER = "cotizador-apolovibes-v2"
IA_ORIGEN_CLIENTE = "cotizador-apolovibes-v2-front"



class CrearSolicitudDiseno:
    def __init__(self, repositorio, guardar_imagen=None, cotizador_ia: ClienteCotizadorIA | None = None):
        self.repositorio = repositorio
        self.guardar_imagen = guardar_imagen
        self.cotizador_ia = cotizador_ia

    def ejecutar(self, usuario_id: UUID, datos: dict, imagen) -> SolicitudDiseno:
        nombre = str(datos.get("nombre") or "").strip()
        if not nombre or len(nombre) > 150:
            raise ValueError("El nombre es obligatorio y debe tener máximo 150 caracteres.")

        email = str(datos.get("email") or "").strip()
        if not email or len(email) > 255 or not EMAIL_RE.match(email):
            raise ValueError("El correo electrónico no es válido.")

        telefono = datos.get("telefono")
        if telefono is not None:
            telefono = str(telefono).strip()
            if telefono == "":
                telefono = None
            elif len(telefono) > 30:
                raise ValueError("El teléfono debe tener máximo 30 caracteres.")
        else:
            telefono = None

        material = str(datos.get("material") or "").strip()
        if material not in MATERIALES_PERMITIDOS:
            raise ValueError("El material seleccionado no es válido.")

        descripcion = str(datos.get("descripcion") or "").strip()

        alto = self._parse_decimal_pos(datos.get("alto"), "alto")
        ancho = self._parse_decimal_pos(datos.get("ancho"), "ancho")
        largo = self._parse_decimal_pos(datos.get("largo"), "largo")

        cantidad_raw = datos.get("cantidad", 1)
        try:
            cantidad = int(cantidad_raw)
        except (TypeError, ValueError):
            raise ValueError("La cantidad debe ser un número entero.")
        if cantidad < 1:
            raise ValueError("La cantidad debe ser mayor o igual a 1.")

        unidad = str(datos.get("unidad") or "cm").strip() or "cm"
        uso = datos.get("uso")
        if uso is not None:
            uso = str(uso).strip()
            if uso == "":
                uso = None
        color = datos.get("color")
        if color is not None:
            color = str(color).strip()
            if color == "":
                color = None
        modelo_url = datos.get("modelo_url")
        if modelo_url is not None:
            modelo_url = str(modelo_url).strip()
            if modelo_url == "":
                modelo_url = None

        if imagen is None:
            raise ValueError("Falta la imagen de referencia.")

        contenido, extension = validar_imagen_segura(imagen)
        ruta_imagen = None
        if self.guardar_imagen is not None:
            from app.config import Config

            carpeta_base = Config.UPLOAD_FOLDER
            ruta_imagen = self.guardar_imagen(contenido, f".{extension}", carpeta_base)
        else:
            ruta_imagen = None

        solicitud = SolicitudDiseno(
            usuario_id=usuario_id,
            nombre=nombre,
            email=email,
            telefono=telefono,
            material=material,
            descripcion=descripcion,
            alto=alto,
            ancho=ancho,
            largo=largo,
            unidad=unidad,
            cantidad=cantidad,
            uso=uso,
            color=color,
            imagen=ruta_imagen,
            modelo_url=modelo_url,
            precio=None,
            estado=EstadoSolicitud.PENDIENTE,
        )

        # Estrategia: el frontend ya estima al subir la imagen y recibe un token
        # firmado por el backend. Se reutiliza esa estimacion si el token es
        # valido para este usuario, esta imagen y estas especificaciones (una
        # sola llamada al cotizador por cotizacion, sin chocar con su limite de
        # 1 request/minuto). Los precios que mande el navegador fuera del token
        # se ignoran por completo. Sin token valido se estima en el backend.
        try:
            estimacion = self._aplicar_estimacion_firmada(
                datos, solicitud, contenido, usuario_id
            )
            if estimacion is not None:
                self._aplicar_resultado(solicitud, estimacion)
                solicitud.ia_calculado_en = utcnow()
                solicitud.ia_origen = IA_ORIGEN_CLIENTE
            elif self.cotizador_ia is not None:
                estimacion = self._estimar_con_cotizador(
                    solicitud=solicitud,
                    contenido=contenido,
                    extension=extension,
                    alto=alto,
                    ancho=ancho,
                    largo=largo,
                    unidad=unidad,
                    cantidad=cantidad,
                    uso=uso,
                    material=material,
                    color=color,
                )
                if estimacion is not None:
                    self._aplicar_resultado(solicitud, estimacion)
                    solicitud.ia_calculado_en = utcnow()
                    solicitud.ia_origen = IA_ORIGEN_SERVER

        except Exception as exc:
            # La cotizacion se guarda igual, pero el fallo queda visible en
            # `ia_origen` (ej. cotizador-error-429) y en el log.
            solicitud.ia_origen = self._marcador_error(exc)
            logger.exception(
                "No se pudo estimar la cotizacion con el cotizador IA (%s)",
                solicitud.ia_origen,
            )

        return self.repositorio.crear(solicitud)

    def _estimar_con_cotizador(
        self,
        solicitud: SolicitudDiseno,
        contenido,
        extension: str,
        alto,
        ancho,
        largo,
        unidad: str,
        cantidad: int,
        uso: str | None,
        material: str,
        color: str | None,
    ) -> dict:
        return self.cotizador_ia.estimar(
            imagen_bytes=contenido,
            filename=f"cotizacion.{extension}",
            alto=float(alto) if alto else 10,
            ancho=float(ancho) if ancho else 10,
            largo=float(largo) if largo else 10,
            unidad=unidad,
            cantidad=cantidad,
            uso=uso or "Decorativo",
            material_usuario=material,
            color=color or "Negro",
        )

    def _aplicar_estimacion_firmada(
        self,
        datos: dict,
        solicitud: SolicitudDiseno,
        contenido: bytes,
        usuario_id: UUID,
    ) -> dict | None:
        """Reutiliza la estimacion del upload solo si viene en un token firmado
        por el backend y corresponde a este usuario, imagen y especificaciones.

        Nunca se leen precios sueltos del formulario: el cliente puede
        modificarlos y no son confiables.
        """
        token = str(datos.get("estimacion_token") or "").strip()
        if not token:
            return None

        firma_esperada = firma_especificaciones(
            alto=solicitud.alto,
            ancho=solicitud.ancho,
            largo=solicitud.largo,
            unidad=solicitud.unidad,
            cantidad=solicitud.cantidad,
            uso=solicitud.uso,
            material=solicitud.material,
            color=solicitud.color,
        )
        estimacion = verificar_token_estimacion(
            token,
            usuario_id=usuario_id,
            imagen_sha256=hash_imagen(contenido),
            firma=firma_esperada,
            secreto=self._secreto_estimacion(),
            max_age=self._ttl_estimacion(),
        )
        if estimacion is None:
            logger.warning(
                "Token de estimacion invalido, expirado o de otra imagen/usuario; "
                "se vuelve a estimar con el cotizador."
            )
            return None

        precio = self._to_decimal(estimacion.get("precio_estimado_ia"))
        if precio is None or precio <= 0 or precio > Decimal("9999999999.99"):
            return None
        return estimacion

    def _aplicar_resultado(self, solicitud: SolicitudDiseno, res: dict) -> None:
        solicitud.material_sugerido_ia = self._texto_largo(res.get("material_sugerido_ia") or res.get("material_detectado"), 50)
        solicitud.complejidad_ia = self._texto_largo(res.get("complejidad_ia") or res.get("complejidad"), 50)
        solicitud.gramos_estimados_ia = self._to_decimal(res.get("gramos_estimados_ia") if res.get("gramos_estimados_ia") is not None else res.get("gramos_estimados"))
        solicitud.tiempo_estimado_horas_ia = self._to_decimal(res.get("tiempo_estimado_horas_ia") if res.get("tiempo_estimado_horas_ia") is not None else res.get("tiempo_estimado_horas"))
        solicitud.precio_estimado_ia = self._to_decimal(res.get("precio_estimado_ia") if res.get("precio_estimado_ia") is not None else res.get("precio_clp"))
        solicitud.confianza_material_ia = self._to_decimal(res.get("confianza_material_ia") if res.get("confianza_material_ia") is not None else res.get("confianza_material"))
        solicitud.confianza_complejidad_ia = self._to_decimal(res.get("confianza_complejidad_ia") if res.get("confianza_complejidad_ia") is not None else res.get("confianza_complejidad"))

    def _secreto_estimacion(self) -> str:
        return str(self._config("SECRET_KEY") or "")

    def _ttl_estimacion(self) -> int:
        try:
            return int(self._config("ESTIMACION_TOKEN_TTL_SECONDS") or 7200)
        except (TypeError, ValueError):
            return 7200

    def _config(self, clave: str):
        """Lee la configuracion de la app; fuera de un request usa `Config`."""
        try:
            from flask import current_app, has_app_context

            if has_app_context():
                return current_app.config.get(clave)
        except Exception:
            pass
        from app.config import Config

        return getattr(Config, clave, None)

    def _marcador_error(self, exc: Exception) -> str:
        respuesta = getattr(exc, "response", None)
        codigo = getattr(respuesta, "status_code", None)
        detalle = codigo if codigo is not None else exc.__class__.__name__
        return f"cotizador-error-{detalle}"[:50]

    def _texto_largo(self, valor, maximo: int):
        texto = str(valor).strip() if valor is not None else ""
        return texto[:maximo] or None

    def _altura_referencia(self, alto, ancho, largo):
        vals = []
        for v in (alto, ancho, largo):
            if v is not None:
                try:
                    vals.append(float(v))
                except Exception:
                    pass
        if not vals:
            return None
        return max(vals)

    def _to_decimal(self, v):
        if v is None:
            return None
        try:
            if isinstance(v, float):
                return Decimal(str(v))
            return Decimal(str(v))
        except Exception:
            return None

    def _parse_decimal_pos(self, valor, campo: str):
        if valor is None or str(valor).strip() == "":
            return None
        s = str(valor).strip().replace(",", ".")
        try:
            d = Decimal(s)
        except (InvalidOperation, TypeError):
            raise ValueError(f"El valor de {campo} no es numérico.")
        if d <= 0:
            raise ValueError(f"El valor de {campo} debe ser mayor a 0.")
        return d
