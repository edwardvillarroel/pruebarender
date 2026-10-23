ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS subtotal numeric(10,2),
    ADD COLUMN IF NOT EXISTS descuento_productos numeric(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS descuento_cupon numeric(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cupon_codigo varchar(30);

ALTER TABLE detalle_pedidos
    ADD COLUMN IF NOT EXISTS precio_original numeric(10,2);
