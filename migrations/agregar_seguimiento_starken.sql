

ALTER TABLE pedidos ADD (
    codigo_seguimiento           VARCHAR2(50),
    estado_seguimiento           VARCHAR2(100),
    seguimiento_actualizado_en   TIMESTAMP
);
