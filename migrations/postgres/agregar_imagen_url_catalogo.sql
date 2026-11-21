-- FASE 2 - Tablas del catálogo: URL pública en vez de blob/ruta interna
-- Ejecutar en Supabase SQL Editor.

-- Solo guardamos la URL, no el archivo
ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen_url text;
ALTER TABLE categorias ADD COLUMN IF NOT EXISTS imagen_url text;

-- Lectura pública del catálogo (excepción documentada: SELECT con anon key, sin datos sensibles)
DROP POLICY IF EXISTS "productos publicos" ON productos;
CREATE POLICY "productos publicos"
ON productos FOR SELECT
TO anon, authenticated
USING (true);

DROP POLICY IF EXISTS "categorias publicas" ON categorias;
CREATE POLICY "categorias publicas"
ON categorias FOR SELECT
TO anon, authenticated
USING (true);
