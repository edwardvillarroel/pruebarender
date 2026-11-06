from __future__ import annotations

import hashlib
import hmac
import io
import os
import time
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from PIL import Image

from app.application.diseno.purgar_cotizaciones import PurgadorCotizaciones
from app.domain.time import utcnow
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.solicitud_diseno_model import (
    SolicitudDisenoModel,
)
from app.infrastructure.database.models.usuario_model import UsuarioModel
from app.infrastructure.imagenes.firmas_upload import firmar, verificar
from app.infrastructure.repositories.solicitud_diseno_repository import (
    SolicitudDisenoRepository,
)


def _cabeceras(usuario_id: uuid.UUID) -> dict:
    return {"X-User-Id": str(usuario_id)}


def _crear_usuario(db_sesion, centinela: str) -> UsuarioModel:
    u = UsuarioModel(
        email=f"{centinela}-cotizacion@apolovibes.test",
        password_hash="r0-no-se-usa",
        nombre="R0",
        apellido="Cotizacion",
    )
    db_sesion.add(u)
    db_sesion.commit()
    return u


def _png_bytes() -> bytes:
    img = Image.new("RGB", (10, 10), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_post_cotizacion_valido_crea_fila(client, db_sesion, centinela):
    u = _crear_usuario(db_sesion, centinela)
    try:
        data = {
            "nombre": "Juan Perez",
            "email": "juan@test.cl",
            "telefono": "+56912345678",
            "material": "PLA+",
            "alto": "10",
            "ancho": "5",
            "largo": "3",
            "unidad": "cm",
            "cantidad": "2",
            "uso": "prototipo",
            "color": "Rojo",
            "descripcion": "Tamaño: 10x5x3 cm / Cantidad: 2 / Uso: prototipo / Color: Rojo / Detalles: prueba",
            "imagen": (io.BytesIO(_png_bytes()), "ref.png"),
        }
        resp = client.post(
            "/api/cotizaciones",
            data=data,
            headers=_cabeceras(u.id),
        )
        assert resp.status_code == 201, resp.get_json()
        body = resp.get_json()
        assert body["id"]
        assert body["estado"] == "pendiente"
        fila = db.session.execute(db.text("SELECT usuario_id, material, cantidad, uso, color, alto, ancho, largo FROM solicitudes_diseno WHERE id = :id"), {"id": body["id"]}).fetchone()
        assert fila is not None
        assert str(fila[0]) == str(u.id)
        assert fila[1] == "PLA+"
        assert fila[2] == 2
        assert fila[3] == "prototipo"
        assert fila[4] == "Rojo"
        assert float(fila[5]) == 10.0
        assert float(fila[6]) == 5.0
        assert float(fila[7]) == 3.0
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE id = :id"), {"id": body["id"]})
        db.session.commit()
    finally:
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE usuario_id = :uid"), {"uid": u.id})
        db.session.execute(db.text("DELETE FROM usuarios WHERE id = :uid"), {"uid": u.id})
        db.session.commit()


def test_post_cotizacion_material_no_estoy_seguro(client, db_sesion, centinela):
    u = _crear_usuario(db_sesion, centinela)
    try:
        data = {
            "nombre": "Ana",
            "email": "ana@test.cl",
            "material": "No estoy seguro",
            "descripcion": "Necesito asesoría",
            "cantidad": "1",
            "imagen": (io.BytesIO(_png_bytes()), "ref.png"),
        }
        resp = client.post(
            "/api/cotizaciones",
            data=data,
            headers=_cabeceras(u.id),
        )
        assert resp.status_code == 201, resp.get_json()
        body = resp.get_json()
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE id = :id"), {"id": body["id"]})
        db.session.commit()
    finally:
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE usuario_id = :uid"), {"uid": u.id})
        db.session.execute(db.text("DELETE FROM usuarios WHERE id = :uid"), {"uid": u.id})
        db.session.commit()


def test_post_cotizacion_sin_imagen(client, db_sesion, centinela):
    u = _crear_usuario(db_sesion, centinela)
    try:
        data = {"nombre": "Ana", "email": "ana@test.cl", "material": "PLA", "descripcion": "x"}
        resp = client.post(
            "/api/cotizaciones",
            data=data,
            headers=_cabeceras(u.id),
        )
        assert resp.status_code == 400
    finally:
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE usuario_id = :uid"), {"uid": u.id})
        db.session.execute(db.text("DELETE FROM usuarios WHERE id = :uid"), {"uid": u.id})
        db.session.commit()


def test_post_cotizacion_email_invalido(client, db_sesion, centinela):
    u = _crear_usuario(db_sesion, centinela)
    try:
        data = {"nombre": "Ana", "email": "mal", "material": "PLA", "descripcion": "x", "imagen": (io.BytesIO(_png_bytes()), "ref.png")}
        resp = client.post(
            "/api/cotizaciones",
            data=data,
            headers=_cabeceras(u.id),
        )
        assert resp.status_code == 400
    finally:
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE usuario_id = :uid"), {"uid": u.id})
        db.session.execute(db.text("DELETE FROM usuarios WHERE id = :uid"), {"uid": u.id})
        db.session.commit()


def test_post_cotizacion_alto_no_numerico_o_cantidad_cero(client, db_sesion, centinela):
    u = _crear_usuario(db_sesion, centinela)
    try:
        data = {"nombre": "Ana", "email": "ana@test.cl", "material": "PLA", "descripcion": "x", "alto": "abc", "cantidad": "1", "imagen": (io.BytesIO(_png_bytes()), "ref.png")}
        resp = client.post(
            "/api/cotizaciones",
            data=data,
            headers=_cabeceras(u.id),
        )
        assert resp.status_code == 400

        data2 = {"nombre": "Ana", "email": "ana@test.cl", "material": "PLA", "descripcion": "x", "cantidad": "0", "imagen": (io.BytesIO(_png_bytes()), "ref.png")}
        resp2 = client.post(
            "/api/cotizaciones",
            data=data2,
            headers=_cabeceras(u.id),
        )
        assert resp2.status_code == 400
    finally:
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE usuario_id = :uid"), {"uid": u.id})
        db.session.execute(db.text("DELETE FROM usuarios WHERE id = :uid"), {"uid": u.id})
        db.session.commit()


def test_post_cotizacion_sin_header_x_user_id(client, db_sesion, centinela):
    u = _crear_usuario(db_sesion, centinela)
    try:
        data = {"nombre": "Ana", "email": "ana@test.cl", "material": "PLA", "descripcion": "x", "imagen": (io.BytesIO(_png_bytes()), "ref.png")}
        resp = client.post(
            "/api/cotizaciones",
            data=data,
        )
        assert resp.status_code == 401
    finally:
        db.session.execute(db.text("DELETE FROM solicitudes_diseno WHERE usuario_id = :uid"), {"uid": u.id})
        db.session.execute(db.text("DELETE FROM usuarios WHERE id = :uid"), {"uid": u.id})
        db.session.commit()


# ---------------------------------------------------------------------------
# F1: URLs firmadas de /api/uploads
# ---------------------------------------------------------------------------

def _crear_solicitud(
    db_sesion,
    usuario_id: uuid.UUID,
    *,
    imagen: str | None = None,
    creado_en=None,
) -> uuid.UUID:
    s = SolicitudDisenoModel(
        usuario_id=usuario_id,
        nombre="Juan Perez",
        email="juan@test.cl",
        telefono="+56912345678",
        material="PLA",
        descripcion="prueba de la ruta",
        imagen=imagen,
    )
    if creado_en is not None:
        s.creado_en = creado_en
    db_sesion.add(s)
    db_sesion.commit()
    return s.id


def _limpiar_cotizaciones(db_sesion, usuario_id: uuid.UUID) -> None:
    """Borra pedidos (por cotizacion_id) y solicitudes del usuario del test.

    Los pedidos del usuario de prueba los limpia el teardown si el email es
    `@caracterizacion.test`, pero las solicitudes_diseno no están en la lista
    de residuos: se borran aca, y antes que el usuario por la FK.
    """
    db_sesion.execute(
        db.text(
            "DELETE FROM pedidos WHERE cotizacion_id IN "
            "(SELECT id FROM solicitudes_diseno WHERE usuario_id = :uid)"
        ),
        {"uid": usuario_id},
    )
    db_sesion.execute(
        db.text("DELETE FROM solicitudes_diseno WHERE usuario_id = :uid"),
        {"uid": usuario_id},
    )
    db_sesion.commit()


def _existe_solicitud(solicitud_id: uuid.UUID) -> bool:
    fila = db.session.execute(
        db.text("SELECT 1 FROM solicitudes_diseno WHERE id = :id"),
        {"id": solicitud_id},
    ).fetchone()
    return fila is not None


def _archivo_temporal(tmp_path, nombre: str = "prueba-firma.png"):
    carpeta = tmp_path / "cotizaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / nombre
    archivo.write_bytes(b"png-de-prueba")
    return archivo


def test_uploads_sin_firma_devuelve_403(client, app, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", tmp_path)
    _archivo_temporal(tmp_path)

    resp = client.get("/api/uploads/cotizaciones/prueba-firma.png")

    assert resp.status_code == 403
    assert "error" in resp.get_json()


def test_uploads_con_firma_valida_devuelve_200(client, app, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", tmp_path)
    _archivo_temporal(tmp_path)
    url = firmar("cotizaciones/prueba-firma.png")

    resp = client.get(f"/api/uploads/{url}")

    assert resp.status_code == 200
    assert resp.data == b"png-de-prueba"


def test_uploads_con_firma_expirada_devuelve_403(client, app, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", tmp_path)
    _archivo_temporal(tmp_path)
    exp = str(int(time.time()) - 60)
    secreto = str(app.config["UPLOAD_SIGN_SECRET"])
    sig = hmac.new(
        secreto.encode(),
        f"cotizaciones/prueba-firma.png|{exp}".encode(),
        hashlib.sha256,
    ).hexdigest()

    resp = client.get(
        f"/api/uploads/cotizaciones/prueba-firma.png?exp={exp}&sig={sig}"
    )

    assert resp.status_code == 403


def test_detalle_cotizacion_devuelve_imagen_firmada(client, db_sesion, usuario):
    sid = _crear_solicitud(
        db_sesion, usuario.id, imagen="cotizaciones/firma-detalle.png"
    )
    try:
        resp = client.get(f"/api/cotizaciones/{sid}")
        assert resp.status_code == 200
        imagen = resp.get_json()["imagen"]
        assert imagen.startswith("cotizaciones/firma-detalle.png?")
        assert "exp=" in imagen and "sig=" in imagen
        args = parse_qs(urlparse(imagen).query)
        assert verificar(
            "cotizaciones/firma-detalle.png", args["exp"][0], args["sig"][0]
        ) is True
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_listado_admin_devuelve_imagen_firmada(client, db_sesion, usuario):
    sid = _crear_solicitud(
        db_sesion, usuario.id, imagen="cotizaciones/firma-listado.png"
    )
    try:
        resp = client.get(
            "/api/cotizaciones",
            headers={"X-User-Id": str(usuario.id), "X-User-Rol": "admin"},
        )
        assert resp.status_code == 200
        fila = next(
            (f for f in resp.get_json() if f["id"] == str(sid)), None
        )
        assert fila is not None
        assert "exp=" in fila["imagen"] and "sig=" in fila["imagen"]
        assert fila["imagen"].startswith("cotizaciones/firma-listado.png?")
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


# ---------------------------------------------------------------------------
# F3: purga de 12 meses + borrado manual
# ---------------------------------------------------------------------------

def test_purga_borra_vencida_sin_pedido_y_su_archivo(
    db_sesion, usuario, tmp_path
):
    archivo = _archivo_temporal(tmp_path, "purga-vieja.png")
    antiguo = utcnow() - timedelta(days=400)
    sid = _crear_solicitud(
        db_sesion,
        usuario.id,
        imagen="cotizaciones/purga-vieja.png",
        creado_en=antiguo,
    )
    try:
        res = PurgadorCotizaciones(
            SolicitudDisenoRepository(), carpeta_uploads=tmp_path
        ).ejecutar(edad_dias=365)

        assert res["filas"] >= 1
        assert res["dry_run"] is False
        assert not _existe_solicitud(sid)
        assert not archivo.exists()
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_purga_no_borra_vencida_con_pedido(db_sesion, usuario, tmp_path):
    antiguo = utcnow() - timedelta(days=400)
    sid = _crear_solicitud(
        db_sesion, usuario.id, imagen="cotizaciones/con-pedido.png", creado_en=antiguo
    )
    db.session.add(
        PedidoModel(usuario_id=usuario.id, cotizacion_id=sid, total=0)
    )
    db.session.commit()
    try:
        PurgadorCotizaciones(
            SolicitudDisenoRepository(), carpeta_uploads=tmp_path
        ).ejecutar(edad_dias=365)

        # Relación comercial activa: la fila sobrevive a la purga.
        assert _existe_solicitud(sid)
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_purga_dry_run_no_borra_nada(db_sesion, usuario, tmp_path):
    archivo = _archivo_temporal(tmp_path, "dry-run.png")
    antiguo = utcnow() - timedelta(days=400)
    sid = _crear_solicitud(
        db_sesion,
        usuario.id,
        imagen="cotizaciones/dry-run.png",
        creado_en=antiguo,
    )
    try:
        res = PurgadorCotizaciones(
            SolicitudDisenoRepository(), carpeta_uploads=tmp_path
        ).ejecutar(edad_dias=365, dry_run=True)

        assert res["dry_run"] is True
        assert res["filas"] >= 1
        assert _existe_solicitud(sid)
        assert archivo.exists()
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_purga_limpia_huerfanos_viejos(db_sesion, usuario, tmp_path):
    carpeta = tmp_path / "cotizaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    marca_vieja = time.time() - 400 * 86400

    huerfano_viejo = carpeta / "huerfano-viejo.png"
    huerfano_viejo.write_bytes(b"x")
    os.utime(huerfano_viejo, (marca_vieja, marca_vieja))

    huerfano_nuevo = carpeta / "huerfano-nuevo.png"
    huerfano_nuevo.write_bytes(b"x")

    # Mtime viejo pero referenciado por una fila vigente: no es huérfano.
    referenciada = carpeta / "referenciada.png"
    referenciada.write_bytes(b"x")
    os.utime(referenciada, (marca_vieja, marca_vieja))
    sid = _crear_solicitud(
        db_sesion, usuario.id, imagen="cotizaciones/referenciada.png"
    )
    try:
        res = PurgadorCotizaciones(
            SolicitudDisenoRepository(), carpeta_uploads=tmp_path
        ).ejecutar(edad_dias=365)

        assert res["huerfanos"] == 1
        assert not huerfano_viejo.exists()
        assert huerfano_nuevo.exists()
        assert referenciada.exists()
        assert _existe_solicitud(sid)
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_purgar_endpoint_sin_secreto_devuelve_503(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "CRON_SECRET", "")

    resp = client.post("/api/admin/cotizaciones/purgar")

    assert resp.status_code == 503


def test_purgar_endpoint_con_secreto_correcto(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "CRON_SECRET", "secreto-cron-test")

    resp = client.post(
        "/api/admin/cotizaciones/purgar?dry_run=1",
        headers={"X-Cron-Secret": "secreto-cron-test"},
    )

    assert resp.status_code == 200
    cuerpo = resp.get_json()
    assert cuerpo["dry_run"] is True
    assert {"filas", "archivos", "huerfanos", "dry_run"} <= set(cuerpo)


def test_purgar_endpoint_header_invalido_devuelve_401(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "CRON_SECRET", "secreto-cron-test")

    resp = client.post(
        "/api/admin/cotizaciones/purgar?dry_run=1",
        headers={"X-Cron-Secret": "otro-secreto"},
    )

    assert resp.status_code == 401


def test_delete_cotizacion_como_admin_borra(client, db_sesion, usuario, centinela):
    imagen = f"cotizaciones/delete-{centinela}.png"
    sid = _crear_solicitud(db_sesion, usuario.id, imagen=imagen)
    cabeceras = {"X-User-Id": str(usuario.id), "X-User-Rol": "admin"}
    try:
        resp = client.delete(f"/api/cotizaciones/{sid}", headers=cabeceras)

        assert resp.status_code == 200
        cuerpo = resp.get_json()
        assert cuerpo["ok"] is True
        assert cuerpo["id"] == str(sid)
        assert not _existe_solicitud(sid)
    finally:
        # Si el endpoint falló antes de borrar, la fila no debe quedar huérfana.
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_delete_cotizacion_requiere_rol_admin(client, db_sesion, usuario):
    sid = _crear_solicitud(db_sesion, usuario.id)
    try:
        resp = client.delete(
            f"/api/cotizaciones/{sid}",
            headers={"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"},
        )
        assert resp.status_code == 403

        resp_anonimo = client.delete(f"/api/cotizaciones/{sid}")
        assert resp_anonimo.status_code == 403

        # Ninguno de los dos tocó la fila.
        assert _existe_solicitud(sid)
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_delete_cotizacion_con_pedido_devuelve_409(client, db_sesion, usuario):
    sid = _crear_solicitud(db_sesion, usuario.id, imagen=None)
    db.session.add(
        PedidoModel(usuario_id=usuario.id, cotizacion_id=sid, total=0)
    )
    db.session.commit()
    try:
        resp = client.delete(
            f"/api/cotizaciones/{sid}",
            headers={"X-User-Id": str(usuario.id), "X-User-Rol": "admin"},
        )

        assert resp.status_code == 409
        assert _existe_solicitud(sid)
    finally:
        _limpiar_cotizaciones(db_sesion, usuario.id)


def test_delete_cotizacion_inexistente_devuelve_404(client, db_sesion, usuario):
    resp = client.delete(
        f"/api/cotizaciones/{uuid.uuid4()}",
        headers={"X-User-Id": str(usuario.id), "X-User-Rol": "admin"},
    )

    assert resp.status_code == 404
