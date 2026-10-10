# Proposal: Migrar la BD a Supabase (Postgres gestionado)

## Problema y contexto

ApoloVibes corre sobre Oracle Autonomous Database con wallet mTLS (`ORACLE_DSN`), sin ruta de salida portable. El esquema no tiene dueño: Alembic sin setup, `db.create_all()` nunca invocado y cambios de esquema como SQL manual en `migrations/*.sql`. El DDL destino sale de un volcado `GET_DDL` de Oracle, no del ORM, que no declara `server_default`.

## Objetivos

- Correr backend y gateway sobre el Postgres gestionado de Supabase.
- Eliminar `python-oracledb` y el wallet mTLS.
- Dejar un esquema de 20 tablas con tipos nativos, defaults reales y fuente de verdad declarativa.

## No objetivos

- Supabase Auth y RLS: el gateway conserva su auth propia (JWT, `refresh_tokens` con rotación y detección de reuso, EmailJS, Google OAuth, MFA/TOTP).
- El `TUU_SECRET_KEY` de `app/config.py:52`: se deja constancia, no se corrige.

## Alcance

| Elemento | Definición |
|---|---|
| 20 tablas | 15 con modelo ORM (`logs_auditoria`, `notificaciones`, `solicitudes_diseno` sin uso) + 5 del gateway (`refresh_tokens`, `logs_seguridad`, `codigos_verificacion`, `bloqueos_login`, `codigos_respaldo`) + 4 `ALTER TABLE usuarios ADD` |
| Backend | SQLAlchemy 2.0, cero SQL crudo; UUID → `uuid`; `DateTime` → `timestamptz`; `specs` en `Text` con `TypeDecorator` |
| Gateway | `oracledb` crudo → `psycopg2`; `MERGE ... dual` → `ON CONFLICT`; `1`/`0` → booleanos; `user_tab_columns` → `information_schema` |
| Datos | Solo esquema (~50 filas). Carga con verificación de conteos y checksums |

## Blockers

- **B1** `oracle_pool.py`: pool con wallet → `psycopg2`.
- **B2** `repositorios.py`: ~30 binds `:n` → `%(n)s`; `**kwargs` → `dict`.
- **B3** `ddl.py`: tipos Oracle → Postgres.
- **B4** `gateway/__init__.py:43`: la puerta `ORACLE_DSN` debe fallar ruidoso.
- **B5** `app/config.py:12-42`: borrar `_oracle_uri()` y `connect_args`.
- **B6** `crear_producto_colores.sql:100`: índice con `NVL` → `NULLS NOT DISTINCT`.
- **B7** 14 `DateTime` naive: normalizar a `timestamptz`.
- **B8** `producto_repository.py:71`: `# noqa: E712` → booleanos.
- **B9** `_run_seed.py:31`: `ROWNUM` → `LIMIT 10`.
- **B10** `_run_migracion_descuento.py`: `CEIL` exige `::numeric`.
- **B11** `productos.specs`: `Text` + `TypeDecorator`, no `jsonb`.

## Capacidades

**Nuevas**: `persistencia-postgres`, `fuente-de-verdad-esquema`, `caracterizacion-sql`. **Modificadas**: ninguna; API y dominio no cambian.

## Enfoque

Secuencia fija: **R0** caracterización contra Oracle (con seam de DI en el gateway) → **R1** DDL → **R2** carga y verificación → **R3** backend → **R4** DDL del gateway → **R5** repos del gateway → **R6** corte y documentación. R0 va primero: sin él la comparación pre/post no prueba nada. El backend usa el Session Pooler (`:5432`) para preservar prepared statements; `sslmode=require` y `pool_pre_ping=True` son obligatorios.

## Áreas afectadas

`gateway/infrastructure/*`, `gateway/__init__.py`, `app/config.py`, `app/infrastructure/*`, `_run_seed.py`, `_run_migracion_descuento.py`, `migrations/*.sql`, `app/tests/`.

## Riesgos

| Riesgo | Prob. | Mitigación |
|---|---|---|
| Ningún test valida SQL | Alta | R0 antes de tocar código |
| Esquema sin dueño | Alta | DDL desde el volcado + verificación de columnas |
| Volumen de R5 | Media | Slices encadenados, 400 líneas |
| Filas de `carrito_items` | Media | Checksums y prueba del índice con color nulo |

## Plan de rollback

Cada etapa R se revierte sola. Hasta R6 Oracle sigue activo: restaurar `ORACLE_DSN` y revertir el tramo. Tras el corte, reprocesar el volcado sobre Oracle. No se borran datos.

## Dependencias

Connection string de Supabase (no provista; bloquea R1), volcado `GET_DDL`, `postgres:16` local.

## Fuera de alcance

Plan o facturación de Supabase, limpieza de `docker-compose.yaml`, contratos de `docs/ARQUITECTURA.md` §6.

## Criterios de éxito

- [ ] Ambos servicios arrancan contra Supabase sin `oracledb` instalado.
- [ ] Las 20 tablas coinciden con el volcado en columnas, tipos y defaults.
- [ ] Los tests de R0 pasan idénticos contra Oracle y Supabase.
- [ ] Conteos y checksums coinciden pre/post.
- [ ] El gateway falla con error explícito sin configuración de base.