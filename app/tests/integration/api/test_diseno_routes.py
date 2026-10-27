from __future__ import annotations

import io
import uuid

from PIL import Image

from app.infrastructure.database.connection import db
from app.infrastructure.database.models.usuario_model import UsuarioModel


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
