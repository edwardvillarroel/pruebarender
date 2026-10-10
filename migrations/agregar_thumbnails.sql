
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


-- producto_colores.imagen_thumb_*
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
