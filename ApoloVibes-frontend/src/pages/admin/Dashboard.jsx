const stats = [
  { label: 'Ventas hoy', value: '$1.284.000' },
  { label: 'Pedidos pendientes', value: '18' },
  { label: 'Cotizaciones sin revisar', value: '5' },
  { label: 'Ingresos del mes', value: '$24,6M' },
]

export default function Dashboard() {
  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24, color: 'var(--surface-2)' }}>Dashboard</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 18 }}>
        {stats.map(s => (
          <div key={s.label} style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 15, color: 'var(--surface)', marginBottom: 8, textAlign: 'center' }}>{s.label}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 24, color: 'var(--surface)', textAlign: 'center' }}>{s.value}</div>
          </div>
        ))}
      </div>
    </>
  )
}
