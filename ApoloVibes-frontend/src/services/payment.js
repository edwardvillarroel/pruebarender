import { api } from './api.js'
import { VERSION_LEGAL } from './legal.js'

export async function iniciarPago({ items, cliente, entrega, totalEsperado, claveIdempotencia,
  guardarDatos, mayorEdad, aceptaTerminos}) {

  // `total` no se manda: el backend recalcula el total desde `productos.precio`
  // y lo contrasta con `totalEsperado` (409 si no coincide). Mandar el total
  // tambien seria redundante con `totalEsperado`, que es el numero que SI
  // valida el backend.
  //
  // El `rut` se normaliza a proposito: el backend lo guarda crudo en el pedido
  // y TUU manda el comprobante con ese valor. "12.345.678-9" y "123456789"
  // tienen que ser el mismo cliente.
  const pedido = {
    items: items.map(i => ({
      id: i.id,
      cantidad: i.cantidad,
      ...(i.color ? { color: i.color } : {}),
    })),
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
    versionLegal: VERSION_LEGAL
  }

  const data = await api.post('/pago/crear', pedido)
  if (!data.url) throw new Error('No se pudo iniciar el pago')

  // Sin guardar `data.token` en sessionStorage: nadie lo leia. El resultado del
  // pago vuelve por la query `x_*` de la redireccion de TUU, que es lo que
  // `confirmarPago` manda a `/pago/confirmar`. Ademas el sessionStorage no
  // sobrevive al ida y vuelta a la pasarela, asi que un token guardado ahi
  // seria practicamente inaccesible igual.
  window.location.href = data.url
}


export async function confirmarPago(parametros) {
  return api.post('/pago/confirmar', parametros)
}