import { useParams, Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { useState } from 'react'
import { useProductos } from '../context/ProductContext.jsx'
import { useCart } from '../context/CartContext.jsx'
import { Minus, Plus } from 'lucide-react'

const COLOR_NUEVO = '#2fa018'
const COLOR_DESCUENTO = '#FA7F19'
const COLOR_SIN_STOCK = '#e71414'
const COLOR_BUTTON = '#FA7F19'

export default function ProductoDetalle() {
  const { id } = useParams()
  const { productos, categorias, cargando } = useProductos()
  const producto = productos.find(p => p.id === id)
  const { agregarProducto } = useCart()
  const [cantidad, setCantidad] = useState(1)

  if (cargando) return <div className="wrap" style={{ padding: 80 }}>Cargando…</div>
  if (!producto) return <div className="wrap" style={{ padding: 80 }}>Producto no encontrado.</div>

  const categoria = categorias.find(c => c.id === producto.categoria_id)

  return (
    <section className="wrap" style={{ paddingTop: '48px', paddingBottom: '80px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 13,
        color: 'var(--text-dim)',
        marginBottom: 20
      }}>
        <Link to="/categorias" style={{ color: 'var(--surface)' }}>Catálogo</Link>
        {categoria && (
          <>
            <span></span>
            <Link to={`/categorias?cat=${categoria.id}`} style={{ color: 'var(--accent)' }}>{categoria.nombre}</Link>
          </>
        )}
        <span></span>
        <span style={{ color: 'var(--surface)' }}>{producto.nombre}</span>
      </div>

      <div className="producto-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48 }}>
        <div style={{
          position: 'relative',
          height: 420,
          background: producto.imagen ? '#FFFFFF' : 'var(--surface)',
          border: '1px solid var(--border-card)',
          borderRadius: 12,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
        >
          {producto.imagen && (
            <img
              src={producto.imagen}
              alt={producto.nombre}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain'
              }}
            />
          )}

          {producto.sinStock ? (
            <span style={{
              position: 'absolute',
              top: 30,
              right: -70,
              width: 210,
              transform: 'rotate(45deg)',
              background: COLOR_SIN_STOCK,
              color: '#FFFFFF',
              fontSize: 12,
              fontWeight: 500,
              lineHeight: '1.4',
              padding: '5px 0',
              textAlign: 'center',
            }}
            >
              SIN STOCK
            </span>
          ) : producto.descuento ? (
            <span style={{
              position: 'absolute',
              top: 30,
              right: -70,
              width: 210,
              transform: 'rotate(45deg)',
              background: COLOR_DESCUENTO,
              color: '#FFFFFF',
              fontSize: 12,
              fontWeight: 500,
              lineHeight: '1.4',
              padding: '5px 0',
              textAlign: 'center',
            }}
            >
              -{producto.descuento}%
            </span>
          ) : producto.badge ? (
            <div style={{
              position: 'absolute',
              top: 30,
              right: -70,
              width: 210,
              transform: 'rotate(45deg)',
              background: COLOR_NUEVO,
              color: '#FFFFFF',
              fontSize: 12,
              fontWeight: 500,
              lineHeight: '1.4',
              padding: '5px 0',
              textAlign: 'center',
            }}
            >
              {producto.badge}
            </div>
          ) : null}
        </div>

        <div>
          {categoria && (
            <span style={{
              display: 'inline-block',
              background: '#FA7F19',
              color: '#FFFFFF',
              fontSize: 11,
              padding: '3px 10px',
              borderRadius: 999,
              marginBottom: 12,
            }}
            >
              {categoria.nombre}
            </span>
          )}
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 30, marginBottom: 14, color: 'var(--surface)' }}>{producto.nombre}</h1>
          {producto.descripcion && (
            <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 24, maxWidth: 420 }}>
              {producto.descripcion}
            </p>
          )}
          {producto.specs && producto.specs.length > 0 && (
            <ul style={{
              listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 420
            }}>
              {producto.specs.map((spec, i) => (
                <li
                  key={i}
                  style={{
                    fontSize: 13,
                    color: 'var(--text-dim)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                  }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#FA7F19', marginTop: 6, flexShrink: 0 }} />
                  {spec}
                </li>
              ))}
            </ul>
          )}
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 10,
            marginBottom: 24
          }}>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 22,
              color: 'var(--surface)'
            }}>
              ${producto.precio.toLocaleString('es-CL')} CLP
            </span>
            {producto.precioOriginal && (
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 15,
                color: 'var(--text-dim)',
                textDecoration: 'line-through',
              }}
              >
                ${producto.precioOriginal.toLocaleString('es-CL')}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', border: '1px solid var(--line)', borderRadius: 6, overflow: 'hidden' }}>
              <button
                onClick={() => setCantidad(c => Math.max(1, c - 1))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 36,
                  height: 36,
                  border: 'none',
                  background: 'transparent',
                  color: 'inherit',
                  cursor: 'pointer',
                }}
              >
                <Minus size={16} style={{ color: 'var(--surface-2)' }} />
              </button>
              <span style={{ width: 32, textAlign: 'center', textAlign: 'center', fontSize: 14, color: 'var(--surface-2)' }}>{cantidad}</span>
              <button onClick={() => setCantidad(c => c + 1)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 36,
                  height: 36,
                  border: 'none',
                  background: 'transparent',
                  color: 'inherit',
                  cursor: 'pointer',
                }}
              >
                <Plus size={16} style={{ color: 'var(--surface-2)' }} />
              </button>
            </div>

            <button
              className="btn btn-primary"
              disabled={producto.sinStock}
              onClick={() => agregarProducto(producto, cantidad)}
              style={{
                flex: 1,
                background: producto.sinStock ? 'var(--surface-2)' : COLOR_BUTTON,
                color: producto.sinStock ? 'var(--text-dim)' : '#FFFFFF',
                cursor: producto.sinStock ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8
              }}
            >
              {!producto.sinStock && (
                <img
                  src={mediaPath('cart.png')}
                  alt=""
                  style={{ width: 20, height: 20, filter: 'brightness(0) invert(1)' }}
                />
              )}
              {producto.sinStock ? 'Sin Stock' : 'Agregar al carrito'}
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}



