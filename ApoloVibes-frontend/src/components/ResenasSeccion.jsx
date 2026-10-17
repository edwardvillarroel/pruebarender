import { useState, useMemo } from 'react'
import { Star, ChevronDown, ChevronUp } from 'lucide-react'
import { mediaPath } from '../utils/media.js';

const POR_PAGINA = 4
const COLOR_NUEVO = '#2fa018'

function Estrellas({ valor, size = 16 }) {
    return (
        <span style={{ display: 'inline-flex', gap: 2 }} aria-label={`${valor} de 5 estrellas`}>
            {Array.from({ length: 5 }).map((_, i) => (
                <Star
                    key={i}
                    size={size}
                    fill={i < Math.round(valor) ? '#FA7F19' : 'none'}
                    color={i < Math.round(valor) ? '#FA7F19' : '#d5dbe1'}
                />
            ))}
        </span>
    )
}

export default function ResenasSeccion({ producto, resenas, cargando, error }) {
    const [filtro, setFiltro] = useState(null)
    const [visibles, setVisibles] = useState(POR_PAGINA)

    const distribucion = useMemo(() => {
        const conteo = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 }
        resenas.forEach((r) => {
            const n = Math.round(Number(r.estrellas))
            if (conteo[n] !== undefined) conteo[n] += 1
        })
        return conteo
    }, [resenas])

    const total = resenas.length
    const filtradas = filtro ? resenas.filter((r) => Math.round(Number(r.estrellas)) === filtro) : resenas
    const mostradas = filtradas.slice(0, visibles)
    const rating = Number(producto.rating) || 0
    const cantidad = producto.resenas_count || total

    const cambiarFiltro = (n) => {
        setFiltro((actual) => (actual === n ? null : n))
        setVisibles(POR_PAGINA)
    }

    return (
        <div style={{ margin: '64px auto 0', textAlign: 'left' }}>
            <hr className="separador" />
            <h2 style={{ textAlign: 'center', fontSize: 22, fontWeight: 600, color: 'var(--surface-2)', margin: '0 0 20px' }}>
                Opiniones del producto
            </h2>

            {cargando ? (
                <p style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>Cargando reseñas…</p>
            ) : error ? (
                <p style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>{error}</p>
            ) : total === 0 ? (
                <div style={{ textAlign: 'center' }}>
                    <img
                        src={mediaPath('sinReseñas.webp')}
                        alt="Logo"
                        loading="lazy"
                        decoding="async"
                        width="512"
                        height="512"
                        style={{ display: 'block', height: 100, width: 'auto', margin: '0 auto 10px' }}
                    />
                    <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
                        Todavía no hay reseñas de este producto.
                    </p>
                </div>
            ) : (
                <>
                    {/* Resumen */}
                    <div style={{
                        background: '#FFFFFF', border: '1px solid var(--line)', borderRadius: 14,
                        padding: '24px 28px', marginBottom: 28,
                        display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center', gap: 40,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                            <span style={{ fontSize: 52, fontWeight: 700, lineHeight: 1, color: '#2b3640' }}>
                                {rating.toFixed(1)}
                            </span>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                <Estrellas valor={rating} size={18} />
                                <span style={{ fontSize: 14, color: '#5b6b78' }}>
                                    {cantidad} reseña{cantidad === 1 ? '' : 's'}
                                </span>
                            </div>
                        </div>

                        {/* Barras de calificaciones */}
                        <div style={{ flex: '1 1 280px', maxWidth: 640, display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {[5, 4, 3, 2, 1].map((n) => {
                                const pct = total ? (distribucion[n] / total) * 100 : 0
                                return (
                                    <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                        <span style={{ width: 34, fontSize: 12, color: '#2b3640', display: 'flex', alignItems: 'center', gap: 3 }}>
                                            <Star size={13} fill="#FA7F19" color="#FA7F19" /> {n}
                                        </span>
                                        <div style={{ flex: 1, height: 8, borderRadius: 4, background: '#e3e8ed', overflow: 'hidden' }}>
                                            <div style={{ width: `${pct}%`, height: '100%', background: '#FA7F19', borderRadius: 4, transition: 'width .4s' }} />
                                        </div>
                                        <span style={{ width: 24, textAlign: 'right', fontSize: 12, color: '#5b6b78' }}>
                                            {distribucion[n]}
                                        </span>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    {/* Filtros */}
                    <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--surface-2)', marginBottom: 10 }}>
                        Filtrar reseñas por:
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                        {[5, 4, 3, 2, 1].map((n) => {
                            const activo = filtro === n
                            const vacio = distribucion[n] === 0
                            return (
                                <button
                                    key={n}
                                    type="button"
                                    disabled={vacio}
                                    onClick={() => cambiarFiltro(n)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 6,
                                        padding: '6px 16px', borderRadius: 20, fontSize: 13,
                                        border: `1px solid ${activo ? '#FA7F19' : '#d5dbe1'}`,
                                        background: activo ? '#fff1e4' : '#FFFFFF',
                                        color: '#2b3640', cursor: vacio ? 'not-allowed' : 'pointer',
                                        opacity: vacio ? 0.45 : 1,
                                    }}
                                >
                                    <Star size={15} fill="#FA7F19" color="#FA7F19" /> {n}
                                </button>
                            )
                        })}
                        {filtro && (
                            <button
                                type="button"
                                onClick={() => { setFiltro(null); setVisibles(POR_PAGINA) }}
                                style={{ background: 'none', border: 'none', color: '#FA7F19', fontSize: 13, cursor: 'pointer' }}
                            >
                                Quitar filtro
                            </button>
                        )}
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: '0 0 8px' }}>
                        {filtradas.length} de {total} reseña{total === 1 ? '' : 's'}
                    </p>

                    {/* Lista */}
                    <div>
                        {mostradas.map((r) => (
                            <article key={r.id} style={{ borderTop: '1px solid var(--line)', padding: '18px 0' }}>
                                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--surface-2)', textTransform: 'capitalize', marginBottom: 6 }}>
                                    {r.autor}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: r.comentario ? 10 : 0 }}>
                                    <Estrellas valor={Number(r.estrellas)} size={15} />
                                    <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                                        {r.creado_en
                                            ? new Date(r.creado_en).toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' })
                                            : ''}
                                    </span>
                                    <span style={{ fontSize: 11, color: COLOR_NUEVO, fontWeight: 500 }}>✓ Compra verificada</span>
                                </div>
                                {r.comentario && (
                                    <p style={{ marginBottom: -50, fontSize: 14, lineHeight: 1.6, color: '#3b4a57', whiteSpace: 'pre-line', overflowWrap: 'anywhere' }}>
                                        {r.comentario}
                                    </p>
                                )}
                            </article>
                        ))}
                        {filtradas.length === 0 && (
                            <p style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
                                No hay reseñas con esa calificación.
                            </p>
                        )}
                    </div>

                    {filtradas.length > POR_PAGINA && (
                        <div style={{ borderTop: '1px solid var(--line)', textAlign: 'center', padding: '18px 0 0' }}>
                            <button
                                type="button"
                                onClick={() =>
                                    setVisibles(visibles >= filtradas.length ? POR_PAGINA : filtradas.length)}
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: '#FA7F19', fontSize: 15, fontWeight: 600,
                                    display: 'inline-flex', alignItems: 'center', gap: 6,
                                }}
                            >
                               {visibles >= filtradas.length ? 'Mostrar menos reseñas' : 'Mostrar todas las reseñas'}
                               {visibles >= filtradas.length ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}