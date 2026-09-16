import { api } from './api.js'

export const carritoApi = {
  obtener: () => api.get('/cart'),
  agregarProducto: (productoId, cantidad = 1) =>
    api.post('/cart/items', { producto_id: productoId, cantidad }),
  actualizarCantidad: (itemId, cantidad) =>
    api.put(`/cart/items/${itemId}`, { cantidad }),
  eliminarItem: (itemId) => api.del(`/cart/items/${itemId}`),
  vaciar: () => api.del('/cart'),
  // TODO: mock temporal — simula la venta completada (descarta stock y vacía
  // el carrito). Reemplazar por el flujo real de pago (POST /pago/crear) cuando exista.
  finalizarCompra: () => api.post('/cart/finalizar-compra-mock'),
}