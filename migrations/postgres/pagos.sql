
CREATE TABLE PAGOS 
   (	ID uuid DEFAULT gen_random_uuid(), 
	PEDIDO_ID uuid NOT NULL , 
	MONTO numeric(10,2) NOT NULL , 
	PROVEEDOR varchar(50)  NOT NULL , 
	TOKEN varchar(255) , 
	ESTADO varchar(30)  DEFAULT 'pendiente' NOT NULL , 
	CREADO_EN timestamptz DEFAULT now() NOT NULL , 
	 CHECK (monto >= 0) , 
	 CHECK (estado IN (
                   'pendiente', 'autorizado', 'completado',
                   'fallido', 'reembolsado'
               )) , 
	 PRIMARY KEY (ID)
    
   
    , 
	 CONSTRAINT FK_PAGO_PEDIDO FOREIGN KEY (PEDIDO_ID)
	  REFERENCES PEDIDOS (ID) 
   );

CREATE INDEX IF NOT EXISTS idx_pago_estado ON pagos (estado);
CREATE INDEX IF NOT EXISTS idx_pago_pedido ON pagos (pedido_id);
