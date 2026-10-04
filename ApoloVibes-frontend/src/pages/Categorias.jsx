import { useSearchParams } from 'react-router-dom'
import ProductCard from '../components/ProductCard.jsx'
import { useProductos } from '../context/ProductContext.jsx'

const slugify = (texto) =>
  texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')

export default function Categorias() {
  const { productos, categorias, cargando, error } = useProductos()
  const [params, setParams] = useSearchParams()

  const slugActivo = params.get('cat')
  const catActiva = categorias.find(
    (c) => slugify(c.nombre) === slugActivo || c.id === slugActivo
  )
  const activa = catActiva ? catActiva.id : null

  const seleccionar = (cat) => {
    if (cat) setParams({ cat: slugify(cat.nombre) })
    else setParams({})
  }
  const filtrados = activa ? productos.filter(p => p.categoria_id === activa) : productos

  return (
    <section className="wrap section-py-mobile" style={{ paddingTop: '48px', paddingBottom: '80px' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 30, marginBottom: 24, textAlign: 'center', color: 'var(--surface)' }}>Catálogo</h1>

      <div style={{ display: 'flex', gap: 10, marginBottom: 32, flexWrap: 'wrap', justifyContent: 'center' }}>
        <button
          className="btn btn-ghost"
          onClick={() => seleccionar(null)}
          style={{
            background: activa == null ? 'var(--accent)' : 'var(--accent-2)',
            color: activa == null ? '#ffffff' : 'var(--surface)',
            borderColor: activa == null ? 'transparent' : 'var(--line)',
          }}
        >Todas
        </button>
        {categorias.map(cat => (
          <button key={cat.id}
            className="btn btn-ghost"
            onClick={() => seleccionar(cat)}
            style={{
              background: activa == cat.id ? 'var(--accent)' : 'var(--accent-2)',
              color: activa == cat.id ? '#ffffff' : 'var(--surface)',
              borderColor: activa == cat.id ? 'transparent' : 'var(--line)',
            }}
          >
            {cat.nombre}
          </button>
        ))}
      </div>

      {cargando ? (
        <p style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '4px 0' }}>
          Cargando productos…
        </p>
      ) : error ? (
        <p style={{ textAlign: 'center', color: '#ef4444', padding: '4px 0' }}>
          Error al cargar productos: {error}
        </p>
      ) : filtrados.length === 0 ? (
        <p style={{
          textAlign: 'center', color: 'var(--text-dim)', padding: '40px 0'
        }}>
          No hay productos en esta categoría todavía.
        </p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 20 }}>
          {filtrados.map((p, i) => <ProductCard key={p.id} producto={p} index={i} />)}
        </div>
      )}
    </section>
  )
}