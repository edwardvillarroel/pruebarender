"""Script one-off: crea SOLO las tablas de venta local si no existen.

Uso: `.venv\\Scripts\\python.exe crear_tablas_ventas_local.py` (desde la raíz
del repo, con la BD apuntada por `.env`).

Nota: se usa SQL crudo con RAW(16) para las claves UUID, igual que el
resto del esquema manual del repo. `create_all` no sirve aquí porque
`UuidRaw` compila a BLOB en Oracle y Oracle no permite FK BLOB -> RAW(16).
"""

from sqlalchemy import text

from app import create_app
from app.infrastructure.database.connection import db

DDL = [
    """CREATE TABLE sesiones_venta (
        id RAW(16) NOT NULL,
        lugar VARCHAR2(150 CHAR) NOT NULL,
        fecha DATE NOT NULL,
        estado VARCHAR2(20 CHAR) NOT NULL,
        usuario_id RAW(16) NOT NULL,
        creado_en DATE NOT NULL,
        cerrada_en DATE NULL,
        CONSTRAINT pk_sesiones_venta PRIMARY KEY (id),
        CONSTRAINT fk_sesiones_venta_usuario FOREIGN KEY (usuario_id)
            REFERENCES usuarios (id)
    )""",
    """CREATE TABLE ventas_local (
        id RAW(16) NOT NULL,
        sesion_id RAW(16) NOT NULL,
        medio_pago VARCHAR2(20 CHAR) NOT NULL,
        total NUMBER(19, 0) NOT NULL,
        creado_en DATE NOT NULL,
        CONSTRAINT pk_ventas_local PRIMARY KEY (id),
        CONSTRAINT fk_ventas_local_sesion FOREIGN KEY (sesion_id)
            REFERENCES sesiones_venta (id)
    )""",
    """CREATE TABLE venta_local_items (
        id RAW(16) NOT NULL,
        venta_id RAW(16) NOT NULL,
        producto_id RAW(16) NOT NULL,
        nombre VARCHAR2(200 CHAR) NOT NULL,
        cantidad NUMBER(19, 0) NOT NULL,
        precio_unitario NUMBER(19, 0) NOT NULL,
        CONSTRAINT pk_venta_local_items PRIMARY KEY (id),
        CONSTRAINT fk_items_venta FOREIGN KEY (venta_id)
            REFERENCES ventas_local (id),
        CONSTRAINT fk_items_producto FOREIGN KEY (producto_id)
            REFERENCES productos (id)
    )""",
    "CREATE INDEX ix_sesiones_venta_usuario ON sesiones_venta (usuario_id)",
    "CREATE INDEX ix_ventas_local_sesion ON ventas_local (sesion_id)",
    "CREATE INDEX ix_items_venta ON venta_local_items (venta_id)",
    "CREATE INDEX ix_items_producto ON venta_local_items (producto_id)",
]

app = create_app()
with app.app_context():
    creadas = []
    with db.engine.begin() as conn:
        for sentencia in DDL:
            nombre = sentencia.split()[2]
            existe = conn.execute(
                text(
                    "SELECT COUNT(*) FROM user_tables "
                    "WHERE table_name = UPPER(:nombre)"
                ),
                {"nombre": nombre},
            ).scalar()
            if existe:
                continue
            conn.execute(text(sentencia))
            creadas.append(nombre)
    print("Tablas de venta local creadas:", creadas or "(ninguna, ya existían)")