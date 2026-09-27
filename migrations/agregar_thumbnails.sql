-- Migracion: thumbnails de imagenes de producto y de color
-- Ejecutar desde la raiz del proyecto:
--   Oracle: sqlplus user/pass@DSN @migrations/agregar_thumbnails.sql
--
-- El catalogo mostraba cada foto en una tarjeta de ~240px descargando el
-- archivo completo: 43 MB para 18 productos (2,4 MB en promedio, 3,5 MB el
-- peor caso). Estas columnas guardan una version reducida para la grilla,
-- mientras `imagen_bytes` sigue siendo la foto original en resolucion
-- completa para la vista de detalle.
--
-- No hay backfill: el thumbnail se genera perezosamente en el primer request
-- que lo pide y queda cacheado en la columna. Por eso el script solo agrega
-- las columnas y no toca los 18 productos existentes.

-- ---------------------------------------------------------------------------
-- productos.imagen_thumb_*
-- ---------------------------------------------------------------------------
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_tab_columns
    WHERE table_name = 'PRODUCTOS'
      AND column_name = 'IMAGEN_THUMB_BYTES';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE productos ADD (imagen_thumb_bytes BLOB)';
        DBMS_OUTPUT.PUT_LINE('productos.imagen_thumb_bytes agregada');
    ELSE
        DBMS_OUTPUT.PUT_LINE('productos.imagen_thumb_bytes ya existia');
    END IF;

    SELECT COUNT(*) INTO v_count
    FROM user_tab_columns
    WHERE table_name = 'PRODUCTOS'
      AND column_name = 'IMAGEN_THUMB_CONTENT_TYPE';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE productos ADD (imagen_thumb_content_type VARCHAR2(50))';
        DBMS_OUTPUT.PUT_LINE('productos.imagen_thumb_content_type agregada');
    ELSE
        DBMS_OUTPUT.PUT_LINE('productos.imagen_thumb_content_type ya existia');
    END IF;
END;
/

-- ---------------------------------------------------------------------------
-- producto_colores.imagen_thumb_*
-- ---------------------------------------------------------------------------
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_tab_columns
    WHERE table_name = 'PRODUCTO_COLORES'
      AND column_name = 'IMAGEN_THUMB_BYTES';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE producto_colores ADD (imagen_thumb_bytes BLOB)';
        DBMS_OUTPUT.PUT_LINE('producto_colores.imagen_thumb_bytes agregada');
    ELSE
        DBMS_OUTPUT.PUT_LINE('producto_colores.imagen_thumb_bytes ya existia');
    END IF;

    SELECT COUNT(*) INTO v_count
    FROM user_tab_columns
    WHERE table_name = 'PRODUCTO_COLORES'
      AND column_name = 'IMAGEN_THUMB_CONTENT_TYPE';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE producto_colores ADD (imagen_thumb_content_type VARCHAR2(50))';
        DBMS_OUTPUT.PUT_LINE('producto_colores.imagen_thumb_content_type agregada');
    ELSE
        DBMS_OUTPUT.PUT_LINE('producto_colores.imagen_thumb_content_type ya existia');
    END IF;
END;
/

-- Verificacion. Ojo: en Oracle no se puede COUNT() sobre un BLOB; hay que
-- medirlo con LENGTH(), que devuelve el tamano en bytes.
SELECT 'productos' AS tabla,
       COUNT(*) AS con_foto,
       SUM(CASE WHEN LENGTH(imagen_thumb_bytes) > 0 THEN 1 ELSE 0 END) AS con_thumb
FROM productos
WHERE imagen_bytes IS NOT NULL
UNION ALL
SELECT 'producto_colores',
       COUNT(*),
       SUM(CASE WHEN LENGTH(imagen_thumb_bytes) > 0 THEN 1 ELSE 0 END)
FROM producto_colores
WHERE imagen_bytes IS NOT NULL;
