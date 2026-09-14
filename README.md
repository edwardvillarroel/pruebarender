# ApoloVibes

Tienda web de productos impresos en 3D con disenos personalizados asistidos
por LLM. Monorepo:

- `gateway/` — API Gateway Flask (`:3000`, publico): auth JWT, proxy, rate limiting, CORS.
- `app/` — Backend Flask (`:8000`, interno): logica de negocio, Clean Architecture.
- `ApoloVibes-frontend/` — Frontend React + Vite (`:5173`).

Diseno y contratos API: `docs/ARQUITECTURA.md` (duplicado en la raiz).

## Requisitos

- Python 3.12+.
- Docker (PostgreSQL 16 para tests).
- Node 20+.
- Oracle Instant Client o wallet para Oracle Autonomous DB.

## Estructura

```
ApoloVibes/
├── gateway/          # API Gateway (:3000, publico)
│   ├── auth JWT, proxy reverso, rate limiting, CORS
│   └── oracle pool, token service, DDL
├── app/              # Backend interno (:8000)
│   └── logica de negocio (Clean Architecture)
└── ApoloVibes-frontend/  # React + Vite (:5173)
```

El backend NUNCA se expone publicamente. El gateway es el unico punto de entrada.

## Puesta en marcha (desarrollo)

### 1. PostgreSQL (tests)

```bash
docker compose up -d db
```

Crea la base `print3d_dev` (user `app` / pass `app`).

### 2. Gateway (puerto 3000)

```bash
# Activar venv
python -m venv .venv
# Windows: .venv\Scripts\activate   |  Unix: source .venv/bin/activate
pip install -r gateway/requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Oracle, secrets, etc.

# Iniciar gateway
flask --app gateway.main run --port 3000
```

### 3. Backend interno (puerto 8000, opcional en dev)

Solo necesario si se necesita probar el backend directamente sin pasar por el gateway.

```bash
pip install -r requirements.txt
flask --app app run --port 8000
```

### 4. Frontend (puerto 5173)

```bash
cd ApoloVibes-frontend
npm install
npm run dev
```

Abrir http://localhost:5173. Vite proxya `/api` al gateway `:3000`.

## Variables de entorno

Ver `.env.example` para la lista completa. Variables principales:

| Variable                | Descripcion |
|-------------------------|-------------|
| `ORACLE_DSN`            | TNS name del Oracle Autonomous DB (ej. `apolodev_high`). |
| `ORACLE_PASSWORD`       | Password del usuario Oracle. |
| `ORACLE_WALLET_DIR`     | Ruta al directorio del wallet Oracle. |
| `ORACLE_WALLET_PASSWORD`| Password del wallet. |
| `GATEWAY_SECRET_KEY`    | Secret key para Flask (session signing). |
| `GATEWAY_JWT_SECRET`    | Secret para firmar/verificar JWT. |
| `GATEWAY_COOKIE_SECURE` | `1` en prod (https), `0` en dev (http). |
| `BACKEND_INTERNAL_URL`  | URL del backend interno (default `http://localhost:8000`). |
| `CORS_ORIGINS`          | Origenes permitidos (default `http://localhost:5173`). |

## Administrador

Credenciales de desarrollo (tabla `usuarios` de Oracle):

- **Email:** `admin@apolovibes.cl`
- **Password:** `Admin123!`

CAMBIAR EN PRODUCCION.

## Produccion

```bash
# Gateway con gunicorn
gunicorn --bind 0.0.0.0:3000 'gateway.main:create_app()'

# O sin gunicorn (desarrollo)
flask --app gateway.main run --port 3000
```
