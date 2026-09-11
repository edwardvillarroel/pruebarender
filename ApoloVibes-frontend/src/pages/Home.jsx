import HeroVideo from '../components/HeroVideo.jsx'
import ProductCard from '../components/ProductCard.jsx'
import { productos, categorias } from '../data/products.js'
import { mediaPath } from '../utils/media.js'

const CATEGORY_BACKGROUNDS = {
  anime: mediaPath('banerAnime.png'),
  animales: mediaPath('banerAnimales.png'),
  llaveros: mediaPath('banerllaveros.png'),
  diseno: mediaPath('banerdiseño .png'),
}

export default function Home() {
  return (
    <>
      <HeroVideo />

      <section className="wrap section-py-mobile" style={{ padding: '80px 0' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 28, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Explora por categoría</h2>
        <div className="grid-3">
          {categorias.map(cat => {
            const bg = CATEGORY_BACKGROUNDS[cat.id]
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
                {/* Overlay oscuro para que el texto sea legible */}
                {bg && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'rgba(0,0,0,.5)',
                    borderRadius: 12,
                  }} />
                )}
                <div style={{ position: 'relative', zIndex: 1 }}>
                  <h3 style={{ fontSize: 16, marginBottom: 4, color: bg ? '#fff' : 'inherit' }}>{cat.nombre}</h3>
                  {cat.cantidad && (
                    <span style={{ fontSize: 12, color: bg ? 'rgba(255,255,255,.75)' : 'var(--text-dim)' }}>
                      {cat.cantidad} referencias
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="wrap section-py-mobile" style={{ padding: '0 0 80px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 28, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Productos más vendidos</h2>
        <div className="grid-4">
          {productos.map(p => <ProductCard key={p.id} producto={p} />)}
        </div>
      </section>
    </>
  )
}
