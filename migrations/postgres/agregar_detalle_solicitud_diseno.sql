ALTER TABLE solicitudes_diseno
    ADD COLUMN IF NOT EXISTS alto numeric(8,2),
    ADD COLUMN IF NOT EXISTS ancho numeric(8,2),
    ADD COLUMN IF NOT EXISTS largo numeric(8,2),
    ADD COLUMN IF NOT EXISTS unidad varchar(10) DEFAULT 'cm',
    ADD COLUMN IF NOT EXISTS cantidad integer DEFAULT 1 NOT NULL,
    ADD COLUMN IF NOT EXISTS uso varchar(30),
    ADD COLUMN IF NOT EXISTS color varchar(60);

ALTER TABLE solicitudes_diseno DROP CONSTRAINT IF EXISTS solicitudes_diseno_material_check;
ALTER TABLE solicitudes_diseno
    ADD CONSTRAINT solicitudes_diseno_material_check CHECK (material IN ('PLA','PLA+','ABS+','ABS','PETG','Resina','No estoy seguro'));

ALTER TABLE solicitudes_diseno DROP CONSTRAINT IF EXISTS solicitudes_diseno_cantidad_check;
ALTER TABLE solicitudes_diseno
    ADD CONSTRAINT solicitudes_diseno_cantidad_check CHECK (cantidad >= 1);
