ALTER TABLE productos ADD (
    stock_minimo            NUMBER,
    aviso_stock_enviado     NUMBER(1) DEFAULT 0 NOT NULL
);