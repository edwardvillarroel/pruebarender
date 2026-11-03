ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS aviso_stock_notificado_en timestamptz;
