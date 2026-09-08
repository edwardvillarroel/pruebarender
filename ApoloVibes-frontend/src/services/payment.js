import { api } from './api.js'

export async function iniciarPago({ items, total, cliente }) {
  const pedido = {
    items: items.map(i => ({ id: i.id, cantidad: i.cantidad, precio: i.precio })),
    total,
    cliente,
  }


  const { url, token } = await api.post('/pago/crear', pedido)


  const form = document.createElement('form')
  form.method = 'POST'
  form.action = url
  const input = document.createElement('input')
  input.type = 'hidden'
  input.name = 'token_ws'
  input.value = token
  form.appendChild(input)
  document.body.appendChild(form)
  form.submit()
}

export async function confirmarPago(token) {
  return api.post('/pago/confirmar', { token })
}
