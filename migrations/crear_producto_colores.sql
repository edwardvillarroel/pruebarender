-- Migracion: colores por producto (una imagen por color) + color en carrito y pedido
-- Ejecutar desde la raiz del proyecto:
--   Oracle: sqlplus user/pass@DSN @migrations/crear_producto_colores.sql
--
-- Un producto puede tener N colores y cada uno tiene su propia imagen. En el
-- detalle el cliente elige el color y la foto cambia antes de agregar al
-- carrito. El color elegido queda registrado en la linea del carrito y en el
-- detalle del pedido para que la impresora sepa que pintar.
--
-- Los productos SIN colores siguen funcionando exactamente igual que hoy,
-- usando la imagen unica de productos.imagen_bytes.

-- ---------------------------------------------------------------------------
-- Tabla producto_colores
-- ---------------------------------------------------------------------------
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_tables
    WHERE table_name = 'PRODUCTO_COLORES';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE '
            CREATE TABLE producto_colores (
                id                  RAW(16) NOT NULL,
                producto_id         RAW(16) NOT NULL,
                nombre              VARCHAR2(50) NOT NULL,
                imagen_bytes        BLOB,
                imagen_content_type VARCHAR2(50),
                orden               NUMBER(10) DEFAULT 0 NOT NULL,
                creado_en           TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                CONSTRAINT pk_producto_colores PRIMARY KEY (id),
                CONSTRAINT fk_producto_colores_producto
                    FOREIGN KEY (producto_id) REFERENCES productos (id)
            )';
        EXECUTE IMMEDIATE
            'CREATE INDEX ix_producto_colores_producto ON producto_colores (producto_id)';
        EXECUTE IMMEDIATE
            'CREATE UNIQUE INDEX ux_producto_colores_nombre ON producto_colores (producto_id, nombre)';
    END IF;
END;
/

-- ---------------------------------------------------------------------------
-- Color elegido en la linea del carrito
-- ---------------------------------------------------------------------------
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_tab_columns
    WHERE table_name = 'CARRITO_ITEMS' AND column_name = 'COLOR';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE carrito_items ADD color VARCHAR2(50)';
    END IF;
END;
/

-- ---------------------------------------------------------------------------
-- La unicidad por producto debe incluir el color
--
-- carrito_items tenia UQ_CARRITO_ITEM_PRODUCTO UNIQUE (carrito_id, producto_id),
-- creada antes de que existieran los colores. Con esa restriccion el mismo
-- producto no puede tener dos lineas, asi que agregar el mismo producto en dos
-- colores falla con ORA-00001 y el carrito queda con una sola linea.
--
-- Se reemplaza por un indice unico sobre (carrito_id, producto_id, color).
-- El NVL es necesario porque en Oracle NULL no es igual a NULL en un indice
-- unico: sin el, un producto sin color podria repetirse ilimitadamente. Con
-- NVL(color, ' ') dos lineas sin color siguen chocando, que es lo que quiere
-- la regla de negocio (mismo producto + mismo color = una sola linea).
-- ---------------------------------------------------------------------------
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_constraints
    WHERE constraint_name = 'UQ_CARRITO_ITEM_PRODUCTO'
      AND table_name = 'CARRITO_ITEMS'
      AND constraint_type = 'U';

    IF v_count > 0 THEN
        EXECUTE IMMEDIATE
            'ALTER TABLE carrito_items DROP CONSTRAINT UQ_CARRITO_ITEM_PRODUCTO';
    END IF;
END;
/

DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_indexes
    WHERE index_name = 'UX_CARRITO_ITEM_PRODUCTO_COLOR';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE
            'CREATE UNIQUE INDEX ux_carrito_item_producto_color ON carrito_items (carrito_id, producto_id, NVL(color, '' ''))';
    END IF;
END;
/

-- ---------------------------------------------------------------------------
-- Color elegido en el detalle del pedido
-- ---------------------------------------------------------------------------
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_tab_columns
    WHERE table_name = 'DETALLE_PEDIDOS' AND column_name = 'COLOR';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE detalle_pedidos ADD color VARCHAR2(50)';
    END IF;
END;
/
