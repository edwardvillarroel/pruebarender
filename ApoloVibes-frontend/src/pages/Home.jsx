import { useMemo, useState } from 'react'
import HeroVideo from '../components/HeroVideo.jsx'
import ProductCarousel from '../components/ProductCarousel.jsx'
import ProductCard from '../components/ProductCard.jsx'
import SelectOpciones from '../components/SelectOpciones.jsx'
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

// Ventanas del ranking de "más vendidos". Los valores son los que acepta el
// backend (`GET /api/productos/mas-vendidos?periodo=`): 7d, 30d o todo.
const PERIODOS = [
  { value: '7d', label: 'Esta semana' },
  { value: '30d', label: 'Este mes' },
  { value: 'todo', label: 'Histórico' },
]

const DESCRIPCION_PERIODO = {
  '7d': 'Productos más vendidos en los últimos 7 días.',
  '30d': 'Productos más vendidos en los últimos 30 días.',
  'todo': 'Productos más vendidos en todo el historial de ventas.',
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

// Estilo compartido por las tarjetas de la grilla de categorías.
const ESTILO_TARJETA = {
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
}

/**
 * Tarjeta "Más vendidos" de la grilla de categorías.
 *
 * No es una categoría de verdad: no tiene productos asignados ni pagina
 * propia, asi que no es un `Link` sino un boton que abre el filtro del
 * ranking en el mismo lugar. Se ve distinta a propósito (gradiente en vez
 * de foto de fondo) para que no se confunda con una categoría mas.
 */
function TarjetaMasVendidos({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        ...ESTILO_TARJETA,
        background: 'linear-gradient(135deg, var(--accent) 0%, var(--gold) 100%)',
        border: '1px solid var(--gold)',
        fontFamily: 'inherit',
        cursor: 'pointer',
        color: 'var(--navy)',
        transition: 'filter .2s, transform .2s',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.filter = 'brightness(1.06)' }}
      onMouseLeave={(e) => { e.currentTarget.style.filter = 'none' }}
    >
      <div style={{ position: 'relative', zIndex: 1, padding: '0 16px' }}>
        <h3 style={{ fontSize: 18, marginTop: -5, color: 'var(--navy)' }}>Más vendidos</h3>
        <span style={{ display: 'block', marginTop: -5, fontSize: 12, color: 'rgba(30,58,95,.75)' }}>
          Ranking de ventas
        </span>
      </div>
    </button>
  )
}

/**
 * Vista del filtro de "más vendidos": reemplaza la grilla de categorías por
 * la lista de los mas vendidos del periodo elegido, con el desplegable para
 * cambiar la ventana de venta.
 */
function VistaMasVendidos({ ranking, periodo, onPeriodo, onVolver }) {
  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          gap: 16,
          flexWrap: 'wrap',
          marginBottom: 24,
        }}
      >
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, color: 'var(--surface)', margin: 0 }}>
            Más vendidos
          </h2>
          <p style={{ fontSize: 12.5, color: 'var(--text-dim)', margin: '6px 0 0' }}>
            {DESCRIPCION_PERIODO[periodo]}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ width: 190 }}>
            <SelectOpciones options={PERIODOS} value={periodo} onChange={onPeriodo} />
          </div>
          <button type="button" className="btn btn-ghost" onClick={onVolver}>
            Ver todas las categorías
          </button>
        </div>
      </div>

      {ranking.cargando ? (
        <p style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '4px 0' }}>
          Cargando productos…
        </p>
      ) : ranking.error ? (
        <p style={{ textAlign: 'center', color: '#ef4444', padding: '4px 0' }}>
          No se pudo cargar el ranking: {ranking.error}
        </p>
      ) : ranking.productos.length === 0 ? (
        <p style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '4px 0' }}>
          No hay ventas registradas en este periodo.
        </p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 20 }}>
          {ranking.productos.map((p, i) => (
            <div key={p.id} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    top: 10,
                    right: 10,
                    zIndex: 3,
                    background: 'var(--gold)',
                    color: 'var(--navy)',
                    fontSize: 12,
                    fontWeight: 700,
                    padding: '4px 10px',
                    borderRadius: 20,
                  }}
                >
                  #{i + 1}
                </span>
                <ProductCard producto={p} index={i} />
              </div>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--text-dim)', textAlign: 'center' }}>
                {p.unidades_vendidas} {p.unidades_vendidas === 1 ? 'unidad' : 'unidades'} · ${Number(p.ingresos).toLocaleString('es-CL')} CLP
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Home() {
  const { productos, categorias, cargando } = useProductos()
  // "Los más vendidos de la semana" sale del ranking real del backend
  // (`GET /api/productos/mas-vendidos?periodo=7d`). Si el endpoint falla se
  // muestra el catálogo completo con otro título: es preferible una home sin
  // ranking a una home en blanco o un ranking inventado.
  const rankingSemanal = useMasVendidos('7d', 10)
  // Filtro de "más vendidos" dentro de la grilla de categorías: la tarjeta
  // abre la lista de los más vendidos y el desplegable cambia la ventana de
  // venta. El ranking no se pide hasta que se abre el filtro.
  const [periodo, setPeriodo] = useState('7d')
  const [vistaMasVendidos, setVistaMasVendidos] = useState(false)
  const ranking = useMasVendidos(periodo, 12, vistaMasVendidos)
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
        {vistaMasVendidos ? (
          <VistaMasVendidos
            ranking={ranking}
            periodo={periodo}
            onPeriodo={setPeriodo}
            onVolver={() => setVistaMasVendidos(false)}
          />
        ) : (
          <>
            {cargando && categorias.length === 0 && (
              <p style={{ textAlign: 'center', color: 'var(--text-dim)' }}>Cargando categorías…</p>
            )}
            <div className="grid-3" style={{ rowGap: 8 }}>
              <TarjetaMasVendidos onClick={() => setVistaMasVendidos(true)} />
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
                      ...ESTILO_TARJETA,
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
          </>
        )}
      </section >
    </>
  )
}