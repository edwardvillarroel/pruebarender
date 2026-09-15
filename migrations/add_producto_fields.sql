-- Migracion: agregar campos faltantes a productos
-- Ejecutar desde la raiz del proyecto:
--   Oracle: sqlplus user/pass@DSN @migrations/add_producto_fields.sql
--   Postgres: psql -U app -d print3d_dev -f migrations/add_producto_fields.sql

-- Oracle: verificar y agregar columnas
-- PostgreSQL: usar IF NOT EXISTS (soportado desde v9.6)

ALTER TABLE productos ADD specs TEXT NULL;
ALTER TABLE productos ADD descuento INTEGER NULL;
ALTER TABLE productos ADD badge VARCHAR(50) NULL;
ALTER TABLE productos ADD precio_original INTEGER NULL;
ALTER TABLE productos ADD rating INTEGER NULL;
