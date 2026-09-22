-- Migracion: tablas de pedidos, pagos y detalle_pedidos (transaccion de compra)
-- Ejecutar desde la raiz del proyecto:
--   Oracle:   sqlplus user/pass@DSN @migrations/crear_tablas_pedidos.sql
--   Postgres: psql -U app -d print3d_dev -f migrations/crear_tablas_pedidos.sql
--
-- Las claves son UUIDs en RAW(16) (Oracle) / UUID (Postgres), igual que las
-- tablas `usuarios`/`productos` existentes. La columna `direccion_envio`
-- guarda el JSON de datos del cliente/direccion (CLOB/TEXT).

-- ============ Oracle (RAW(16), VARCHAR2, TIMESTAMP) ============

CREATE TABLE pedidos (
    id              RAW(16)     PRIMARY KEY,
    usuario_id      RAW(16)     NOT NULL REFERENCES usuarios(id),
    estado          VARCHAR2(30) DEFAULT 'pendiente' NOT NULL,
    total           NUMBER(10,0) DEFAULT 0 NOT NULL,
    direccion_envio CLOB,
    creado_en       TIMESTAMP   DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE pagos (
    id         RAW(16)      PRIMARY KEY,
    pedido_id  RAW(16)      NOT NULL REFERENCES pedidos(id),
    monto      NUMBER(10,0) NOT NULL,
    proveedor  VARCHAR2(50) NOT NULL,
    token      VARCHAR2(255),
    estado     VARCHAR2(30) DEFAULT 'pendiente' NOT NULL,
    creado_en  TIMESTAMP    DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE detalle_pedidos (
    id              RAW(16)      PRIMARY KEY,
    pedido_id       RAW(16)      NOT NULL REFERENCES pedidos(id),
    producto_id     RAW(16)      NOT NULL REFERENCES productos(id),
    cantidad        NUMBER(10,0) NOT NULL,
    precio_unitario NUMBER(10,0) NOT NULL
);

CREATE INDEX idx_detalle_pedidos_pedido ON detalle_pedidos (pedido_id);

-- ============ PostgreSQL (equivalente con UUID/TEXT) ============

-- CREATE TABLE pedidos (
--     id              UUID         PRIMARY KEY,
--     usuario_id      UUID         NOT NULL REFERENCES usuarios(id),
--     estado          VARCHAR(30)  DEFAULT 'pendiente' NOT NULL,
--     total           INTEGER      DEFAULT 0 NOT NULL,
--     direccion_envio TEXT,
--     creado_en       TIMESTAMP    DEFAULT now() NOT NULL
-- );
--
-- CREATE TABLE pagos (
--     id         UUID         PRIMARY KEY,
--     pedido_id  UUID         NOT NULL REFERENCES pedidos(id),
--     monto      INTEGER      NOT NULL,
--     proveedor  VARCHAR(50)  NOT NULL,
--     token      VARCHAR(255),
--     estado     VARCHAR(30)  DEFAULT 'pendiente' NOT NULL,
--     creado_en  TIMESTAMP    DEFAULT now() NOT NULL
-- );
--
-- CREATE TABLE detalle_pedidos (
--     id              UUID         PRIMARY KEY,
--     pedido_id       UUID         NOT NULL REFERENCES pedidos(id),
--     producto_id     UUID         NOT NULL REFERENCES productos(id),
--     cantidad        INTEGER      NOT NULL,
--     precio_unitario INTEGER      NOT NULL
-- );
--
-- CREATE INDEX idx_detalle_pedidos_pedido ON detalle_pedidos (pedido_id);