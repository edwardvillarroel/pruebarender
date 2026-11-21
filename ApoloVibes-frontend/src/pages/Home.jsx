import { useEffect, useMemo, useState } from 'react'
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
  if (n.includes('diseno') || n.includes('diseño') || n.includes('medida'))
    return CATEGORY_BACKGROUNDS.diseno
  return null
}

function AvisoFallback() {
  return (
    <div
      role="status"
      style={{
        margin: '0 auto 24px',
        maxWidth: 760,
        padding: '12px 14px',
        borderRadius: 12,
        border: '1px solid rgba(250,127,25,.35)',
        background: 'rgba(250,127,25,.10)',
        color: 'var(--surface)',
        fontSize: 13,
        textAlign: 'center',
      }}
    >
      Catálogo no disponible en este momento, mostrando selección destacada.
    </div>
  )
}

export default function Home() {
  const { productos, categorias, cargando, error } = useProductos()
  const rankingSemanal = useMasVendidos('semana', 10)
  const [fallback, setFallback] = useState(null)

  useEffect(() => {
    const debeUsarFallback = Boolean(error) || (Boolean(rankingSemanal.error) && productos.length === 0)
    if (!debeUsarFallback || fallback) return
    let vigente = true
    fetch('/fallback/fallback.json', { cache: 'no-store' })
      .then((res) => {
        if (!res.ok) throw new Error('No se pudo cargar el fallback')
        return res.json()
      })
      .then((data) => {
        if (vigente) setFallback(data)
      })
      .catch((err) => {
        console.error('Error al cargar fallback del Home:', err)
      })
    return () => { vigente = false }
  }, [error, rankingSemanal.error, productos.length, fallback])

  const modoFallbackCatalogo = Boolean(error) && Boolean(fallback)
  const mostrarFallbackRanking = (Boolean(error) || Boolean(rankingSemanal.error)) && Boolean(fallback?.masVendidos?.length)
  const mostrarFallbackLanzamientos = Boolean(error) && Boolean(fallback?.lanzamientos?.length)

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
  const tipoSemana = rankingSemanal.semana?.tipo
  const esSemanaAnterior = tipoSemana === 'anterior'
  const tituloRanking = mostrarFallbackRanking
    ? 'Productos destacados'
    : !hayRanking
      ? 'Nuestros productos'
      : esSemanaAnterior
        ? 'Los más vendidos de la semana anterior'
        : 'Los más vendidos de la semana'

  const productosRanking = mostrarFallbackRanking
    ? (fallback?.masVendidos || [])
    : rankingSemanal.productos

  const productosLanzamiento = mostrarFallbackLanzamientos
    ? (fallback?.lanzamientos || [])
    : lanzamientos

  return (
    <>
      <HeroVideo />
      <section className="wrap section-py-mobile" style={{ paddingTop: '80px' }}>
        <hr className="separador" />
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>
          {tituloRanking}
        </h2>
        {mostrarFallbackRanking && <AvisoFallback />}
        {rankingSemanal.cargando && !mostrarFallbackRanking && (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando productos…</p>
        )}
        {rankingSemanal.error && !mostrarFallbackRanking && (
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
        {hayRanking && !mostrarFallbackRanking && rankingSemanal.productos.length === 0 && (
          <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>
            Todavía no hay ventas registradas en las últimas semanas.
          </p>
        )}
        {((hayRanking && rankingSemanal.productos.length > 0) || mostrarFallbackRanking) && productosRanking.length > 0 && (
          <ProductCarousel productos={productosRanking} />
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

      {productosLanzamiento.length > 0 && (
        <section className="wrap" style={{ paddingTop: 32, paddingBottom: 32 }}>
          <hr className="separador" />
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Nuevos Lanzamientos</h2>
          {mostrarFallbackLanzamientos && <AvisoFallback />}
          <ProductCarousel productos={productosLanzamiento} />
        </section>
      )}

      <style>{`
        .cat-titulo { color: inherit; text-decoration: none; cursor: pointer; }
        .cat-titulo:hover { text-decoration: underline; }
      `}</style>

      {!modoFallbackCatalogo && (
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
        </section>
      )}
      {modoFallbackCatalogo && (
        <section className="wrap section-py-mobile" style={{ paddingBottom: '80px' }}>
          <hr className="separador" />
          <AvisoFallback />
        </section>
      )}
    </>
  )
}
