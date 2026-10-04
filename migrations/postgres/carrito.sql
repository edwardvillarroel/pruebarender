-- CARRITO: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE CARRITO 
   (	ID uuid DEFAULT gen_random_uuid(), 
	USUARIO_ID uuid NOT NULL , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	ACTUALIZADO_EN timestamptz DEFAULT now() NOT NULL , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT UQ_CARRITO_USUARIO UNIQUE (USUARIO_ID)
    
   
    , 
	 CONSTRAINT FK_CARRITO_USUARIO FOREIGN KEY (USUARIO_ID)
	  REFERENCES USUARIOS (ID) 
   );
