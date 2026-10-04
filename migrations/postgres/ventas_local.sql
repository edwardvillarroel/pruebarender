-- VENTAS_LOCAL: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE VENTAS_LOCAL 
   (	ID uuid NOT NULL , 
	SESION_ID uuid NOT NULL , 
	MEDIO_PAGO varchar(20)  NOT NULL , 
	TOTAL bigint NOT NULL , 
	CREADO_EN timestamptz NOT NULL , 
	 CONSTRAINT PK_VENTAS_LOCAL PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_VENTAS_LOCAL_SESION FOREIGN KEY (SESION_ID)
	  REFERENCES SESIONES_VENTA (ID) 
   );

CREATE INDEX IF NOT EXISTS ix_ventas_local_sesion ON ventas_local (sesion_id);
CREATE UNIQUE INDEX IF NOT EXISTS pk_ventas_local ON ventas_local (id);
