-- Catálogo público: URLs de las fotos en el bucket `catalogo`.
-- Las imágenes NO se sirven desde la tabla: solo se guarda la URL pública.
-- Incremental idempotente: se puede volver a correr.

ALTER TABLE public.producto_colores
    ADD COLUMN IF NOT EXISTS imagen_url text,
    ADD COLUMN IF NOT EXISTS imagen_thumb_url text;

-- Lectura pública de solo SELECT para el front (anon/authenticated).
-- El backend usa el usuario postgres de la DATABASE_URL, que bypasea RLS.
ALTER TABLE public.productos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.producto_colores ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'productos'
          AND policyname = 'productos publicos'
    ) THEN
        CREATE POLICY "productos publicos" ON public.productos
            FOR SELECT TO anon, authenticated USING (activo = true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'categorias'
          AND policyname = 'categorias publicas'
    ) THEN
        CREATE POLICY "categorias publicas" ON public.categorias
            FOR SELECT TO anon, authenticated USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'producto_colores'
          AND policyname = 'producto_colores publicos'
    ) THEN
        CREATE POLICY "producto_colores publicos" ON public.producto_colores
            FOR SELECT TO anon, authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM public.productos p
                    WHERE p.id = public.producto_colores.producto_id
                      AND p.activo = true
                )
            );
    END IF;
END
$$;

-- Bucket público `catalogo`. El bucket privado Cotizaciones NO se toca.
-- En BDs de tests sin Supabase Storage el esquema no existe: se omite sin fallar.
DO $$
BEGIN
    IF to_regclass('storage.buckets') IS NULL THEN
        RAISE NOTICE 'Sin esquema storage: se omiten bucket y politicas de storage';
        RETURN;
    END IF;

    EXECUTE $sql$
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('catalogo', 'catalogo', true)
        ON CONFLICT (id) DO UPDATE SET public = true
    $sql$;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects'
          AND policyname = 'catalogo lectura publica'
    ) THEN
        CREATE POLICY "catalogo lectura publica" ON storage.objects
            FOR SELECT TO anon, authenticated
            USING (bucket_id = 'catalogo');
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects'
          AND policyname = 'catalogo solo backend subir'
    ) THEN
        CREATE POLICY "catalogo solo backend subir" ON storage.objects
            FOR INSERT TO service_role
            WITH CHECK (bucket_id = 'catalogo');
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects'
          AND policyname = 'catalogo solo backend borrar'
    ) THEN
        CREATE POLICY "catalogo solo backend borrar" ON storage.objects
            FOR DELETE TO service_role
            USING (bucket_id = 'catalogo');
    END IF;
END
$$;
