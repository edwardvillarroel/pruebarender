import { useState } from 'react'
import ProductCard from '../components/ProductCard.jsx'
import { categorias, productos } from '../data/products.js'

export default function Categorias() {
  const [activa, setActiva] = useState(null)

  const filtrados = activa ? productos.filter(p => p.categoria === activa) : productos

  return (
    <section className="wrap section-py-mobile" style={{ padding: '48px 0 80px' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 30, marginBottom: 24, textAlign: 'center', color: 'var(--surface)' }}>Catálogo</h1>

      <div style={{ display: 'flex', gap: 10, marginBottom: 32, flexWrap: 'wrap', justifyContent: 'center' }}>
        <button
          className="btn btn-ghost"
          onClick={() => setActiva(null)}
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
            onClick={() => setActiva(cat.id)}
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

      {filtrados.length === 0 ? (
        <p style={{
          textAlign: 'center', color: 'var(--text-dim)', padding: '410px 0'
        }}>
          No hay productos en esta categoría todavía.
        </p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 20 }}>
          {filtrados.map(p => <ProductCard key={p.id} producto={p} />)}
        </div>
      )}
    </section>
  )
}
