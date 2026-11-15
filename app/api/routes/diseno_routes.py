from uuid import UUID
import hmac
import io
import os
from pathlib import Path

import requests
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    request,
    send_file,
    send_from_directory,
)

from app.api.middleware.auth import requiere_sesion, usuario_actual, usuario_confiable, rol_requerido
from app.application.diseno.firma_especificaciones import firma_especificaciones
from app.config import Config
from app.infrastructure.imagenes.firmas_upload import firmar, verificar
from app.infrastructure.imagenes.miniaturas_cotizacion import (
    MIME_MINIATURA,
    crear_miniatura,
    ruta_miniatura,
)
from app.infrastructure.imagenes.validador_imagen_segura import ImagenInvalida
from app.infrastructure.cotizador import ClienteCotizadorIA
from app.infrastructure.cotizador.token_estimacion import (
    crear_token_estimacion,
    hash_imagen,
)
from app.infrastructure.database.connection import utcnow
from app.infrastructure.storage.supabase_storage import almacen_desde_config
from app.domain.entities.solicitud_diseno import EstadoSolicitud
from decimal import Decimal

diseno_bp = Blueprint("disenos", __name__)

# C: cache de las imágenes servidas por la app. La ruta de una cotización es un
# UUID inmutable, así que la miniatura de esa ruta no cambia nunca; los
# archivos legacy en disco se cachean un día (el TTL de la firma).
_CACHE_MINIATURA_SEGUNDOS = 7 * 24 * 3600
_CACHE_IMAGEN_SEGUNDOS = 86400


def _notificar_nueva_cotizacion(solicitud) -> None:
    correo = current_app.config.get("CORREO_SERVICE")
    if correo is None:
        return
    try:
        correo.avisar_admin_nueva_cotizacion(solicitud)
    except Exception: 
        current_app.logger.exception(
            "No se pudo avisar al admin de la cotización %s", solicitud.id
        )


def _notificar_estado_cotizacion(solicitud, estado: str, precio=None) -> None:
    correo = current_app.config.get("CORREO_SERVICE")
    if correo is None:
        return
    try:
        correo.enviar_estado_cotizacion(solicitud, estado, precio)
    except Exception:  
        current_app.logger.exception(
            "No se pudo enviar el correo de cotización %s (%s)",
            solicitud.id,
            estado,
        )


@diseno_bp.post("/cotizaciones/validar-imagen")
def validar_imagen_cotizacion():
    try:
        if "imagen" not in request.files:
            return jsonify({"mensaje": "Falta la imagen de referencia."}), 400

        imagen = request.files["imagen"]
        if imagen.filename == "":
            return jsonify({"mensaje": "Debes seleccionar una imagen."}), 400

        from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura

        validar_imagen_segura(imagen)
        return jsonify({"ok": True, "valido": True}), 200
    except ImagenInvalida as e:
        return jsonify({"mensaje": str(e)}), 400
    except Exception:
        return jsonify({"mensaje": "No pudimos validar la imagen."}), 500


@diseno_bp.post("/cotizaciones")
@requiere_sesion()
def crear_cotizacion():
    try:
        imagen = request.files.get("imagen")
        if imagen is None or imagen.filename == "":
            return jsonify({"mensaje": "Falta la imagen de referencia."}), 400

        datos = request.form.to_dict()
        if "modeloUrl" in datos and "modelo_url" not in datos:
            datos["modelo_url"] = datos.pop("modeloUrl")

        usuario_id_str = usuario_actual()
        if not usuario_id_str:
            return jsonify({"mensaje": "Sesión requerida"}), 401
        try:
            usuario_id = UUID(usuario_id_str)
        except Exception:
            return jsonify({"mensaje": "Sesión requerida"}), 401

        servicio = current_app.config.get("COTIZACION_SERVICE")
        if servicio is None:
            return jsonify({"mensaje": "No pudimos procesar la solicitud."}), 500

        solicitud = servicio.ejecutar(usuario_id, datos, imagen)
        _notificar_nueva_cotizacion(solicitud)
        return jsonify({"id": str(solicitud.id), "estado": solicitud.estado.value, "creado_en": solicitud.creado_en.isoformat()}), 201
    except ImagenInvalida as e:
        return jsonify({"mensaje": str(e)}), 400
    except ValueError as e:
        return jsonify({"mensaje": str(e)}), 400
    except Exception:
        current_app.logger.exception("Error creando cotización")
        return jsonify({"mensaje": "No pudimos procesar la solicitud."}), 500


@diseno_bp.get("/cotizaciones")
@requiere_sesion()
@rol_requerido("admin")
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
                    "imagen": firmar(s.imagen),
                    "imagen_thumb": _firmar_miniatura(s.imagen),
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
        return jsonify({"mensaje": "No pudimos obtener las cotizaciones."}), 500


@diseno_bp.get("/cotizaciones/mias")
@requiere_sesion()
def listar_mis_cotizaciones():
    try:
        from app.infrastructure.repositories.pedido_repository import PedidoRepository
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        usuario_id_str = usuario_actual()
        if not usuario_id_str:
            return jsonify({"mensaje": "Sesión requerida"}), 401
        try:
            usuario_id = UUID(str(usuario_id_str))
        except Exception:
            return jsonify({"mensaje": "Sesión requerida"}), 401

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
                    "imagen": firmar(s.imagen),
                    "imagen_thumb": _firmar_miniatura(s.imagen),
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
        return jsonify({"mensaje": "No pudimos obtener tus cotizaciones."}), 500

@diseno_bp.post("/cotizaciones/<uuid:solicitud_id>/aviso/visto")
@requiere_sesion()
def marcar_aviso_cotizacion_visto(solicitud_id):
    try:
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        usuario_id_str = usuario_actual()
        if not usuario_id_str:
            return jsonify({"mensaje": "Sesión requerida"}), 401
        try:
            usuario_id = UUID(usuario_id_str)
        except Exception:
            return jsonify({"mensaje": "Sesión requerida"}), 401
        repo = SolicitudDisenoRepository()
        s = repo.obtener_por_id(solicitud_id)
        if s is None:
            return jsonify({"mensaje": "Cotización no encontrada"}), 404

        # Solo dueño o admin puede verla
        from app.api.middleware.auth import rol_actual
        if s.usuario_id and str(s.usuario_id) != str(usuario_id_str) and rol_actual() != "admin":
            return jsonify({"mensaje": "No autorizado"}), 403

        s.aviso_estado_visto = True
        repo.actualizar(s)
        return jsonify({"ok": True}), 200
    except Exception:
        current_app.logger.exception("Error marcando aviso de cotización visto")
        return jsonify({"mensaje": "No pudimos marcar el aviso como visto."}), 500


@diseno_bp.get("/cotizaciones/<uuid:solicitud_id>")
@requiere_sesion()
def obtener_cotizacion(solicitud_id):
    try:
        from app.infrastructure.repositories.pedido_repository import PedidoRepository
        from app.infrastructure.repositories.solicitud_diseno_repository import SolicitudDisenoRepository

        repo = SolicitudDisenoRepository()
        s = repo.obtener_por_id(solicitud_id)

        # Solo dueño o admin puede verla
        from app.api.middleware.auth import rol_actual
        usuario_id_str = usuario_actual()
        if s is None:
            return jsonify({"mensaje": "Cotización no encontrada"}), 404
        if s.usuario_id and str(s.usuario_id) != str(usuario_id_str) and rol_actual() != "admin":
            return jsonify({"mensaje": "No autorizado"}), 403
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
                "imagen": firmar(s.imagen),
                "imagen_thumb": _firmar_miniatura(s.imagen),
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
        return jsonify({"mensaje": "No pudimos obtener la cotización."}), 500


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
            return jsonify({"mensaje": "Cotización no encontrada"}), 404

        estado_previo = s.estado
        precio_previo = s.precio

        if estado == "aprobada":
            if precio_raw is None or str(precio_raw).strip() == "":
                return jsonify({"mensaje": "Debes ingresar el precio asignado para aprobar la cotización."}), 400
            try:
                if isinstance(precio_raw, str):
                    precio_limpio = precio_raw.replace(".", "").replace(",", ".")
                    precio_num = Decimal(precio_limpio)
                else:
                    precio_num = Decimal(str(precio_raw))
            except Exception:
                return jsonify({"mensaje": "Precio inválido."}), 400
            if precio_num <= 0:
                return jsonify({"mensaje": "El precio debe ser mayor a 0."}), 400
            s.precio = precio_num
            s.estado = EstadoSolicitud.APROBADA
            s.aviso_estado_en = utcnow()
            s.aviso_estado_visto = False
            repo.actualizar(s)
            if estado_previo != s.estado or precio_previo != s.precio:
                _notificar_estado_cotizacion(
                    s,
                    "aprobada",
                    int(s.precio) if s.precio is not None else None,
                )
            return jsonify({"ok": True, "id": str(s.id), "estado": s.estado.value, "precio": float(s.precio) if s.precio is not None else None}), 200

        if estado == "rechazada":
            s.estado = EstadoSolicitud.RECHAZADA
            s.aviso_estado_en = utcnow()
            s.aviso_estado_visto = False
            repo.actualizar(s)
            if estado_previo != s.estado:
                _notificar_estado_cotizacion(s, "rechazada", s.precio)
            return jsonify({"ok": True, "id": str(s.id), "estado": s.estado.value}), 200

        return jsonify({"mensaje": "Estado inválido. Usa 'aprobada' o 'rechazada'."}), 400
    except Exception:
        current_app.logger.exception("Error evaluando cotización")
        return jsonify({"mensaje": "No pudimos evaluar la cotización."}), 500


@diseno_bp.post("/cotizaciones/estimar")
def estimar_cotizacion():
    try:
        archivo = None
        imagen = None
        if "imagen" in request.files:
            imagen = request.files["imagen"]
            archivo = imagen
        elif "file" in request.files:
            archivo = request.files["file"]
        imagen = imagen or archivo
        if imagen is None or imagen.filename == "":
            return jsonify({"mensaje": "Falta la imagen de referencia."}), 400

        def _numero(nombre, default):
            valor = request.form.get(nombre)
            if valor is None or str(valor).strip() == "":
                return default
            try:
                numero = float(str(valor).replace(",", "."))
            except (TypeError, ValueError):
                return default
            return numero if numero > 0 else default

        alto = _numero("alto", _numero("altura", 10))
        ancho = _numero("ancho", 10)
        largo = _numero("largo", 10)
        unidad = request.form.get("unidad") or "cm"
        cantidad = request.form.get("cantidad") or 1
        try:
            cantidad_int = max(1, int(float(str(cantidad).replace(",", "."))))
        except (TypeError, ValueError):
            cantidad_int = 1
        uso = request.form.get("uso") or "Decorativo"
        material_usuario = request.form.get("material_usuario") or request.form.get("material")
        color = request.form.get("color") or "Negro"

        from app.infrastructure.imagenes.validador_imagen_segura import validar_imagen_segura

        contenido, extension = validar_imagen_segura(imagen)

        cliente = ClienteCotizadorIA(
            base_url=current_app.config.get("COTIZADOR_IA_URL"),
            api_key=current_app.config.get("APOLO_API_KEY"),
            timeout=int(current_app.config.get("COTIZADOR_IA_TIMEOUT") or 60),
        )
        resultado = cliente.estimar(
            imagen_bytes=contenido,
            filename=imagen.filename or f"imagen.{extension}",
            alto=alto,
            ancho=ancho,
            largo=largo,
            unidad=unidad,
            cantidad=cantidad_int,
            uso=uso,
            material_usuario=material_usuario,
            color=color,
        )

        respuesta = {
            "precio_estimado_ia": resultado.get("precio_estimado_ia") or resultado.get("precio_estimado") or resultado.get("precio_clp"),
            "precio_unitario_ia": resultado.get("precio_unitario_ia") or resultado.get("precio_unitario") or resultado.get("precio_unitario_clp"),
            "gramos_estimados_ia": resultado.get("gramos_estimados_ia") or resultado.get("gramos_estimados"),
            "tiempo_estimado_horas_ia": resultado.get("tiempo_estimado_horas_ia") or resultado.get("tiempo_estimado_horas"),
            "material_sugerido_ia": resultado.get("material_sugerido_ia") or resultado.get("material_sugerido") or resultado.get("material_detectado"),
            "complejidad_ia": resultado.get("complejidad_ia") or resultado.get("complejidad"),
            "confianza_material_ia": resultado.get("confianza_material_ia") or resultado.get("confianza_material"),
            "confianza_complejidad_ia": resultado.get("confianza_complejidad_ia") or resultado.get("confianza_complejidad"),
            "ia_origen": resultado.get("ia_origen") or resultado.get("origen_ia") or resultado.get("origen") or "ia",
        }

        firma = firma_especificaciones(
            alto=alto,
            ancho=ancho,
            largo=largo,
            unidad=unidad,
            cantidad=cantidad_int,
            uso=uso,
            material=material_usuario,
            color=color,
        )
        respuesta["firma"] = firma

        # El token liga la estimacion a este usuario, estos bytes de imagen y
        # estas especificaciones. Solo se emite para usuarios autenticados a
        # traves del gateway; el alta lo consume y nunca lee precios sueltos.
        usuario = usuario_confiable()
        if usuario:
            try:
                usuario_token = str(UUID(str(usuario)))
            except Exception:
                usuario_token = str(usuario)
            token = crear_token_estimacion(
                usuario_id=usuario_token,
                imagen_sha256=hash_imagen(contenido),
                firma=firma,
                estimacion=resultado,
                secreto=str(current_app.config.get("SECRET_KEY") or ""),
            )
            if token:
                respuesta["token"] = token

        return jsonify(respuesta), 200
    except requests.exceptions.RequestException:
        current_app.logger.exception("Error llamando al servicio de estimación")
        return jsonify({"mensaje": "No pudimos procesar tu solicitud. Inténtalo de nuevo."}), 503
    except Exception:
        current_app.logger.exception("Error estimando cotización")
        return jsonify({"mensaje": "No pudimos procesar tu solicitud. Inténtalo de nuevo."}), 500

@diseno_bp.get("/uploads/<path:filename>")
def servir_uploads(filename):
    try:
        # F1: sin firma vigente no se sirve el archivo (antes era público).
        if not verificar(filename, request.args.get("exp"), request.args.get("sig")):
            return jsonify({"mensaje": "Enlace inválido o expirado."}), 403
        # C: el listado muestra 96×96; servir la foto completa ahí es lo que
        # hacía tardar la carga. Si hay miniatura se responde con eso.
        if request.args.get("thumb") == "1":
            respuesta = _servir_miniatura(filename)
            if respuesta is not None:
                return respuesta
        # F4: si el objeto vive en Supabase Storage se redirige (302) a una URL
        # firmada de vida corta; el servicio jamás ve la service-role key.
        # B: no se pregunta antes si el objeto existe — si no está en el bucket
        # (archivos legacy en disco) el `sign` falla y se sirve local igual.
        almacen = almacen_desde_config(current_app.config)
        if almacen is not None:
            url = almacen.url_firmada(filename)
            if url:
                return redirect(url, code=302)
        carpeta = current_app.config.get("UPLOAD_FOLDER") or Config.UPLOAD_FOLDER
        return send_from_directory(carpeta, filename, max_age=_CACHE_IMAGEN_SEGUNDOS)
    except Exception:
        return jsonify({"mensaje": "Archivo no encontrado"}), 404


def _firmar_miniatura(ruta):
    """URL de la miniatura, o la de la imagen original si no hay miniatura.

    La firma cubre la ruta (no los query params extra): `thumb=1` solo cambia
    cómo se sirve el mismo contenido ya autorizado.
    """
    firmada = firmar(ruta)
    if firmada is None or ruta_miniatura(ruta) is None:
        return firmada
    return f"{firmada}&thumb=1"


def _servir_miniatura(filename):
    """Respuesta con la miniatura, o `None` si conviene servir el original.

    `None` (foto ya chica, Pillow ausente, original ilegible) no es un error:
    es preferible bajar la foto grande antes que mostrar una imagen rota.
    """
    datos = _obtener_miniatura(filename)
    if datos is None:
        return None
    respuesta = send_file(io.BytesIO(datos), mimetype=MIME_MINIATURA)
    # El UUID de la imagen es inmutable: su miniatura no cambia nunca.
    respuesta.headers["Cache-Control"] = (
        f"private, max-age={_CACHE_MINIATURA_SEGUNDOS}"
    )
    return respuesta


def _obtener_miniatura(filename):
    """Bytes de la miniatura, generándola y guardándola si todavía no existe."""
    destino = ruta_miniatura(filename)
    if destino is None:
        return None
    almacen = almacen_desde_config(current_app.config)
    if almacen is not None:
        cacheada = almacen.descargar(destino)
        if cacheada:
            return cacheada
        return _generar_miniatura_bucket(
            almacen, destino, almacen.descargar(filename)
        )
    return _obtener_miniatura_local(filename, destino)


def _generar_miniatura_bucket(almacen, destino, original):
    generada = crear_miniatura(original)
    if generada is None:
        return None
    # Best-effort: si la subida falla se sirve igual y se reintenta al próximo
    # request (el `subir` del almacen ya avisa y no lanza).
    almacen.subir(destino, generada, MIME_MINIATURA)
    return generada


def _obtener_miniatura_local(filename, destino):
    carpeta = Path(current_app.config.get("UPLOAD_FOLDER") or Config.UPLOAD_FOLDER)
    try:
        raiz = carpeta.resolve()
        cacheada = (raiz / destino).resolve()
        # Anti path-traversal: la ruta derivada debe quedar dentro de uploads.
        cacheada.relative_to(raiz)
    except (OSError, ValueError):
        return None
    if cacheada.is_file():
        return cacheada.read_bytes()
    try:
        original = (raiz / filename).resolve()
        original.relative_to(raiz)
    except (OSError, ValueError):
        return None
    if not original.is_file():
        return None
    generada = crear_miniatura(original.read_bytes())
    if generada is None:
        return None
    try:
        cacheada.parent.mkdir(parents=True, exist_ok=True)
        cacheada.write_bytes(generada)
    except OSError:
        # Disco efímero o permisos: se sirve la miniatura recién generada igual.
        pass
    return generada


@diseno_bp.post("/admin/cotizaciones/purgar")
def purgar_cotizaciones_admin():
    """Purga semanal de cotizaciones vencidas (F3 / A.8.10), vía cron."""
    try:
        secreto = str(current_app.config.get("CRON_SECRET") or "")
        if not secreto:
            return jsonify({"mensaje": "Purga no configurada"}), 503
        header = request.headers.get("X-Cron-Secret") or ""
        if not hmac.compare_digest(secreto.encode("utf-8"), header.encode("utf-8")):
            return jsonify({"mensaje": "No autorizado"}), 401

        from app.application.diseno.purgar_cotizaciones import PurgadorCotizaciones
        from app.infrastructure.repositories.solicitud_diseno_repository import (
            SolicitudDisenoRepository,
        )

        dry_run = (
            (request.args.get("dry_run") or "").strip().lower()
            in ("1", "true", "yes", "si")
        )
        resultado = PurgadorCotizaciones(SolicitudDisenoRepository()).ejecutar(
            dry_run=dry_run
        )
        return jsonify(resultado), 200
    except Exception:
        current_app.logger.exception("Error purgando cotizaciones")
        return jsonify({"mensaje": "No pudimos purgar las cotizaciones."}), 500


@diseno_bp.post("/admin/cotizaciones/migrar")
def migrar_cotizaciones_storage():
    """Migración one-time de imágenes al bucket de Supabase (F4), vía cron.

    Mismo patrón de guard que la purga (F3): 503 sin `CRON_SECRET`, 401 con
    `X-Cron-Secret` incorrecto, `?dry_run=1|true|yes|si` solo cuenta.
    """
    try:
        secreto = str(current_app.config.get("CRON_SECRET") or "")
        if not secreto:
            return jsonify({"mensaje": "Migración no configurada"}), 503
        header = request.headers.get("X-Cron-Secret") or ""
        if not hmac.compare_digest(secreto.encode("utf-8"), header.encode("utf-8")):
            return jsonify({"mensaje": "No autorizado"}), 401

        almacen = almacen_desde_config(current_app.config)
        if almacen is None:
            return jsonify({"mensaje": "Migración no configurada"}), 503

        from app.application.diseno.migrar_cotizaciones import MigradorCotizaciones
        from app.infrastructure.repositories.solicitud_diseno_repository import (
            SolicitudDisenoRepository,
        )

        dry_run = (
            (request.args.get("dry_run") or "").strip().lower()
            in ("1", "true", "yes", "si")
        )
        resultado = MigradorCotizaciones(
            SolicitudDisenoRepository(), almacen
        ).ejecutar(dry_run=dry_run)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"mensaje": str(e)}), 503
    except Exception:
        current_app.logger.exception("Error migrando cotizaciones al bucket")
        return jsonify({"mensaje": "No pudimos migrar las cotizaciones."}), 500


@diseno_bp.delete("/cotizaciones/<uuid:solicitud_id>")
@rol_requerido("admin")
def eliminar_cotizacion(solicitud_id):
    """Borrado manual de una cotización sin pedido asociado (retención A.8.10)."""
    try:
        from app.application.diseno.purgar_cotizaciones import PurgadorCotizaciones
        from app.infrastructure.repositories.pedido_repository import PedidoRepository
        from app.infrastructure.repositories.solicitud_diseno_repository import (
            SolicitudDisenoRepository,
        )

        repo = SolicitudDisenoRepository()
        s = repo.obtener_por_id(solicitud_id)
        if s is None:
            return jsonify({"mensaje": "Cotización no encontrada"}), 404
        if PedidoRepository().pagos_por_cotizacion([s.id]):
            return jsonify({"mensaje": "La cotización tiene un pedido asociado."}), 409
        PurgadorCotizaciones(repo).eliminar_solicitud(s)
        return jsonify({"ok": True, "id": str(s.id)}), 200
    except Exception:
        current_app.logger.exception("Error eliminando cotización %s", solicitud_id)
        return jsonify({"mensaje": "No pudimos eliminar la cotización."}), 500
