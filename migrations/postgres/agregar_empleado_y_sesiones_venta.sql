-- Rol «empleado» y propiedad/auditoría de las ventas locales.
--
-- Idempotente: se puede volver a correr. No borra ni modifica sesiones
-- históricas (hay un usuario con 9 sesiones cerradas el mismo día en producción).
--
-- La regla «una sesión por usuario y día» se aplica en tres capas:
--   1. servicio: rechaza cualquier sesión previa del día, abierta o cerrada;
--   2. índice parcial: evita dos sesiones abiertas simultáneas;
--   3. trigger: evita nuevas inserciones repetidas sin tocar el histórico.

BEGIN;

-- 1. El CHECK de producción se llama usuarios_rol_check (verificado).
ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check;
ALTER TABLE usuarios
    ADD CONSTRAINT usuarios_rol_check
    CHECK (rol IN ('admin', 'cliente', 'empleado'));

-- 2. Auditoría: quién registró cada venta. Las filas antiguas se completan
--    desde la sesión a la que pertenecen.
ALTER TABLE ventas_local ADD COLUMN IF NOT EXISTS usuario_id uuid;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_ventas_local_usuario'
    ) THEN
        ALTER TABLE ventas_local
            ADD CONSTRAINT fk_ventas_local_usuario
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_ventas_local_usuario ON ventas_local (usuario_id);

UPDATE ventas_local v
   SET usuario_id = s.usuario_id
  FROM sesiones_venta s
 WHERE v.sesion_id = s.id
   AND v.usuario_id IS NULL;

-- 3. Una sesión abierta por usuario y día (el histórico tiene duplicados
--    cerrados, por eso el índice es parcial).
CREATE UNIQUE INDEX IF NOT EXISTS uq_sesiones_venta_abierta_usuario_fecha
    ON sesiones_venta (usuario_id, fecha)
    WHERE estado = 'abierta';

CREATE OR REPLACE FUNCTION evitar_sesion_venta_repetida_dia()
RETURNS trigger AS $$
BEGIN
    -- Serializa inserciones concurrentes del mismo usuario/día.
    PERFORM pg_advisory_xact_lock(hashtext(NEW.usuario_id::text || NEW.fecha::text));

    IF EXISTS (
        SELECT 1
          FROM sesiones_venta
         WHERE usuario_id = NEW.usuario_id
           AND fecha = NEW.fecha
    ) THEN
        RAISE EXCEPTION 'Ya existe una sesión de venta para este usuario y fecha'
            USING ERRCODE = 'unique_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sesiones_venta_unica_por_dia ON sesiones_venta;
CREATE TRIGGER trg_sesiones_venta_unica_por_dia
    BEFORE INSERT ON sesiones_venta
    FOR EACH ROW
    EXECUTE FUNCTION evitar_sesion_venta_repetida_dia();

COMMIT;
