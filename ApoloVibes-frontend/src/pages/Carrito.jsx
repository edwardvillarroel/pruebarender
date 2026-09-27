
import { Link, useNavigate } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { Trash2, Minus, Plus, ShoppingCart, Truck, ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { useCart } from '../context/CartContext.jsx'

const ENVIO_GRATIS_DESDE = 50000

export default function Carrito() {
  const { items, quitarItem, actualizarCantidadItem, vaciarCarrito, error, total, requiereLogin, abrirLogin } = useCart()
  const navigate = useNavigate()
  const envioGratis = total >= ENVIO_GRATIS_DESDE

  if (requiereLogin) {
    return (
      <div className="wrap" style={{ paddingTop: '80px', paddingBottom: '80px', textAlign: 'center' }} >
        <ShoppingCart size={64} strokeWidth={1.5} style={{ display: 'block', margin: '0 auto 20px', color: 'var(--text-dim)' }}
        />
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
      <div className="wrap" style={{ paddingTop: '80px', paddingBottom: '80px', textAlign: 'center' }} >
        <ShoppingCart size={64} strokeWidth={1.5} style={{ display: 'block', margin: '0 auto 20px', color: 'var(--text-dim)' }}
        />
        <p style={{ color: 'var(--text-dim)', marginBottom: 20 }}> Tu carrito está vacío. </p>
        <Link to="/categorias" className="btn btn-primary"> Ver catálogo
        </Link>
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
              ({items.length} {items.length === 1 ? 'producto' : 'productos'})
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
              {envioGratis ? 'Felicidades, no pagarás costo de envio en esta compra.' : 'Bajo ese monto no se aplica un costo de envío fijo según tu comuna.'}
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
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                )}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <p style={{ fontWeight: 600, color: 'var(--text)', margin: '0 0 6px', fontSize: 15, color: 'var(--surface)' }}>
                    {item.nombre}
                  </p>
                  {item.color && (
                    <p style={{ margin: '0 0 6px', fontSize: 12, color: 'var(--text-dim)' }}>
                      Color: {item.color}
                    </p>
                  )}
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
                        width: 32, height: 32, border: 'none', background: 'transparent',
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
                        width: 32, height: 32, border: 'none', background: 'transparent',
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
            <img src={mediaPath('apolo-vibes-logo.png')} alt='logo-icon' className='logoicon'></img>
            <img src={mediaPath('nombrelogo.png')} alt='logo' className='nombre-logo'></img>
            <h2 style={{ fontSize: 15, fontWeight: 300, color: 'var(--accent)', marginBottom: '20px', textAlign: 'center' }}>
              Resumen del pedido
            </h2>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
              <span>{items.length} {items.length === 1 ? 'producto' : 'productos'}</span>
              <span>${total.toLocaleString('es-CL')}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 16 }}>
              <span>Envío</span>
              <span>{envioGratis ? 'Gratis' : 'Se calcula al pagar'}</span>
            </div>

            <div className="separador-suave" style={{
              display: 'flex', justifyContent: 'space-between', fontSize: 16, fontWeight: 600, color: 'var(--text)', paddingTop: 14, marginBottom: 20
            }}
            >
              <span style={{ color: 'var(--surface-2)' }}>Total</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>${Math.round(total * 1.19).toLocaleString('es-CL')} CLP</span>
            </div>

            <p style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20, marginTop: -15 }}>
              [IVA incluido ${Math.round(total * 0.19).toLocaleString('es-CL')}]
            </p>
            <button
              type="button"
              onClick={() => navigate('/checkout')}
              className="btn btn-primary"
              style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, color: 'var(--text)', marginBottom: 12 }}>
              Ir a pagar
              <ArrowRight size={16} color='var(--text)' />
            </button>
            <p style={{ fontSize: 11, color: 'var(--text-dim)', textAlign: 'center', margin: '0 0 20px' }}>
              Pago procesado de forma segura por Tuu.
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
    </section >
  )
}


