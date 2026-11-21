-- FASE 3 - Normalizar `solicitudes_diseno`: PII vive en `usuarios`
-- Ejecutar en Supabase SQL Editor. Revisar paso 3 antes de borrar columnas.

-- 1. Asegurar columna usuario_id
ALTER TABLE solicitudes_diseno ADD COLUMN IF NOT EXISTS usuario_id uuid;

-- 2. Rellenar usuario_id buscando por email (para filas históricas)
UPDATE solicitudes_diseno s
SET usuario_id = u.id
FROM usuarios u
WHERE s.email = u.email
  AND s.usuario_id IS NULL;

-- 3. Revisar las que quedaron sin dueño (cotizaciones de invitados / email no coincide).
--    Estas se mantienen con usuario_id NULL para no perder historial.
-- SELECT COUNT(*) FROM solicitudes_diseno WHERE usuario_id IS NULL;

-- 4. Permitir NULL para ON DELETE SET NULL y recrear FK
ALTER TABLE solicitudes_diseno ALTER COLUMN usuario_id DROP NOT NULL;

ALTER TABLE solicitudes_diseno DROP CONSTRAINT IF EXISTS fk_solicitudes_usuario;
ALTER TABLE solicitudes_diseno DROP CONSTRAINT IF EXISTS fk_solicitud_usuario;
ALTER TABLE solicitudes_diseno
  ADD CONSTRAINT fk_solicitudes_usuario
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
  ON DELETE SET NULL;

-- 5. Borrar PII duplicada (ejecutar solo cuando el paso 3 esté verificado)
ALTER TABLE solicitudes_diseno DROP COLUMN IF EXISTS nombre;
ALTER TABLE solicitudes_diseno DROP COLUMN IF EXISTS email;
ALTER TABLE solicitudes_diseno DROP COLUMN IF EXISTS telefono;

-- Verificación:
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'solicitudes_diseno'
--   AND column_name IN ('nombre','email','telefono','usuario_id');
-- Debe salir solo usuario_id.
