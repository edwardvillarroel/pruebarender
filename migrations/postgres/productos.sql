

CREATE TABLE PRODUCTOS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	CATEGORIA_ID uuid NOT NULL , 
	NOMBRE varchar(150)  NOT NULL , 
	DESCRIPCION text , 
	PRECIO numeric(10,2) NOT NULL , 
	STOCK numeric DEFAULT 0 NOT NULL , 
	IMAGEN varchar(500) , 
	ACTIVO boolean DEFAULT true NOT NULL , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	IMAGEN_BYTES bytea, 
	IMAGEN_CONTENT_TYPE varchar(50) , 
	SPECS text , 
	DESCUENTO numeric, 
	BADGE varchar(50) , 
	PRECIO_ORIGINAL numeric, 
	RATING numeric, 
	MATERIAL varchar(100) , 
	TAMANO varchar(100) , 
	COLOR varchar(100) , 
	IMAGEN_THUMB_BYTES bytea, 
	IMAGEN_THUMB_CONTENT_TYPE varchar(50) , 
	NUEVO_LANZAMIENTO boolean DEFAULT false NOT NULL , 
	 CHECK (precio >= 0) , 
	 CHECK (stock >= 0) , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_PRODUCTO_CATEGORIA FOREIGN KEY (CATEGORIA_ID)
	  REFERENCES CATEGORIAS (ID) 
   );

CREATE INDEX IF NOT EXISTS idx_producto_activo ON productos (activo);
CREATE INDEX IF NOT EXISTS idx_producto_categoria ON productos (categoria_id);
