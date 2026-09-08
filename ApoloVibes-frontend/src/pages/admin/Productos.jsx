import { productos } from '../../data/products.js'

// En producción: CRUD real contra /api/productos (crear, editar, eliminar).
export default function Productos() {
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24 }}>Productos</h1>
        <button className="btn btn-primary">+ Nuevo producto</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {productos.map(p => (
          <div key={p.id} style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12, padding: 18 }}>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>{p.nombre}</h4>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--text-dim)' }}>
              ${p.precio.toLocaleString('es-CL')}
            </p>
          </div>
        ))}
      </div>
    </>
  )
}
