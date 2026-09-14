
const BASE_URL = '/api'
const AUTH_STORAGE_KEY = 'apolovibes_auth'

const EXCLUDE_RETRY = ['/auth/login', '/auth/refresh', '/auth/logout']

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

async function request(path, options = {}, _retry = false) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...authHeaders(),
      ...options.headers,
    },
  })

  if (res.status === 401 && !_retry && !EXCLUDE_RETRY.includes(path)) {
    const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    })
    if (refreshRes.ok) {
      const body = await refreshRes.json()
      guardarToken(body.access_token)
      return request(path, options, true)
    }
    localStorage.removeItem(AUTH_STORAGE_KEY)
    throw new Error('Sesion expirada. Inicie sesion de nuevo.')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.mensaje || `Error ${res.status} al llamar ${path}`)
  }
  return res.json()
}

export const api = {
  get: (path) => request(path),
  post: (path, body) =>
    request(path, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: (path, body) =>
    request(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: (path, body) =>
    request(path, { method: 'PATCH', body: JSON.stringify(body) }),
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
