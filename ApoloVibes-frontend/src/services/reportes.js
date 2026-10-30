import { api } from './api.js'

export const reportesApi = {
  resumen: () => api.get('/reportes'),
}
