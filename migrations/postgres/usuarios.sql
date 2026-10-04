-- USUARIOS: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE USUARIOS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	EMAIL varchar(255)  NOT NULL , 
	PASSWORD_HASH varchar(255)  NOT NULL , 
	NOMBRE varchar(100)  NOT NULL , 
	APELLIDO varchar(100) , 
	TELEFONO varchar(30) , 
	ROL varchar(20)  DEFAULT 'cliente' NOT NULL , 
	ACTIVO boolean DEFAULT true NOT NULL , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	AUTH_PROVIDER varchar(20)  DEFAULT 'local' NOT NULL , 
	GOOGLE_SUB varchar(255) , 
	MFA_SECRET varchar(64) , 
	MFA_ACTIVO boolean DEFAULT false NOT NULL , 
	 CHECK (rol IN ('admin', 'cliente')) , 
	 CONSTRAINT CK_USUARIOS_APELLIDO CHECK (rol <> 'cliente' OR apellido IS NOT NULL) , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT UQ_USUARIOS_EMAIL UNIQUE (EMAIL)
    
   
    
   );

CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios (rol);
