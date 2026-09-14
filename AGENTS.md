# AGENTS.md

ApoloVibes: web store for 3D-printed products with LLM-assisted custom designs. Monorepo: Flask API Gateway at repo root (`gateway/`, public `:3000`), Flask backend at `app/` (internal `:8000`, reachable ONLY through the gateway), React frontend in `ApoloVibes-frontend/`. All code, comments, and docs are in **Spanish** (entities, routes, error messages); write new code in Spanish to match.

## Governance

- `docs/ARQUITECTURA.md` (duplicated at root as `ARQUITECTURA.md`, byte-identical; edit `docs/`) is the design contract. The API contracts in §6 are **imposed by the already-built frontend** — do not change route shapes, field names, or response formats without updating the frontend.
- **Mandatory Clean Architecture layering** (ARQUITECTURA §3.1):
  - `app/domain/` — pure Python, no Flask/SQLAlchemy.
  - `app/application/` — use cases depend only on `domain` via interfaces (DI); application modules must never import each other.
  - `app/api/` — routes/middleware, depends on `application` + `domain`, **never on `infrastructure` directly**.
  - `app/infrastructure/` — implements `domain` interfaces (repositories, ORM models, LLM client, Celery).
- Two parallel entity sets mapping the same tables: pure entities in `domain/entities/` and ORM models in `infrastructure/database/models/`. The ER model (9 entities) is fixed; keep both in sync.

## Backend commands

Two Flask services. The backend (`app/`) is **internal only** — it trusts `X-User-Id`/`X-User-Rol` headers that only the gateway injects; never expose it publicly. The gateway (`gateway/`) owns auth (login/refresh/logout/me), rate limiting and proxies `/api/*` to the backend.

Run from repo root, in a venv (gateway deps from `gateway/requirements.txt`):

1. `docker compose up -d db` — PostgreSQL 16 only (db `print3d_dev`, user/pass `app`/`app`). Redis/Celery are in requirements but have **no compose service**; LLM async task infra is not runnable via compose yet.
2. `flask --app app run --port 8000` — backend interno. El gateway apunta ahí vía `BACKEND_INTERNAL_URL` (default `http://localhost:8000`).
3. `flask --app gateway.main run --port 3000` — API Gateway público. Sin `ORACLE_DSN` corre sin DB (health/proxy sí; login/me no).
4. Tests: `python -m pytest` from root. Fixtures (`app`, `client`) in `app/tests/conftest.py` use `TestingConfig` → `TEST_DATABASE_URL` (`print3d_test`), so integration tests need Postgres up. There are currently **no real test files** (only package `__init__.py` skeletons). No pytest.ini/lint/typecheck config exists.

## Frontend commands

Run in `ApoloVibes-frontend/`:

1. `npm install`, then `npm run dev` (Vite on 5173).
2. No lint/test scripts exist (`package.json` only has dev/build/preview).
3. Vite proxies `/api` → `http://localhost:3000` (`vite.config.js`). `src/services/api.js` hardcodes base `'/api'` — there is **no `VITE_API_BASE_URL` override in code** and no frontend `.env.example` (README mentions both, but it's not implemented).

## Current state (verify before assuming anything works)

- Backend bootstraps in `create_app()` (`app/__init__.py`): CORS (Flask-Cors, `CORS_ORIGINS` env) + error handlers (`{mensaje}` JSON, incl. 501 for `NotImplementedError`) + SPA serving. No JWT: la identidad llega como headers `X-User-Id`/`X-User-Rol` y el monolito **confía en ellos** (frontera de confianza = el gateway, jamás exponer `app/`).
- **Auth vive en el gateway** (`gateway/api/routes/auth_routes.py`): `POST /api/auth/login`, `POST /api/auth/refresh` (cookie HttpOnly `refresh_token`, rotación con detección de reuso), `POST /api/auth/logout`, `GET /api/auth/me`. JWT access 15 min; refresh en Oracle (`refresh_tokens`) si `ORACLE_DSN` está seteado. `/api/auth/register` no existe aún (404 vía proxy).
- Most non-auth endpoints still `raise NotImplementedError` (catalogo, pedidos, pago, cotizaciones — those live in `app/api/routes/diseno_routes.py` — and ai/image-to-3d). Flask-SQLAlchemy `db` is instantiated in `infrastructure/database/connection.py` but **never `init_app`-ed**, so the DB layer is not wired up despite models existing.
- Frontend category/payment features run on mock data (`src/data/products.js`, `generarModelo3DMock` in `src/services/ai-model.js` — swap back to real `generarModelo3D` when the AI endpoint lands). Vite `base` is `/ApoloVibes3D-Frontend/`.
- Frontend login is wired to the API: `LoginModal` calls `POST /api/auth/login` with `{ email, password }` (backend accepts `username` or `email`) and shows `err.mensaje` on failure. `AuthContext` persists `{ token, user }` in localStorage key `apolovibes_auth`; `src/services/api.js` attaches `Authorization: Bearer <token>` to every request when a token exists. `ProtectedRoute` (guards `/admin` in `App.jsx`) requires `rol === 'admin'`.
- Reusable helpers exist but are **not wired up** — use them when implementing endpoints instead of reinventing: `rol_requerido(*roles)` y `usuario_actual()` (`app/api/middleware/auth.py`, leen los headers `X-User-Rol`/`X-User-Id` del gateway) for the routes marked `TODO: solo rol admin` (`POST /api/productos`, `GET`/`PATCH /api/cotizaciones`); `auditar(accion)` (`app/api/middleware/audit_logger.py`) for RNF-06 audit logging; `app/api/middleware/rate_limiter.py` defines `LLM_RATE_LIMIT` ("5 per minute") / `API_GENERAL_RATE_LIMIT` but Flask-Limiter is never initialized, so rate limiting is inactive.

## API conventions (frontend expects these)

- Base URL `http://localhost:3000/api`; error responses must be `{ "mensaje": string }` (frontend `src/services/api.js` throws `err.mensaje`).
- AI generation: `POST /api/ai/image-to-3d` (multipart field `imagen`) → `{ taskId }`; poll `GET /api/ai/image-to-3d/:taskId` every ~2s → `{ status: processing|completed|failed, modelUrl, error }`.
- Payment: `POST /api/pago/crear` → `{ url, token }`; frontend auto-submits `token_ws` to `url`; `POST /api/pago/confirmar` with `{ token }`.
- LLM inputs must be sanitized for prompt injection before reaching the model (see `application/asistente_llm/validar_prompt.py`, `application/disenos_personalizados/sanitizar_input.py`).