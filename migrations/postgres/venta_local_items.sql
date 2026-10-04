-- VENTA_LOCAL_ITEMS: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE VENTA_LOCAL_ITEMS 
   (	ID uuid NOT NULL , 
	VENTA_ID uuid NOT NULL , 
	PRODUCTO_ID uuid NOT NULL , 
	NOMBRE varchar(200)  NOT NULL , 
	CANTIDAD bigint NOT NULL , 
	PRECIO_UNITARIO bigint NOT NULL , 
	 CONSTRAINT PK_VENTA_LOCAL_ITEMS PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_ITEMS_VENTA FOREIGN KEY (VENTA_ID)
	  REFERENCES VENTAS_LOCAL (ID) , 
	 CONSTRAINT FK_ITEMS_PRODUCTO FOREIGN KEY (PRODUCTO_ID)
	  REFERENCES PRODUCTOS (ID) 
   );

CREATE INDEX IF NOT EXISTS ix_items_producto ON venta_local_items (producto_id);
CREATE INDEX IF NOT EXISTS ix_items_venta ON venta_local_items (venta_id);
CREATE UNIQUE INDEX IF NOT EXISTS pk_venta_local_items ON venta_local_items (id);
