
import { Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { Trash2, Minus, Plus, ShoppingCart, Truck, ArrowRight } from 'lucide-react'
import { useCart } from '../context/CartContext.jsx'

const ENVIO_GRATIS_DESDE = 50000

export default function Carrito() {
  const { items, quitarProducto, actualizarCantidad, total } = useCart()
  const envioGratis = total >= ENVIO_GRATIS_DESDE

  if (items.length === 0) {
    return (
      <div className="wrap" style={{ padding: '80px 0', textAlign: 'center' }} >
        <ShoppingCart size={64} strokeWidth={1.5} style={{ display: 'block', margin: '0 auto 20px', color: 'var(--text-dim)' }}
        />
        <p style={{ color: 'var(--text-dim)', marginBottom: 20 }}> Tu carrito está vacío. </p>
        <Link to="/categorias" className="btn btn-primary"> Ver catálogo
        </Link>
      </div>
    )
  }

  return (
    <section className="wrap" style={{ padding: '48px 0 80px' }}>
      <div className="carrito-grid" style={{ display: 'flex', gap: 40, flexWrap: 'wrap' }}>
        <div style={{ flex: 2, minWidth: 340 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 6 }}>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: 0 }}> Tu carrito</h1>
            <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>
              ({items.length} {items.length === 1 ? 'producto' : 'productos'})
            </span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 16 }}>
            Los Productos en tu carrito no están reservados.
          </p>

          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--line)',
            borderRadius: 10,
            padding: 16,
            marginBottom: 24,
          }}
          >
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', margin: '0 0 6px', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Truck size={15} color="#FA7F19" />
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
                borderBottom: '1px solid var(--line)',
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
                  <p style={{ fontWeight: 600, color: 'var(--text)', margin: '0 0 6px', fontSize: 15 }}>
                    {item.nombre}
                  </p>
                  <button
                    type="button"
                    onClick={() => quitarProducto(item.id)}
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
                      onClick={() => actualizarCantidad(item.id, Math.max(1, item.cantidad - 1))}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        width: 32, height: 32, border: 'none', background: 'transparent',
                        color: 'inherit', cursor: 'pointer',
                      }}
                    >
                      <Minus size={15} />
                    </button>
                    <span style={{ minWidth: 32, textAlign: 'center', fontSize: 14, color: 'var(--text)' }}>
                      {item.cantidad}
                    </span>
                    <button
                      type="button"
                      onClick={() => actualizarCantidad(item.id, item.cantidad + 1)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        width: 32, height: 32, border: 'none', background: 'transparent',
                        color: 'inherit', cursor: 'pointer',
                      }}
                    >
                      <Plus size={15} />
                    </button>
                  </div>

                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>
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
              background: 'var(--surface)',
              border: '1px solid var(--line)',
              borderRadius: 12,
              padding: 20,
              position: 'sticky',
              top: 24,
            }}
          >
            <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)', margin: '0 0 16px' }}>
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

            <div style={{
              display: 'flex', justifyContent: 'space-between', fontSize: 16, fontWeight: 600, color: 'var(--text)', paddingTop: 14, borderTop: '1px solid var(--line)', marginBottom: 20
            }}
            >
              <span>Total</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>${Math.round(total * 1.19).toLocaleString('es-CL')} CLP</span>
            </div>

            <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 20px' }}>
              [IVA incluido ${Math.round(total * 0.19).toLocaleString('es-CL')}]
            </p>
            <Link
              to="/checkout"
              className="btn btn-primary"
              style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              Ir a pagar <ArrowRight size={16} />
            </Link>
            <div style={{ paddingTop: 16, borderTop: '1px solid var(--line)' }}>
              <p style={{
                fontSize: 11, fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase', color: 'var(--text-dim)', margin: '0 0 10px',
              }}>
                Formas de pago aceptadas
              </p>
              <div style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                padding: '6px 16px', borderRadius: 6, background: '#ffffffb6',
              }}>
                <img src={mediaPath('tuu.png')} alt="Tuu" style={{ height: 18 }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}


