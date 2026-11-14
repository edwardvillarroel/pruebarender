from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.domain.entities.solicitud_diseno import EstadoSolicitud, SolicitudDiseno
from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura
from app.infrastructure.cotizador import ClienteCotizadorIA


MATERIALES_PERMITIDOS = {"PLA", "PLA+", "ABS+", "ABS", "PETG", "Resina", "No estoy seguro"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IA_ORIGEN_SERVER = "cotizador-apolovibes-v2"



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

        try:
            estimacion = None
            if self.cotizador_ia is not None:
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

        except Exception as e:
            import traceback
            print(f"[Estimacion] Fallo: {e}")
            traceback.print_exc()

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
        res = self.cotizador_ia.estimar(
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
        solicitud.material_sugerido_ia = self._texto_largo(res.get("material_sugerido_ia") or res.get("material_detectado"), 50)
        solicitud.complejidad_ia = self._texto_largo(res.get("complejidad_ia") or res.get("complejidad"), 50)
        solicitud.gramos_estimados_ia = self._to_decimal(res.get("gramos_estimados_ia") if res.get("gramos_estimados_ia") is not None else res.get("gramos_estimados"))
        solicitud.tiempo_estimado_horas_ia = self._to_decimal(res.get("tiempo_estimado_horas_ia") if res.get("tiempo_estimado_horas_ia") is not None else res.get("tiempo_estimado_horas"))
        solicitud.precio_estimado_ia = self._to_decimal(res.get("precio_estimado_ia") if res.get("precio_estimado_ia") is not None else res.get("precio_clp"))
        solicitud.confianza_material_ia = self._to_decimal(res.get("confianza_material_ia") if res.get("confianza_material_ia") is not None else res.get("confianza_material"))
        solicitud.confianza_complejidad_ia = self._to_decimal(res.get("confianza_complejidad_ia") if res.get("confianza_complejidad_ia") is not None else res.get("confianza_complejidad"))
        solicitud.ia_calculado_en = datetime.utcnow()
        solicitud.ia_origen = IA_ORIGEN_SERVER
        return res

    def _aplicar_resultado(self, solicitud: SolicitudDiseno, res: dict) -> None:
        solicitud.material_sugerido_ia = self._texto_largo(res.get("material_sugerido_ia") or res.get("material_detectado"), 50)
        solicitud.complejidad_ia = self._texto_largo(res.get("complejidad_ia") or res.get("complejidad"), 50)
        solicitud.gramos_estimados_ia = self._to_decimal(res.get("gramos_estimados_ia") if res.get("gramos_estimados_ia") is not None else res.get("gramos_estimados"))
        solicitud.tiempo_estimado_horas_ia = self._to_decimal(res.get("tiempo_estimado_horas_ia") if res.get("tiempo_estimado_horas_ia") is not None else res.get("tiempo_estimado_horas"))
        solicitud.precio_estimado_ia = self._to_decimal(res.get("precio_estimado_ia") if res.get("precio_estimado_ia") is not None else res.get("precio_clp"))
        solicitud.confianza_material_ia = self._to_decimal(res.get("confianza_material_ia") if res.get("confianza_material_ia") is not None else res.get("confianza_material"))
        solicitud.confianza_complejidad_ia = self._to_decimal(res.get("confianza_complejidad_ia") if res.get("confianza_complejidad_ia") is not None else res.get("confianza_complejidad"))

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
