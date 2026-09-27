
const BASE_URL = '/api'
const AUTH_STORAGE_KEY = 'apolovibes_auth'

const EXCLUDE_RETRY = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/mfa/verificar', '/auth/mfa/activar', '/auth/mfa/desactivar', '/auth/cambiar-contrasena']

// Sin techo de espera, un fetch que se estanca deja el `await` del caller sin
// asentar nunca: en guardar producto eso era el boton en "Guardando..." para
// siempre, sin error. Toda la capa HTTP lleva limite explicito.
const TIMEOUT_MS = 30000
// Subir imagen (multipart) legitimamente tarda mas que un GET: presupuesto aparte.
const TIMEOUT_SUBIDA_MS = 120000
// El refresh no es una request barata: rota el token en Oracle y hace 6-7
// round-trips a la BD. Con el presupuesto normal de 30s se caia antes de
// terminar, y el error que veia el usuario era un corte, no un timeout real.
const TIMEOUT_REFRESH_MS = 60000

// fetch que siempre se asienta: o responde, o corta y lanza un error legible.
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

// Un FormData es un stream de un solo uso: si hay que reintentar, el objeto ya
// fue consumido y el reintento sube el body vacio (una foto de color sin
// archivo). Se guarda el contenido para poder reconstruirlo.
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

// Toda escritura exige sesión, sin importar el prefijo. Antes el matcheo por
// prefijo contaba `/productos/<uuid>` como público, y el PATCH de admin
// (guardar producto) se reintentaba SIN token en silencio tras un 401.
const METODOS_ESCRITURA = ['POST', 'PUT', 'PATCH', 'DELETE']

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

// `esPublica` decide si un 401 se reintenta sin token o cierra la sesión, así
// que tiene que considerar el método además del prefijo: mismo `/productos/…`
// es lectura pública con GET y escritura que exige sesión con PATCH.
function esPublica(path, metodo) {
  if (METODOS_ESCRITURA.includes((metodo || 'GET').toUpperCase())) return false
  return PUBLIC_PATHS.some(p => path === p || path.startsWith(`${p}/`))
}

function intentarRefresh() {
  if (refreshPromise) return refreshPromise

  // El timeout es lo que garantiza que el `await` del 401 se asiente. Antes, si
  // esta request se colgaba, el caller (guardar producto) quedaba esperando para
  // siempre y su `finally` nunca limpiaba el estado de "Guardando...".
  refreshPromise = fetchConTimeout(
    `${BASE_URL}/auth/refresh`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    },
    TIMEOUT_REFRESH_MS
  ).finally(() => { refreshPromise = null })

  return refreshPromise
}

async function request(path, options = {}, _retry = false) {
  // `timeoutMs` se saca de `options` para que nunca llegue a fetch, y permite
  // que una llamada concreta pida más presupuesto.
  const { headers = {}, timeoutMs, ...rest } = options
  const esSubida = rest.body instanceof FormData
  const limite = timeoutMs ?? (esSubida ? TIMEOUT_SUBIDA_MS : TIMEOUT_MS)
  // Foto de color y foto principal: si hay que reintentar, el FormData ya fue
  // consumido y subiría el body vacío. Se guarda para poder reconstruirlo.
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
    const refreshRes = await intentarRefresh()

    if (refreshRes.ok) {
      const body = await refreshRes.json()
      guardarToken(body.access_token)
      return request(path, opcionesConBodyValido(options, partes), true)
    }

    // Endpoint público: reintentar sin token en vez de borrar sesión
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

    // Endpoint privado: sesión expirada de verdad
    localStorage.removeItem(AUTH_STORAGE_KEY)
    throw new Error('Sesion expirada. Inicie sesion de nuevo.')
  }

  if (!res.ok) {
    throw await errorDeRespuesta(res, path)
  }
  return res.json()
}

// Reconstruye el body del reintento: un FormData se re-arma desde la
// instantánea porque el original ya se consumió en el primer envío. Se pasan
// las `options` completas para no perder headers ni timeout del caller.
function opcionesConBodyValido(options, partes) {
  if (!partes) return options
  return { ...options, body: reconstruirFormData(partes) }
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
