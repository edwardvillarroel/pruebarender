import { api } from './api.js'

export const productoApi = {
  obtener: () => api.get('/productos'),
  detalle: (id) => api.get(`/productos/${id}`),
  listarCategorias: () => api.get('/categorias'),
}