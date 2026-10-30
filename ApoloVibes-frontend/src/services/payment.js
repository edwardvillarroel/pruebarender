import { api } from './api.js'
import { VERSION_LEGAL } from './legal.js'

export async function iniciarPago({ items, cliente, entrega, totalEsperado, claveIdempotencia,
  guardarDatos, mayorEdad, aceptaTerminos, cuponCodigo, cotizacionId}) {
  const pedido = {
    ...(cotizacionId
      ? { cotizacionId }
      : {
          items: (items || []).map(i => ({
            id: i.id,
            cantidad: i.cantidad,
            ...(i.color ? { color: i.color } : {}),
          })),
        }),
    entrega,
    cliente: {
      ...cliente,
      rut: (cliente.rut ?? '').replace(/[.\s]/g, '').toUpperCase(),
    },
    totalEsperado,
    claveIdempotencia,
    guardarDatos: !!guardarDatos,
    mayorEdad: !!mayorEdad,
    aceptaTerminos: !!aceptaTerminos,
    versionLegal: VERSION_LEGAL,
    cuponCodigo: cuponCodigo || ''
  }

  const data = await api.post('/pago/crear', pedido)
  if (!data.url) throw new Error('No se pudo iniciar el pago')

  window.location.href = data.url
}


export async function confirmarPago(parametros) {
  return api.post('/pago/confirmar', parametros)
}