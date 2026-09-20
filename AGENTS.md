# AGENTS.md

ApoloVibes: web store for 3D-printed products with LLM-assisted custom designs. Monorepo: Flask API Gateway at repo root (`gateway/`, public `:3000`), Flask backend at `app/` (internal `:8000`, reachable ONLY through the gateway), React frontend in `ApoloVibes-frontend/`. All code, comments, and docs are in **Spanish** (entities, routes, error messages); write new code in Spanish to match.

## Governance

- `docs/ARQUITECTURA.md` is the design contract; **its copy at root `ARQUITECTURA.md` is now stale** (not synced). `docs/` has a "Nota de desviación" (Producto gained BLOB columns `imagen_bytes`/`imagen_content_type`, new `GET /api/productos/:id/imagen`) and **still contains un-resolved `<<<<<<< HEAD` merge-conflict markers around §6** — resolve/reconcile with `docs/` when touching it. The API contracts in §6 are **imposed by the already-built frontend** — do not change route shapes, field names, or response formats without updating the frontend.
- **Mandatory Clean Architecture layering** (ARQUITECTURA §3.1):
  - `app/domain/` — pure Python, no Flask/SQLAlchemy.
  - `app/application/` — use cases depend only on `domain` via interfaces (DI); application modules must never import each other.
  - `app/api/` — routes/middleware, depends on `application` + `domain`, **never on `infrastructure` directly**.
  - `app/infrastructure/` — implements `domain` interfaces (repositories, ORM models, LLM client, Celery).
- Two parallel entity sets mapping the same tables: pure entities in `domain/entities/` and ORM models in `infrastructure/database/models/`. The ER model (9 entities) is fixed; keep both in sync.

## Backend commands

Two Flask services. The backend (`app/`) is **internal only** — it trusts `X-User-Id`/`X-User-Rol` headers that only the gateway injects; never expose it publicly. The gateway (`gateway/`) owns auth (login/refresh/logout/me), rate limiting and proxies `/api/*` to the backend.

Run from repo root, in a venv. Instala TODO con un solo archivo: `pip install -r requirements.txt` (incluye las deps del gateway, p.ej. `httpx`; `gateway/requirements.txt` queda obsoleto):

1. `docker compose up -d db` — PostgreSQL 16 only for tests (db `print3d_dev`, user/pass `app`/`app`). `docker-compose.yaml` also declares `backend`/`gateway` services, but the referenced `Dockerfile.backend`/`Dockerfile.gateway` **do not exist** — `docker compose up` (all) will fail; only `-d db` works. Redis/Celery are in requirements but have **no compose service**; LLM async task infra is not runnable via compose.
2. `flask --app app run --port 8000` — backend interno. El gateway apunta ahí vía `BACKEND_INTERNAL_URL` (default `http://localhost:8000`).
3. `flask --app gateway.main run --port 3000` — API Gateway público. Sin `ORACLE_DSN` corre sin DB (health/proxy sí; login/me no).
4. Tests: `python -m pytest` from root. Fixtures (`app`, `client`) in `app/tests/conftest.py` use `TestingConfig` → `TEST_DATABASE_URL` (`print3d_test`), so integration tests need Postgres up. There are currently **no real test files** (only package `__init__.py` skeletons) — the de-facto integration test is the root script `prueba_stock.py` (see below), not pytest. No pytest.ini/lint/typecheck config exists.

Data scripts (root, run with the backend venv, hit whatever DB `.env` points at — Oracle or Postgres). **All of them are gitignored** (`.gitignore`, junto a `test_oracle.py`) — existen solo en working trees, no en un clone fresco (los `migrations/*.sql` sí están versionados):
- `agregar_producto.py` — insert a product + image as BLOB (`--imagen ruta.png`, `--what-if` dry-run). Sets `productos.imagen` to the `/api/productos/:id/imagen` URL.
- `seed_productos_prueba.py` — seeds products intentionally missing descripcion/imagen (frontend robustness test), category "Llaveros".
- `migrar_imagen_blob.py` — one-off migration adding `imagen_bytes`/`imagen_content_type` (raw SQL, Oracle). Keep as-is unless re-running the migration.
- `ver_tablas.py` — dump tables/rows of the configured DB.
- `prueba_stock.py` — the **only real integration test** of stock semantics (reserva/hold, venta exitosa, cancelación, validación de stock, reabastecimiento) against the configured DB. Creates a temp product/categoría, prints `[PASS]/[FAIL]`, exit 0/1; `--conservar` keeps the temp rows.

Schema migrations: despite Alembic/Flask-Migrate in requirements (and ARQUITECTURA §2 claiming Alembic), **there is no Alembic setup** — schema changes are raw SQL in `migrations/*.sql` (run via sqlplus/psql) and one-off Python scripts.

## Frontend commands

Run in `ApoloVibes-frontend/`:

1. `npm install`, then `npm run dev` (Vite on 5173).
2. No lint/test scripts exist (`package.json` only has dev/build/preview).
3. Vite proxies `/api` → `http://localhost:3000` (`vite.config.js`). `src/services/api.js` hardcodes base `'/api'` — there is **no `VITE_API_BASE_URL` override in code** and no frontend `.env.example` (README mentions both, but it's not implemented).
4. Sólo CI existente: `ApoloVibes-frontend/.github/workflows/deploy.yml` — en push a `main` hace `npm ci && npm run build` (Node 20) y despliega `dist` a GitHub Pages.

## Current state (verify before assuming anything works)

- Backend bootstraps in `create_app()` (`app/__init__.py`): CORS (Flask-Cors, `CORS_ORIGINS` env) + `db.init_app(app)` (DB **is wired**: repos/models registered, config reads `DATABASE_URL` or Oracle via `_oracle_uri`) + error handlers (`{mensaje}` JSON, incl. 429 and 501 for `NotImplementedError`) + SPA serving of `ApoloVibes-frontend/dist` under `FRONTEND_BASE_URL`. No JWT: la identidad llega como headers `X-User-Id`/`X-User-Rol` y el monolito **confía en ellos** (frontera de confianza = el gateway, jamás exponer `app/`).
- **Auth vive en el gateway** (`gateway/api/routes/auth_routes.py`): `POST /api/auth/login`, `POST /api/auth/refresh` (cookie HttpOnly `refresh_token`, rotación con detección de reuso), `POST /api/auth/logout`, `GET /api/auth/me`. JWT access 15 min; refresh en Oracle (`refresh_tokens`) si `ORACLE_DSN` está seteado (el gateway crea `refresh_tokens`/`logs_seguridad` al arrancar vía `infrastructure/ddl.py`). `/api/auth/register` no existe aún (404 vía proxy).
- **Implementados y contra la BD**: catálogo (`catalogo_routes.py` — GET/POST/PATCH/DELETE `/productos`, `GET /categorias`, `GET|POST /productos/:id/imagen` sirviendo el BLOB; los writes POST/PATCH/DELETE `/productos` y POST imagen exigen `requiere_sesion()+rol_requerido("admin")`. Solo `listar` de categorías funciona: `GestionarCategoria.crear/actualizar/eliminar` siguen `raise NotImplementedError`) y **carrito de compras** (`cart_routes.py` — GET `POST`/`PUT`/`DELETE` bajo `/cart`, persiste por usuario real via `CarritoRepositoryBd`, exige sesión con `requiere_sesion()`; ver composición en `_configurar_carrito`/`_configurar_catalogo`, `app/__init__.py`).
- **Siguen `raise NotImplementedError`**: pedidos y pago (`pedido_routes.py`), cotizaciones (`diseno_routes.py` — TODO `solo rol admin` para GET/PATCH), y ai/image-to-3d (`llm_routes.py`); también `infrastructure/llm/llm_client.py`, `infrastructure/tasks/llm_tasks.py` (Celery), `crear_pedido`/`consultar_pedido`/`procesar_pago` y los casos de uso de cotizaciones.
- Frontend catálogo y carrito **sí llaman al API** (`src/services/products.js` → `GET /productos`, `/categorias`; `src/services/cart.js` → `/cart`; `ProductContext`/`CartContext`). La generación 3D sigue en mock (`Cotizacion.jsx` usa `generarModelo3DMock`, `src/services/ai-model.js`) — swap a `generarModelo3D` cuando el endpoint LLM aterrice. Vite `base` es `/ApoloVibes3D-Frontend/`.
- **El checkout/pago está en mock temporal**: el botón "Ir a pagar" del carrito (`Carrito.jsx`) llama `POST /api/cart/finalizar-compra-mock` (requiere sesión): valida el stock de TODOS los items antes de descontar nada (409 con mensaje si falta), descuenta stock y vacía el carrito, y navega a `/compra-exitosa`. El endpoint está marcado TODO para desaparecer cuando aterricen pedidos/pago. La página `/checkout` (`Checkout.jsx` + `src/services/payment.js`, `iniciarPago` → `POST /api/pago/crear` y auto-submit `token_ws`) y `/pago/retorno` (`PagoRetorno.jsx`) siguen en el router con el contrato de ARQUITECTURA, pero no son el flujo activo.
- Zona admin (`src/pages/admin/`, rutas bajo `/admin` en el router via `ProtectedRoute` `rol==='admin'`): `Dashboard`, `Pedidos`, `RegistrarVentaLocal` (placeholder estático, "Venta Local" que no toca el API), `Inventario`, `Cotizaciones` — en su mayoría estáticos/placeholders; los endpoints detrás de ellos (pedidos, cotizaciones admin) siguen sin implementar.
- Frontend login is wired to the API: `LoginModal` calls `POST /api/auth/login` with `{ email, password }` (backend accepts `username` or `email`) and shows `err.mensaje` on failure. `AuthContext` persists `{ token, user }` in localStorage key `apolovibes_auth`; `src/services/api.js` attaches `Authorization: Bearer <token>` to every request, auto-refreshes on 401 via `/auth/refresh` (single-flight) y hace logout solo en rutas privadas. `ProtectedRoute` (guards `/admin` in `App.jsx`) requires `rol === 'admin'`.
- Reusable helpers exist — use them when implementing endpoints instead of reinventing: `requiere_sesion()`, `rol_requerido(*roles)` y `usuario_actual()` (`app/api/middleware/auth.py`, leen los headers `X-User-Id`/`X-User-Rol` del gateway) for the routes marked `TODO: solo rol admin`; `auditar(accion)` (`app/api/middleware/audit_logger.py`) for RNF-06 audit logging; `app/api/middleware/rate_limiter.py` defines `LLM_RATE_LIMIT` ("5 per minute") / `API_GENERAL_RATE_LIMIT` but Flask-Limiter is **never initialized in the backend**, so backend rate limiting is inactive (el gateway sí lo usa: 5/min login, 10/min refresh en `auth_routes.py`).

## API conventions (frontend expects these)

- Base URL `http://localhost:3000/api`; error responses must be `{ "mensaje": string }` (frontend `src/services/api.js` throws `err.mensaje`).
- AI generation: `POST /api/ai/image-to-3d` (multipart field `imagen`) → `{ taskId }`; poll `GET /api/ai/image-to-3d/:taskId` every ~2s → `{ status: processing|completed|failed, modelUrl, error }`.
- Payment: `POST /api/pago/crear` → `{ url, token }`; frontend auto-submits `token_ws` to `url`; `POST /api/pago/confirmar` with `{ token }`.
- LLM inputs must be sanitized for prompt injection before reaching the model (see `application/asistente_llm/validar_prompt.py`, `application/disenos_personalizados/sanitizar_input.py`).