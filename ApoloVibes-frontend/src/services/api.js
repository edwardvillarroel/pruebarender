
const BASE_URL = '/api'
const AUTH_STORAGE_KEY = 'apolovibes_auth'
const EXCLUDE_RETRY = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/mfa/verificar', '/auth/mfa/activar', '/auth/mfa/desactivar', '/auth/cambiar-contrasena']
const TIMEOUT_MS = 30000
const TIMEOUT_SUBIDA_MS = 120000
const TIMEOUT_REFRESH_MS = 60000
const MENSAJE_CONEXION = 'No pudimos cargar la información. Revisa tu conexión e inténtalo de nuevo.'

async function fetchConTimeout(url, opciones, ms) {
  const controlador = new AbortController()
  const temporizador = setTimeout(() => controlador.abort(), ms)
  try {
    return await fetch(url, { ...opciones, signal: controlador.signal })
  } catch (error) {
    if (controlador.signal.aborted) {
      throw new Error(`La request a ${url} tardo mas de ${Math.round(ms / 1000)}s y se cancelo.`)
    }
    throw error
  } finally {
    clearTimeout(temporizador)
  }
}

function instantaneaFormData(fd) {
  const partes = []
  for (const [nombre, valor] of fd.entries()) partes.push([nombre, valor])
  return partes
}

function reconstruirFormData(partes) {
  const fd = new FormData()
  for (const [nombre, valor] of partes) fd.append(nombre, valor)
  return fd
}

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

const PUBLIC_PATHS = ['/productos', '/categorias', '/productos/']
const METODOS_ESCRITURA = ['POST', 'PUT', 'PATCH', 'DELETE']
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
  } catch {}
}

function esPublica(path, metodo) {
  if (METODOS_ESCRITURA.includes((metodo || 'GET').toUpperCase())) return false
  return PUBLIC_PATHS.some(p => path === p || path.startsWith(`${p}/`))
}

function intentarRefresh() {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    try {
      const res = await fetchConTimeout(
        `${BASE_URL}/auth/refresh`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
        },
        TIMEOUT_REFRESH_MS
      )
      const body = await res.json().catch(() => null)
      return { ok: res.ok, body }
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

function conErrorAmigable(promesa) {
  return promesa.catch(error => {
    const esInternaDelNavegador =
      error instanceof TypeError ||
      error instanceof SyntaxError ||
      error instanceof DOMException
    if (esInternaDelNavegador) {
      throw new Error(MENSAJE_CONEXION, { cause: error })
    }
    throw error
  })
}

async function request(path, options = {}, _retry = false) {
  const { headers = {}, timeoutMs, ...rest } = options
  const esSubida = rest.body instanceof FormData
  const limite = timeoutMs ?? (esSubida ? TIMEOUT_SUBIDA_MS : TIMEOUT_MS)
  const partes = esSubida ? instantaneaFormData(rest.body) : null

  const res = await fetchConTimeout(
    `${BASE_URL}${path}`,
    {
      ...rest,
      headers: {
        ...(esSubida ? {} : { 'Content-Type': 'application/json' }),
        ...authHeaders(),
        ...headers,
      },
    },
    limite
  )

  if (res.status === 401 && !_retry && !EXCLUDE_RETRY.includes(path)) {
    const { ok, body } = await intentarRefresh()

    if (ok && body?.access_token) {
      guardarToken(body.access_token)
      return request(path, opcionesConBodyValido(options, partes), true)
    }

    if (esPublica(path, rest.method)) {
      const retryRes = await fetchConTimeout(
        `${BASE_URL}${path}`,
        {
          ...rest,
          body: partes ? reconstruirFormData(partes) : rest.body,
          headers: {
            ...(esSubida ? {} : { 'Content-Type': 'application/json' }),
            ...headers,
          },
        },
        limite
      )
      if (!retryRes.ok) {
        throw await errorDeRespuesta(retryRes, path)
      }
      return retryRes.json()
    }

    localStorage.removeItem(AUTH_STORAGE_KEY)
    throw new Error('Sesion expirada. Inicie sesion de nuevo.')
  }

  if (!res.ok) {
    throw await errorDeRespuesta(res, path)
  }
  return res.json()
}


function opcionesConBodyValido(options, partes) {
  if (!partes) return options
  return { ...options, body: reconstruirFormData(partes) }
}

export const api = {
  get: (path, options = {}) => conErrorAmigable(request(path, options)),
  post: (path, body, options = {}) =>
    conErrorAmigable(
      request(path, {
        ...options,
        method: 'POST',
        body: body instanceof FormData ? body : JSON.stringify(body),
      })
    ),
  put: (path, body, options = {}) =>
    conErrorAmigable(request(path, { ...options, method: 'PUT', body: JSON.stringify(body) })),
  patch: (path, body, options = {}) =>
    conErrorAmigable(request(path, { ...options, method: 'PATCH', body: JSON.stringify(body) })),
  del: (path, options = {}) => conErrorAmigable(request(path, { ...options, method: 'DELETE' })),
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
