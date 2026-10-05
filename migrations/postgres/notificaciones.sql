
CREATE TABLE NOTIFICACIONES 
   (	ID uuid DEFAULT gen_random_uuid(), 
	USUARIO_ID uuid NOT NULL , 
	TIPO varchar(50)  NOT NULL , 
	CANAL varchar(20)  DEFAULT 'email' NOT NULL , 
	ASUNTO varchar(255) , 
	CONTENIDO text , 
	LEIDA boolean DEFAULT false NOT NULL , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	 CHECK (canal IN ('email', 'sms', 'push')) , 
	 PRIMARY KEY (ID)
   , 
	 CONSTRAINT FK_NOTIF_USUARIO FOREIGN KEY (USUARIO_ID)
	  REFERENCES USUARIOS (ID) 
   );

CREATE INDEX IF NOT EXISTS idx_notif_leida ON notificaciones (leida);
CREATE INDEX IF NOT EXISTS idx_notif_usuario ON notificaciones (usuario_id);
