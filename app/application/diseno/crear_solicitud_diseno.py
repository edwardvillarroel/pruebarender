from __future__ import annotations

import logging
import os
import re
import requests
import threading
import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.application.diseno.estimacion_local import estimacion_local
from app.application.diseno.firma_especificaciones import firma_especificaciones
from app.config import Config
from app.domain.entities.solicitud_diseno import EstadoSolicitud, SolicitudDiseno
from app.domain.time import utcnow
from app.infrastructure.cotizador import ClienteCotizadorIA
from app.infrastructure.cotizador.token_estimacion import (
    hash_imagen,
    verificar_token_estimacion,
)
from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura

logger = logging.getLogger(__name__)

MATERIALES_PERMITIDOS = {"PLA", "PLA+", "ABS+", "ABS", "PETG", "Resina", "No estoy seguro"}
UNIDADES_PERMITIDAS = {"mm", "cm", "in"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TELEFONO_RE = re.compile(r"^[0-9+()\-.\s]{6,30}$")

MAX_DIMENSION = Decimal("10000")
MAX_CANTIDAD = 1000
MAX_DESCRIPCION = 2000
MAX_MODELO_URL = 500
MAX_PRECIO = Decimal("9999999999.99")

LIMITE_POR_MINUTO = 3
LIMITE_POR_HORA = 10

IA_ORIGEN_SERVER = "cotizador-apolovibes-v2"
IA_ORIGEN_CLIENTE = "cotizador-apolovibes-v2-front"
IA_ORIGEN_PENDIENTE = "cotizador-pendiente"

# Control de frecuencia del cotizador (por proceso).
# Si se usan varios workers, este control debe moverse a Redis o a una cola de tareas.
INTERVALO_COTIZADOR_SEGUNDOS = 65
_LOCK_COTIZADOR = threading.Lock()
_ULTIMO_LLAMADO = 0.0

class CotizadorOcupado(Exception):
    """El cotizador está en uso o dentro del intervalo mínimo entre llamados."""

class CrearSolicitudDiseno:
    def __init__(self, repositorio, guardar_imagen=None, cotizador_ia: ClienteCotizadorIA | None = None):
        self.repositorio = repositorio
        self.guardar_imagen = guardar_imagen
        self.cotizador_ia = cotizador_ia

    # ------------------------------------------------------------------
    # Caso de uso principal
    # ------------------------------------------------------------------
    def ejecutar(self, usuario_id: UUID, datos: dict, imagen) -> SolicitudDiseno:
        datos = self._normalizar_datos(datos)

        nombre = str(datos.get("nombre") or "").strip()
        if not nombre or len(nombre) > 150:
            raise ValueError("El nombre es obligatorio y debe tener máximo 150 caracteres.")

        email = str(datos.get("email") or "").strip()
        if not email or len(email) > 255 or not EMAIL_RE.match(email):
            raise ValueError("El correo electrónico no es válido.")

        telefono = self._opcional_texto(datos.get("telefono"))
        if telefono is not None and not TELEFONO_RE.match(telefono):
            raise ValueError("El teléfono no es válido.")

        material = str(datos.get("material") or "").strip()
        if material not in MATERIALES_PERMITIDOS:
            raise ValueError("El material seleccionado no es válido.")

        descripcion = str(datos.get("descripcion") or "").strip()
        if len(descripcion) > MAX_DESCRIPCION:
            raise ValueError(f"La descripción debe tener máximo {MAX_DESCRIPCION} caracteres.")

        alto = self._parse_decimal_pos(datos.get("alto"), "alto")
        ancho = self._parse_decimal_pos(datos.get("ancho"), "ancho")
        largo = self._parse_decimal_pos(datos.get("largo"), "largo")

        try:
            cantidad = int(datos.get("cantidad", 1))
        except (TypeError, ValueError):
            raise ValueError("La cantidad debe ser un número entero.")
        if cantidad < 1:
            raise ValueError("La cantidad debe ser mayor o igual a 1.")
        if cantidad > MAX_CANTIDAD:
            raise ValueError(f"La cantidad no puede superar {MAX_CANTIDAD}.")

        unidad = (str(datos.get("unidad") or "cm").strip() or "cm").lower()
        if unidad not in UNIDADES_PERMITIDAS:
            raise ValueError("La unidad de medida no es válida.")

        uso = self._opcional_texto(datos.get("uso"))
        color = self._opcional_texto(datos.get("color"))
        modelo_url = self._validar_modelo_url(datos.get("modelo_url"))

        if imagen is None:
            raise ValueError("Falta la imagen de referencia.")
        contenido, extension = validar_imagen_segura(imagen)

        # La imagen aún NO se guarda en disco: primero se valida todo lo demás.
        solicitud = SolicitudDiseno(
            usuario_id=usuario_id, nombre=nombre, email=email, telefono=telefono,
            material=material, descripcion=descripcion, alto=alto, ancho=ancho,
            largo=largo, unidad=unidad, cantidad=cantidad, uso=uso, color=color,
            imagen=None, modelo_url=modelo_url, precio=None,
            estado=EstadoSolicitud.PENDIENTE,
        )

        # 1) Se verifica el token. Solo un token VÁLIDO exime del límite por cuenta.
        estimacion_firmada = None
        try:
            estimacion_firmada = self._aplicar_estimacion_firmada(datos, solicitud, contenido, usuario_id)
        except Exception:
            logger.exception("Error al verificar el token de estimación")

        # 2) Sin token válido se aplica el límite, antes de tocar disco o cotizador.
        if estimacion_firmada is None:
            self._verificar_limite_cuenta(usuario_id)

        # 3) Estimación
        try:
            if estimacion_firmada is not None:
                self._aplicar_resultado(solicitud, estimacion_firmada)
                solicitud.ia_calculado_en = utcnow()
                solicitud.ia_origen = IA_ORIGEN_CLIENTE
            else:
                estimacion_front = self._estimacion_desde_datos(datos)
                if estimacion_front is not None:
                    self._aplicar_resultado(solicitud, estimacion_front)
                    solicitud.ia_calculado_en = utcnow()
                    solicitud.ia_origen = IA_ORIGEN_CLIENTE
                elif self.cotizador_ia is not None:
                    estimacion = self._estimar_con_cola(
                        contenido=contenido, extension=extension,
                        alto=alto, ancho=ancho, largo=largo, unidad=unidad,
                        cantidad=cantidad, uso=uso, material=material, color=color,
                    )
                    self._aplicar_resultado(solicitud, estimacion)
                    solicitud.ia_calculado_en = utcnow()
                    solicitud.ia_origen = IA_ORIGEN_SERVER
        except CotizadorOcupado:
            solicitud.ia_origen = IA_ORIGEN_PENDIENTE
            logger.info("Cotizador ocupado; la solicitud queda pendiente de estimación.")
        except Exception as exc:
            solicitud.ia_origen = self._marcador_error(exc)
            logger.exception("No se pudo estimar la cotización con el cotizador IA (%s)", solicitud.ia_origen)

        # 4) Recién ahora se guarda la imagen; si falla la persistencia, se limpia.
        ruta_imagen = None
        if self.guardar_imagen is not None:
            ruta_imagen = self.guardar_imagen(contenido, f".{extension}", Config.UPLOAD_FOLDER)
            solicitud.imagen = ruta_imagen

        try:
            return self.repositorio.crear(solicitud)
        except Exception:
            self._eliminar_imagen(ruta_imagen)
            raise

    def _estimacion_desde_datos(self, datos: dict) -> dict | None:
        precio = self._to_decimal(
            self._primero_no_nulo(datos, "precio_estimado_ia", "precio_estimado", "precio_clp")
        )
        if precio is None or precio <= 0 or precio > MAX_PRECIO:
            return None
        return {
            "precio_estimado_ia": precio,
            "precio_unitario_ia": self._to_decimal(
                self._primero_no_nulo(datos, "precio_unitario_ia", "precio_unitario")
            ),
            "gramos_estimados_ia": self._to_decimal(
                self._primero_no_nulo(datos, "gramos_estimados_ia", "gramos_estimados")
            ),
            "tiempo_estimado_horas_ia": self._to_decimal(
                self._primero_no_nulo(datos, "tiempo_estimado_horas_ia", "tiempo_estimado_horas")
            ),
            "material_sugerido_ia": self._primero_no_nulo(
                datos, "material_sugerido_ia", "material_sugerido", "material_detectado"
            ),
            "complejidad_ia": self._primero_no_nulo(datos, "complejidad_ia", "complejidad"),
            "confianza_material_ia": self._to_decimal(
                self._primero_no_nulo(datos, "confianza_material_ia", "confianza_material")
            ),
            "confianza_complejidad_ia": self._to_decimal(
                self._primero_no_nulo(datos, "confianza_complejidad_ia", "confianza_complejidad")
            ),
        }

    # ------------------------------------------------------------------
    # Normalización y validaciones
    # ------------------------------------------------------------------
    @staticmethod
    def _normalizar_datos(datos: dict) -> dict:
        datos = dict(datos or {})
        if datos.get("token") and not datos.get("estimacion_token"):
            datos["estimacion_token"] = datos["token"]
        if datos.get("material_usuario") and not datos.get("material"):
            datos["material"] = datos["material_usuario"]
        if datos.get("material") and not datos.get("material_usuario"):
            datos["material_usuario"] = datos["material"]
        return datos

    @staticmethod
    def _opcional_texto(valor) -> str | None:
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    def _validar_modelo_url(self, valor) -> str | None:
        url = self._opcional_texto(valor)
        if url is None:
            return None
        if len(url) > MAX_MODELO_URL:
            raise ValueError(f"La URL del modelo debe tener máximo {MAX_MODELO_URL} caracteres.")
        if not re.match(r"^https?://[^\s]+$", url, re.IGNORECASE):
            raise ValueError("La URL del modelo debe comenzar con http:// o https://.")
        return url

    def _parse_decimal_pos(self, valor, campo: str):
        if valor is None or str(valor).strip() == "":
            return None
        texto = str(valor).strip().replace(",", ".")
        try:
            d = Decimal(texto)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"El valor de {campo} no es numérico.")
        if not d.is_finite():
            raise ValueError(f"El valor de {campo} no es numérico.")
        if d <= 0:
            raise ValueError(f"El valor de {campo} debe ser mayor a 0.")
        if d > MAX_DIMENSION:
            raise ValueError(f"El valor de {campo} no puede superar {MAX_DIMENSION}.")
        return d

    # ------------------------------------------------------------------
    # Límite por cuenta
    # ------------------------------------------------------------------
    def _verificar_limite_cuenta(self, usuario_id: UUID) -> None:
        from datetime import timezone
        ahora = utcnow()
        if ahora.tzinfo is None:
            ahora = ahora.replace(tzinfo=timezone.utc)
        hace_1min = ahora - timedelta(minutes=1)
        hace_1hora = ahora - timedelta(hours=1)

        def _normalizar(fecha):
            if fecha is None:
                return None
            if fecha.tzinfo is None:
                return fecha.replace(tzinfo=timezone.utc)
            return fecha

        contar = getattr(self.repositorio, "contar_por_usuario_desde", None)
        try:
            if callable(contar):
                c_1min = contar(usuario_id, hace_1min)
                c_1hora = contar(usuario_id, hace_1hora)
            else:
                existentes = self.repositorio.listar_por_usuario(usuario_id) or []
                c_1min = sum(1 for s in existentes if _normalizar(s.creado_en) and _normalizar(s.creado_en) >= hace_1min)
                c_1hora = sum(1 for s in existentes if _normalizar(s.creado_en) and _normalizar(s.creado_en) >= hace_1hora)
        except Exception:
            logger.exception("No se pudo verificar el límite por cuenta (usuario=%s)", usuario_id)
            return

        if c_1min >= LIMITE_POR_MINUTO:
            raise ValueError("Estás cotizando muy rápido. Espera 1 minuto e inténtalo de nuevo.")
        if c_1hora >= LIMITE_POR_HORA:
            raise ValueError(f"Llegaste al límite de {LIMITE_POR_HORA} cotizaciones por hora.")

    # ------------------------------------------------------------------
    # Cotizador
    # ------------------------------------------------------------------
    def _estimar_con_cola(self, contenido, extension, alto, ancho, largo, unidad, cantidad, uso, material, color) -> dict:
        """Llamado no bloqueante: si el cotizador está ocupado o dentro del
        intervalo mínimo, lanza CotizadorOcupado en lugar de dormir la petición."""
        global _ULTIMO_LLAMADO
        if not _LOCK_COTIZADOR.acquire(blocking=False):
            raise CotizadorOcupado()
        try:
            if time.time() - _ULTIMO_LLAMADO < INTERVALO_COTIZADOR_SEGUNDOS:
                raise CotizadorOcupado()
            try:
                return self._estimar_con_cotizador(
                    contenido=contenido, extension=extension,
                    alto=alto, ancho=ancho, largo=largo, unidad=unidad,
                    cantidad=cantidad, uso=uso, material=material, color=color,
                )
            finally:
                _ULTIMO_LLAMADO = time.time()
        finally:
            _LOCK_COTIZADOR.release()

    def _estimar_con_cotizador(self, contenido, extension, alto, ancho, largo, unidad, cantidad, uso, material, color) -> dict:
        if alto is None or ancho is None or largo is None or not uso or not color:
            logger.warning(
                "Cotización con valores por defecto (alto=%s ancho=%s largo=%s uso=%s color=%s)",
                alto, ancho, largo, uso, color,
            )
        try:
            return self.cotizador_ia.estimar(
                imagen_bytes=contenido, filename=f"cotizacion.{extension}",
                alto=float(alto) if alto else 10, ancho=float(ancho) if ancho else 10,
                largo=float(largo) if largo else 10, unidad=unidad, cantidad=cantidad,
                uso=uso or "Decorativo", material_usuario=material, color=color or "Negro",
            )
        except requests.exceptions.RequestException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 429 or "429" in str(e):
                logger.warning("Cotizador IA devolvió 429; usando estimación local al crear solicitud.")
                return estimacion_local(alto, ancho, largo, cantidad, material)
            raise

    def _aplicar_estimacion_firmada(self, datos, solicitud, contenido, usuario_id) -> dict | None:
        token = str(datos.get("estimacion_token") or "").strip()
        if not token:
            return None
        firma_esperada = firma_especificaciones(
            alto=solicitud.alto, ancho=solicitud.ancho, largo=solicitud.largo,
            unidad=solicitud.unidad, cantidad=solicitud.cantidad,
            uso=solicitud.uso, material=solicitud.material, color=solicitud.color,
        )
        estimacion = verificar_token_estimacion(
            token, usuario_id=usuario_id, imagen_sha256=hash_imagen(contenido),
            firma=firma_esperada, secreto=self._secreto_estimacion(), max_age=self._ttl_estimacion(),
        )
        if estimacion is None:
            logger.warning("Token de estimación inválido, expirado o de otra imagen/usuario.")
            return None
        precio = self._to_decimal(
            self._primero_no_nulo(estimacion, "precio_estimado_ia", "precio_estimado", "precio_clp")
        )
        if precio is None or precio <= 0 or precio > MAX_PRECIO:
            return None
        return estimacion

    def _aplicar_resultado(self, solicitud, res: dict) -> None:
        pn = self._primero_no_nulo
        solicitud.material_sugerido_ia = self._texto_largo(
            pn(res, "material_sugerido_ia", "material_sugerido", "material_detectado"), 50)
        solicitud.complejidad_ia = self._texto_largo(pn(res, "complejidad_ia", "complejidad"), 50)
        solicitud.gramos_estimados_ia = self._to_decimal(pn(res, "gramos_estimados_ia", "gramos_estimados"))
        solicitud.tiempo_estimado_horas_ia = self._to_decimal(
            pn(res, "tiempo_estimado_horas_ia", "tiempo_estimado_horas"))
        solicitud.precio_estimado_ia = self._to_decimal(
            pn(res, "precio_estimado_ia", "precio_estimado", "precio_clp"))
        solicitud.confianza_material_ia = self._to_decimal(pn(res, "confianza_material_ia", "confianza_material"))
        solicitud.confianza_complejidad_ia = self._to_decimal(
            pn(res, "confianza_complejidad_ia", "confianza_complejidad"))

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _primero_no_nulo(res: dict, *claves: str):
        for clave in claves:
            valor = res.get(clave)
            if valor is None:
                continue
            if isinstance(valor, str) and valor.strip().lower() in ("", "undefined", "null", "none"):
                continue
            return valor
        return None

    def _secreto_estimacion(self) -> str:
        return str(self._config("SECRET_KEY") or "")

    def _ttl_estimacion(self) -> int:
        try:
            return int(self._config("ESTIMACION_TOKEN_TTL_SECONDS") or 7200)
        except (TypeError, ValueError):
            return 7200

    def _config(self, clave: str):
        try:
            from flask import current_app, has_app_context
            if has_app_context():
                return current_app.config.get(clave)
        except ImportError:
            pass
        return getattr(Config, clave, None)

    def _marcador_error(self, exc: Exception) -> str:
        respuesta = getattr(exc, "response", None)
        codigo = getattr(respuesta, "status_code", None)
        detalle = codigo if codigo is not None else exc.__class__.__name__
        return f"cotizador-error-{detalle}"[:50]

    @staticmethod
    def _texto_largo(valor, maximo: int):
        texto = str(valor).strip() if valor is not None else ""
        return texto[:maximo] or None

    @staticmethod
    def _to_decimal(valor):
        if valor is None:
            return None
        try:
            d = Decimal(str(valor))
        except (InvalidOperation, ValueError):
            return None
        return d if d.is_finite() else None

    @staticmethod
    def _eliminar_imagen(ruta) -> None:
        if not ruta:
            return
        try:
            ruta_str = str(ruta)
            if not os.path.isabs(ruta_str):
                ruta_str = os.path.join(Config.UPLOAD_FOLDER, ruta_str)
            if os.path.isfile(ruta_str):
                os.remove(ruta_str)
        except OSError:
            logger.warning("No se pudo eliminar la imagen huérfana: %s", ruta)