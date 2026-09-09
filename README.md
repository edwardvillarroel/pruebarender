# ApoloVibes

Tienda web de productos impresos en 3D con diseños personalizados asistidos
por LLM. Monorepo:

- `app/` — Backend Flask (API REST, Clean Architecture).
- `ApoloVibes-frontend/` — Frontend React + Vite.

Diseño y contratos API: `docs/ARQUITECTURA.md` (duplicado en la raíz).

## Requisitos

- Python 3.12+ y Docker (PostgreSQL 16).
- Node 20+.

## Puesta en marcha (desarrollo)

### Backend (puerto 4000)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |  Unix: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # edita SECRET_KEY y JWT_SECRET_KEY
docker compose up -d db            # PostgreSQL (print3d_dev)
flask --app app run --port 4000
```

> El puerto debe ser `4000`: el proxy de Vite y la URL base de la API
> (`http://localhost:4000/api`) lo asumen.

### Frontend (puerto 5173)

```bash
cd ApoloVibes-frontend
npm install
npm run dev
```

Abrir http://localhost:5173. En desarrollo Vite proxya `/api` →
`http://localhost:4000` (sin problemas de CORS ni URL absoluta): el frontend
siempre llama a `'/api/...'` relativo al origen (`src/services/api.js`), y el
backend ya responde CORS en cada ruta (`CORS_ORIGINS` en `.env`).

Para probar el login desde un navegador o `curl`:
`POST http://localhost:4000/api/auth/login` con `{ "email": "admin", "password": "admin123" }`
→ `{ access_token, user }`.

## Administrador (temporal)

No hay base de usuarios todavía: el login del panel admin usa credenciales
**hardcodeadas** en `app/application/auth/autenticar.py`
(ADMIN_USERNAME / ADMIN_PASSWORD). Se eliminan cuando exista la tabla de
usuarios. Entrar con `admin` / `admin123` desde el modal "Iniciar sesión": el
frontend llama a `POST /api/auth/login`, guarda `{ token, user }` en
localStorage y el panel `/admin` queda protegido (`rol === 'admin'`).

## Producción

Construir el frontend y Flask servirá el build y la API desde el mismo puerto:

```bash
cd ApoloVibes-frontend && npm run build
cd .. && flask --app app run --port 4000   # o gunicorn 'app:create_app()'
```