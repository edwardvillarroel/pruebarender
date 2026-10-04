-- REFRESH_TOKENS: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE REFRESH_TOKENS 
   (	JTI varchar(36) , 
	USER_ID varchar(36)  NOT NULL , 
	EXPIRA_EN timestamptz NOT NULL , 
	REVOCADO boolean DEFAULT false NOT NULL , 
	IP varchar(45) , 
	USER_AGENT varchar(255) , 
	CREADO_EN timestamptz DEFAULT now(), 
	 PRIMARY KEY (JTI)
    
   
    
   );
