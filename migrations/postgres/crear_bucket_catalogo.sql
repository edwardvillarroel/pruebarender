-- FASE 1 - Crear bucket público `catalogo`
-- Ejecutar en Supabase SQL Editor.
-- El bucket `Cotizaciones` NO se toca: queda privado, con 0 políticas.

-- 1) Crear el bucket desde Dashboard: Storage > New bucket > nombre `catalogo` > Public.
--    Alternativa por SQL (si se usa la API de storage de Supabase):
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('catalogo', 'catalogo', true)
-- ON CONFLICT (id) DO UPDATE SET public = true;

-- 2) Políticas de Storage para el bucket `catalogo`

-- Lectura pública: cualquiera puede ver las fotos del catálogo
DROP POLICY IF EXISTS "catalogo lectura publica" ON storage.objects;
CREATE POLICY "catalogo lectura publica"
ON storage.objects FOR SELECT
TO anon, authenticated
USING (bucket_id = 'catalogo');

-- Solo el backend (service_role) puede subir
DROP POLICY IF EXISTS "catalogo solo backend subir" ON storage.objects;
CREATE POLICY "catalogo solo backend subir"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'catalogo');

-- Solo el backend (service_role) puede borrar
DROP POLICY IF EXISTS "catalogo solo backend borrar" ON storage.objects;
CREATE POLICY "catalogo solo backend borrar"
ON storage.objects FOR DELETE
TO service_role
USING (bucket_id = 'catalogo');
