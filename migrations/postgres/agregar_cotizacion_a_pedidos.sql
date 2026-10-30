
ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS cotizacion_id uuid;

ALTER TABLE detalle_pedidos
    ALTER COLUMN producto_id DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_pedido_cotizacion'
          AND conrelid = 'pedidos'::regclass
    ) THEN
        ALTER TABLE pedidos
            ADD CONSTRAINT fk_pedido_cotizacion
            FOREIGN KEY (cotizacion_id) REFERENCES solicitudes_diseno (id);
    END IF;
END
$$;


CREATE UNIQUE INDEX IF NOT EXISTS idx_pedidos_cotizacion
    ON pedidos (cotizacion_id)
    WHERE cotizacion_id IS NOT NULL;
