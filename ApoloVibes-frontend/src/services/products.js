import { api } from './api.js'

const imagenesPorColor = new Map()

function claveColor(productoId, color) {
  return `${productoId}::${color}`
}

export function registrarColores(productoId, colores) {
  for (const c of colores || []) {
    if (c?.imagen) imagenesPorColor.set(claveColor(productoId, c.nombre), c.imagen)
  }
}

export function imagenDeColor(productoId, color) {
  if (!productoId || !color) return null
  return imagenesPorColor.get(claveColor(productoId, color)) || null
}

export const productoApi = {
  obtener: () => api.get('/productos'),
  detalle: (id) => api.get(`/productos/${id}`),
  listarCategorias: () => api.get('/categorias'),
  eliminar: (id) => api.del(`/productos/${id}`),
  listarColores: (id) => api.get(`/productos/${id}/colores`),
  guardarColor: (id, color, archivo) => {
    const fd = new FormData()
    fd.append('color', color)
    fd.append('imagen', archivo)
    return api.post(`/productos/${id}/colores`, fd)
  },
  eliminarColor: (colorId) => api.del(`/productos/colores/${colorId}`),
}
