-- CATEGORIAS: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE CATEGORIAS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	NOMBRE varchar(100)  NOT NULL , 
	DESCRIPCION text , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT UQ_CATEGORIAS_NOMBRE UNIQUE (NOMBRE)
    
   
    
   );
