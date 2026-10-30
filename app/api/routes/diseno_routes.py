from uuid import UUID
import os

import requests
from flask import Blueprint, current_app, jsonify, request, send_from_directory

from app.api.middleware.auth import requiere_sesion, usuario_actual, rol_requerido
from app.config import Config
from app.infrastructure.imagenes.validador_imagen_segura import ImagenInvalida
from app.infrastructure.cotizador import ClienteCotizadorIA
from app.infrastructure.database.connection import utcnow
from app.domain.entities.solicitud_diseno import EstadoSolicitud
from decimal import Decimal

diseno_bp = Blueprint("disenos", __name__)


@diseno_bp.post("/cotizaciones/validar-imagen")
def validar_imagen_cotizacion():
    try:
        if "imagen" not in request.files:
            return jsonify({"error": "Falta la imagen de referencia."}), 400

        imagen = request.files["imagen"]
        if imagen.filename == "":
            return jsonify({"error": "Debes seleccionar una imagen."}), 400

        from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura

        validar_imagen_segura(imagen)
        return jsonify({"ok": True, "valido": True}), 200
    except ImagenInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "No pudimos validar la imagen."}), 500


@diseno_bp.post("/cotizaciones")
@requiere_sesion()
def crear_cotizacion():
    try:
        imagen = request.files.get("imagen")
        if imagen is None or imagen.filename == "":
            return jsonify({"error": "Falta la imagen de referencia."}), 400

        datos = request.form.to_dict()
        if "modeloUrl" in datos and "modelo_url" not in datos:
            datos["modelo_url"] = datos.pop("modeloUrl")

        usuario_id_str = usuario_actual()
        if not usuario_id_str:
            return jsonify({"error": "Sesión requerida"}), 401
        try:
            usuario_id = UUID(usuario_id_str)
        except Exception:
            return jsonify({"error": "Sesión requerida"}), 401

        servicio = current_app.config.get("COTIZACION_SERVICE")
        if servicio is None:
            return jsonify({"error": "No pudimos procesar the solicitud."}), 500

        solicitud = servicio.ejecutar(usuario_id, datos, imagen)
        return jsonify({"id": str(solicitud.id), "estado": solicitud.estado.value, "creado_en": solicitud.creado_en.isoformat()}), 201
    except ImagenInvalida as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        current_app.logger.exception("Error creando cotización")
        return jsonify({"error": "No pudimos procesar the solicitud."}), 500


@diseno_bp.get("/cotizaciones")
def listar_cotizaciones():
    try:
        from app.infrastructure.repositories.pedido_repository import PedidoRepository
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        repo = SolicitudDisenoRepository()
        solicitudes = repo.listar_todos()
        pagos = PedidoRepository().pagos_por_cotizacion([s.id for s in solicitudes])
        resultado = []
        for s in solicitudes:
            pago = pagos.get(s.id, {})
            resultado.append(
                {
                    "id": str(s.id),
                    "usuario_id": str(s.usuario_id) if s.usuario_id else None,
                    "nombre": s.nombre,
                    "email": s.email,
                    "telefono": s.telefono,
                    "material": s.material,
                    "descripcion": s.descripcion,
                    "alto": float(s.alto) if s.alto is not None else None,
                    "ancho": float(s.ancho) if s.ancho is not None else None,
                    "largo": float(s.largo) if s.largo is not None else None,
                    "unidad": s.unidad,
                    "cantidad": s.cantidad,
                    "uso": s.uso,
                    "color": s.color,
                    "imagen": s.imagen,
                    "modelo_url": s.modelo_url,
                    "precio": float(s.precio) if s.precio is not None else None,
                    "estado": s.estado.value if s.estado else "pendiente",
                    "creado_en": s.creado_en.isoformat() if s.creado_en else None,
                    "material_sugerido_ia": s.material_sugerido_ia,
                    "complejidad_ia": s.complejidad_ia,
                    "gramos_estimados_ia": float(s.gramos_estimados_ia) if s.gramos_estimados_ia is not None else None,
                    "tiempo_estimado_horas_ia": float(s.tiempo_estimado_horas_ia) if s.tiempo_estimado_horas_ia is not None else None,
                    "precio_estimado_ia": float(s.precio_estimado_ia) if s.precio_estimado_ia is not None else None,
                    "confianza_material_ia": float(s.confianza_material_ia) if s.confianza_material_ia is not None else None,
                    "confianza_complejidad_ia": float(s.confianza_complejidad_ia) if s.confianza_complejidad_ia is not None else None,
                    "ia_calculado_en": s.ia_calculado_en.isoformat() if s.ia_calculado_en else None,
                    "ia_origen": s.ia_origen,
                    "pagada": bool(pago.get("pagada", False)),
                    "pedido_id": pago.get("pedido_id"),
                }
            )
        return jsonify(resultado), 200
    except Exception:
        current_app.logger.exception("Error listando cotizaciones")
        return jsonify({"error": "No pudimos obtener las cotizaciones."}), 500


@diseno_bp.get("/cotizaciones/mias")
def listar_mis_cotizaciones():
    try:
        from flask import request, session
        from app.infrastructure.repositories.pedido_repository import PedidoRepository
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        try:
            from flask_login import current_user
        except Exception:
            current_user = None

        usuario_id_str = (
            request.headers.get("X-User-Id")
            or request.headers.get("x-user-id")
            or request.args.get("usuario_id")
            or request.args.get("user_id")
            or session.get("usuario_id")
            or session.get("user_id")
            or session.get("uid")
            or session.get("id")
        )

        if not usuario_id_str and current_user and getattr(current_user, "is_authenticated", False):
            cid = getattr(current_user, "id", None)
            if cid is not None:
                usuario_id_str = cid

        if not usuario_id_str:
            user_sess = session.get("user") or session.get("usuario")
            if isinstance(user_sess, dict):
                usuario_id_str = user_sess.get("id") or user_sess.get("usuario_id") or user_sess.get("_id")
            elif user_sess is not None:
                uid = getattr(user_sess, "id", None)
                if uid is not None:
                    usuario_id_str = uid

        if not usuario_id_str:
            return jsonify({"error": "Sesión requerida"}), 401

        try:
            usuario_id = UUID(str(usuario_id_str))
        except Exception:
            return jsonify({"error": "Sesión requerida"}), 401

        repo = SolicitudDisenoRepository()
        solicitudes = repo.listar_por_usuario(usuario_id)
        pagos = PedidoRepository().pagos_por_cotizacion([s.id for s in solicitudes])
        resultado = []
        for s in solicitudes:
            pago = pagos.get(s.id, {})
            resultado.append(
                {
                    "id": str(s.id),
                    "usuario_id": str(s.usuario_id) if s.usuario_id else None,
                    "nombre": s.nombre,
                    "email": s.email,
                    "telefono": s.telefono,
                    "material": s.material,
                    "descripcion": s.descripcion,
                    "alto": float(s.alto) if s.alto is not None else None,
                    "ancho": float(s.ancho) if s.ancho is not None else None,
                    "largo": float(s.largo) if s.largo is not None else None,
                    "unidad": s.unidad,
                    "cantidad": s.cantidad,
                    "uso": s.uso,
                    "color": s.color,
                    "imagen": s.imagen,
                    "modelo_url": s.modelo_url,
                    "precio": float(s.precio) if s.precio is not None else None,
                    "estado": s.estado.value if s.estado else "pendiente",
                    "creado_en": s.creado_en.isoformat() if s.creado_en else None,
                    "material_sugerido_ia": s.material_sugerido_ia,
                    "complejidad_ia": s.complejidad_ia,
                    "gramos_estimados_ia": float(s.gramos_estimados_ia) if s.gramos_estimados_ia is not None else None,
                    "tiempo_estimado_horas_ia": float(s.tiempo_estimado_horas_ia) if s.tiempo_estimado_horas_ia is not None else None,
                    "precio_estimado_ia": float(s.precio_estimado_ia) if s.precio_estimado_ia is not None else None,
                    "confianza_material_ia": float(s.confianza_material_ia) if s.confianza_material_ia is not None else None,
                    "confianza_complejidad_ia": float(s.confianza_complejidad_ia) if s.confianza_complejidad_ia is not None else None,
                    "ia_calculado_en": s.ia_calculado_en.isoformat() if s.ia_calculado_en else None,
                    "ia_origen": s.ia_origen,
                    "aviso_estado_en": s.aviso_estado_en.isoformat() if getattr(s, "aviso_estado_en", None) else None,
                    "aviso_estado_visto": bool(getattr(s, "aviso_estado_visto", False)),
                    "aviso_estado_pendiente": bool(getattr(s, "aviso_estado_en", None)) and not bool(getattr(s, "aviso_estado_visto", False)),
                    "pagada": bool(pago.get("pagada", False)),
                    "pedido_id": pago.get("pedido_id"),
                }
            )
        return jsonify(resultado), 200
    except Exception:
        current_app.logger.exception("Error listando mis cotizaciones")
        return jsonify({"error": "No pudimos obtener tus cotizaciones."}), 500


@diseno_bp.post("/cotizaciones/<uuid:solicitud_id>/aviso/visto")
@requiere_sesion()
def marcar_aviso_cotizacion_visto(solicitud_id):
    try:
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        usuario_id_str = usuario_actual()
        if not usuario_id_str:
            return jsonify({"error": "Sesión requerida"}), 401
        try:
            usuario_id = UUID(usuario_id_str)
        except Exception:
            return jsonify({"error": "Sesión requerida"}), 401

        repo = SolicitudDisenoRepository()
        s = repo.obtener_por_id(solicitud_id)
        if s is None:
            return jsonify({"error": "Cotización no encontrada"}), 404
        if s.usuario_id and str(s.usuario_id) != str(usuario_id):
            return jsonify({"error": "No autorizado"}), 403

        s.aviso_estado_visto = True
        repo.actualizar(s)
        return jsonify({"ok": True}), 200
    except Exception:
        current_app.logger.exception("Error marcando aviso de cotización visto")
        return jsonify({"error": "No pudimos marcar el aviso como visto."}), 500


@diseno_bp.get("/cotizaciones/<uuid:solicitud_id>")
def obtener_cotizacion(solicitud_id):
    try:
        from app.infrastructure.repositories.pedido_repository import PedidoRepository
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        repo = SolicitudDisenoRepository()
        s = repo.obtener_por_id(solicitud_id)
        if s is None:
            return jsonify({"error": "Cotización no encontrada"}), 404
        pago = PedidoRepository().pagos_por_cotizacion([s.id]).get(s.id, {})
        return jsonify(
            {
                "id": str(s.id),
                "usuario_id": str(s.usuario_id) if s.usuario_id else None,
                "nombre": s.nombre,
                "email": s.email,
                "telefono": s.telefono,
                "material": s.material,
                "descripcion": s.descripcion,
                "alto": float(s.alto) if s.alto is not None else None,
                "ancho": float(s.ancho) if s.ancho is not None else None,
                "largo": float(s.largo) if s.largo is not None else None,
                "unidad": s.unidad,
                "cantidad": s.cantidad,
                "uso": s.uso,
                "color": s.color,
                "imagen": s.imagen,
                "modelo_url": s.modelo_url,
                "precio": float(s.precio) if s.precio is not None else None,
                "estado": s.estado.value if s.estado else "pendiente",
                "creado_en": s.creado_en.isoformat() if s.creado_en else None,
                "material_sugerido_ia": s.material_sugerido_ia,
                "complejidad_ia": s.complejidad_ia,
                "gramos_estimados_ia": float(s.gramos_estimados_ia) if s.gramos_estimados_ia is not None else None,
                "tiempo_estimado_horas_ia": float(s.tiempo_estimado_horas_ia) if s.tiempo_estimado_horas_ia is not None else None,
                "precio_estimado_ia": float(s.precio_estimado_ia) if s.precio_estimado_ia is not None else None,
                "confianza_material_ia": float(s.confianza_material_ia) if s.confianza_material_ia is not None else None,
                "confianza_complejidad_ia": float(s.confianza_complejidad_ia) if s.confianza_complejidad_ia is not None else None,
                "ia_calculado_en": s.ia_calculado_en.isoformat() if s.ia_calculado_en else None,
                "ia_origen": s.ia_origen,
                "pagada": bool(pago.get("pagada", False)),
                "pedido_id": pago.get("pedido_id"),
            }
        ), 200
    except Exception:
        current_app.logger.exception("Error obteniendo cotización")
        return jsonify({"error": "No pudimos obtener la cotización."}), 500


@diseno_bp.patch("/cotizaciones/<uuid:solicitud_id>")
@rol_requerido("admin")
def evaluar_cotizacion(solicitud_id):
    try:
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        data = request.get_json(silent=True) or {}
        estado = (data.get("estado") or "").strip().lower()
        precio_raw = data.get("precio") or data.get("precio_asignado") or data.get("precio_final")

        repo = SolicitudDisenoRepository()
        s = repo.obtener_por_id(solicitud_id)
        if s is None:
            return jsonify({"error": "Cotización no encontrada"}), 404

        if estado == "aprobada":
            if precio_raw is None or str(precio_raw).strip() == "":
                return jsonify({"error": "Debes ingresar el precio asignado para aprobar la cotización."}), 400
            try:
                if isinstance(precio_raw, str):
                    precio_limpio = precio_raw.replace(".", "").replace(",", ".")
                    precio_num = Decimal(precio_limpio)
                else:
                    precio_num = Decimal(str(precio_raw))
            except Exception:
                return jsonify({"error": "Precio inválido."}), 400
            if precio_num <= 0:
                return jsonify({"error": "El precio debe ser mayor a 0."}), 400
            s.precio = precio_num
            s.estado = EstadoSolicitud.APROBADA
            s.aviso_estado_en = utcnow()
            s.aviso_estado_visto = False
            repo.actualizar(s)
            return jsonify({"ok": True, "id": str(s.id), "estado": s.estado.value, "precio": float(s.precio) if s.precio is not None else None}), 200

        if estado == "rechazada":
            s.estado = EstadoSolicitud.RECHAZADA
            s.aviso_estado_en = utcnow()
            s.aviso_estado_visto = False
            repo.actualizar(s)
            return jsonify({"ok": True, "id": str(s.id), "estado": s.estado.value}), 200

        return jsonify({"error": "Estado inválido. Usa 'aprobada' o 'rechazada'."}), 400
    except Exception:
        current_app.logger.exception("Error evaluando cotización")
        return jsonify({"error": "No pudimos evaluar la cotización."}), 500


@diseno_bp.post("/cotizaciones/estimar-ia")
def estimar_cotizacion_ia():
    try:
        if "imagen" not in request.files:
            return jsonify({"error": "Falta la imagen de referencia."}), 400
        imagen = request.files["imagen"]
        if imagen.filename == "":
            return jsonify({"error": "Debes seleccionar una imagen."}), 400
        altura_raw = request.form.get("altura") or request.form.get("alto")
        if not altura_raw:
            return jsonify({"error": "Falta la altura en cm."}), 400

        try:
            altura_cm = int(float(str(altura_raw).replace(",", ".")))
        except (TypeError, ValueError):
            return jsonify({"error": "La altura debe be a número en cm."}), 400

        if altura_cm <= 0:
            return jsonify({"error": "La altura debe be a mayor a 0."}), 400

        material_usuario = request.form.get("material_usuario") or request.form.get("material")

        from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura

        contenido, extension = validar_imagen_segura(imagen)

        cliente = ClienteCotizadorIA(base_url=current_app.config.get("COTIZADOR_IA_URL"))
        resultado = cliente.estimar(contenido, imagen.filename or f"imagen.{extension}", altura_cm, material_usuario)

        return jsonify(resultado), 200
    except requests.exceptions.RequestException:
        current_app.logger.exception("Error llamando al cotizador IA")
        return jsonify({"error": "El cotizador IA no está disponible. Verifica que este levantado el puerto 8001."}), 503
    except Exception:
        current_app.logger.exception("Error estimando with cotizador IA")
        return jsonify({"error": "No pudimos estimar with IA."}), 500


@diseno_bp.get("/uploads/<path:filename>")
def servir_uploads(filename):
    try:
        carpeta = Config.UPLOAD_FOLDER
        return send_from_directory(carpeta, filename)
    except Exception:
        return jsonify({"error": "Archivo no encontrado"}), 404
