-- Facturación electrónica: documento electrónico emitido por pedido.
--
-- Idempotente: se puede aplicar varias veces sin romper.

-- Tipo de documento que pide el cliente al pagar ("boleta" | "factura").
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS tipo_documento varchar(20);

CREATE TABLE IF NOT EXISTS documentos_tributarios (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id               uuid REFERENCES pedidos (id) ON DELETE CASCADE,
    tipo_dte                smallint NOT NULL,          -- 33 factura, 39 boleta
    estado                  varchar(20) NOT NULL DEFAULT 'pendiente',
    clave_idempotencia      varchar(120) NOT NULL,
    folio                   integer,
    token                   varchar(120),
    rut_emisor              varchar(20) NOT NULL,
    rut_receptor            varchar(20) NOT NULL,
    razon_social_receptor   varchar(200),
    giro_receptor           varchar(200),
    direccion_receptor      varchar(300),
    comuna_receptor          varchar(120),
    monto_neto              integer NOT NULL DEFAULT 0,
    iva                     integer NOT NULL DEFAULT 0,
    monto_total             integer NOT NULL DEFAULT 0,
    fecha_emision           date,
    error                   text,
    pdf                     bytea,
    creado_en               timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_documentos_tributarios_tipo_dte
        CHECK (tipo_dte IN (33, 39)),
    CONSTRAINT ck_documentos_tributarios_estado
        CHECK (estado IN ('pendiente', 'emitido', 'error'))
);

-- Un documento por pedido: es lo que impide emitir dos veces la misma venta.
CREATE UNIQUE INDEX IF NOT EXISTS idx_documentos_tributarios_pedido
    ON documentos_tributarios (pedido_id)
    WHERE pedido_id IS NOT NULL;

-- La clave de idempotencia se deriva del pedido, así que es única de verdad.
CREATE UNIQUE INDEX IF NOT EXISTS idx_documentos_tributarios_idem
    ON documentos_tributarios (clave_idempotencia);

CREATE INDEX IF NOT EXISTS idx_documentos_tributarios_estado
    ON documentos_tributarios (estado);
