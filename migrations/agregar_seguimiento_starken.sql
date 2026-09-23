-- Migracion ADITIVA: seguimiento Starken sobre `pedidos`
-- Ejecutar desde la raiz del proyecto:
--   Oracle:   sqlplus user/pass@DSN @migrations/agregar_seguimiento_starken.sql
--   Postgres: psql -U app -d print3d_dev -f migrations/agregar_seguimiento_starken.sql
--
-- Solo agrega columnas; no elimina tablas ni datos. `codigo_seguimiento` es la
-- Orden de Flete (OF) que Starken entrega al despachar. `estado_seguimiento`
-- guarda el ultimo estado sincronizado desde la API (vista off-line); la
-- consulta en vivo se hace contra la API de developers.starken.cl.

-- ============ Oracle ============

ALTER TABLE pedidos ADD (
    codigo_seguimiento           VARCHAR2(50),
    estado_seguimiento           VARCHAR2(100),
    seguimiento_actualizado_en   TIMESTAMP
);

-- ============ PostgreSQL (equivalente) ============

-- ALTER TABLE pedidos
--     ADD COLUMN codigo_seguimiento         VARCHAR(50),
--     ADD COLUMN estado_seguimiento         VARCHAR(100),
--     ADD COLUMN seguimiento_actualizado_en TIMESTAMP;