import { api } from './api.js'

export const usuariosApi = {
  listar: () => api.get('/usuarios'),
  crear: (datos) => api.post('/usuarios', datos),
  cambiarRol: (id, rol) => api.patch(`/usuarios/${id}/rol`, { rol }),
  cambiarEstado: (id, activo) => api.patch(`/usuarios/${id}/estado`, { activo }),
  eliminar: (id) => api.del(`/usuarios/${id}`),
}
