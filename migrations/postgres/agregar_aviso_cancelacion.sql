ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS aviso_cancelacion_en timestamptz;

ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS aviso_cancelacion_visto boolean DEFAULT false NOT NULL;
