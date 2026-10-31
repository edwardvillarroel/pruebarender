
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS password_configurada boolean NOT NULL DEFAULT true;


UPDATE usuarios u
SET password_configurada = false
WHERE u.auth_provider = 'google'
  AND u.google_sub IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM logs_seguridad l
      WHERE l.user_id = u.id::text
        AND l.evento IN ('registro_ok', 'password_reset', 'cambio_pass_ok')
  );
