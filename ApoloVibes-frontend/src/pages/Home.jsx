import HeroVideo from '../components/HeroVideo.jsx'
import ProductCard from '../components/ProductCard.jsx'
import { useProductos } from '../context/ProductContext.jsx'
import { mediaPath } from '../utils/media.js'

const CATEGORY_BACKGROUNDS = {
  anime: mediaPath('banerAnime.png'),
  animales: mediaPath('banerAnimales.png'),
  llaveros: mediaPath('banerllaveros.png'),
  diseno: mediaPath('banerdiseño .png'),
}

function fondoDeCategoria(nombre) {
  const n = (nombre || '').toLowerCase()
  if (n.includes('anime')) return CATEGORY_BACKGROUNDS.anime
  if (n.includes('animal')) return CATEGORY_BACKGROUNDS.animales
  if (n.includes('llavero')) return CATEGORY_BACKGROUNDS.llaveros
  if (n.includes('diseño') || n.includes('diseno') || n.includes('medida'))
    return CATEGORY_BACKGROUNDS.diseno
  return null
}

export default function Home() {
  const { productos, categorias, cargando, error } = useProductos()

  return (
    <>
      <HeroVideo />

      <section className="wrap section-py-mobile" style={{ paddingTop: '80px', paddingBottom: '80px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 28, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Explora por categoría</h2>
        {cargando ? (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando categorías…</p>
        ) : (
          <div className="grid-3">
            {categorias.map(cat => {
              const bg = fondoDeCategoria(cat.nombre)
              return (
                <div
                  key={cat.id}
                  style={{
                    backgroundImage: bg ? `url(${bg})` : 'none',
                    backgroundSize: bg ? 'cover' : 'auto',
                    backgroundPosition: bg ? 'center' : 'unset',
                    backgroundRepeat: 'no-repeat',
                    backgroundColor: bg ? 'var(--surface-2)' : 'var(--surface)',
                    position: 'relative',
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    padding: '26px 22px',
                    minHeight: 130,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'flex-end',
                    overflow: 'hidden',
                  }}
                >
                  {bg && (
                    <div style={{
                      position: 'absolute', inset: 0,
                      background: 'rgba(0,0,0,.5)',
                      borderRadius: 12,
                    }} />
                  )}
                  <div style={{ position: 'relative', zIndex: 1 }}>
                    <h3 style={{ fontSize: 16, marginBottom: 4, color: bg ? '#fff' : 'inherit' }}>{cat.nombre}</h3>
                    {cat.cantidad > 0 && (
                      <span style={{ fontSize: 12, color: bg ? 'rgba(255,255,255,.75)' : 'var(--text-dim)' }}>
                        {cat.cantidad} {cat.cantidad === 1 ? 'producto' : 'productos'}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <section className="wrap section-py-mobile" style={{ padding: '0 0 80px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 28, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Todos los productos</h2>
        {cargando ? (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando productos…</p>
        ) : error ? (
          <p style={{ textAlign: 'center', color: '#ef4444' }}>Error al cargar productos: {error}</p>
        ) : productos.length === 0 ? (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Aún no hay productos en el catálogo.</p>
        ) : (
          <div className="grid-4">
            {productos.map((p, i) => <ProductCard key={p.id} producto={p} index={i} />)}
          </div>
        )}
      </section>
    </>
  )
}