import { useParams, Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { useState, useMemo, useEffect } from 'react'
import { useProductos } from '../context/ProductContext.jsx'
import { useCart } from '../context/CartContext.jsx'
import { Minus, Plus, Star } from 'lucide-react'
import ProductCard from '../components/ProductCard.jsx'
import { productoApi, registrarColores } from '../services/products.js'

const COLOR_NUEVO = '#2fa018'
const COLOR_DESCUENTO = '#FA7F19'
const COLOR_SIN_STOCK = '#e71414'
const COLOR_BUTTON = '#FA7F19'

const SPECS_BLOQUEADAS = ['resistencia', 'colores']
function specsFiltrados(specs, material, tamano, color) {
  if (!specs) return []
  const lower = [material, tamano, color].filter(Boolean).map(s => s.toLowerCase())
  return specs.filter(s => {
    const sl = s.toLowerCase()
    if (SPECS_BLOQUEADAS.some(b => sl.startsWith(b))) return false
    return !lower.some(v => sl.includes(v) || v.includes(sl))
  })
}

export default function ProductoDetalle() {
  const { id } = useParams()
  const { productos, categorias, cargando } = useProductos()
  const producto = productos.find(p => p.id === id)
  const { agregarProducto } = useCart()
  const [cantidad, setCantidad] = useState(1)
  const [colores, setColores] = useState([])
  const [colorElegido, setColorElegido] = useState(null)
  const [agregando, setAgregando] = useState(false)

  useEffect(() => {
    let vigente = true
    if (!id) {
      setColores([])
      setColorElegido(null)
      return
    }
    productoApi.listarColores(id)
      .then(({ colores }) => {
        if (!vigente) return
        const lista = [...(colores || [])].sort((a, b) => (a.orden ?? 0) - (b.orden ?? 0))
        setColores(lista)
        setColorElegido(lista[0]?.id ?? null)
        registrarColores(id, lista)
      })
      .catch(() => {
        if (!vigente) return
        setColores([])
        setColorElegido(null)
      })
    return () => { vigente = false }
  }, [id])

  const recomendados = useMemo(
    () => (producto
      ? productos
        .filter(p => p.categoria_id === producto.categoria_id && p.id !== producto.id)
        .slice(0, 4)
      : []),
    [productos, producto]
  )

  if (cargando) return <div className="wrap" style={{ padding: 80 }}>Cargando…</div>
  if (!producto) return <div className="wrap" style={{ padding: 80 }}>Producto no encontrado.</div>

  const categoria = categorias.find(c => c.id === producto.categoria_id)
  const specsLimpios = specsFiltrados(producto.specs, producto.material, producto.tamano, producto.color)
  const tieneVariantes = colores.length > 0
  const colorActual = colores.find(c => c.id === colorElegido) || null
  const faltaElegirColor = tieneVariantes && !colorActual
  const fotoActual = (tieneVariantes && colorActual?.imagen) ? colorActual.imagen : producto.imagen
  const rating = Number(producto.rating) || 0

  const handleAgregar = async () => {
    if (agregando) return
    setAgregando(true)
    try {
      await agregarProducto(
        {...producto, color: colorActual?.nombre ?? producto.color, imagen: fotoActual },
        cantidad
      )
    } finally {
      setAgregando(false)
    }
  }

  return (
    <section className="wrap" style={{ paddingTop: '25px', paddingBottom: '80px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 3,
        fontSize: 11,
        color: 'var(--text-dim)',
        marginBottom: 5,
      }}>
        <span></span>
        <Link to="/categorias" style={{ color: 'var(--surface)' }}>Catálogo /</Link>
        {categoria && (
          <>
            <span></span>
            <Link to={`/categorias?cat=${categoria.id}`} style={{ color: 'var(--accent)' }}>{categoria.nombre} /</Link>
          </>
        )}
        <span></span>
        <span style={{ color: 'var(--surface)' }}>{producto.nombre}</span>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 3,
        fontSize: 35,
        color: 'var(--text-dim)',
        fontWeight: 500,
        marginTop: -10
      }}>
        <span></span>
        <span style={{ color: 'var(--surface)' }}>{producto.nombre}</span>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 3,
        fontSize: 12,
        color: 'var(--text-dim)',
        marginBottom: 40,
        marginTop: -5
      }}>
        <span></span>
        <span style={{ color: 'var(--text-dim)' }}>Apolo Vibes 3D</span>
      </div>

      <div className="producto-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48 }}>
        <div>
          <div style={{
            position: 'relative',
            height: 600,
            background: fotoActual ? '#FFFFFF' : 'var(--surface)',
            borderRadius: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
          >
            {fotoActual && (
              <img
                src={fotoActual}
                alt={producto.nombre}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  objectPosition: 'center',
                  transformOrigin: 'center'
                }}
              />
            )}


            {producto.sinStock ? (
              <span style={{
                position: 'absolute',
                top: 12,
                left: 12,
                background: COLOR_SIN_STOCK,
                color: '#FFFFFF',
                fontSize: 13,
                fontWeight: 700,
                padding: '5px 16px',
                borderRadius: 20,
                zIndex: 2,
              }}>
                Agotado
              </span>
            ) : producto.descuento ? (
              <span style={{
                position: 'absolute',
                top: 12,
                left: 12,
                background: COLOR_DESCUENTO,
                color: '#FFFFFF',
                fontSize: 13,
                fontWeight: 700,
                padding: '5px 16px',
                borderRadius: 20,
                zIndex: 2,
              }}>
                -{producto.descuento}% OFF
              </span>
            ) : producto.badge ? (
              <span style={{
                position: 'absolute',
                top: 12,
                left: 12,
                background: COLOR_NUEVO,
                color: '#FFFFFF',
                fontSize: 13,
                fontWeight: 700,
                padding: '5px 16px',
                borderRadius: 20,
                zIndex: 2,
              }}>
                {producto.badge}
              </span>
            ) : null}
          </div>

          {tieneVariantes && (
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'center' }}>
                {colores.map(c => {
                  const activo = c.id === colorElegido
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setColorElegido(c.id)}
                      title={c.nombre}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '6px 12px 6px 6px',
                        border: `1px solid ${activo ? COLOR_BUTTON : 'var(--line)'}`,
                        borderRadius: 24,
                        background: activo ? 'var(--surface-3)' : 'transparent',
                        color: 'var(--text-dim)',
                        fontSize: 13,
                        cursor: 'pointer',
                      }}
                    >
                      <span
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: '50%',
                          overflow: 'hidden',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          background: 'var(--surface-2)',
                          flexShrink: 0,
                        }}
                      >
                        {c.imagen ? (
                          <img
                            src={c.imagen_thumb || c.imagen}
                            alt=""
                            loading="lazy"
                            decoding="async"
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                        ) : null}
                      </span>
                      {c.nombre}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        <div>
          {producto.descripcion && (
            <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 16, textAlign: 'justify', marginTop: 10 }}>
              {producto.descripcion}
            </p>
          )}

          <p style={{ fontSize: 14, color: 'var(--surface)', lineHeight: 1.6, marginBottom: 12, textAlign: 'left' }}>
            Detalles:
          </p>

          <ul style={{
            listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: 8
          }}>
            {producto.material && (
              <li style={{ fontSize: 13, color: 'var(--text-dim)', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#FA7F19', marginTop: 6, flexShrink: 0 }} />
                Material: {producto.material}
              </li>
            )}
            {producto.tamano && (
              <li style={{ fontSize: 13, color: 'var(--text-dim)', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#FA7F19', marginTop: 6, flexShrink: 0 }} />
                Tamaño: {producto.tamano}
              </li>
            )}
            {producto.color && (
              <li style={{ fontSize: 13, color: 'var(--text-dim)', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#FA7F19', marginTop: 6, flexShrink: 0 }} />
                Color: {producto.color}
              </li>
            )}
            {specsLimpios.map((spec, i) => (
              <li
                key={i}
                style={{ fontSize: 13, color: 'var(--text-dim)', display: 'flex', alignItems: 'flex-start', gap: 8 }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#FA7F19', marginTop: 6, flexShrink: 0 }} />
                {spec}
              </li>
            ))}
          </ul>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
              {Array.from({ length: 5 }).map((_, i) => (
                <Star
                  key={i}
                  size={18}
                  fill={i < rating ? '#FA7F19' : 'none'}
                  color={i < rating ? '#FA7F19' : 'var(--line)'}
                />
              ))}
              {rating > 0 && (
                 <span style={{ fontSize: 13, color: 'var(--text-dim)', marginLeft: 4 }}>
                {producto.rating}.0
              </span>
              )}
            </div>

          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 10,
            marginBottom: 24
          }}>
            <span style={{
              fontSize: 30,
              fontWeight: 600,
              color: 'var(--surface)'
            }}>
              ${producto.precio.toLocaleString('es-CL')} CLP
            </span>
            {producto.precio_original && (
              <span style={{
                fontSize: 16,
                color: 'var(--text-dim)',
                textDecoration: 'line-through',
              }}
              >
                ${producto.precio_original.toLocaleString('es-CL')}
              </span>
            )}
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20, marginTop: -25 }}>Precio con IVA incluido</p>

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
              <span style={{ width: 32, textAlign: 'center', fontSize: 14, color: 'var(--surface-2)' }}>{cantidad}</span>
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
              disabled={producto.sinStock || faltaElegirColor || agregando}
              onClick={handleAgregar}
              style={{
                flex: 1,
                background: producto.sinStock || faltaElegirColor ? 'var(--surface-2)' : COLOR_BUTTON,
                color: producto.sinStock || faltaElegirColor ? 'var(--text-dim)' : '#FFFFFF',
                cursor: producto.sinStock || faltaElegirColor ? 'not-allowed' : agregando ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8
              }}
            >
              {!producto.sinStock && !faltaElegirColor && !agregando && (
                <img
                  src={mediaPath('cart.png')}
                  alt=""
                  style={{ width: 20, height: 20, filter: 'brightness(0) invert(1)' }}
                />
              )}
              {producto.sinStock
                ? 'Sin Stock'
                : faltaElegirColor ? 'Elige un color' : agregando ? 'Agregando...' : 'Agregar al carrito'}
            </button>
            {faltaElegirColor && (
              <p style={{ margin: '10px 0 0', fontSize: 12, color: 'var(--text-dim)' }}>
                Seleccioná el color para continuar.
              </p>
            )}
          </div>
          <div style={{
            marginTop: 16,
            padding: '12px 16px',
            textAlign: 'center',
            background: 'var(--surface-3)',
            borderRadius: 8,
            fontSize: 13,
            color: 'var(--text-dim)',
            lineHeight: 1.5,
          }}>
            {producto.sinStock ? (
              <span style={{ color: COLOR_SIN_STOCK, fontWeight: 600 }}>Producto sin stock actualmente.</span>
            ) : (
              <>
                Producto listo para envío — envío en 3-5 días hábiles
                {producto.stock > 0 && (
                  <span style={{ marginLeft: 8, color: 'var(--accent)' }}>· {producto.stock} unidades disponibles</span>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {/*ACA MOSTRAR SOLO 4 PERO LO MAS VENDIDOS !!!*/}
      {recomendados.length > 0 && (
        <div style={{ marginTop: 64 }}>
          <hr className="separador" />
          <h2 style={{
            fontSize: 22,
            fontWeight: 600,
            color: 'var(--surface-2)',
            marginBottom: 24,
            textAlign: 'center',
          }}>
            También te recomendamos
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 20,
          }}>
            {recomendados.map((p, i) => (
              <ProductCard key={p.id} producto={p} index={i} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
