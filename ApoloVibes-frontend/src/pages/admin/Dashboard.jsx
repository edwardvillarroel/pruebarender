const stats = [
  { label: 'Ventas hoy', value: '$1.284.000' },
  { label: 'Pedidos pendientes', value: '18' },
  { label: 'Cotizaciones sin revisar', value: '5' },
  { label: 'Ingresos del mes', value: '$24,6M' },
]

export default function Dashboard() {
  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24 }}>Dashboard</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 18 }}>
        {stats.map(s => (
          <div key={s.label} style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 12 }}>{s.label}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 24 }}>{s.value}</div>
          </div>
        ))}
      </div>
    </>
  )
}
