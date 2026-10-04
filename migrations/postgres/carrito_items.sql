-- CARRITO_ITEMS: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE CARRITO_ITEMS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	CARRITO_ID uuid NOT NULL , 
	PRODUCTO_ID uuid NOT NULL , 
	CANTIDAD numeric DEFAULT 1 NOT NULL , 
	AGREGADO_EN timestamptz DEFAULT now() NOT NULL , 
	COLOR varchar(50) , 
	 CHECK (cantidad > 0) , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_CARRITO_ITEM_CARRITO FOREIGN KEY (CARRITO_ID)
	  REFERENCES CARRITO (ID) , 
	 CONSTRAINT FK_CARRITO_ITEM_PRODUCTO FOREIGN KEY (PRODUCTO_ID)
	  REFERENCES PRODUCTOS (ID) 
   );

ALTER TABLE carrito_items ADD CONSTRAINT ck_carrito_items_color_vacio CHECK (color IS NULL OR color <> '');
CREATE INDEX IF NOT EXISTS idx_carrito_item_producto ON carrito_items (producto_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_carrito_item_producto_color ON carrito_items (carrito_id, producto_id, color) NULLS NOT DISTINCT;
