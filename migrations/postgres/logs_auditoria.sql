

CREATE TABLE LOGS_AUDITORIA 
   (	ID uuid DEFAULT gen_random_uuid(), 
	USUARIO_ID uuid, 
	ACCION varchar(100)  NOT NULL , 
	ENTIDAD_TIPO varchar(50)  NOT NULL , 
	ENTIDAD_ID varchar(50) , 
	DETALLE text , 
	IP varchar(45) , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	 PRIMARY KEY (ID)
   , 
	 CONSTRAINT FK_LOG_USUARIO FOREIGN KEY (USUARIO_ID)
	  REFERENCES USUARIOS (ID) 
   );

CREATE INDEX IF NOT EXISTS idx_log_creado ON logs_auditoria (creado_en);
CREATE INDEX IF NOT EXISTS idx_log_entidad ON logs_auditoria (entidad_tipo, entidad_id);
CREATE INDEX IF NOT EXISTS idx_log_usuario ON logs_auditoria (usuario_id);
