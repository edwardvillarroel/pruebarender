import { Pencil, Trash2 } from 'lucide-react';

const stockCritico = [
  { id: 1, categoria: 'Figuras de anime', nombre: 'charmander', descripcion: 'Coleccionable de pokemon', material: 'acero', tamano: '10cm', precio: 15000, stock: 3 },
  { id: 2, categoria: 'Figuras de anime', nombre: 'Eeve', descripcion: 'Coleccionable de pokemon', material: 'acero', tamano: '10cm', precio: 15000, stock: 5 },
  { id: 3, categoria: 'LLaveros', nombre: 'Escudo Capitan America', descripcion: 'Llavero azul-rojo-blanco', material: 'carton', tamano: '5cm', precio: 5000, stock: 15 },
]

export default function Inventario() {
  return (
    <>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24, color: 'var(--surface-2)' }}>Inventario</h1>
        <button className="btn btn-primary">+ Nuevo producto</button>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ color: 'var(--surface)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
            <th style={{ padding: '0 10px 12px' }}>#</th>
            <th style={{ padding: '0 10px 12px' }}>Categoria</th>
            <th style={{ padding: '0 10px 12px' }}>Nombre</th>
            <th style={{ padding: '0 10px 12px' }}>Descripción</th>
            <th style={{ padding: '0 10px 12px' }}>Material</th>
            <th style={{ padding: '0 10px 12px' }}>Tamaño</th>
            <th style={{ padding: '0 10px 12px' }}>Precio</th>
            <th style={{ padding: '0 10px 12px' }}>Stock</th>
            <th style={{ padding: '0 10px 12px' }}></th>
            <th style={{ padding: '0 10px 12px' }}></th>
          </tr>
        </thead>
        <tbody>
          {stockCritico.map(s => (
            <tr key={s.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
              <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>{s.id}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{s.categoria}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{s.nombre}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{s.descripcion}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{s.material}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{s.tamano}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{s.precio}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{s.stock}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}><Pencil size={16} color='var(--green)' /></td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}><Trash2 size={16} color='var(--red)' /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
