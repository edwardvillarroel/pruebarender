-- Endurecimiento del catálogo público (P0 + P1).
--
-- P0: las policies de SELECT dejan de ser USING (true). El anon key puede
--     leer productos publicados, pero no los ocultos con activo=false.
-- P1: anon/authenticated pierden los GRANT ALL que Supabase da por defecto
--     sobre todo public. Solo conservan SELECT en las tablas del catálogo.
--
-- Idempotente: se puede volver a correr. El backend usa el rol postgres
-- (bypasea RLS) y service_role para Storage, así que no se ve afectado.
-- Migración válida también en postgres_test (sin esquema storage).

-- P0 ------------------------------------------------------------------------

DROP POLICY IF EXISTS "productos publicos" ON public.productos;
CREATE POLICY "productos publicos" ON public.productos
    FOR SELECT TO anon, authenticated
    USING (activo = true);

DROP POLICY IF EXISTS "producto_colores publicos" ON public.producto_colores;
CREATE POLICY "producto_colores publicos" ON public.producto_colores
    FOR SELECT TO anon, authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.productos p
            WHERE p.id = public.producto_colores.producto_id
              AND p.activo = true
        )
    );

-- P1 ------------------------------------------------------------------------

DO $$
DECLARE
    hay_anon boolean := EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon');
    hay_auth boolean := EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated');
BEGIN
    IF hay_anon THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
    END IF;
    IF hay_auth THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;
    END IF;

    IF hay_anon THEN
        GRANT SELECT ON public.productos, public.categorias, public.producto_colores TO anon;
    END IF;
    IF hay_auth THEN
        GRANT SELECT ON public.productos, public.categorias, public.producto_colores TO authenticated;
    END IF;

    -- keepalive tiene su propia policy de lectura para monitoreo; se conserva.
    IF to_regclass('public.keepalive') IS NOT NULL THEN
        IF hay_anon THEN
            GRANT SELECT ON public.keepalive TO anon;
        END IF;
        IF hay_auth THEN
            GRANT SELECT ON public.keepalive TO authenticated;
        END IF;
    END IF;

    IF hay_anon AND hay_auth THEN
        ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
            REVOKE ALL ON TABLES FROM anon, authenticated;

        -- Supabase también crea default privileges como supabase_admin. Ese rol
        -- es superuser; si no tenemos membership, al menos quedó cubierto el
        -- rol postgres, que es el que usan nuestras migraciones.
        BEGIN
            ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public
                REVOKE ALL ON TABLES FROM anon, authenticated;
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'Default privileges de supabase_admin no modificados: se requiere ese rol';
        END;
    END IF;
END
$$;

-- PostgREST debe recargar el schema cache después de cambiar ACLs.
NOTIFY pgrst, 'reload schema';
