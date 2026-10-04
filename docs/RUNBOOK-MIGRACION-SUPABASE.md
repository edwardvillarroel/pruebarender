# Runbook: migración Oracle → Supabase (ApoloVibes)

Estado: **cerrada**. La app corre contra PostgreSQL en Supabase con los datos
reales cargados. Este documento es lo que tenés que leer para operar y para
decidir si hay que volver atrás.

Última verificación: 151 tests en verde, 754 filas migradas, base de tests en 0.

---

## 1. Dónde está cada cosa

| Qué | Dónde | Estado |
|---|---|---|
| Datos de producción | Supabase `postgres` (proyecto `egcpkhmcyjxihxbdsjxf`) | 754 filas migradas |
| Datos de tests | Supabase `postgres_test` | Esquema instalado, **0 filas** |
| Copia local vieja | Docker `print3d_dev` | Sigue en pie (rollback) |
| Esquema canónico | `migrations/postgres/schema_completo.sql` | Versionado |
| Config | `.env` | 47 claves, **cero** `ORACLE_*` |

El `.env` ya no tiene ninguna variable de Oracle. `DB_BACKEND=postgres` es
explícito, y el default del código también es `postgres`: Oracle solo entra si
alguien pone `DB_BACKEND=oracle` **y** las variables `ORACLE_*` a mano. No hay
forma de volver a Oracle por accidente.

## 2. Conexiones

**Desarrollo (host directo, IPv6-only).** Es el que está en el `.env`:

```
postgresql://postgres:<password>@db.egcpkhmcyjxihxbdsjxf.supabase.co:5432/postgres?sslmode=require
```

Ojo: el host directo **no resuelve por IPv4**. Desde una red sin IPv6 (Docker
en Windows con ciertas configs, CI sin IPv6) falla con timeout aunque todo esté bien.

**Producción y despliegue (Session Pooler).** Este es el que hay que usar en
servidores: sale por IPv4 y mantiene pocas conexiones, que es lo que pide el
plan de Supabase:

```
postgresql://postgres.egcpkhmcyjxihxbdsjvf:<password>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

El usuario del pooler lleva el prefijo `postgres.` seguido del ref del proyecto;
no es el mismo que el del host directo. Por eso el pool `POSTGRES_POOL_MAX` está
en 5.

## 3. Verificación

Todo esto tiene que dar verde antes de tocar producción:

```powershell
# Suite completa: unitarios + caracterización R0
$env:DB_BACKEND="postgres"
.\.venv\Scripts\python.exe -m pytest app/tests -q          # -> 151 passed

# La base de tests debe quedar en 0 filas
.\.venv\Scripts\python.exe -c "import os,psycopg2; from dotenv import load_dotenv; load_dotenv(); c=psycopg2.connect(os.environ['TEST_DATABASE_URL']); print(c.execute('select count(*) from productos').fetchone())"
```

Verificadores de datos (leen, no escriben):

| Script | Qué prueba |
|---|---|
| `tools/verificar_migracion.py` | Oracle ↔ Supabase: conteos, FKs, BLOBs byte a byte, fechas |
| `tools/verificar_gateway_pg.py` | Login/refresh/logout contra la base real |
| `tools/verificar_backend_pg.py` | Carrito y catálogo con datos migrados |
| `tools/verificar_ventas_pg.py` | Ciclo de venta local con descuento atómico |
| `tools/verificar_api_completa.py` | Que ninguna ruta reviente por esquema |

Todos aceptan un `*_TEST_DSN` para apuntar a destino. **Apuntarlos a
producción solo para leer**: escriben filas de prueba y las borran, y el script
verifica que el conteo vuelva al inicial. Si no lo hace, lo dice.

## 4. Reproducir el esquema desde cero

`schema_completo.sql` es la **única fuente reproducible** del esquema. No hay
Alembic. Si la base se pierde, se reconstruye con ese archivo:

```powershell
psql "<pooler-url>" -f migrations/postgres/schema_completo.sql
```

No borrar `migrations/` por eso.

## 5. Rollback

Orden de preferencia:

1. **Problemas de app, no de datos.** Corregir en código y redeployar. Es el 95% de los casos.
2. **Rollback de datos.** El dump de producción está en Supabase (backups
   automáticos del plan) o en el `print3d_dev` local. Para volcar:
   ```powershell
   pg_dump "<pooler-url>" -Fc -f apolovibes.dump
   ```
3. **Volver a Oracle.** Solo si Oracle sigue vivo. Requiere dos cosas:
   - volver a poner `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`,
     `ORACLE_WALLET_DIR`, `ORACLE_WALLET_PASSWORD` en el `.env`;
   - `DB_BACKEND=oracle`.

   Sin wallet mTLS, `oracledb` necesita thin mode; si falla, es que falta el
   wallet. `oracledb` sigue en `requirements.txt` justamente para que esta puerta
   no esté cerrada de antemano.

## 6. Lo que todavía NO está

- **Ruta de pedidos por API sin coverage R0.** Hay tests del caso de uso de pago
  (`app/tests/integration/test_pedido_pago.py`) y de venta local, pero no del
  flujo HTTP completo de `POST /api/pago/crear` → callback → `confirmar`.
- **Paridad Oracle ↔ PostgreSQL sin ejecutar.** Los tests R0 están escritos para
  correr en ambos motores (`TEST_DB_BACKEND=oracle` + `TEST_ORACLE_DSN`), pero
  Oracle ya no tiene DSN de pruebas configurado, así que esa pata nunca corrió.
  La caracterización real es contra PostgreSQL.
- **Rutas en 501:** cotizaciones (`GET /api/cotizaciones`), AI
  (`/api/ai/image-to-3d/<id>`), y los casos de uso de cotizaciones. No las
  implementa la migración; siguen pendientes de negocio.
- **`GET /api/productos/:id/imagen`** ya existe (BLOB) pero `docs/ARQUITECTURA.md`
  §6 tiene marcadores de merge sin resolver; el contrato de esa ruta lo fija el
  frontend, no lo cambies sin tocar el frontend.

## 7. Detalles que muerden

- **El descuento de stock es atómico a propósito.** `ProductoRepository.descontar_stock()`
  hace `UPDATE ... WHERE stock >= cantidad` en una transacción. La versión
  anterior (leer, restar en Python, escribir) vendía la misma unidad dos veces
  bajo concurrencia, y el stock **terminaba en 0 igual**, así que ningún test de
  "nunca negativo" lo detectaba. El test que lo cubre
  (`test_descontar_stock_es_atomico_entre_hilos`) afirma que de dos pagos
  simultáneos solo uno gana. No "simplificar" ese `descontar_stock` a un `update`.
- **`specs` es `Text` con property, no `JSONB`.** `ProductoModel.specs_raw`
  serializa a mano. Funciona y los datos migran bien; no hay que migrarlo a
  `jsonb` salvo que haga falta indexar.
- **`verificar_migracion.py` tira en `logs_auditoria`.** Esa tabla usa UUID, así
  que no tiene `max(id)` numérico; el error es del script, no de los datos.
- **Supabase corta conexiones ociosas.** `pool_pre_ping=True` está en
  `SQLALCHEMY_ENGINE_OPTIONS` por eso. No lo saques.
- **La password del `.env` estuvo expuesta una vez en una salida de terminal** y
  se rotó. Si se filtra de nuevo: rotar en el panel y actualizar el `.env`, sin
  dejar copias (`.env.bak`, backups del editor).

## 8. Checklist de cierre de la migración

- [x] Esquema aplicado en producción y en `postgres_test`
- [x] Datos migrados (754 filas) y verificados cruzada y byte a byte
- [x] `.env` sin variables `ORACLE_*`
- [x] `DB_BACKEND` con default `postgres` (Oracle solo explícito)
- [x] Carrera de stock corregida y cubierta por test de concurrencia
- [x] Suite verde (151 tests) y base de tests en 0
- [x] AGENTS.md actualizado (ya no dice que la BD es Oracle)
- [x] Runbook escrito
- [ ] Decidir si `oracledb` se queda en `requirements.txt` o se saca
- [ ] Decidir qué hacer con `print3d_dev` local y los scripts scratch del root
- [ ] Implementar las rutas 501, si es que están en el roadmap