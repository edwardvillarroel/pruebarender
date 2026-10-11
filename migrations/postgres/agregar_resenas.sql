-- Reseñas de producto (estrellas 1-5) por pedido entregado.
-- Idempotente: se puede re-ejecutar sin error (patrón de los increments).

CREATE TABLE IF NOT EXISTS resenas (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id uuid NOT NULL REFERENCES usuarios (id),
    pedido_id uuid NOT NULL REFERENCES pedidos (id),
    producto_id uuid NOT NULL REFERENCES productos (id),
    estrellas numeric NOT NULL CHECK (estrellas >= 1 AND estrellas <= 5),
    comentario text,
    creado_en timestamptz DEFAULT now() NOT NULL,
    actualizado_en timestamptz,
    UNIQUE (usuario_id, pedido_id, producto_id)
);

CREATE INDEX IF NOT EXISTS idx_resenas_producto ON resenas (producto_id);
CREATE INDEX IF NOT EXISTS idx_resenas_pedido ON resenas (pedido_id);

-- `rating` NO se altera: el DDL base ya lo define como numeric. Solo se
-- alinea el ORM a Numeric(3,1). El contador denormalizado es nuevo.
ALTER TABLE productos ADD COLUMN IF NOT EXISTS resenas_count integer NOT NULL DEFAULT 0;
