import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmarPago } from '../services/payment.js'
import { useCart } from '../context/CartContext.jsx'
import { mediaPath } from '../utils/media.js'

const estiloImagen = { display: 'block', width: 200, height: 200, ObjectFit: 'contain', margin: '0 auto 12px'}

export default function PagoRetorno() {
  const [params] = useSearchParams()
  const { vaciarCarrito } = useCart()
  const [estado, setEstado] = useState('verificando')
  const [mensaje, setMensaje] = useState('')
  const [correoEnviado, setCorreoEnviado] = useState(null)
  const confirmadoRef = useRef(false)

  useEffect(() => {
    if (confirmadoRef.current) return
    confirmadoRef.current = true

    const parametros = {
      ...Object.fromEntries(new URLSearchParams(window.location.search).entries()),
      ...Object.fromEntries(params.entries()),
    }
    if (!parametros.x_reference) {
      setEstado('error')
      setMensaje('No se recibió la referencia del pago.')
      return
    }

    confirmarPago(parametros)
      .then(res => {
        if (res.estado === 'completado') {
          setEstado('completado')
          setCorreoEnviado(res.correo_enviado ?? null)
          vaciarCarrito()
        } else if (res.estado === 'fallido') {
          setEstado('fallido')
          setMensaje('El pago fue rechazado o cancelado. Tu carrito sigue disponible.')
        } else {
          setEstado('pendiente')
          setMensaje('Tu pago aún está en proceso. Te avisaremos cuando se confirme.')
        }
      })
      .catch(err => {
        setEstado('error')
        setMensaje(err?.message || 'No pudimos confirmar tu pago. Intenta nuevamente.')
      })
  }, [params, vaciarCarrito])

  return (
    <section className="wrap" style={{ paddingTop: '100px', paddingBottom: '100px', textAlign: 'center' }}>
      {estado === 'completado' && (
        <>
          <img src={mediaPath('logoExitoCompra.png')} alt="Pago exitoso" style={estiloImagen} />
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>¡Pedido realizado con éxito!</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>
            {correoEnviado === true && 'Gracias por tu comprar y confiar en ApoloVibes. Te enviamos el comprobante de pago a tu correo.'}
            {correoEnviado === false && (
              <>
                Gracias por comprar y confiar en ApoloVibes. Tu pago quedó confirmado, pero no pudimos enviarte el
                comprobante por correo. Si no lo recibes, escríbenos y te lo mandamos.
              </>
            )}
            {correoEnviado === null && 'Gracias por tu compra. Tu pago quedó confirmado.'}
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/" className="btn btn-primary">Volver al inicio</Link>
            <Link to="/categorias" className="btn btn-ghost">Seguir comprando</Link>
          </div>
        </>
      )}

      {(estado === 'fallido' || estado === 'pendiente') && (
        <>
        {estado === 'fallido' && (
            <img src={mediaPath('logoFailCompra.png')} alt="Pago rechazado" style={estiloImagen} />
        )}
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>
            {estado === 'fallido' ? 'Pago rechazado' : 'Pago en proceso'}
          </h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>{mensaje}</p>
          <Link to="/carrito" className="btn btn-ghost">Volver al carrito</Link>
        </>
      )}

      {estado === 'error' && (
        <>
          <img src={mediaPath('logoFailCompra.png')} alt="Error en el pago" style={estiloImagen} />
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>No pudimos confirmar el pago</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>{mensaje}</p>
          <Link to="/carrito" className="btn btn-ghost">Volver al carrito</Link>
        </>
      )}
    </section>
  )
}