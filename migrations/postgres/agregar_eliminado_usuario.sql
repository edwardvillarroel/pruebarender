
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS eliminado_en timestamptz;

CREATE INDEX IF NOT EXISTS idx_usuarios_eliminado_en ON usuarios (eliminado_en);
