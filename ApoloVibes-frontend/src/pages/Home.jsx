import { useMemo } from 'react'
import HeroVideo from '../components/HeroVideo.jsx'
import ProductCarousel from '../components/ProductCarousel.jsx'
import { useProductos } from '../context/ProductContext.jsx'
import { useMasVendidos } from '../hooks/useMasVendidos.js'
import { mediaPath } from '../utils/media.js'
import { Link } from 'react-router-dom'
import { rutaDeCategoria } from '../utils/categorias.js'

const CATEGORY_BACKGROUNDS = {
  videoJuegos: mediaPath('banerAnime.webp'),
  animales: mediaPath('Animales.webp'),
  llaveros: mediaPath('banerllaveros.webp'),
  diseno: mediaPath('banerdiseño.webp'),
  accesorios: mediaPath('AccesoriosBaner.webp'),
  articulados: mediaPath('ArticuladosBaner.webp')
}


function fondoDeCategoria(nombre) {
  const n = (nombre || '').toLowerCase()
  if (n.includes('videojuego') || n.includes('cine')) return CATEGORY_BACKGROUNDS.videoJuegos
  if (n.includes('animales')) return CATEGORY_BACKGROUNDS.animales
  if (n.includes('llavero')) return CATEGORY_BACKGROUNDS.llaveros
  if (n.includes('accesorios')) return CATEGORY_BACKGROUNDS.accesorios
  if (n.includes('articulados')) return CATEGORY_BACKGROUNDS.articulados
  if (n.includes('diseno') || n.includes('diseno') || n.includes('medida'))
    return CATEGORY_BACKGROUNDS.diseno
  return null
}

export default function Home() {
  const { productos, categorias, cargando } = useProductos()
  const rankingSemanal = useMasVendidos('7d', 10)
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

  const hayRanking = !rankingSemanal.cargando && !rankingSemanal.error

  return (
    <>
      <HeroVideo />
      <section className="wrap section-py-mobile" style={{ paddingTop: '80px' }}>
        <hr className="separador" />
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>
          {hayRanking ? 'Los más vendidos de la semana' : 'Nuestros productos'}
        </h2>
        {rankingSemanal.cargando && (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando productos…</p>
        )}
        {rankingSemanal.error && (
          <>
            <p style={{ textAlign: 'center', color: '#ef4444' }}>
              No se pudo cargar el ranking de más vendidos: {rankingSemanal.error}
            </p>
            {productos.length > 0 ? (
              <ProductCarousel productos={productos} />
            ) : !cargando ? (
              <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>
                Aún no hay productos en el catálogo.
              </p>
            ) : null}
          </>
        )}
        {hayRanking && rankingSemanal.productos.length === 0 && (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>
            Todavía no hay ventas registradas esta semana.
          </p>
        )}
        {hayRanking && rankingSemanal.productos.length > 0 && (
          <ProductCarousel productos={rankingSemanal.productos} />
        )}
      </section>

      <section className="wrap" style={{ paddingTop: 32, paddingBottom: 32 }}>
        <hr className="separador" />
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Destacados</h2>
        <div className="grid-destacados">
          {['DesDragon.webp', 'DesCubone.webp', 'destacados.webp'].map(f => (
            <div key={f} className="destacado-card">
              <img src={mediaPath(f)} alt="" loading="lazy" decoding="async" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
            </div>
          ))}
        </div>
        <style>{`
          .grid-destacados { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
          .destacado-card {
            aspect-ratio: 6 / 8;
            min-height: 130px;
            border-radius: 0px;
            background: transparent;
            border: 1px solid var(--line);
            overflow: hidden;
          }
          @media (max-width: 768px) {
            .grid-destacados { grid-template-columns: 1fr; }
          }
        `}</style>
      </section>

      {lanzamientos.length > 0 && (
        <section className="wrap" style={{ paddingTop: 32, paddingBottom: 32 }}>
          <hr className="separador" />
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Nuevos Lanzamientos</h2>
          <ProductCarousel productos={lanzamientos} />
        </section>
      )}


<style>{`
  .cat-titulo { color: inherit; text-decoration: none; cursor: pointer; }
  .cat-titulo:hover { text-decoration: underline; }
`}</style>

      <section className="wrap section-py-mobile" style={{ paddingBottom: '80px' }}>
        <hr className="separador" />
        {cargando && categorias.length === 0 && (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando categorías…</p>
        )}
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
                  <h3 style={{ fontSize: 18, marginTop: -5, color: bg ? '#fff' : 'var(--text)' }}>
                    <Link to={rutaDeCategoria(cat)} className="cat-titulo">
                      {cat.nombre}
                    </Link>
                  </h3>
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
      </section >
    </>
  )
}