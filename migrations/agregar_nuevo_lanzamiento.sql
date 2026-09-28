-- Migracion: marcar productos como "nuevo lanzamiento"
-- El flag lo activa el admin desde el modal de producto y la seccion
-- "Lanzamientos" de la home muestra solo los que lo tienen.
-- Ejecutar desde la raiz del proyecto:
--   Oracle: sqlplus user/pass@DSN @migrations/agregar_nuevo_lanzamiento.sql
--   Postgres: psql -U app -d print3d_dev -f migrations/agregar_nuevo_lanzamiento.sql
--
-- El DEFAULT 0 con NOT NULL hace el backfill de las filas existentes: en Oracle
-- agregar una columna NOT NULL con DEFAULT completa la tabla con ese valor, asi
-- que no hace falta un UPDATE aparte.

-- Oracle: NUMBER(1) es el tipo booleano que ya usa productos.activo
ALTER TABLE productos ADD nuevo_lanzamiento NUMBER(1) DEFAULT 0 NOT NULL;

-- PostgreSQL: usar IF NOT EXISTS (soportado desde v9.6)
-- ALTER TABLE productos ADD COLUMN IF NOT EXISTS nuevo_lanzamiento BOOLEAN NOT NULL DEFAULT FALSE;
