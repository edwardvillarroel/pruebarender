import { api } from './api.js'

export const ventasApi = {
  abrirSesion: (lugar) => api.post('/ventas/sesiones', { lugar }),
  sesionActual: () => api.get('/ventas/sesiones/actual'),
  registrarVenta: (sesionId, medioPago, items) =>
    api.post(`/ventas/sesiones/${sesionId}/ventas`, { medio_pago: medioPago, items }),
  cerrarSesion: (sesionId) => api.post(`/ventas/sesiones/${sesionId}/cierre`),
  listarReportes: () => api.get('/ventas/reportes'),
  detalleReporte: (id) => api.get(`/ventas/reportes/${id}`),
}