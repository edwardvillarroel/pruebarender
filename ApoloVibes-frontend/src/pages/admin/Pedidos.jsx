const pedidosMock = [
  { id: '#F3D-1042', cliente: 'Camila Reyes', producto: 'Nova X1 Core', estado: 'Enviado', total: 489000 },
  { id: '#F3D-1041', cliente: 'Taller Polígono', producto: 'Resina 0.5L ×6', estado: 'En producción', total: 135000 },
  { id: '#F3D-1040', cliente: 'Ignacio Soto', producto: 'PETG translúcido', estado: 'Enviado', total: 14900 },
]

// En producción: reemplazar pedidosMock por useEffect + api.get('/pedidos')
export default function Pedidos() {
  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24 }}>Pedidos</h1>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ color: 'var(--text-dim)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
            <th style={{ padding: '0 10px 12px' }}>Pedido</th>
            <th style={{ padding: '0 10px 12px' }}>Cliente</th>
            <th style={{ padding: '0 10px 12px' }}>Producto</th>
            <th style={{ padding: '0 10px 12px' }}>Estado</th>
            <th style={{ padding: '0 10px 12px' }}>Total</th>
          </tr>
        </thead>
        <tbody>
          {pedidosMock.map(p => (
            <tr key={p.id} style={{ borderTop: '1px solid var(--line)' }}>
              <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>{p.id}</td>
              <td style={{ padding: '13px 10px' }}>{p.cliente}</td>
              <td style={{ padding: '13px 10px' }}>{p.producto}</td>
              <td style={{ padding: '13px 10px' }}>{p.estado}</td>
              <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)' }}>${p.total.toLocaleString('es-CL')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
