ALTER TABLE solicitudes_diseno
ADD COLUMN material_sugerido_ia VARCHAR(50),
ADD COLUMN complejidad_ia VARCHAR(50),
ADD COLUMN gramos_estimados_ia NUMERIC(10,2),
ADD COLUMN tiempo_estimado_horas_ia NUMERIC(10,2),
ADD COLUMN precio_estimado_ia NUMERIC(12,0),
ADD COLUMN confianza_material_ia NUMERIC(4,2),
ADD COLUMN confianza_complejidad_ia NUMERIC(4,2),
ADD COLUMN ia_calculado_en TIMESTAMP WITH TIME ZONE,
ADD COLUMN ia_origen VARCHAR(50);
