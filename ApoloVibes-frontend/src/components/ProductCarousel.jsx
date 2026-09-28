import { useRef, useState, useCallback, useEffect } from 'react'
import ProductCard from './ProductCard.jsx'
import { ChevronLeft, ChevronRight } from 'lucide-react'

const GAP = 20

export default function ProductCarousel({ productos }) {
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
        scrollRef.current.scrollBy({ left: direccion * (cardWidth + GAP), behavior: 'smooth' })
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

            <div className="carousel-nav">
                {!enInicio && (
                    <button
                        onClick={() => scroll(-1)}
                        className="carousel-flecha carousel-flecha-izq"
                        aria-label="Ver productos anteriores"
                        style={{ ...btnFlecha, zIndex: 2 }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
                    >
                        <ChevronLeft size={20} color="var(--surface)" />
                    </button>
                )}

                <div
                    ref={scrollRef}
                    className="carousel-hide"
                    onScroll={actualizarFlechas}
                    style={{
                        display: 'flex', gap: GAP, overflowX: 'auto', scrollSnapType: 'x mandatory',
                        scrollbarWidth: 'none', msOverflowStyle: 'none', paddingBottom: 4,
                    }}
                >
                    {productos.map((p, i) => (
                        <div key={p.id} className="carousel-item" style={{ minWidth: 0 }}>
                            <ProductCard producto={p} index={i} />
                        </div>
                    ))}
                </div>

                {!enFinal && (
                    <button
                        onClick={() => scroll(1)}
                        className="carousel-flecha carousel-flecha-der"
                        aria-label="Ver productos siguientes"
                        style={{ ...btnFlecha, zIndex: 2 }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
                    >
                        <ChevronRight size={20} color="var(--surface)" />
                    </button>
                )}
            </div>
        </>
    )
}
