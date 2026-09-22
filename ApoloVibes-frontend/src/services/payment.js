import { api } from './api.js'

// TUU (Pago Online) crea el intento en el backend y devuelve la URL del
// formulario. Como la pasarela trabaja con X-REDIRECT=false, el navegador
// viaja directo a esa URL (window.location), no se hace POST manual.
export async function iniciarPago({ items, total, cliente, entrega }) {
  const pedido = {
    items: items.map(i => ({ id: i.id, cantidad: i.cantidad })),
    total,
    entrega,
    cliente,
  }

  const { url } = await api.post('/pago/crear', pedido)
  window.location.href = url
}

// TUU devuelve al navegador a /pago/retorno con los parámetros x_* (+firma)
// en la URL. Confirmamos esos parámetros contra el backend, que valida la
// firma y aplica el resultado de forma idempotente (callback server-to-server
// o esta misma confirmación: el que llegue primero gana).
export async function confirmarPago(parametros) {
  return api.post('/pago/confirmar', parametros)
}