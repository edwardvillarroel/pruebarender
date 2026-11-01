# Despliegue — ApoloVibes en Render + V2NET (hosting compartido)

Arquitectura acordada para el despliegue productivo:

```
https://apolovibes3d.cl        -> V2NET (hosting compartido): build estático del frontend React
https://api.apolovibes3d.cl    -> Render (free tier): gateway Flask + backend Flask en un solo servicio
```

- **Frontend**: vive en su propio repo, un nivel arriba de este (`../apolovibes-front`),
  y no está versionado acá. V2NET sirve su `dist/` en el dominio principal.
- **API**: Render (plan free) corre **backend + gateway en el mismo servicio** (`render.yaml`,
  `scripts/iniciar_render.sh`): gunicorn en `127.0.0.1:8000` (backend interno) y gunicorn en
  `0.0.0.0:$PORT` (gateway público, healthcheck en `/health`).
- **BD**: Supabase/PostgreSQL (`DATABASE_URL`). Las imágenes de producto son BLOB en la
  base (`/api/productos/<id>/imagen`), así que sobreviven a los redeploys de Render; los
  archivos subidos a `uploads/` no (el disco de Render free es efímero).

Flujo de datos: el navegador (origen `https://apolovibes3d.cl`) llama a
`https://api.apolovibes3d.cl/api/...`; el gateway autentica y reenvía al backend.
Front y API comparten el dominio registrable `apolovibes3d.cl`, así que la cookie de
refresh (`SameSite=Strict`, `Path=/api/auth`) viaja sin problema: es same-site.

## 1. Render (backend + gateway)

`render.yaml` ya define el servicio (`apolovibes`, runtime python, plan free, region ohio):

- `buildCommand: pip install -r requirements.txt` (solo Python: el frontend se despliega en V2NET).
- `startCommand: bash scripts/iniciar_render.sh` (backend en loopback :8000 + gateway en `$PORT`).
- `healthCheckPath: /health`.

### Variables de entorno obligatorias (dashboard de Render)

| Variable | Valor / nota |
|---|---|
| `DATABASE_URL` | Connection string Postgres/Supabase (Session Pooler). Obligatoria. |
| `SECRET_KEY` | Generada (`generateValue`) — compartir con gateway. |
| `GATEWAY_SECRET_KEY` | Generada (`generateValue`). |
| `DB_BACKEND` | `postgres` |
| `BACKEND_INTERNAL_URL` | `http://127.0.0.1:8000` (interno, mismo servicio). |
| `GATEWAY_COOKIE_SECURE` | `true` (HTTPS en Render). |
| `GATEWAY_COOKIE_SAMESITE` | `Strict` (front y API comparten dominio registrable). |
| `CORS_ORIGINS` | `https://apolovibes3d.cl` (y `https://www.apolovibes3d.cl` si se usa). |
| `FRONTEND_URL` | `https://apolovibes3d.cl` (redirects de Google/MFA). |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Credenciales del cliente OAuth. |
| `GOOGLE_REDIRECT_URI` | `https://api.apolovibes3d.cl/api/auth/google/callback` |
| `RECAPTCHA_SITE_KEY` / `RECAPTCHA_SECRET_KEY` | reCAPTCHA v2. |
| `EMAILJS_*` | Credenciales/plantillas EmailJS. |
| `TUU_*`, `STARKEN_*`, `OPENFACTURA_*`, `EMISOR_*` | Integraciones pago/facturación/LLM. |
| `LLM_API_KEY` / `COTIZADOR_IA_URL` | LLM para cotizador. |

## 2. Google OAuth (Google Cloud Console)

El `redirect_uri` lo arma el gateway con `GOOGLE_REDIRECT_URI` y lo valida Google antes
de redirigir. Si no coincide **exactamente** con un URI autorizado del cliente, Google
devuelve `Error 400: redirect_uri_mismatch` y nunca se llega al gateway.

En *APIs & Services > Credentials > OAuth 2.0 Client IDs* (cliente web
`502203188423-...`), en **Authorized redirect URIs**:

- `https://api.apolovibes3d.cl/api/auth/google/callback`  (producción)
- `http://localhost:3000/api/auth/google/callback`       (desarrollo)

Sin barra final, sin `www`, con `https`. Los "Authorized JavaScript origins" no se usan
(el flujo es server-side con Authorization Code). Cambios en la consola pueden tardar
unos minutos en propagarse.

Para verificar qué URI está pidiendo producción:

```bash
curl -s https://api.apolovibes3d.cl/api/auth/google/url
# -> {"url":"https://accounts.google.com/o/oauth2/v2/auth?...&redirect_uri=https%3A%2F%2Fapi.apolovibes3d.cl%2Fapi%2Fauth%2Fgoogle%2Fcallback..."}
```

## 3. Frontend (V2NET — hosting compartido)

El repo del front vive en `../apolovibes-front` (repo git aparte). El build se hace en
el propio hosting:

1. `git pull` en el hosting.
2. `rm -rf dist && npm run build`.
3. `cp -a dist/. ~/public_html/` (con `dist/*` **no** se copia `.htaccess`).

Dos requisitos que no son obvios:

- **`VITE_API_URL`**: el build de producción necesita
  `VITE_API_URL=https://api.apolovibes3d.cl`. Está en `.env.production` (Vite lo lee solo
  en `npm run build`) y `vite.config.js` aborta el build si falta. Sin esa variable
  `BASE_URL` queda en `/api`, las imágenes (`/api/productos/<id>/imagen`) se piden al
  dominio del hosting (503) y el refresh de sesión apunta a otro sitio: las cards salen
  sin imagen y la sesión muere al primer 401.
- **`public/.htaccess`**: el sitio es un SPA con React Router. Sin el rewrite a
  `index.html`, cualquier ruta que no sea un archivo real (`/admin`, `/producto/<id>`,
  `/pago/retorno`) responde 503/404 del hosting al recargar o entrar directo, y parece
  que la sesión del admin "se cerró sola". El archivo se versiona en `public/` y viaja
  a `dist/` en cada build.

## 4. DNS

- `apolovibes3d.cl` -> A/AAAA a la IP de V2NET (o nameservers V2NET).
- `api.apolovibes3d.cl` -> CNAME `apolovibes.onrender.com` (o registro A de Render).
  `apolovibes.onrender.com` sigue funcionando como URL interna de Render; el front **no**
  debe apuntar ahí (sería cross-site y rompería la cookie de refresh).

## 5. Verificación

- `curl -s https://api.apolovibes3d.cl/health` -> `{"mensaje":"gateway ok"}`.
- `curl -sI https://api.apolovibes3d.cl/api/productos/<id>/imagen` -> `200 image/jpeg`.
- `curl -sI https://apolovibes3d.cl/admin` -> `200 text/html` (index.html del SPA).
- `curl -sI "https://apolovibes3d.cl/pago/retorno?x_result=failed&x_reference=test"` -> `200 text/html`.
  TUU redirige al cliente a `TUU_URL_COMPLETE` (`https://apolovibes3d.cl/pago/retorno`): es una ruta
  del SPA, así que sin el `.htaccess` el cliente ve un 503 justo después de pagar (la confirmación
  server-to-server a `TUU_URL_CALLBACK` sigue funcionando igual).
- `curl -sI https://apolovibes3d.cl/api/productos` -> `403` (en el hosting estático no hay
  API: si devuelve `200 text/html`, el build no tiene `VITE_API_URL`).
- Login/refresh con cookie `refresh_token` (`HttpOnly`, `Secure`, `SameSite=Strict`,
  `Path=/api/auth`).
- Flujo completo: front (V2NET) -> API (Render) -> backend (Render, loopback).

## Problemas ya diagnosticados

| Síntoma | Causa | Arreglo |
|---|---|---|
| Cards de producto sin imagen | Build sin `VITE_API_URL`: las rutas `/api/productos/<id>/imagen` se piden a `apolovibes3d.cl` (503) | Rebuild con `.env.production` y `urlMedia` (ya mapea `/api/*` al origen de la API) |
| `redirect_uri_mismatch` en Google | El URI de producción no está en *Authorized redirect URIs* del cliente | Agregar `https://api.apolovibes3d.cl/api/auth/google/callback` |
| La sesión del admin "se cierra" al entrar al panel | (a) ruta `/admin` recargada -> sin `.htaccess` el hosting devuelve 503; (b) build apuntando a `onrender.com`: cookie de refresh de otro sitio + `/reportes` 401 -> `api.js` borra la sesión | `.htaccess` + build con `VITE_API_URL=https://api.apolovibes3d.cl`; `api.js` ahora emite `apolovibes:sesion-expirada` y `AuthContext` limpia el estado |
