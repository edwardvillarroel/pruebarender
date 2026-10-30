import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmarPago } from '../services/payment.js'
import { useCart } from '../context/CartContext.jsx'
import { mediaPath } from '../utils/media.js'

const estiloImagen = { display: 'block', width: 200, height: 200, objectFit: 'contain', margin: '0 auto 12px'}

const RESULTADOS_FALLIDOS = ['failed', 'aborted', 'cancelled']

function estadoSegunPasarela(resultado) {
  //if (resultado === 'completed') return 'completado'
  if (RESULTADOS_FALLIDOS.includes(resultado)) return 'fallido'
  return 'verificando'
}

export default function PagoRetorno() {
  const [params] = useSearchParams()
  const { vaciarCarrito } = useCart()

  const resultadoPasarela = (params.get('x_result') || '').toLowerCase()

  // --- DETECCIÓN COTIZACIÓN ---
  const referencia = params.get('x_reference') || params.get('referencia') || ''
  const cotizacionIdLocal = typeof window !== 'undefined' ? localStorage.getItem('pago_cotizacion_en_curso') : null
  const deteccionCotizacion = 
  referencia.toUpperCase().startsWith('COT-') || !!cotizacionIdLocal 
  || !!params.get('cotizacion_id')

  const estadoInicial = estadoSegunPasarela(resultadoPasarela)
  const [esCotizacion, setEsCotizacion] = useState(deteccionCotizacion)
  const [estado, setEstado] = useState(estadoInicial)
  const [mensaje, setMensaje] = useState(
    estadoInicial === 'fallido' ? (deteccionCotizacion ? 'El pago fue rechazado o cancelado. Puedes intentarlo nuevamente desde Mis Cotizaciones.'
      : 'El pago fue rechazado o cancelado. Tu carrito sigue disponible.') : ''
  )
  const [correoEnviado, setCorreoEnviado] = useState(null)
  const confirmadoRef = useRef(false)
  const estadoYaMostradoRef = useRef(estadoInicial === 'fallido')

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
        const esCotizacionRespuesta = Boolean(res.cotizacion_id)
        setEsCotizacion(esCotizacionRespuesta)
        if (res.estado === 'completado') {
          setEstado('completado')
          setCorreoEnviado(res.correo_enviado ?? null)
          if (esCotizacionRespuesta) localStorage.removeItem('pago_cotizacion_en_curso')
          else vaciarCarrito()
        } else if (res.estado === 'fallido') {
          setEstado('fallido')
          setMensaje(
            esCotizacionRespuesta
            ? 'El pago de la cotización fue cancelado. Puedes intentarlo de nuevo desde Mis Cotizaciones.'
            : 'El pago fue rechazado o cancelado. Tu carrito sigue disponible.'
          )
          if (esCotizacionRespuesta) localStorage.removeItem('pago_cotizacion_en_curso')
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
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>
            {esCotizacion ? '¡Cotización pagada con éxito!' : '¡Pedido realizado con éxito!'}
          </h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>
            {esCotizacion 
              ? 'Gracias por confiar en ApoloVibes. Tu diseño personalizado ya está en producción.'
              : correoEnviado === true
                ? 'Gracias por tu compra y confiar en ApoloVibes. Te enviamos el comprobante de pago a tu correo.'
                : correoEnviado === false
                ? 'Gracias por comprar y confiar en ApoloVibes. Tu pago quedó confirmado, pero no pudimos enviarte el comprobante por correo.'
                : 'Gracias por tu compra. Tu pago quedó confirmado.'
            }
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to={esCotizacion ? "/mis-pedidos" : "/"} className="btn btn-primary">
              {esCotizacion ? 'Ver mi pedido' : 'Volver al inicio'}
            </Link>
            {esCotizacion
              ? <Link to="/mis-cotizaciones" className="btn btn-ghost">Ver mis cotizaciones</Link>
              : <Link to="/categorias" className="btn btn-ghost">Seguir comprando</Link>}
          </div>
        </>
      )}

      {(estado === 'fallido' || estado === 'pendiente') && (
        <>
        {estado === 'fallido' && (
            <img src={mediaPath('logoFailCompra.webp')} alt="Pago rechazado" loading="lazy" decoding="async" style={estiloImagen} />
        )}
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>
            {estado === 'fallido' ? (esCotizacion ? 'Pago de cotización cancelado' : 'Pago rechazado') : 'Pago en proceso'}
          </h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>{mensaje}</p>
          <Link to={esCotizacion ? "/mis-cotizaciones" : "/carrito"} className="btn btn-ghost">
            {esCotizacion ? 'Volver a mis cotizaciones' : 'Volver al carrito'}
          </Link>
        </>
      )}

      {estado === 'error' && (
        <>
          <img src={mediaPath('logoFailCompra.webp')} alt="Error en el pago" loading="lazy" decoding="async" style={estiloImagen} />
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>No pudimos confirmar el pago</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>{mensaje}</p>
          <Link to={esCotizacion ? "/mis-cotizaciones" : "/carrito"} className="btn btn-ghost">
            {esCotizacion ? 'Volver a mis cotizaciones' : 'Volver al carrito'}
          </Link>
        </>
      )}
    </section>
  )
}