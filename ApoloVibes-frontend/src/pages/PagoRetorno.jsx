import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmarPago } from '../services/payment.js'
import { useCart } from '../context/CartContext.jsx'

// TUU redirige aquí (x_url_complete) con los parámetros x_* en la URL y su
// firma. Esta página solo confirma la transacción contra el backend y muestra
// el resultado — nunca decide por sí sola si el pago fue exitoso.
export default function PagoRetorno() {
  const [params] = useSearchParams()
  const { vaciarCarrito } = useCart()
  // verificando | completado | fallido | pendiente | error
  const [estado, setEstado] = useState('verificando')
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    const parametros = Object.fromEntries(params.entries())
    if (!parametros.x_reference) {
      setEstado('error')
      setMensaje('No se recibió la referencia del pago.')
      return
    }

    confirmarPago(parametros)
      .then(res => {
        if (res.estado === 'completado') {
          setEstado('completado')
          vaciarCarrito()
        } else if (res.estado === 'fallido') {
          setEstado('fallido')
          setMensaje('El pago fue rechazado o cancelado. Tu carrito sigue disponible.')
        } else {
          setEstado('pendiente')
          setMensaje('Tu pago aún está en proceso. Te avisaremos cuando se confirme.')
        }
      })
      .catch(() => {
        setEstado('error')
        setMensaje('No pudimos confirmar tu pago. Intenta nuevamente.')
      })
  }, [params, vaciarCarrito])

  return (
    <section className="wrap" style={{ paddingTop: '100px', paddingBottom: '100px', textAlign: 'center' }}>
      {estado === 'verificando' && <p style={{ color: 'var(--text-dim)' }}>Verificando tu pago…</p>}

      {estado === 'completado' && (
        <>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>Pago confirmado</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>Te enviamos el comprobante a tu correo.</p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/" className="btn btn-primary">Volver al inicio</Link>
            <Link to="/categorias" className="btn btn-ghost">Seguir comprando</Link>
          </div>
        </>
      )}

      {(estado === 'fallido' || estado === 'pendiente') && (
        <>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>
            {estado === 'fallido' ? 'Pago rechazado' : 'Pago en proceso'}
          </h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>{mensaje}</p>
          <Link to="/carrito" className="btn btn-ghost">Volver al carrito</Link>
        </>
      )}

      {estado === 'error' && (
        <>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>No pudimos confirmar el pago</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>{mensaje}</p>
          <Link to="/carrito" className="btn btn-ghost">Volver al carrito</Link>
        </>
      )}
    </section>
  )
}