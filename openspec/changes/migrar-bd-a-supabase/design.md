# Design: Migrar la BD a Supabase (Postgres gestionado)

## Resumen ejecutivo

Se migra ApoloVibes de Oracle Autonomous Database a Supabase Postgres gestionado. El backend usa SQLAlchemy 2.0 y el gateway pasa de `oracledb` a `psycopg2` con bind style `%(n)s`. El esquema se deriva del DDL de Oracle (`DBMS_METADATA.GET_DDL`), no de los modelos ORM. Los `RAW(16)` se vuelven `uuid` nativo, los timestamps se normalizan a `timestamptz`, `MERGE INTO` se reemplaza por `ON CONFLICT` sobre un índice único plano con `clave` normalizada en minúsculas, se aisla el pool del gateway para permitir inyección de dependencias, se mantiene la ausencia intencional de cascadas en las FKs, y se establece un harnes de tests en R0 para congelar el comportamiento actual **antes de migrar**, no antes de cortar.

## Abordaje técnico

La migración se organiza por etapas R0-R6: primero caracterizar (R0) con seam de DI en gateway para poder ejecutar los mismos tests contra Oracle y Supabase. R1 define el DDL canónico de 20 tablas con mapeo Oracle→Postgres explícito. R2 carga datos con verificación de conteos y checksums. R3 adapta backend (SQLAlchemy), R4 DDL del gateway, R5 repositorios del gateway, R6 corte y documentación. El backend utilizará Session Pooler de Supabase en puerto 5432 (para preservar prepared statements), con `sslmode=require` y `pool_pre_ping=True`. El gateway (Flask threaded) usará `psycopg2.pool.ThreadedConnectionPool` con min/max configurables por variables de entorno.

## Decisiones técnicas

### Decisión 1: Reemplazar UuidRaw (UUID nativo en Postgres)

- **Elección**: (b) **eliminar `UuidRaw` por completo** y usar `sqlalchemy.Uuid(as_uuid=True)` directamente en los 15 modelos, actualizando los imports.
- **Alternativa descartada**: (a) conservar `UuidRaw` y cambiar solo `impl = LargeBinary(16)` por `impl = sa.Uuid(as_uuid=True)`.
- **Por qué se descarta (a) — es incorrecta, no solo una cuestión de nombre**: `UuidRaw` es un `TypeDecorator` y define `process_bind_param` (`connection.py:23-32`), que devuelve `value.bytes`, y `process_result_value` (`connection.py:34-41`), que reconstruye el UUID desde bytes. En `TypeDecorator` esos hooks **tienen prioridad sobre el `impl`**. Cambiar únicamente `impl` deja el hook activo: cada UUID seguiría saliendo como 16 bytes crudos contra una columna `uuid` de Postgres, que es exactamente el bug que la migración viene a eliminar. Para que (a) funcionara habría que borrar los tres métodos igual, con lo cual `UuidRaw` queda siendo un alias sin comportamiento propio.
- **Justificación de (b)**: `sqlalchemy.Uuid(as_uuid=True)` (disponible en SQLAlchemy 2.0.52, la versión del repo) ya provee la serialización, la validación y el mapeo al `uuid` nativo de Postgres. El diff es mecánico — cambiar el símbolo importado en 15 modelos — y a cambio elimina un `TypeDecorator` que ya no hace falta y un nombre que describiría mal lo que hace. Un nombre que miente es deuda: dentro de seis meses nadie va a leer `UuidRaw` y pensar "Oracle `RAW(16)`", van a asumir que hay algo binario abajo.

### Decisión 2: Normalización de timestamps

- **Elección**: Convertir todas las columnas `DateTime`/`DateTime(timezone=True)` a `timestamptz` (Postgres). Para columnas naive actuales (11 en modelos + defaults `datetime.utcnow`): usar `DateTime(timezone=True)` en SQLAlchemy con `server_default=text("now()")` cuando corresponda al DDL canónico (mapeado desde TIMESTAMP/TIMESTAMP WITH TIME ZONE de Oracle) y eliminar defaults Python dependientes de `datetime.utcnow` (deprecado en Python 3.12). Para `carrito_model.py` (3 columnas `timezone=True`) mantener semántica con TZ pero forzar `server_default=text("now()")` y evitar `default=datetime.utcnow` (naive).
- **Alternativas consideradas**: Mantener naive (arriesga ambigüedad y comparación incorrecta al cruzar zonas), o usar `timestamp without time zone` (no refleja intención de timestamps de auditoría).
- **Justificación**: Oracle `TIMESTAMP` (sin TZ explícito) convivía con columnas TZ; en Postgres es más seguro unificar a `timestamptz`. Los repositorios (`pedido_repository.py`, `pago_repository.py`, `venta_local_repository.py`) filtran/ordenan por fechas, por lo que la normalización preserva orden cronológico. Se reemplaza `datetime.utcnow` por `datetime.now(datetime.timezone.utc)` en defaults Python puntuales (solo cuando sean necesarios en creación ORM) o se delega a `server_default=now()` para evitar valores inconsistentes. El DDL canónico usará `timestamptz` y `DEFAULT now()` según corresponda.

### Decisión 3: MERGE INTO → ON CONFLICT en gateway

- **Elección**: (b) normalizar `clave` a minúsculas al escribir, crear índice único plano `(clave, tipo)` en `bloqueos_login`, y usar `ON CONFLICT (clave, tipo)` en `gateway/infrastructure/repositorios.py:216-238`. Asimismo aplicar la misma normalización para `codigos_verificacion` (lecturas ya usan `LOWER(...)`).
- **Alternativas consideradas**: (a) índice único de expresión `ON bloqueos_login (LOWER(clave), tipo)` y `ON CONFLICT (LOWER(clave), tipo)`.
- **Justificación**: Todas las lecturas consultan con `LOWER(clave)=LOWER(:clave)` y `LOWER(email)=LOWER(:email)`, por lo que normalizar al escribir no rompe ninguna consulta existente. Esto simplifica el `ON CONFLICT` (columnas planas), evita dependencia de índice expresado en algunos escenarios y hace el DDL más claro. El upsert queda: `INSERT ... ON CONFLICT (clave,tipo) DO UPDATE SET ...` tras haber escrito `clave = LOWER(clave)`. No se altera lógica de bloqueo/verificación.

### Decisión 4: Seam de DI del gateway (desbloquea R0)

- **Elección**: Modificar `gateway/__init__.py` para aceptar un parámetro `pool=None` (o `db_pool`) en `create_app(config=None, pool=None)`. `obtener_pool()` se mantiene como factory para producción, pero `create_app` inyecta el pool cuando se pasa; en tests se inyectará `psycopg2.pool.ThreadedConnectionPool` o un stub. `gateway/infrastructure/oracle_pool.py` se reemplaza por `gateway/infrastructure/db_pool.py` (o se adapta) para crear pool de psycopg2. El gateway es Flask threaded, por lo que `psycopg2.pool.ThreadedConnectionPool` es apropiado (threads comparten conexiones). Valores `minconn/maxconn` leídos desde variables de entorno (`DB_POOL_MIN`, `DB_POOL_MAX`, defaults conservadores). Sin configuración válida, la aplicación debe **fallar ruidoso** (no arrancar en estado "sin tablas" como hoy ocurre cuando `ORACLE_DSN` no existe).
- **Alternativas consideradas**: Singleton global irreemplazable (impide tests R0 entre Oracle/Supabase), o usar `current_app.extensions`.
- **Justificación**: Permite inyectar pool Oracle o Supabase en R0 para correr los mismos tests. Justifica ThreadedConnectionPool por modelo threaded de Flask y necesidad de reutilización. Se documenta que el backend usará Session Pooler (5432) y gateway usará pool propio con psycopg2.

### Decisión 5: Estrategia de DDL de las 20 tablas

- **Elección**: Derivar DDL desde volcado `DBMS_METADATA.GET_DDL` de Oracle. Scripts SQL versionados y numerados bajo `migrations/` (o `schema/`) con enfoque **idempotente** donde corresponda. Mapeo completo:
  - `RAW(16)` → `uuid`
  - `NUMBER(1)` → `boolean`
  - `NUMBER(10,0)` → `integer`, `NUMBER(19,0)` → `bigint`
  - `VARCHAR2(n)` / `VARCHAR2(n CHAR)` → `varchar(n)` (se descarta semántica `CHAR` por alineación con uso actual)
  - `TIMESTAMP` → `timestamptz` (unificado; Oracle DATE se mapea a `timestamptz` excepto `sesiones_venta.fecha` que es `date`)
  - `CLOB` → `text`
  - `BLOB` → `bytea`
  - `DEFAULT SYSTIMESTAMP` → `DEFAULT now()`
  - `DEFAULT 0` en booleanas → `DEFAULT false`
  - `NUMBER GENERATED BY DEFAULT AS IDENTITY` → `bigint GENERATED BY DEFAULT AS IDENTITY`

- **Decisión sobre FKs/cascadas**: Las 14 FKs **no tienen `ON DELETE`/cascadas** en DDL (intencional). Los `cascade="all, delete-orphan"` son únicamente a nivel ORM. El schema Postgres tendrá **cero cascadas** — esto se documenta explícitamente como decisión (no omisión).
- **Decisión sobre tablas muertas**: `logs_auditoria`, `notificaciones`, `solicitudes_diseno` **no se migran** (no tienen repositorio instanciado y sus rutas levantan `NotImplementedError`). No se crean por simetría para evitar mantener esquema no usado; si en el futuro se habilitan, se agregan en cambio separado.
- **Justificación**: El DDL canónico debe reflejar lo que existe en Oracle (fuente de verdad), no lo inferido por ORM (15 modelos sin `server_default`). Scripts numerados e idempotentes facilitan revisión (R1 puede dividirse por slices). El mapeo respeta tipos nativos y defaults reales.

### Decisión 6: Índices de carrito_items (NVL + NULLS NOT DISTINCT)

- **Elección**: Preservar la semántica única con `NULLS NOT DISTINCT` (Postgres 15+). Crear índice único: `CREATE UNIQUE INDEX ux_carrito_item_producto_color ON carrito_items (carrito_id, producto_id, color) NULLS NOT DISTINCT;` y agregar `CHECK (color IS NULL OR color <> '')` porque en Postgres string vacío es valor distinto de NULL. Mantener la regla "mismo producto + mismo color = una línea". El comentario original que explica el `NVL` en Oracle (NULL tratados iguales) se traslada al script DDL.
- **Alternativas consideradas**: Usar expresión `(carrito_id, producto_id, COALESCE(color,''))` con índice único sobre expresión (también válido), pero `NULLS NOT DISTINCT` sobre la columna es más claro y preserva semántica directa.
- **Justificación**: `NVL(color,' ')` en Oracle hacía equivalentes NULL y espacio; en Postgres la opción (b) con `NULLS NOT DISTINCT` sobre `(carrito_id,producto_id,color)` logra que dos filas con color NULL no se consideren distintas entre sí para el índice único, preservando la regla de negocio. El CHECK evita ambigüedad entre `''` y `NULL`. Verificación: insertar casos (color NULL, color '', color 'rojo') para confirmar unicidad.

### Decisión 7: Script de migración de datos

- **Elección**: Lectura con `oracledb`, escritura con `psycopg2`, orden por FK (padres antes que hijos), decodificación de UUID `RAW(16)` → convertir a `uuid.UUID(bytes=...)` o hex → string UUID canónico para insertar en tipo `uuid` de Postgres. BLOBs vía `psycopg2.Binary`. Verificación obligatoria: conteos por tabla (`SELECT count(*)`) pre y post, y checksums por tabla (e.g. `SUM(OCTET_LENGTH(col_blob))`/checksums sobre columnas críticas: totales numéricos, hashes MD5/SHA256 de concatenados deterministas para columnas no-BLOB, con columnas ordenadas por PK). Detecta filas perdidas y columnas corruptas.
- **Justificación**: Orden FK evita violaciones; decodificación correcta de RAW(16) preserva identidad; verificación con doble criterio (conteo + checksum) es necesaria para datos financieros/operativos. Scripts ejecutables, con logs y salida determinista.

### Decisión 8: Harnes de tests de R0

- **Elección**: R0 crea el esquema desde el DDL canónico en cada base de prueba y ejecuta **los mismos tests** contra ambas. `TestingConfig` deja de ser config muerta: inicializa el esquema y asegura aislamiento entre tests (truncado por tablas en orden inverso de FK, o rollback por transacción).
- **Mecanismo de la doble ejecución**: la base destino NO se elige con un flag en el `conftest.py`. El `conftest.py` resuelve la conexión desde `TEST_DATABASE_URL` (backend) y `GATEWAY_TEST_DATABASE_URL` (gateway), y la suite se ejecuta **dos veces con distinta URL**: una contra Oracle para congelar el comportamiento actual, otra contra Supabase para verificar que es idéntico. La comparación de ambos resultados ES la prueba de que la migración no cambió nada.
- **Por qué NO `testcontainers`**: no está en `requirements.txt` y, sobre todo, **no puede levantar Oracle**, que es la mitad del objetivo de R0. Un `testcontainers` de Postgres solo serviría para iterar el DDL de R1, y para eso ya está el `postgres:16` del `docker-compose.yaml` (servicio `db`, que funciona aunque `backend`/`gateway` estén rotos). Agregar una dependencia nueva sin necesidad rompe la regla de no ampliar alcance.
- **Alcance de R0**: caracterizar el comportamiento real, no agregar cobertura nueva. Los directorios `app/tests/integration/api/` e `integration/repositories/` se pueblan con los casos que hoy solo cubre `prueba_stock.py` (reserva de stock, venta exitosa, cancelación, validación de stock, reabastecimiento) más lo que sí toca base de datos vía repositorio: carrito con y sin color, creación de pedido con detalle y pago, y los flujos de auth del gateway. No se introduce SQLite.
- **Justificación**: Congelar comportamiento antes de migrar (punto clave R0). Flask-SQLAlchemy lazy engine requiere inicialización explícita en test setup. Aislamiento evita contaminación entre tests. Mantener comparación Oracle vs Supabase valida mapeo de tipos y semántica.

### Decisión 9: Estrategia de PRs (review_budget_lines: 400)

- **Elección**: un PR por etapa R, en orden, respetando los 400 líneas. **R0 va primero, sin excepción**:
  - **PR1 - R0 Characterization tests**: seam de DI del gateway + `conftest.py` + la suite de caracterización corriendo verde **contra Oracle**. Es el PR que pone la red de seguridad; todo lo demás depende de él. Debe aterrizar antes de tocar una sola línea de esquema o de código de acceso a datos.
  - **PR2 - R1 DDL del esquema**: scripts DDL de las 20 tablas + índices. Si supera 400 líneas, partir por dominio: (a) entidades de negocio (`productos`, `categorias`, `productos_categorias`, `carritos`, `carrito_items`), (b) pedidos y pago, (c) auth del gateway (`usuarios`, `refresh_tokens`, `logs_seguridad`, `codigos_verificacion`, `bloqueos_login`, `sesiones_venta`, `configuracion`).
  - **PR3 - R2 Datos y verificación**: script de migración + verificación de conteos/checksums. Bloqueado hasta tener el connection string.
  - **PR4 - R3 Backend (SQLAlchemy)**: `app/infrastructure/database/*` y `app/config.py` — `UuidRaw` eliminado, timestamps a `timestamptz`, `_oracle_uri()` fuera.
  - **PR5 - R4 Gateway: pool y DDL**: `db_pool.py` con `ThreadedConnectionPool`, seam `create_app(pool=None)`, fallo ruidoso sin config, y adaptación de `infrastructure/ddl.py` a Postgres.
  - **PR6 - R5 Repositorios gateway**: binds `:n`→`%(n)s`, `MERGE`→`ON CONFLICT`, booleanos, `user_tab_columns`. Es el de mayor volumen: dividir por repositorio (`auth`, `catalogo`, `carrito`, `pedidos`) en sub-slices encadenadas si pasa las 400.
  - **PR7 - R6 Corte y limpieza**: switch de configuración, retiro de `oracledb`, verificación post-corte, documentación.
- **Por qué R0 va primero, y no último**: R0 existe para congelar el comportamiento *antes* de cambiar nada. Si la suite de caracterización llega en el PR6, para entonces el código ya escribe en Postgres y los tests describen el destino, no el origen — no comparan nada y el propósito se pierde. Además, el PR1 debe quedar verde contra Oracle: ese es el baseline sin el cual ninguna verificación posterior significa algo.
- **Justificación del resto**: R1 (20 tablas DDL) puede superar 400 líneas, así que se parte por dominio. El corte protege el foco de review y deja cada PR autocontenido y testeable.

### Decisión 10: Rollback por etapa

- **Elección**:
  - **R0**: revertir harnes/tests (archivos creados/modificados), sin tocar BD.
  - **R1 (DDL)**: `DROP TABLE` en orden inverso FK (o scripts down) si se aplicó a ambiente de migración; en producción no aplicado hasta corte.
  - **R2 (datos)**: datos cargados en Supabase son copia; rollback = no promocionar Supabase (mantener Oracle activo). No borrar datos; basta con restaurar conexión a Oracle y revertir código.
  - **R3-R5 (código)**: git revert por PR/commits.
  - **R6 (corte)**: punto de no retorno controlado; plan de rollback = volver a apuntar servicios a Oracle (config), revertir código y reprocesar volcado sobre Oracle si fuera necesario. No se elimina esquema Oracle.
- **Justificación**: Hasta R6 Oracle sigue activo (estrategia propuesta). R2 reversible por corte (no promoción). Cada etapa revierte sola, minimiza riesgo.

## Flujo de datos

```
Oracle (oracledb) --lectura--> Script migración datos --escritura--> Supabase (psycopg2)
Gateway (Flask) --psycopg2--> Supabase (5432, Session Pooler)
Backend (Flask+SQLAlchemy) --engine--> Supabase (5432, Session Pooler)
Tests R0: ejecutan mismos casos contra Oracle y Supabase vía DI/seam
```

## Cambios de archivos (previstos)

| Archivo | Acción | Descripción |
|---|---|---|
| `app/infrastructure/database/connection.py` | Modificar | **Eliminar** `UuidRaw` (el `TypeDecorator` completo, no solo su `impl`) |
| `app/infrastructure/database/models/*.py` | Modificar | Normalizar `DateTime` a `timezone=True` con `server_default` cuando aplique (alineado a DDL) |
| `app/config.py` | Modificar | Limpiar referencias Oracle (B5), habilitar `TEST_DATABASE_URL` efectivo en tests |
| `app/__init__.py`, `app/tests/conftest.py` | Modificar | Soporte tests R0, aislamiento schema |
| `gateway/infrastructure/oracle_pool.py` | Reemplazar/renombrar | Crear `db_pool.py` con `psycopg2.pool.ThreadedConnectionPool`, lectura env |
| `gateway/__init__.py` | Modificar | `create_app(pool=None)` + DI, fallo ruidoso sin config válida |
| `gateway/infrastructure/repositorios.py` | Modificar | Binds `:n`→`%(n)s`, `MERGE`→`ON CONFLICT`, normalizar `clave` a minúsculas |
| `gateway/infrastructure/ddl.py` | Modificar | Tipos Oracle→Postgres, DDL canónico |
| `migrations/*.sql` (nuevos/scripts DDL) | Crear/ajustar | DDL 20 tablas, índices con `NULLS NOT DISTINCT`, CHECK color, mapeo tipos |
| `_run_migracion_descuento.py` | Modificar | Cast `CEIL(... )::numeric` (B10) |
| `_run_seed.py` | Modificar | `ROWNUM`→`LIMIT 10` (B9) |
| `app/infrastructure/repositories/producto_repository.py` | Modificar | Ajuste booleanos (B8) |

## Contratos e interfaces

- Gateway: `create_app(config=None, pool=None)` permite inyección de pool. `obtener_pool()` factory producción.
- Conexiones: backend usa Session Pooler puerto 5432 (`sslmode=require`, `pool_pre_ping=True`). Gateway usa ThreadedConnectionPool con `DB_POOL_MIN`/`DB_POOL_MAX`.
- FKs: sin cascadas en DDL (decisión explícita). ORM mantiene `cascade` solo si existen, pero schema destino cero cascadas.
- UUID: tipo `uuid` nativo Postgres. Lectura/escritura vía SQLAlchemy Uuid.

## Estrategia de pruebas

| Capa | Qué probar | Abordaje |
|---|---|---|
| Unit | Lógica aislada | Mantener tests existentes si los hay |
| Integración (R0) | Mismos tests contra Oracle y Supabase | Caracterización con `prueba_stock.py` + tests integración vacíos poblados; comparar resultados idénticos |
| E2E | Flujo auth/catalogo/pedidos | Smoke tras corte R6 |

## Matriz de amenazas

`N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, o process-integration boundary.`

## Migración y despliegue

- **Requisitos**: connection string Supabase (bloquea R1/R2), volcado `DBMS_METADATA.GET_DDL`, Postgres 16 local para validación.
- **Secuencia**: R0 → R1 → R2 → R3 → R4 → R5 → R6. Hasta R6 Oracle activo.
- **Verificación pre/post**: conteos + checksums (decisión 7). Índice carrito_items con casos NULL/''.
- **B10 (blocker datos financieros)**: `_run_migracion_descuento.py` usa `CEIL(PRECIO * (100-DESCUENTO)/100)` — requiere cast a `numeric` en Postgres para evitar división entera; además blindar con CHECK de rango si procede. (Nota: división entera en Postgres integer; cast explícito.)

## Preguntas abiertas

- Ninguna que bloquee el diseño. El connection string de Supabase queda como insumo pendiente (marcado en riesgos).

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Connection string Supabase no provisto (bloquea R1/R2) | Alta | Marcar bloqueo explícito; no ejecutar R1/R2 hasta tenerlo |
| Volumen R1/R5 supera slices | Media | Dividir por dominios siguiendo review_budget_lines 400 |
| B10 (CEIL/división entera) corrompe precios en silencio | Alta | Cast `::numeric` obligatorio + verificación de checksums en migración descuento |
| Gateway arranca sin DB con comportamiento confuso | Alta | Fallo ruidoso en `create_app` sin pool/config válido |
| Diferencia semántica TIMESTAMP vs timestamptz | Media | Unificación explícita y validación en R0 |

## Próximo paso recomendado

Listo para **sdd-tasks** (generar tareas R0-R6 con slices para PRs y criterios de aceptación).