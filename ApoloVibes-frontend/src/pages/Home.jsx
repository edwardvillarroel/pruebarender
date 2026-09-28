import { useRef, useState, useCallback, useEffect } from 'react'
import HeroVideo from '../components/HeroVideo.jsx'
import ProductCard from '../components/ProductCard.jsx'
import { useProductos } from '../context/ProductContext.jsx'
import { mediaPath } from '../utils/media.js'
import { ChevronLeft, ChevronRight } from 'lucide-react'

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
  const scrollRef = useRef(null)
  const [enInicio, setEnInicio] = useState(true)
  const [enFinal, setEnFinal] = useState(false)

  const actualizarFlechas = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setEnInicio(el.scrollLeft <= 5)
    setEnFinal(el.scrollLeft + el.clientWidth >= el.scrollWidth - 5)
  }, [])

  useEffect(() => {
    actualizarFlechas()
    window.addEventListener('resize', actualizarFlechas)
    return () => window.removeEventListener('resize', actualizarFlechas)
  }, [actualizarFlechas, productos])

  function scroll(direccion) {
    if (!scrollRef.current) return
    const cardWidth = scrollRef.current.firstChild?.offsetWidth || 300
    const gap = 20
    scrollRef.current.scrollBy({ left: direccion * (cardWidth + gap), behavior: 'smooth' })
  }

  const btnFlecha = {
    width: 40, height: 40, borderRadius: '50%', border: '1px solid var(--line)',
    background: 'var(--surface-3)', cursor: 'pointer', display: 'flex',
    alignItems: 'center', justifyContent: 'center', transition: 'border-color .2s',
    boxShadow: '0 2px 8px rgba(0,0,0,.15)'
  }

  return (
    <>
      <style>{`
        .carousel-hide::-webkit-scrollbar { display: none; }
        /* Las cards se reparten en un número ENTERO de columnas por breakpoint, con
           el ancho solvedo para que N cards + N-1 gaps entren justas. Un porcentaje
           fijo (25%) deja una card partida al borde y la flecha parada sobre el
           corte. Las flechas avisan que hay más, así no hace falta asomar un pedazo. */
        .carousel-hide { --carousel-cols: 4; }
        .carousel-item {
          flex: 0 0 calc((100% - (var(--carousel-cols) - 1) * 20px) / var(--carousel-cols));
          scroll-snap-align: start;
        }
        @media (max-width: 1199px) { .carousel-hide { --carousel-cols: 3; } }
        @media (max-width: 899px)  { .carousel-hide { --carousel-cols: 2; } }
        /* 1 sola columna y sin piso de ancho: la card ocupa el track completo, así
           no queda una segunda partida asomando al borde. */
        @media (max-width: 520px)  { .carousel-hide { --carousel-cols: 1; } }
        /* Las flechas van fuera de las cards, no encima: el gutter se reserva con
           padding en el contenedor, así nunca se superponen y tampoco hay que
           empujarlas con left/right negativo (que escapaba de la página). */
        .carousel-nav { position: relative; padding-left: 52px; padding-right: 52px; }
        .carousel-flecha { position: absolute; top: 50%; transform: translateY(-50%); }
        .carousel-flecha-izq { left: 0; }
        .carousel-flecha-der { right: 0; }
        @media (max-width: 768px) {
          .carousel-nav { padding-left: 44px; padding-right: 44px; }
        }
      `}</style>
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
          <div className="carousel-nav">
            {/* Flecha izquierda */}
            {!enInicio && (
              <button
                onClick={() => scroll(-1)}
                className="carousel-flecha carousel-flecha-izq"
                style={{ ...btnFlecha, zIndex: 2 }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
              >
                <ChevronLeft size={20} color="var(--surface)" />
              </button>
            )}

            {/* Carousel */}
            <div
              ref={scrollRef}
              className="carousel-hide"
              onScroll={actualizarFlechas}
              style={{
                display: 'flex', gap: 20, overflowX: 'auto', scrollSnapType: 'x mandatory',
                scrollbarWidth: 'none', msOverflowStyle: 'none', paddingBottom: 4,
              }}
            >
              {productos.map((p, i) => (
                <div
                  key={p.id}
                  className="carousel-item"
                  style={{ minWidth: 0 }}
                >
                  <ProductCard producto={p} index={i} />
                </div>
              ))}
            </div>

            {/* Flecha derecha */}
            {!enFinal && (
              <button
                onClick={() => scroll(1)}
                className="carousel-flecha carousel-flecha-der"
                style={{ ...btnFlecha, zIndex: 2 }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
              >
                <ChevronRight size={20} color="var(--surface)" />
              </button>
            )}
          </div>
        )}
      </section>

      <section className="wrap" style={{ paddingTop: 32 }}>
        <hr className="separador" />
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 30, textAlign: 'center', color: 'var(--surface)' }}>Lanzamientos</h2>
      </section>

      <section className="wrap section-py-mobile" style={{ paddingBottom: '80px' }}>
        <hr className="separador" />
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
                    padding: '100px 22px',
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
                    <h3 style={{ textAlign: 'center', fontSize: 16, marginBottom: 4, color: bg ? '#fff' : 'inherit' }}>{cat.nombre}</h3>
                    {cat.cantidad > 0 && (
                      <span style={{ justifyContent: 'center', fontSize: 12, color: bg ? 'rgba(255,255,255,.75)' : 'var(--text-dim)' }}>
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
    </>
  )
}