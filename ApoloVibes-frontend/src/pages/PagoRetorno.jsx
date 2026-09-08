import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { confirmarPago } from '../services/payment.js'
import { useCart } from '../context/CartContext.jsx'

// Transbank redirige aquí con el token por POST (o query en algunos flujos).
// Esta página solo confirma la transacción contra el backend y muestra
// el resultado — nunca decide por sí sola si el pago fue exitoso.
export default function PagoRetorno() {
  const [params] = useSearchParams()
  const { vaciarCarrito } = useCart()
  const [estado, setEstado] = useState('verificando') // verificando | ok | error

  useEffect(() => {
    const token = params.get('token_ws')
    if (!token) { setEstado('error'); return }

    confirmarPago(token)
      .then(() => { setEstado('ok'); vaciarCarrito() })
      .catch(() => setEstado('error'))
  }, [params])

  return (
    <section className="wrap" style={{ padding: '100px 0', textAlign: 'center' }}>
      {estado === 'verificando' && <p style={{ color: 'var(--text-dim)' }}>Verificando tu pago…</p>}
      {estado === 'ok' && (
        <>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>Pago confirmado</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>Te enviamos el comprobante a tu correo.</p>
          <Link to="/" className="btn btn-primary">Volver al inicio</Link>
        </>
      )}
      {estado === 'error' && (
        <>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>No pudimos confirmar el pago</h1>
          <Link to="/carrito" className="btn btn-ghost">Volver al carrito</Link>
        </>
      )}
    </section>
  )
}
