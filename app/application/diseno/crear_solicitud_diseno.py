from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.domain.entities.solicitud_diseno import EstadoSolicitud, SolicitudDiseno
from app.domain.time import utcnow
from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura
from app.infrastructure.cotizador import ClienteCotizadorIA

logger = logging.getLogger(__name__)

MATERIALES_PERMITIDOS = {"PLA", "PLA+", "ABS+", "ABS", "PETG", "Resina", "No estoy seguro"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IA_ORIGEN_SERVER = "cotizador-apolovibes-v2"
IA_ORIGEN_CLIENTE = "cotizador-apolovibes-v2-front"

# Valores que el navegador puede mandar cuando no tiene una estimacion real
# (FormData convierte `undefined` a la cadena "undefined").
_VALORES_VACIOS = {"", "undefined", "null", "none", "nan"}



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

        # Estrategia: el frontend ya estima al subir la imagen y manda el
        # resultado junto con la firma de las especificaciones. Se reutiliza si
        # la firma coincide (una sola llamada al cotizador por cotizacion, sin
        # chocar con su limite de 1 request/minuto). Solo si no hay estimacion
        # valida del cliente se llama al cotizador desde el backend.
        try:
            estimacion = self._aplicar_estimacion_cliente(datos, solicitud)
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

    def _aplicar_estimacion_cliente(self, datos: dict, solicitud: SolicitudDiseno) -> dict | None:
        """Reutiliza la estimacion calculada por el cliente (en el upload) si la firma
        de las especificaciones sigue siendo la misma."""
        firma_esperada = self._firma_especificaciones(
            alto=solicitud.alto,
            ancho=solicitud.ancho,
            largo=solicitud.largo,
            unidad=solicitud.unidad,
            cantidad=solicitud.cantidad,
            uso=solicitud.uso,
            material=solicitud.material,
            color=solicitud.color,
        )
        if str(datos.get("estimacion_firma") or "").strip() != firma_esperada:
            return None

        def _get(*nombres):
            for n in nombres:
                v = datos.get(n)
                if v is None:
                    continue
                texto = str(v).strip()
                if texto.lower() in _VALORES_VACIOS:
                    continue
                return v
            return None

        precio = self._to_decimal(_get("precio_estimado", "precio_estimado_ia", "precio_clp"))
        if precio is None or precio <= 0 or precio > Decimal("9999999999.99"):
            return None
        return {
            "precio_estimado_ia": precio,
            "precio_unitario_ia": self._to_decimal(_get("precio_unitario", "precio_unitario_ia", "precio_unitario_clp")),
            "gramos_estimados_ia": self._to_decimal(_get("gramos_estimados", "gramos_estimados_ia")),
            "tiempo_estimado_horas_ia": self._to_decimal(_get("tiempo_estimado_horas", "tiempo_estimado_horas_ia")),
            "material_sugerido_ia": self._texto_largo(_get("material_sugerido", "material_sugerido_ia", "material_detectado"), 50),
            "complejidad_ia": self._texto_largo(_get("complejidad", "complejidad_ia"), 50),
            "confianza_material_ia": self._to_decimal(_get("confianza_material", "confianza_material_ia")),
            "confianza_complejidad_ia": self._to_decimal(_get("confianza_complejidad", "confianza_complejidad_ia")),
        }

    def _aplicar_resultado(self, solicitud: SolicitudDiseno, res: dict) -> None:
        solicitud.material_sugerido_ia = self._texto_largo(res.get("material_sugerido_ia") or res.get("material_detectado"), 50)
        solicitud.complejidad_ia = self._texto_largo(res.get("complejidad_ia") or res.get("complejidad"), 50)
        solicitud.gramos_estimados_ia = self._to_decimal(res.get("gramos_estimados_ia") if res.get("gramos_estimados_ia") is not None else res.get("gramos_estimados"))
        solicitud.tiempo_estimado_horas_ia = self._to_decimal(res.get("tiempo_estimado_horas_ia") if res.get("tiempo_estimado_horas_ia") is not None else res.get("tiempo_estimado_horas"))
        solicitud.precio_estimado_ia = self._to_decimal(res.get("precio_estimado_ia") if res.get("precio_estimado_ia") is not None else res.get("precio_clp"))
        solicitud.confianza_material_ia = self._to_decimal(res.get("confianza_material_ia") if res.get("confianza_material_ia") is not None else res.get("confianza_material"))
        solicitud.confianza_complejidad_ia = self._to_decimal(res.get("confianza_complejidad_ia") if res.get("confianza_complejidad_ia") is not None else res.get("confianza_complejidad"))

    def _firma_especificaciones(
        self,
        alto,
        ancho,
        largo,
        unidad: str,
        cantidad: int,
        uso: str | None,
        material: str,
        color: str | None,
    ) -> str:
        """Firma canonica de las especificaciones de la pieza.

        Debe coincidir con `firmaEspecificaciones` del frontend
        (src/services/cotizador.js) para poder reutilizar su estimacion.
        """
        return "|".join([
            self._num_firma(alto, 10),
            self._num_firma(ancho, 10),
            self._num_firma(largo, 10),
            str(unidad or "cm").strip() or "cm",
            str(int(cantidad or 1)),
            str((uso or "Decorativo").strip() or "Decorativo"),
            str((material or "").strip()),
            str((color or "Negro").strip() or "Negro"),
        ])

    def _num_firma(self, valor, default=None) -> str:
        if valor is None or str(valor).strip() == "":
            valor = default
        if valor is None or str(valor).strip() == "":
            return ""
        try:
            numero = Decimal(str(valor).strip().replace(",", ".")).normalize()
            if numero == numero.to_integral_value():
                return str(int(numero))
            texto = format(numero, "f")
            if "." in texto:
                texto = texto.rstrip("0").rstrip(".")
            return texto or "0"
        except Exception:
            return str(valor).strip()

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
