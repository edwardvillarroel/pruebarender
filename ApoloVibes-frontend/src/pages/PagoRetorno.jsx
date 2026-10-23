import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmarPago } from '../services/payment.js'
import { useCart } from '../context/CartContext.jsx'
import { mediaPath } from '../utils/media.js'

const estiloImagen = { display: 'block', width: 200, height: 200, objectFit: 'contain', margin: '0 auto 12px'}

const RESULTADOS_FALLIDOS = ['failed', 'aborted', 'cancelled']

function estadoSegunPasarela(resultado) {
  if (resultado === 'completed') return 'completado'
  if (RESULTADOS_FALLIDOS.includes(resultado)) return 'fallido'
  return 'verificando'
}

export default function PagoRetorno() {
  const [params] = useSearchParams()
  const { vaciarCarrito, cargarCarrito } = useCart()
  const resultadoPasarela = (params.get('x_result') || '').toLowerCase()
  const estadoInicial = estadoSegunPasarela(resultadoPasarela)
  const [estado, setEstado] = useState(estadoInicial)
  const [mensaje, setMensaje] = useState(
    estadoInicial === 'fallido' ? 'El pago fue rechazado o cancelado. Tu carrito sigue disponible.' : ''
  )
  const [correoEnviado, setCorreoEnviado] = useState(null)
  const confirmadoRef = useRef(false)
  const estadoYaMostradoRef = useRef(estadoInicial !== 'verificando')
  const vaciadoOptimistaRef = useRef(false)

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

    if (resultadoPasarela === 'completed') {
      vaciadoOptimistaRef.current = true
      vaciarCarrito()
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
          if (vaciadoOptimistaRef.current) cargarCarrito()
        } else {
          setEstado('pendiente')
          setMensaje('Tu pago aún está en proceso. Te avisaremos cuando se confirme.')
        }
      })
      .catch(err => {
        if (estadoYaMostradoRef.current) return
        setEstado('error')
        setMensaje(err?.message || 'No pudimos confirmar tu pago. Intenta nuevamente.')
      })
  }, [params, vaciarCarrito])

  return (
    <section className="wrap" style={{ paddingTop: '100px', paddingBottom: '100px', textAlign: 'center' }}>
      {estado === 'verificando' && (
        <>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>Confirmando tu pago…</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>Estamos verificando el resultado con la pasarela.</p>
        </>
      )}

      {estado === 'completado' && (
        <>
          <img src={mediaPath('logoExitoCompra.webp')} alt="Pago exitoso" loading="lazy" decoding="async" style={estiloImagen} />
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
            <img src={mediaPath('logoFailCompra.webp')} alt="Pago rechazado" loading="lazy" decoding="async" style={estiloImagen} />
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
          <img src={mediaPath('logoFailCompra.webp')} alt="Error en el pago" loading="lazy" decoding="async" style={estiloImagen} />
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>No pudimos confirmar el pago</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>{mensaje}</p>
          <Link to="/carrito" className="btn btn-ghost">Volver al carrito</Link>
        </>
      )}
    </section>
  )
}