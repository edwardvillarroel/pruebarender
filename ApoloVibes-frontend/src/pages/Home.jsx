import { useMemo } from 'react'
import HeroVideo from '../components/HeroVideo.jsx'
import ProductCarousel from '../components/ProductCarousel.jsx'
import { useProductos } from '../context/ProductContext.jsx'
import { mediaPath } from '../utils/media.js'

const CATEGORY_BACKGROUNDS = {
  videoJuegos: mediaPath('banerAnime.png'),
  animales: mediaPath('Animales.png'),
  llaveros: mediaPath('banerllaveros.png'),
  diseno: mediaPath('banerdiseño.png'),
}

function fondoDeCategoria(nombre) {
  const n = (nombre || '').toLowerCase()
  if (n.includes('videojuego') || n.includes('cine')) return CATEGORY_BACKGROUNDS.videoJuegos
  if (n.includes('animal')) return CATEGORY_BACKGROUNDS.animales
  if (n.includes('llavero')) return CATEGORY_BACKGROUNDS.llaveros
  if (n.includes('diseno') || n.includes('diseno') || n.includes('medida'))
    return CATEGORY_BACKGROUNDS.diseno
  return null
}

export default function Home() {
  const { productos, categorias, cargando, error } = useProductos()
  const lanzamientos = useMemo(
    () => productos
      .filter(p => p.nuevo_lanzamiento)
      .slice()
      .sort((a, b) => {
        if (!a.creado_en) return 1
        if (!b.creado_en) return -1
        return a.creado_en < b.creado_en ? 1 : a.creado_en > b.creado_en ? -1 : 0
      }),
    [productos]
  )

  return (
    <>
      <HeroVideo />

      <section className="wrap section-py-mobile" style={{ paddingTop: '80px' }}>
        <hr className="separador" />
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Los más vendidos del mes</h2>
        {cargando ? (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando productos…</p>
        ) : error ? (
          <p style={{ textAlign: 'center', color: '#ef4444' }}>Error al cargar productos: {error}</p>
        ) : productos.length === 0 ? (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Aún no hay productos en el catálogo.</p>
        ) : (
          <ProductCarousel productos={productos} />
        )}
      </section>

      {lanzamientos.length > 0 && (
        <section className="wrap" style={{ paddingTop: 32, paddingBottom: 32 }}>
          <hr className="separador" />
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Nuevos Lanzamientos</h2>
          <ProductCarousel productos={lanzamientos} />
        </section>
      )}

      <section className="wrap section-py-mobile" style={{ paddingBottom: '80px' }}>
        <hr className="separador" />
        {cargando ? (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando categorías…</p>
        ) : (
          <div className="grid-3" style={{ rowGap: 8 }}>
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
                    aspectRatio: '8 / 3',
                    padding: '24px 22px',
                    minHeight: 130,
                    display: 'flex',
                    flexDirection: 'row',
                    justifyContent: 'center',
                    textAlign: 'center',
                    overflow: 'hidden',
                  }}
                >
                  {bg && (
                    <div style={{
                      position: 'absolute', inset: 0,
                      background: 'rgba(0,0,0,.5)',
                    }} />
                  )}
                  <div style={{ position: 'relative', zIndex: 1, padding: '0 16px' }}>
                    <h3 style={{ fontSize: 18, marginTop: -5, color: bg ? '#fff' : 'var(--text)' }}>{cat.nombre}</h3>
                    {cat.cantidad > 0 && (
                      <span style={{ display: 'block', marginTop: -5, fontSize: 12, color: bg ? 'rgba(255,255,255,.75)' : 'var(--text-dim)' }}>
                        {cat.cantidad} {cat.cantidad === 1 ? 'producto' : 'productos'}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section >
    </>
  )
}