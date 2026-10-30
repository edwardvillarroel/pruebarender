-- Soft delete de usuarios del panel de administracion.
--
-- Aditivo e idempotente: no borra filas ni modifica datos existentes.
-- `eliminado_en IS NULL` = cuenta viva. Las cuentas eliminadas dejan de
-- aparecer en el panel y no pueden iniciar sesion, pero la fila se conserva
-- porque `pedidos`, `solicitudes_diseno`, `resenas` y `cupones` la referencian
-- con FOREIGN KEY.
--
-- El bloqueo de una cuenta (reversible) NO usa esta columna: usa `activo`.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS eliminado_en timestamptz;

CREATE INDEX IF NOT EXISTS idx_usuarios_eliminado_en ON usuarios (eliminado_en);
