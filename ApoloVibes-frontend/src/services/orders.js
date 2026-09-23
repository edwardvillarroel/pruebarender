import { api } from './api.js'

export const pedidosApi = {
  mios: () => api.get('/pedidos'),
  todos: () => api.get('/pedidos/admin'),
  detalle: (id) => api.get(`/pedidos/${id}`),
  registrarSeguimiento: (id, codigo) => api.post(`/pedidos/${id}/seguimiento`, { codigo }),
  sincronizarSeguimiento: (id) => api.get(`/pedidos/${id}/seguimiento`),
}