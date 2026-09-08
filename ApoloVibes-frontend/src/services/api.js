
const BASE_URL = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  })

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
}
