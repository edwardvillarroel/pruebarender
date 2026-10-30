import { useEffect, useState } from 'react'
import { CreditCard, FileText } from 'lucide-react'
import { productoApi } from '../../services/products.js'
import { reportesApi } from '../../services/reportes.js'

function capitalizar(texto) {
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : '';
}

function formatearFecha(iso) {
  try {
    return capitalizar(new Date(iso).toLocaleDateString('es-CL', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    }));
  } catch {
    return '';
  }
}

function formatoPesos(valor) {
  return `$${Number(valor || 0).toLocaleString('es-CL')}`;
}

// Etiqueta corta del eje X: `YYYY-MM-DD` (fecha local de Chile que ya calcula el
// backend) -> `DD/MM`. Se parsea a mano y no con `new Date(iso)`: el constructor
// interpreta `YYYY-MM-DD` como medianoche UTC y, al mostrarlo en hora de Chile,
// restaría un día.
function formatoDiaMes(iso) {
  const partes = String(iso || '').slice(0, 10).split('-');
  if (partes.length !== 3) return '';
  const [anio, mes, dia] = partes;
  if (!anio || !mes || !dia) return '';
  return `${dia}/${mes}`;
}

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  en_produccion: 'En preparación',
  enviado: 'Enviado',
  entregado: 'Entregado',
  cancelado: 'Cancelado',
};

const COLOR_ESTADO = {
  pendiente: 'var(--orange, #f59e0b)',
  en_produccion: 'var(--blue, #3b82f6)',
  enviado: 'var(--blue, #3b82f6)',
  entregado: 'var(--green, #22c55e)',
  cancelado: 'var(--red, #ef4444)',
};

// ---------- helpers de gráficos (SVG puro, sin librerías) ----------

function Sparkline({ data, up }) {
  const w = 100, h = 28;
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(' ');
  const color = up ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)';

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={28} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function VentasChart({ data }) {
  const w = 560, h = 200, padX = 10, padY = 16;
  if (!data || data.length === 0) {
    return <p style={{ fontSize: 12.5, color: 'var(--text-dim)' }}>Sin datos de ventas todavía.</p>;
  }
  const max = Math.max(...data.map(d => Number(d.valor) || 0));
  const stepX = (w - padX * 2) / (data.length - 1);

  const puntos = data.map((d, i) => {
    const x = padX + i * stepX;
    const y = padY + (h - padY * 2) * (1 - (Number(d.valor) || 0) / (max || 1));
    return { x, y, ...d };
  });

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
  );
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
  );
}

export default function Dashboard() {
  // "Productos más vendidos" sale del ranking real del backend
  // (`GET /api/productos/mas-vendidos`), no de una lista fija: el histórico
  // completo, que es lo que interesa para decidir qué volver a producir.
  const [topProductos, setTopProductos] = useState([]);
  const [errorTopProductos, setErrorTopProductos] = useState(null);

  // Reporte general de ventas y pedidos (backend admin-only).
  const [reporte, setReporte] = useState(null);
  const [cargandoReporte, setCargandoReporte] = useState(true);
  const [errorReporte, setErrorReporte] = useState(null);

  useEffect(() => {
    let vigente = true;
    productoApi.masVendidos('todo', 5)
      .then(res => {
        if (!vigente) return;
        setTopProductos(res.productos ?? []);
      })
      .catch(err => {
        if (!vigente) return;
        setErrorTopProductos(err.message);
      });
    return () => { vigente = false; };
  }, []);

  useEffect(() => {
    let vigente = true;
    (async () => {
      try {
        const res = await reportesApi.resumen();
        if (!vigente) return;
        setReporte(res.reporte || res || {});
      } catch (err) {
        if (!vigente) return;
        setErrorReporte(err.message);
      } finally {
        if (vigente) setCargandoReporte(false);
      }
    })();
    return () => { vigente = false; };
  }, []);

  const ventas = reporte?.ventas || {};
  const pedidos = reporte?.pedidos || {};
  const cotizaciones = reporte?.cotizaciones || {};

  const stats = [
    {
      label: 'Ventas hoy',
      valor: formatoPesos(ventas.hoy?.total ?? 0),
    },
    {
      label: 'Pedidos pendientes',
      valor: String((pedidos.pendientes || []).length),
    },
    {
      label: 'Cotizaciones sin revisar',
      valor: String((cotizaciones.sin_revisar || []).length),
    },
    {
      label: 'Ingresos del mes',
      valor: formatoPesos(ventas.mes?.total ?? 0),
    },
  ];

  // Cada punto es una semana (lunes a domingo, en hora de Chile). El eje X
  // muestra la fecha de inicio de esa semana en DD/MM; el backend ya entrega
  // `desde` como fecha local, así que la etiqueta coincide con los datos.
  const ventasSemana = (ventas.semanas || []).map(w => ({
    label: formatoDiaMes(w.desde),
    valor: Number(w.total) || 0,
  }));

  const pedidosRecientes = (pedidos.recientes || []).map(p => ({
    id: `#${String(p.id || '').slice(0, 8)}`,
    cliente: p.cliente || '—',
    monto: formatoPesos(p.total),
    estado: ETIQUETAS_ESTADO[p.estado] || p.estado,
  }));

  const actividadReciente = [
    ...(pedidos.recientes || []).slice(0, 2).map(p => ({
      icon: CreditCard,
      texto: `Pago registrado en el pedido #${String(p.id || '').slice(0, 8)}`,
      tiempo: p.fecha,
    })),
    ...(cotizaciones.sin_revisar || []).slice(0, 2).map(c => ({
      icon: FileText,
      texto: `Cotización nueva recibida${c.nombre ? ` de ${c.nombre}` : ''}`,
      tiempo: c.creado_en,
    })),
  ];

  return (
    <>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24, color: 'var(--surface-2)' }}>
        Dashboard
      </h1>

      {errorReporte && (
        <p style={{ color: 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
          No se pudo cargar el reporte de ventas: {errorReporte}
        </p>
      )}

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 18, marginBottom: 18 }}>
        {cargandoReporte ? (
          <p style={{ color: 'var(--text-dim)', gridColumn: '1 / -1', margin: 0 }}>Cargando…</p>
        ) : (
          stats.map(s => (
            <div key={s.label} style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 13, color: 'var(--surface)', marginBottom: 6 }}>{s.label}</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 22, color: 'var(--surface)' }}>{s.valor}</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Fila principal: ventas + productos */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 18, marginBottom: 18 }}>
        <Panel title="Resumen de ventas">
          {cargandoReporte ? (
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Cargando…</p>
          ) : errorReporte ? (
            <p style={{ fontSize: 12.5, color: 'var(--red, #ef4444)' }}>
              No se pudo cargar el resumen de ventas.
            </p>
          ) : (
            <VentasChart data={ventasSemana} />
          )}
        </Panel>

        <Panel title="Productos más vendidos">
          {errorTopProductos ? (
            <p style={{ fontSize: 12.5, color: 'var(--red, #ef4444)' }}>
              No se pudo cargar el ranking: {errorTopProductos}
            </p>
          ) : topProductos.length === 0 ? (
            <p style={{ fontSize: 12.5, color: 'var(--text-dim)' }}>
              Todavía no hay ventas registradas.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {topProductos.map((p) => {
                const maxMonto = topProductos[0].ingresos || 1
                const pct = (p.ingresos / maxMonto) * 100
                return (
                  <div key={p.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: 'var(--surface)', marginBottom: 5 }}>
                      <span>{p.nombre}</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>
                        ${Number(p.ingresos).toLocaleString('es-CL')} CLP
                      </span>
                    </div>
                    <div style={{ height: 6, borderRadius: 4, background: 'var(--line)', overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', borderRadius: 4 }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Panel>
      </div>

      {/* Fila secundaria: pedidos recientes + actividad reciente */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 18 }}>
        <Panel title="Pedidos recientes" action="Ver todo">
          {cargandoReporte ? (
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Cargando…</p>
          ) : pedidosRecientes.length === 0 ? (
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Todavía no hay pedidos registrados.</p>
          ) : (
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
                        color: COLOR_ESTADO[p.estado] || 'var(--text-dim)', background: `${COLOR_ESTADO[p.estado] || 'var(--text-dim)'}22`,
                      }}>
                        {p.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        <Panel title="Actividad reciente" action="Ver todo">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {actividadReciente.length === 0 ? (
              <p style={{ fontSize: 12.5, color: 'var(--text-dim)' }}>Sin actividad reciente.</p>
            ) : (
              actividadReciente.map((a, i) => {
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
                    <div style={{ fontSize: 11.5, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>{a.tiempo ? formatearFecha(a.tiempo) : ''}</div>
                  </div>
                )
              })
            )}
          </div>
        </Panel>
      </div>
    </>
  );
}
