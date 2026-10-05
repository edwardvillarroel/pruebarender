
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS clave_idempotencia varchar(100);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS url_intento varchar(500);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pago_idempotencia
    ON pagos (clave_idempotencia)
    WHERE clave_idempotencia IS NOT NULL
      AND estado = 'pendiente';