import { api } from './api.js'

export const carritoApi = {
  obtener: () => api.get('/cart'),
  agregarProducto: (productoId, cantidad = 1, color = null) =>
    api.post('/cart/items', { producto_id: productoId, cantidad, color }),
  actualizarCantidad: (itemId, cantidad) =>
    api.put(`/cart/items/${itemId}`, { cantidad }),
  eliminarItem: (itemId) => api.del(`/cart/items/${itemId}`),
  vaciar: () => api.del('/cart'),
}