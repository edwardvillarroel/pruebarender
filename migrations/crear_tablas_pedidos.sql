

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

