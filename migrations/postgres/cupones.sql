CREATE TABLE IF NOT EXISTS cupones (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    codigo varchar(30) NOT NULL UNIQUE,
    tipo varchar(10) NOT NULL DEFAULT 'porcentaje',
    valor numeric(10,2) NOT NULL,
    activo boolean NOT NULL DEFAULT true,
    uso_unico boolean NOT NULL DEFAULT false,
    usado boolean NOT NULL DEFAULT false,
    usado_por uuid REFERENCES usuarios(id),
    usado_en timestamptz,
    creado_por uuid REFERENCES usuarios(id),
    creado_en timestamptz NOT NULL DEFAULT now(),
    descripcion varchar(255),
    CONSTRAINT chk_cupones_tipo CHECK (tipo IN ('porcentaje', 'monto')),
    CONSTRAINT chk_cupones_valor CHECK (valor > 0)
);

CREATE INDEX IF NOT EXISTS idx_cupones_codigo ON cupones(codigo);
CREATE INDEX IF NOT EXISTS idx_cupones_activo ON cupones(activo);
