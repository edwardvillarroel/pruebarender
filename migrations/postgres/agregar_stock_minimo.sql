ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS stock_minimo numeric;

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS aviso_stock_enviado boolean DEFAULT false NOT NULL;