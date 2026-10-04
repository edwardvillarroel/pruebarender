-- DETALLE_PEDIDOS: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE DETALLE_PEDIDOS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	PEDIDO_ID uuid NOT NULL , 
	PRODUCTO_ID uuid NOT NULL , 
	CANTIDAD numeric NOT NULL , 
	PRECIO_UNITARIO numeric(10,2) NOT NULL , 
	COLOR varchar(50) , 
	 CHECK (cantidad > 0) , 
	 CHECK (precio_unitario >= 0) , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_DETALLE_PEDIDO FOREIGN KEY (PEDIDO_ID)
	  REFERENCES PEDIDOS (ID) , 
	 CONSTRAINT FK_DETALLE_PRODUCTO FOREIGN KEY (PRODUCTO_ID)
	  REFERENCES PRODUCTOS (ID) 
   );

CREATE INDEX IF NOT EXISTS idx_detalle_pedido ON detalle_pedidos (pedido_id);
CREATE INDEX IF NOT EXISTS idx_detalle_producto ON detalle_pedidos (producto_id);
