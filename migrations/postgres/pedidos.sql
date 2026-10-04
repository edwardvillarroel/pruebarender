-- PEDIDOS: generado desde el DDL de Oracle (DBMS_METADATA.GET_DDL).
-- No editar a mano: regenerar con tools/migrar_ddl_oracle.py.

CREATE TABLE PEDIDOS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	USUARIO_ID uuid NOT NULL , 
	ESTADO varchar(30)  DEFAULT 'pendiente' NOT NULL , 
	TOTAL numeric(10,2) DEFAULT 0 NOT NULL , 
	DIRECCION_ENVIO text , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	CODIGO_SEGUIMIENTO varchar(50) , 
	ESTADO_SEGUIMIENTO varchar(100) , 
	SEGUIMIENTO_ACTUALIZADO_EN timestamptz, 
	 CHECK (estado IN (
                        'pendiente', 'en_produccion', 'enviado',
                        'entregado', 'cancelado'
                    )) , 
	 CHECK (total >= 0) , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_PEDIDO_USUARIO FOREIGN KEY (USUARIO_ID)
	  REFERENCES USUARIOS (ID) 
   );

CREATE INDEX IF NOT EXISTS idx_pedido_creado ON pedidos (creado_en);
CREATE INDEX IF NOT EXISTS idx_pedido_estado ON pedidos (estado);
CREATE INDEX IF NOT EXISTS idx_pedido_usuario ON pedidos (usuario_id);
