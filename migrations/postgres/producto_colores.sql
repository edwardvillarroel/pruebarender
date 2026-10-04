-- PRODUCTO_COLORES: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE PRODUCTO_COLORES 
   (	ID uuid NOT NULL , 
	PRODUCTO_ID uuid NOT NULL , 
	NOMBRE varchar(50)  NOT NULL , 
	IMAGEN_BYTES bytea, 
	IMAGEN_CONTENT_TYPE varchar(50) , 
	ORDEN integer DEFAULT 0 NOT NULL , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	IMAGEN_THUMB_BYTES bytea, 
	IMAGEN_THUMB_CONTENT_TYPE varchar(50) , 
	 CONSTRAINT PK_PRODUCTO_COLORES PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_PRODUCTO_COLORES_PRODUCTO FOREIGN KEY (PRODUCTO_ID)
	  REFERENCES PRODUCTOS (ID) 
   );

CREATE INDEX IF NOT EXISTS ix_producto_colores_producto ON producto_colores (producto_id);
CREATE UNIQUE INDEX IF NOT EXISTS pk_producto_colores ON producto_colores (id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_producto_colores_nombre ON producto_colores (producto_id, nombre);
