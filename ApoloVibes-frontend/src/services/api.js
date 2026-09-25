
const BASE_URL = '/api'
const AUTH_STORAGE_KEY = 'apolovibes_auth'

const EXCLUDE_RETRY = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/mfa/verificar', '/auth/mfa/activar', '/auth/mfa/desactivar', '/auth/cambiar-contrasena']

// Convierte un fetch Response en Error que conserva el body JSON del servidor
// (err.datos) para que el UI pueda leer campos extra (captcha_requerido, etc.).
function errorDeRespuesta(res, path) {
  return res.clone().json()
    .then(body => {
      const e = new Error(body.mensaje || `Error ${res.status} al llamar ${path}`)
      e.datos = body
      e.status = res.status
      return e
    })
    .catch(() => {
      const e = new Error(`Error ${res.status} al llamar ${path}`)
      e.datos = null
      e.status = res.status
      return e
    })
}

// Rutas públicas que NO deben causar logout si el token expira
const PUBLIC_PATHS = ['/productos', '/categorias', '/productos/']

// Single-flight refresh: evita carreras de refresh concurrentes
let refreshPromise = null

function authHeaders() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    const data = raw ? JSON.parse(raw) : null
    return data?.token ? { Authorization: `Bearer ${data.token}` } : {}
  } catch {
    return {}
  }
}

function guardarToken(token) {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    const data = raw ? JSON.parse(raw) : {}
    data.token = token
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data))
  } catch { /* noop */ }
}

function esPublica(path) {
  return PUBLIC_PATHS.some(p => path.startsWith(p))
}

function intentarRefresh() {
  if (refreshPromise) return refreshPromise

  refreshPromise = fetch(`${BASE_URL}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  }).finally(() => { refreshPromise = null })

  return refreshPromise
}

async function request(path, options = {}, _retry = false) {
  const { headers = {}, ...rest } = options
  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...(rest.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...authHeaders(),
      ...headers,
    },
  })

  if (res.status === 401 && !_retry && !EXCLUDE_RETRY.includes(path)) {
    const refreshRes = await intentarRefresh()

    if (refreshRes.ok) {
      const body = await refreshRes.json()
      guardarToken(body.access_token)
      return request(path, options, true)
    }

    // Endpoint público: reintentar sin token en vez de borrar sesión
    if (esPublica(path)) {
      const retryRes = await fetch(`${BASE_URL}${path}`, {
        ...rest,
        headers: {
          ...(rest.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
          ...headers,
        },
      })
      if (!retryRes.ok) {
        throw await errorDeRespuesta(retryRes, path)
      }
      return retryRes.json()
    }

    // Endpoint privado: sesión expirada de verdad
    localStorage.removeItem(AUTH_STORAGE_KEY)
    throw new Error('Sesion expirada. Inicie sesion de nuevo.')
  }

  if (!res.ok) {
    throw await errorDeRespuesta(res, path)
  }
  return res.json()
}

export const api = {
  get: (path, options = {}) => request(path, options),
  post: (path, body, options = {}) =>
    request(path, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: (path, body, options = {}) =>
    request(path, { ...options, method: 'PUT', body: JSON.stringify(body) }),
  patch: (path, body, options = {}) =>
    request(path, { ...options, method: 'PATCH', body: JSON.stringify(body) }),
  del: (path, options = {}) => request(path, { ...options, method: 'DELETE' }),
  logout: async () => {
    try {
      await fetch(`${BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders(),
      })
    } catch { /* best-effort */ }
    localStorage.removeItem(AUTH_STORAGE_KEY)
  },
}
