
CREATE TABLE CODIGOS_VERIFICACION 
   (	EMAIL varchar(255)  NOT NULL , 
	CODIGO_HASH varchar(255)  NOT NULL , 
	EXPIRA_EN timestamptz NOT NULL , 
	USADO boolean DEFAULT false NOT NULL , 
	CREADO_EN timestamptz DEFAULT now()
   );
