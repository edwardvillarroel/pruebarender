
CREATE TABLE SESIONES_VENTA 
   (	ID uuid NOT NULL , 
	LUGAR varchar(150)  NOT NULL , 
	FECHA date NOT NULL , 
	ESTADO varchar(20)  NOT NULL , 
	USUARIO_ID uuid NOT NULL , 
	CREADO_EN timestamptz NOT NULL , 
	CERRADA_EN timestamptz, 
	 CONSTRAINT PK_SESIONES_VENTA PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_SESIONES_VENTA_USUARIO FOREIGN KEY (USUARIO_ID)
	  REFERENCES USUARIOS (ID) 
   );

CREATE INDEX IF NOT EXISTS ix_sesiones_venta_usuario ON sesiones_venta (usuario_id);
CREATE UNIQUE INDEX IF NOT EXISTS pk_sesiones_venta ON sesiones_venta (id);
