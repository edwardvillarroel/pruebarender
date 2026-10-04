-- SOLICITUDES_DISENO: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE SOLICITUDES_DISENO 
   (	ID uuid DEFAULT gen_random_uuid(), 
	USUARIO_ID uuid NOT NULL , 
	NOMBRE varchar(150)  NOT NULL , 
	EMAIL varchar(255)  NOT NULL , 
	TELEFONO varchar(30) , 
	MATERIAL varchar(30)  NOT NULL , 
	DESCRIPCION text  NOT NULL , 
	ESTADO varchar(30)  DEFAULT 'pendiente' NOT NULL , 
	IMAGEN varchar(500) , 
	MODELO_URL varchar(500) , 
	PRECIO numeric(10,2), 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	 CHECK (material IN ('PLA', 'PETG', 'Resina', 'ABS')) , 
	 CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')) , 
	 CHECK (precio >= 0) , 
	 PRIMARY KEY (ID)
   , 
	 CONSTRAINT FK_SOLICITUD_USUARIO FOREIGN KEY (USUARIO_ID)
	  REFERENCES USUARIOS (ID) 
   );

CREATE INDEX IF NOT EXISTS idx_solicitud_estado ON solicitudes_diseno (estado);
CREATE INDEX IF NOT EXISTS idx_solicitud_usuario ON solicitudes_diseno (usuario_id);
