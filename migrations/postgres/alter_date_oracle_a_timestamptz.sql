
ALTER TABLE sesiones_venta
    ALTER COLUMN fecha      TYPE date,
    ALTER COLUMN creado_en  TYPE timestamptz,
    ALTER COLUMN cerrada_en TYPE timestamptz;

ALTER TABLE ventas_local
    ALTER COLUMN creado_en  TYPE timestamptz;

ALTER TABLE sesiones_venta ALTER COLUMN creado_en DROP DEFAULT;
ALTER TABLE ventas_local   ALTER COLUMN creado_en DROP DEFAULT;