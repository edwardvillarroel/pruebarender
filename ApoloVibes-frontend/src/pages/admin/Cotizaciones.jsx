import { useState } from 'react'

const cotizacionesMock = [
  {
    id: 'C-108', nombre: 'Valentina Muñoz', email: 'valentina@mail.com',
    material: 'Resina', descripcion: 'Figura articulada de 15cm, 2 unidades, color a definir.',
    estado: 'pendiente', imagen: null,
  },
  {
    id: 'C-107', nombre: 'Estudio Base', email: 'contacto@estudiobase.cl',
    material: 'PETG', descripcion: 'Soporte técnico para sensor, tolerancia ±0.2mm.',
    estado: 'pendiente', imagen: null,
  },
]

const estilosEstado = {
  pendiente: { background: 'var(--gold)', color: 'var(--surface)' },
  aprobada: { background: 'var(--green)', color: 'var(--text)' },
  rechazada: { background: 'var(--red)', color: 'var(--text)' },
}

export default function Cotizaciones() {
  const [items, setItems] = useState(cotizacionesMock)
  const [precios, setPrecios] = useState({})


  function aprobar(id) {
    const precio = precios[id]
    if (!precio) { alert('Ingresa un precio estimado antes de aprobar.'); return }
    setItems(prev => prev.map(c => (c.id === id ? { ...c, estado: 'aprobada' } : c)))
  }

  function rechazar(id) {
    setItems(prev => prev.map(c => (c.id === id ? { ...c, estado: 'rechazada' } : c)))
  }

  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 3, color: 'var(--surface-2)' }}>Cotizaciones</h1>
      <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 24 }}>
        Solicitudes enviadas por clientes desde el formulario de cotización.
      </p>

      <div style={{ display: 'grid', gap: 16 }}>
        {items.map(c => (
          <div key={c.id} style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, display: 'grid', gridTemplateColumns: '140px 1fr 220px', gap: 20 }}>
            <div style={{ width: 140, height: 140, borderRadius: 8, background: 'var(--surface-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: 'var(--text-dim)' }}>
              {c.imagen ? <img src={c.imagen} alt={`Referencia enviada por ${c.nombre}`} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8, }} /> : 'imagen adjunta'}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent)' }}>{c.id}</span>
                <span style={{ fontSize: 11, padding: '3px 9px', borderRadius: 100, fontFamily: 'var(--font-mono)', ...estilosEstado[c.estado] }}>
                  {c.estado}
                </span>
              </div>
              <p style={{ fontWeight: 600, marginBottom: 4, color: 'var(--surface-2)' }}>{c.nombre} <span style={{ fontWeight: 400, color: 'var(--text-dim)', fontSize: 12 }}>· {c.email}</span></p>
              <p style={{ fontSize: 13, color: 'var(--surface-2)', marginBottom: 6 }}>Material sugerido: {c.material}</p>
              <p style={{ fontSize: 13, color: 'var(--text-dim)' }}>{c.descripcion}</p>
            </div>

            {c.estado === 'pendiente' ? (
              <div>
                <label>$ Precio estimado (CLP)</label>
                <input
                  type="number"
                  placeholder="0"
                  onChange={e => setPrecios(prev => ({ ...prev, [c.id]: e.target.value }))}
                  style={{ marginBottom: 10, color: 'var(--surface-2)' }}
                />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary" onClick={() => aprobar(c.id)}>Aprobar</button>
                  <button className="btn btn-ghost" onClick={() => rechazar(c.id)}>Rechazar</button>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 13, color: 'var(--surface)', alignSelf: 'center' }}>
                Respuesta enviada al cliente.
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  )
}
