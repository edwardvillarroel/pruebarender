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
        if not descripcion:
            raise ValueError("La descripción es obligatoria.")

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
            if self.cotizador_ia is not None:
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
                solicitud.material_sugerido_ia = res.get("material_detectado")
                solicitud.complejidad_ia = res.get("complejidad")
                solicitud.gramos_estimados_ia = self._to_decimal(res.get("gramos_estimados"))
                solicitud.tiempo_estimado_horas_ia = self._to_decimal(res.get("tiempo_estimado_horas"))
                solicitud.precio_estimado_ia = self._to_decimal(res.get("precio_clp") or res.get("precio_estimado_ia"))
                solicitud.confianza_material_ia = self._to_decimal(res.get("confianza_material"))
                solicitud.confianza_complejidad_ia = self._to_decimal(res.get("confianza_complejidad"))
                solicitud.ia_calculado_en = datetime.utcnow()
                solicitud.ia_origen = "cotizador-apolovibes-v2"
        except Exception as e:
            import traceback
            print(f"[IA] Fallo cotizador: {e}")
            traceback.print_exc()

        return self.repositorio.crear(solicitud)

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
