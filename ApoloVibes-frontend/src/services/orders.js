import { api } from './api.js'

export const TRANSPORTISTAS = [
  { valor: 'starken', label: 'Starken', placeholder: 'Ej: 222123456', ayuda: 'Número de seguimiento' },
  { valor: 'bluexpress', label: 'Bluexpress', placeholder: 'Ej: 123456789', ayuda: 'Número de seguimiento' },
]

export const transportistaDe = (valor) =>
  TRANSPORTISTAS.find((t) => t.valor === valor) || TRANSPORTISTAS[0]

export const pedidosApi = {
  mios: () => api.get('/pedidos'),
  todos: () => api.get('/pedidos/admin'),
  detalle: (id) => api.get(`/pedidos/${id}`),
  pagarDeNuevo: (id) => api.post(`/pedidos/${id}/pagar`),
  cancelar: (id) => api.post(`/pedidos/${id}/cancelar`),
  eliminar: (id) => api.del(`/pedidos/${id}`),
  registrarSeguimiento: (id, codigo, transportista) => 
    api.post(`/pedidos/${id}/seguimiento`, { codigo, transportista }),
  sincronizarSeguimiento: (id) => api.get(`/pedidos/${id}/seguimiento`),
  cambiarEstado: (id, estado) => api.patch(`/pedidos/${id}/estado`, { estado }),
  informarCancelacion: (id) => api.post(`/pedidos/${id}/aviso-cancelacion`),
  marcarAvisoVisto: (id) => api.post(`/pedidos/${id}/aviso-cancelacion/visto`),
  resenas: (id) => api.get(`/pedidos/${id}/resenas`),
  resenar: (id, producto_id, estrellas, comentario = null) => 
    api.post(`/pedidos/${id}/resenas`, { producto_id, estrellas, comentario }),
}