import { Link, useNavigate } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { Trash2, Minus, Plus, ShoppingCart, Truck, Tag } from 'lucide-react'
import { useCart } from '../context/CartContext.jsx'
import { api } from '../services/api.js'
import { useState } from 'react'

const ENVIO_GRATIS_DESDE = 50000

export default function Carrito() {
  const { items, quitarItem, actualizarCantidadItem, vaciarCarrito, error, total, requiereLogin, abrirLogin } = useCart()
  const navigate = useNavigate() || ((path) => { window.location.hash = `#${path}` })
  const envioGratis = total >= ENVIO_GRATIS_DESDE
  const cantidadTotal = items.reduce((acc, item) => acc + item.cantidad, 0)
  const [cuponCodigo, setCuponCodigo] = useState('')
  const [cupon, setCupon] = useState(null)
  const [cuponError, setCuponError] = useState('')
  const [aplicandoCupon, setAplicandoCupon] = useState(false)
  const [redirigiendo, setRedirigiendo] = useState(false)

  const montoDescuento = items.reduce((acc, item) => {
    if (item.precio_original && item.precio_original > item.precio) {
      return acc + (item.precio_original - item.precio) * item.cantidad
    }
    return acc
  }, 0)


  const subtotal = items.reduce((acc, item) => {
    const base = item.precio_original && item.precio_original > item.precio
      ? item.precio_original
      : item.precio
    return acc + base * item.cantidad
  }, 0)

  let totalConCupon = total
  if (cupon) {
    if (cupon.tipo === 'porcentaje') {
      const desc = Math.round((total * Number(cupon.valor)) / 100)
      totalConCupon = Math.max(0, total - desc)
    } else if (cupon.tipo === 'monto') {
      const desc = Number(cupon.valor)
      totalConCupon = Math.max(0, total - desc)
    }
  }
  const montoCupon = Math.max(0, total - totalConCupon)
  const descuentoTotal = montoDescuento + montoCupon
  const montoConIva = totalConCupon
  const montoNeto = Math.round(montoConIva / 1.19)
  const montoIva = montoConIva - montoNeto

  async function aplicarCupon() {
    if (requiereLogin) {
      if (typeof abrirLogin === 'function') abrirLogin()
      return
    }
    setCuponError('')
    setAplicandoCupon(true)
    try {
      const res = await api.post('/cupones/validar', { codigo: cuponCodigo })
      const data = res.data || res
      setCupon(data.cupon || null)
    } catch (err) {
      setCupon(null)
      setCuponError(err?.response?.data?.error || 'Cupón inválido')
    } finally {
      setAplicandoCupon(false)
    }
  }

  function quitarCupon() {
    setCupon(null)
    setCuponCodigo('')
    setCuponError('')
  }

  function irAlCheckout() {
    setRedirigiendo(true)
    try {
      navigate('/checkout', { state: { cupon } })
    } catch (e) {
      try {
        window.location.hash = '#/checkout'
      } catch (e2) {
        setRedirigiendo(false)
      }
    }
  }

  if (requiereLogin) {
    return (
      <div className="wrap" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', justifyContent: 'center' }}>
        <ShoppingCart size={64} strokeWidth={1.5} style={{ marginBottom: 20, color: 'var(--text-dim)' }} />
        <p style={{ color: 'var(--text-dim)', marginBottom: 20 }}>
          Inicia sesión para ver tu carrito y seguir comprando.
        </p>
        <button className="btn btn-primary" onClick={abrirLogin}>
          Iniciar sesión
        </button>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="wrap" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', justifyContent: 'center' }}>
        <img
          src={mediaPath('carritoVacio.webp')}
          alt="Carrito vacío"
          loading="lazy"
          decoding="async"
          width="512"
          height="512"
          style={{ display: 'block', height: 100, width: 'auto', margin: '0 auto 0' }}
        />
        <p style={{ color: 'var(--text-dim)', marginBottom: 20 }}> Tu carrito está vacío. </p>
        <Link to="/categorias" className="btn btn-primary"> Ver catálogo</Link>
      </div>
    )
  }

  return (
    <section className="wrap" style={{ paddingTop: '48px', paddingBottom: '80px' }}>
      <div className="carrito-grid" style={{ display: 'flex', gap: 40, flexWrap: 'wrap' }}>
        <div style={{ flex: 2, minWidth: 340 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 6 }}>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: 0, color: 'var(--surface)' }}> Tu carrito</h1>
            <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>
              ({cantidadTotal} {cantidadTotal === 1 ? 'producto' : 'productos'})
            </span>
            <button
              type="button"
              onClick={() => window.confirm('¿Vaciar todo el carrito?') && vaciarCarrito()}
              style={{
                marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-dim)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 5,
              }}
            >
              <Trash2 size={15} /> Vaciar carrito
            </button>
          </div>
          {error && (
            <p style={{ color: '#ef4444', fontSize: 13, margin: '0 0 12px' }}>{error}</p>
          )}
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 16 }}>
            Los Productos en tu carrito no están reservados.
          </p>

          <div style={{
            background: 'var(--border-card2)',
            border: '1px solid var(--line)',
            borderRadius: 10,
            padding: 16,
            marginBottom: 24,
          }}
          >
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--surface-2)', margin: '0 0 6px', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Truck size={20} color="#FA7F19" />
              {envioGratis ? 'Tu pedido tiene envio gratis' : `Envío gratis en compras sobre $${ENVIO_GRATIS_DESDE.toLocaleString('es-CL')}`}
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0, lineHeight: 1.5 }}>
              {envioGratis ? 'Felicidades, no pagarás costo de envio en esta compra.' : 'Bajo ese monto se aplica costo de envío segun la empresa de transporte.'}
            </p>
          </div>

          {items.map(item => (
            <div
              key={item.id}
              style={{
                display: 'flex',
                gap: 16,
                paddingBottom: 20,
                marginBottom: 20,
                borderBottom: '1px solid var(--surface-3)',
              }}
            >
              <div
                style={{
                  width: 110,
                  height: 110,
                  borderRadius: 8,
                  overflow: 'hidden',
                  background: item.imagen ? '#FFFFFF' : 'var(--surface-2)',
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {item.imagen && (
                  <img
                    src={item.imagen}
                    alt={item.nombre}
                    loading="lazy"
                    decoding="async"
                    width="110"
                    height="110"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                )}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <p style={{ fontWeight: 600, margin: '0 0 6px', fontSize: 15, color: 'var(--surface)' }}>
                    {item.nombre}
                  </p>
                  <button
                    type="button"
                    onClick={() => quitarItem(item.itemId)}
                    aria-label={`Quitar ${item.nombre} del carrito`}
                    title="Quitar producto"
                    style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 4 }}
                  >
                    <Trash2 size={20} />
                  </button>
                </div>

                {item.color && (
                  <p style={{ margin: '0 0 5px', fontSize: 12, color: 'var(--text-dim)', marginTop: -5 }}>
                    Color: {item.color}
                  </p>
                )}

                <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 16px' }}>
                  ${item.precio.toLocaleString('es-CL')} c/u
                </p>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    border: '1px solid var(--line)',
                    borderRadius: 6,
                    overflow: 'hidden',
                  }}
                  >
                    <button
                      type="button"
                      onClick={() => actualizarCantidadItem(item.itemId, Math.max(1, item.cantidad - 1))}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        width: 32, height: 32, border: 'none', background: 'var(--surface-3)',
                        color: 'inherit', cursor: 'pointer',
                      }}
                    >
                      <Minus size={15} style={{ color: 'var(--surface-2)' }} />
                    </button>
                    <span style={{ minWidth: 32, textAlign: 'center', fontSize: 14, color: 'var(--surface-2)' }}>
                      {item.cantidad}
                    </span>
                    <button
                      type="button"
                      onClick={() => actualizarCantidadItem(item.itemId, item.cantidad + 1)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        width: 32, height: 32, border: 'none', background: 'var(--surface-3)',
                        color: 'inherit', cursor: 'pointer',
                      }}
                    >
                      <Plus size={15} style={{ color: 'var(--surface-2)' }} />
                    </button>
                  </div>

                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 15, fontWeight: 600, color: 'var(--surface-2)' }}>
                    ${(item.precio * item.cantidad).toLocaleString('es-CL')}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, minWidth: 260 }}>
          <div
            style={{
              background: 'var(--surface-3)',
              border: '1px solid var(--surface-2)',
              borderRadius: 12,
              padding: 20,
              position: 'sticky',
              top: 24,
            }}
          >
            <img src={mediaPath('apolo-vibes-logo.webp')} alt='logo-icon' className='logoicon' loading="lazy" decoding="async" width="447" height="512" />
            <img src={mediaPath('nombrelogo.webp')} alt='logo' className='nombre-logo' loading="lazy" decoding="async" width="512" height="72" />
            <h2 style={{ fontSize: 15, fontWeight: 300, color: 'var(--accent)', marginBottom: '20px', textAlign: 'center' }}>
              Resumen del pedido
            </h2>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
              <span>{cantidadTotal} {cantidadTotal === 1 ? 'producto' : 'productos'}</span>
              <span>${subtotal.toLocaleString('es-CL')}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 16 }}>
              <span>Envío</span>
              <span>{envioGratis ? 'Gratis' : 'Se calcula al pagar'}</span>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, color: 'var(--surface-2)', fontSize: 13 }}>
                <span>¿Tienes cupón de descuento?</span>
              </div>
              {cupon ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--surface-4)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                    {cupon.codigo}
                  </div>
                  <button type="button" onClick={quitarCupon} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: 12 }}>Quitar</button>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    value={cuponCodigo}
                    onChange={(e) => setCuponCodigo(e.target.value.toUpperCase())}
                    placeholder="Ingresa tu código"
                    style={{ flex: 1, padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--bg)', color: 'var(--surface-2)', fontSize: 13}}
                  />
                  <button type="button" onClick={aplicarCupon} disabled={aplicandoCupon || !cuponCodigo.trim()} className="btn btn-ghost" style={{ padding: '8px 12px', fontSize: 13 }}>
                    {aplicandoCupon ? 'Aplicando' : 'Aplicar'}
                  </button>
                </div>
              )}
              {cuponError && <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0' }}>{cuponError}</p>}
            </div>

            <div className="separador-suave" style={{ display: 'flex', flexDirection: 'column', fontSize: 16, color: 'var(--text)', paddingTop: 14, marginBottom: 20 }}>
              {cupon && montoCupon > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
                  <span>Cupón de descuento</span>
                  <span>-${montoCupon.toLocaleString('es-CL')}</span>
                </div>
              )}
              {montoDescuento > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
                  <span>Descuento</span>
                  <span>-${montoDescuento.toLocaleString('es-CL')}</span>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
                <span>Monto neto</span>
                <span>${montoNeto.toLocaleString('es-CL')}</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
                <span>IVA (19%)</span>
                <span>${montoIva.toLocaleString('es-CL')}</span>
              </div>
              <div className="separador-suave" style={{ display: 'flex', flexDirection: 'column', fontSize: 16, color: 'var(--text)', marginBottom: 20 }}></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15, color: 'var(--text-dim)', marginBottom: 8, fontWeight: 600 }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>Total</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>${montoConIva.toLocaleString('es-CL')}</span>
              </div>
            </div>
            <h1 style={{ fontSize: 14, color: 'var(--surface)', textAlign: 'justify', margin: '0 0 5px' }}>
              Información Del Pago
            </h1>
            <p style={{ fontSize: 11, marginTop: -5, color: 'var(--text-dim)', textAlign: 'justify', margin: '0 0 10px' }}>
              Todas las transacciones son realizadas mediante conexión segura. La información de tu tarjetas no se guarda en este sitio*
            </p>

            <button
              type="button"
              onClick={irAlCheckout}
              disabled={redirigiendo}
              className="btn btn-primary"
              style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, color: 'var(--text)', marginBottom: 12 }}>
              Paga con Tuu
            </button>

            <p style={{ fontSize: 11, marginTop: -5, color: 'var(--text-dim)', textAlign: 'justify', margin: '0 0 20px' }}>
              Tus datos personales se utilizarán para procesar tu pedido y mejorar tu experiencia en Apolovibes3D.
            </p>
            <div className="separador-suave" style={{ paddingTop: 16 }}>
              <p style={{
                fontSize: 11, fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase', color: 'var(--text-dim)', margin: '0 0 10px',
              }}>
                Formas de pago aceptadas
              </p>
              <div style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                padding: '6px 16px', borderRadius: 6, background: '#ffffffb6',
              }}>
                <img src={mediaPath('tuu.png')} alt="Tuu" style={{ height: 25 }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}