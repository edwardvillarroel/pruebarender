
CREATE TABLE CATEGORIAS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	NOMBRE varchar(100)  NOT NULL , 
	DESCRIPCION text , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT UQ_CATEGORIAS_NOMBRE UNIQUE (NOMBRE)
    
   
    
   );
