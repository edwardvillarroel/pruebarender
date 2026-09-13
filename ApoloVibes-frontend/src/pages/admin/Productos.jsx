import { useProductos } from '../../context/ProductContext.jsx'

// En producción: CRUD real contra /api/productos (crear, editar, eliminar).
export default function Productos() {
  const { productos, categorias, cargando, error } = useProductos()

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24 }}>Productos</h1>
        <button className="btn btn-primary">+ Nuevo producto</button>
      </div>
      {cargando ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando productos…</p>
      ) : error ? (
        <p style={{ color: '#ef4444' }}>Error al cargar productos: {error}</p>
      ) : productos.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>Aún no hay productos.</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {productos.map(p => {
            const categoria = categorias.find(c => c.id === p.categoria_id)
            return (
              <div key={p.id} style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12, padding: 18 }}>
                <h4 style={{ fontSize: 14, marginBottom: 8 }}>{p.nombre}</h4>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--text-dim)' }}>
                  ${p.precio.toLocaleString('es-CL')}
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '8px 0 0' }}>
                  {categoria?.nombre ?? 'Sin categoría'} · {p.sinStock ? 'sin stock' : `${p.stock} en stock`}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}