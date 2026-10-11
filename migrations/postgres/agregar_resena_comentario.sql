-- Comentario escrito (opcional) de una resena. Idempotente.
ALTER TABLE resenas ADD COLUMN IF NOT EXISTS comentario text;
