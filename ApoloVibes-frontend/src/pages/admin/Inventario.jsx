const stockCritico = [
  { nombre: 'PLA negro 1.75mm', cantidad: 3 },
  { nombre: 'Boquilla 0.4mm acero', cantidad: 5 },
  { nombre: 'Resina gris estándar', cantidad: 2 },
]

export default function Inventario() {
  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24 }}>Inventario</h1>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12, padding: 22, maxWidth: 420 }}>
        <h3 style={{ fontSize: 14, marginBottom: 16 }}>Stock crítico</h3>
        {stockCritico.map(s => (
          <div key={s.nombre} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)', fontSize: 13 }}>
            <span>{s.nombre}</span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>{s.cantidad} uds</span>
          </div>
        ))}
      </div>
    </>
  )
}
