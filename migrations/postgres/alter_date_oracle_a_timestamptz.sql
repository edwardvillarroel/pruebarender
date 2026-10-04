-- Correccion de R1: Oracle DATE no es lo mismo que Postgres date.
--
-- Oracle DATE (7 bytes) guarda fecha Y hora hasta segundos. Postgres date solo
-- guarda el dia. El conversor no tenia regla para DATE, asi que el tipo pasaba
-- intacto, Postgres lo aceptaba como date y truncaba la hora en silencio: sin
-- error de sintaxis, sin aviso.
--
-- Impacto verificado contra Oracle: de las 4 columnas DATE del schema,
-- 3 tenian hora real en el 100% de las filas (sesiones_venta.creado_en 9/9,
-- sesiones_venta.cerrada_en 9/9, ventas_local.creado_en 8/8).
-- sesiones_venta.fecha si es fecha pura (0/9) y se queda en date.
--
-- Ademas del historico migrado, el truncate-automatico afectaba a cada venta
-- local nueva: la app escribe datetime.utcnow() y Postgres cortaba a medianoche.
--
-- Idempotente: usar en bases ya creadas con el schema anterior.

ALTER TABLE sesiones_venta
    ALTER COLUMN fecha      TYPE date,
    ALTER COLUMN creado_en  TYPE timestamptz,
    ALTER COLUMN cerrada_en TYPE timestamptz;

ALTER TABLE ventas_local
    ALTER COLUMN creado_en  TYPE timestamptz;

-- La columna queda sin DEFAULT: el default la pone el ORM (datetime.utcnow).
ALTER TABLE sesiones_venta ALTER COLUMN creado_en DROP DEFAULT;
ALTER TABLE ventas_local   ALTER COLUMN creado_en DROP DEFAULT;