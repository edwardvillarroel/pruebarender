import { Package, CreditCard, AlertTriangle, FileText } from 'lucide-react'

// ---------- datos de ejemplo (reemplazar por datos reales del backend) ----------

const stats = [
  { label: 'Ventas hoy', value: '$1.284.000', trend: '+12.9%', up: true, spark: [4, 5, 4.5, 6, 5.5, 7, 8] },
  { label: 'Pedidos pendientes', value: '18', trend: '+8.3%', up: true, spark: [6, 6, 5, 7, 6, 8, 7] },
  { label: 'Cotizaciones sin revisar', value: '5', trend: '-15.7%', up: false, spark: [8, 7, 7, 6, 6, 5, 5] },
  { label: 'Ingresos del mes', value: '$24,6M', trend: '+5.6%', up: true, spark: [3, 4, 4, 5, 6, 6.5, 7] },
]

const ventasSemana = [
  { label: 'Sem 1', valor: 320000 },
  { label: 'Sem 2', valor: 410000 },
  { label: 'Sem 3', valor: 380000 },
  { label: 'Sem 4', valor: 610000 },
  { label: 'Sem 5', valor: 780000 },
]

const topProductos = [
  { nombre: 'Figura Goku 20cm', monto: '$245K' },
  { nombre: 'Maceta Geométrica', monto: '$186K' },
  { nombre: 'Llavero Personalizado', monto: '$142K' },
  { nombre: 'Organizador Escritorio', monto: '$118K' },
  { nombre: 'Base para Celular', monto: '$96K' },
]

const pedidosRecientes = [
  { id: '#1042', cliente: 'María Torres', monto: '$45.000', estado: 'Confirmado' },
  { id: '#1041', cliente: 'Juan Pérez', monto: '$28.900', estado: 'En proceso' },
  { id: '#1040', cliente: 'Sofía Ramírez', monto: '$63.500', estado: 'Enviado' },
  { id: '#1039', cliente: 'Diego Fuentes', monto: '$19.800', estado: 'Confirmado' },
]

const actividadReciente = [
  { icon: Package, texto: 'Nuevo pedido #1042 creado', tiempo: '2m' },
  { icon: CreditCard, texto: 'Pago recibido pedido #1039', tiempo: '15m' },
  { icon: AlertTriangle, texto: 'Stock bajo: Filamento PLA Negro', tiempo: '1h' },
  { icon: FileText, texto: 'Cotización #58 recibida', tiempo: '2h' },
]

const estadoColor = {
  'Confirmado': 'var(--green, #22c55e)',
  'En proceso': 'var(--orange, #f59e0b)',
  'Enviado': 'var(--blue, #3b82f6)',
}

// ---------- helpers de gráficos (SVG puro, sin librerías) ----------

function Sparkline({ data, up }) {
  const w = 100, h = 28
  const max = Math.max(...data), min = Math.min(...data)
  const range = max - min || 1
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - ((v - min) / range) * h
    return `${x},${y}`
  }).join(' ')
  const color = up ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)'

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={28} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function VentasChart({ data }) {
  const w = 560, h = 200, padX = 10, padY = 16
  const max = Math.max(...data.map(d => d.valor))
  const stepX = (w - padX * 2) / (data.length - 1)

  const puntos = data.map((d, i) => {
    const x = padX + i * stepX
    const y = padY + (h - padY * 2) * (1 - d.valor / max)
    return { x, y, ...d }
  })

  const linea = puntos.map(p => `${p.x},${p.y}`).join(' ')
  const area = `${padX},${h - padY} ${linea} ${padX + (data.length - 1) * stepX},${h - padY}`

  return (
    <svg viewBox={`0 0 ${w} ${h + 20}`} width="100%" height={h + 20}>
      <defs>
        <linearGradient id="ventasFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>

      <polygon points={area} fill="url(#ventasFill)" />
      <polyline points={linea} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

      {puntos.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="4" fill="var(--surface-2, #fff)" stroke="var(--accent)" strokeWidth="2" />
      ))}

      {puntos.map((p, i) => (
        <text key={i} x={p.x} y={h + 14} fontSize="11" fill="var(--surface)" textAnchor="middle">
          {p.label}
        </text>
      ))}
    </svg>
  )
}

// ---------- panel base reutilizable ----------

function Panel({ title, action, children }) {
  return (
    <div style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--surface)' }}>{title}</div>
        {action && (
          <span style={{ fontSize: 12, color: 'var(--accent)', cursor: 'pointer', fontWeight: 500 }}>{action}</span>
        )}
      </div>
      {children}
    </div>
  )
}

export default function Dashboard() {
  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24, color: 'var(--surface-2)' }}>
        Dashboard
      </h1>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 18, marginBottom: 18 }}>
        {stats.map(s => (
          <div key={s.label} style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 13, color: 'var(--surface)', marginBottom: 6 }}>{s.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 10 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 22, color: 'var(--surface)' }}>{s.value}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: s.up ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)' }}>
                {s.up ? '↑' : '↓'} {s.trend}
              </span>
            </div>
            <Sparkline data={s.spark} up={s.up} />
          </div>
        ))}
      </div>

      {/* Fila principal: ventas + productos */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 18, marginBottom: 18 }}>
        <Panel title="Resumen de ventas">
          <VentasChart data={ventasSemana} />
        </Panel>

        <Panel title="Productos más vendidos">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {topProductos.map((p, i) => {
              const maxMonto = parseInt(topProductos[0].monto.replace(/\D/g, ''))
              const monto = parseInt(p.monto.replace(/\D/g, ''))
              const pct = (monto / maxMonto) * 100
              return (
                <div key={p.nombre}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: 'var(--surface)', marginBottom: 5 }}>
                    <span>{p.nombre}</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{p.monto}</span>
                  </div>
                  <div style={{ height: 6, borderRadius: 4, background: 'var(--line)', overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', borderRadius: 4 }} />
                  </div>
                </div>
              )
            })}
          </div>
        </Panel>
      </div>

      {/* Fila secundaria: pedidos recientes + actividad reciente */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 18 }}>
        <Panel title="Pedidos recientes" action="Ver todo">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              {pedidosRecientes.map(p => (
                <tr key={p.id} style={{ borderTop: '1px solid var(--line)' }}>
                  <td style={{ padding: '10px 6px', fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>{p.id}</td>
                  <td style={{ padding: '10px 6px', color: 'var(--surface)' }}>{p.cliente}</td>
                  <td style={{ padding: '10px 6px', fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>{p.monto}</td>
                  <td style={{ padding: '10px 6px' }}>
                    <span style={{
                      fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 20,
                      color: estadoColor[p.estado], background: `${estadoColor[p.estado]}22`,
                    }}>
                      {p.estado}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel title="Actividad reciente" action="Ver todo">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {actividadReciente.map((a, i) => {
              const Icon = a.icon
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 8, background: 'var(--accent-2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    color: 'var(--accent)', border: '1px solid var(--line)',
                  }}>
                    <Icon size={15} />
                  </div>
                  <div style={{ flex: 1, fontSize: 12.5, color: 'var(--surface)' }}>{a.texto}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>{a.tiempo}</div>
                </div>
              )
            })}
          </div>
        </Panel>
      </div>
    </>
  )
}