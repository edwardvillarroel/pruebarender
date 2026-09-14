import { Pencil, Trash2 } from 'lucide-react';


const pedidosMock = [
  { id: '#F3D-1042', cliente: 'Camila Reyes', producto: 'Nova X1 Core', estado: 'Enviado', total: 489000 },
  { id: '#F3D-1041', cliente: 'Taller Polígono', producto: 'Resina 0.5L ×6', estado: 'En producción', total: 135000 },
  { id: '#F3D-1040', cliente: 'Ignacio Soto', producto: 'PETG translúcido', estado: 'Enviado', total: 14900 },
]


export default function Pedidos() {
  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24, color: 'var(--surface-2)' }}>Pedidos</h1>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ color: 'var(--surface)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
            <th style={{ padding: '0 10px 12px' }}>Pedido</th>
            <th style={{ padding: '0 10px 12px' }}>Cliente</th>
            <th style={{ padding: '0 10px 12px' }}>Producto</th>
            <th style={{ padding: '0 10px 12px' }}>Estado</th>
            <th style={{ padding: '0 10px 12px' }}>Total</th>
            <th style={{ padding: '0 10px 12px' }}></th>
            <th style={{ padding: '0 10px 12px' }}></th>
          </tr>
        </thead>
        <tbody>
          {pedidosMock.map(p => (
            <tr key={p.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
              <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>{p.id}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.cliente}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.producto}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.estado}</td>
              <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>${p.total.toLocaleString('es-CL')}</td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}><Pencil size={16} color='var(--green)' /></td>
              <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}><Trash2 size={16} color='var(--red)' /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
