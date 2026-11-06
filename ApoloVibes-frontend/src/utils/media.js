const BASE = import.meta.env.BASE_URL
const ORIGEN_API = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')

export const mediaPath = (file) => `${BASE}media/${file}`

export const urlMedia = (ruta) => {
  if (ruta === null || ruta === undefined) return ''
  const valor = String(ruta).trim()
  if (!valor) return ''
  if (/^(https?:|data:|blob:)/i.test(valor)) return valor
  if (valor.startsWith('/api/')) return `${ORIGEN_API}${valor}`
  if (valor.startsWith('/')) return valor
  return `${ORIGEN_API}/api/uploads/${valor.replace(/\\/g, '/')}`
}
