import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { ventasApi } from '../../services/ventas.js';

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

function formatearHora(iso) {
  try {
    return new Date(iso).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function totalVenta(venta) {
  const items = venta.items || [];
  if (items.length) return items.reduce((s, i) => s + Number(i.cantidad) * Number(i.precio_unitario), 0);
  return Number(venta.total) || 0;
}

function normalizarReporte(r) {
  const ventas = r.ventas || [];
  const suma = (medio) => ventas
    .filter(v => (v.medio_pago || '').toLowerCase() === medio)
    .reduce((s, v) => s + totalVenta(v), 0);
  return {
    ...r,
    n_ventas: r.n_ventas ?? ventas.length,
    total_efectivo: r.total_efectivo ?? suma('efectivo'),
    total_tuu: r.total_tuu ?? suma('tuu'),
    total: r.total ?? ventas.reduce((s, v) => s + totalVenta(v), 0),
  };
}

export default function ReporteVentas() {
  const [reportes, setReportes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [mensaje, setMensaje] = useState(null);
  const [detalle, setDetalle] = useState(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const res = await ventasApi.listarReportes();
        if (activo) setReportes(res.reportes || []);
      } catch (err) {
        if (activo) setMensaje({ tipo: 'error', texto: err.message });
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => { activo = false; };
  }, []);

  async function abrirDetalle(reporte) {
    setCargandoDetalle(true);
    setMensaje(null);
    try {
      const res = await ventasApi.detalleReporte(reporte.id);
      setDetalle(normalizarReporte(res.reporte || res));
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setCargandoDetalle(false);
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, color: 'var(--surface-2)' }}>Reporte de Ventas</h1>
      </div>

      {cargando ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando…</p>
      ) : (
        <>
          {mensaje && (
            <p style={{ color: mensaje.tipo === 'ok' ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
              {mensaje.texto}
            </p>
          )}

          {reportes.length === 0 ? (
            <p style={{ color: 'var(--text-dim)' }}>Aún no hay reportes guardados.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'var(--surface)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '0 10px 12px' }}>Lugar</th>
                  <th style={{ padding: '0 10px 12px' }}>Fecha</th>
                  <th style={{ padding: '0 10px 12px' }}>Ventas</th>
                  <th style={{ padding: '0 10px 12px' }}>Efectivo</th>
                  <th style={{ padding: '0 10px 12px' }}>TUU</th>
                  <th style={{ padding: '0 10px 12px' }}>Total</th>
                  <th style={{ padding: '0 10px 12px' }}></th>
                </tr>
              </thead>
              <tbody>
                {reportes.map((r) => {
                  const n = normalizarReporte(r);
                  return (
                    <tr
                      key={r.id}
                      style={{ borderTop: '1px solid var(--surface-3)', cursor: 'pointer' }}
                      onClick={() => abrirDetalle(r)}
                    >
                      <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{r.lugar}</td>
                      <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{formatearFecha(r.fecha)}</td>
                      <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>{n.n_ventas}</td>
                      <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                        ${Number(n.total_efectivo || 0).toLocaleString('es-CL')}
                      </td>
                      <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                        ${Number(n.total_tuu || 0).toLocaleString('es-CL')}
                      </td>
                      <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--green)' }}>
                        ${Number(n.total || 0).toLocaleString('es-CL')}
                      </td>
                      <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>Detalles</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </>
      )}

      {detalle && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 9999, backdropFilter: 'blur(4px)', padding: 24,
          }}
          onClick={() => setDetalle(null)}
        >
          <div
            style={{
              background: 'var(--surface)', borderRadius: 16, padding: '28px',
              width: '100%', maxWidth: 560, maxHeight: '80vh', overflowY: 'auto',
              boxShadow: '0 20px 60px rgba(0,0,0,.3)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 18 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>{detalle.lugar}</h3>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-dim)' }}>{formatearFecha(detalle.fecha)}</p>
              </div>
              <button
                onClick={() => setDetalle(null)}
                aria-label="Cerrar detalle"
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 4 }}
              >
                <X size={18} color="var(--text-dim)" />
              </button>
            </div>

            {cargandoDetalle ? (
              <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Cargando detalle…</p>
            ) : (
              <>
                {(detalle.ventas || []).length === 0 ? (
                  <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Este reporte no tiene ventas.</p>
                ) : (
                  detalle.ventas.map((venta, i) => (
                    <div
                      key={venta.id || i}
                      style={{ borderTop: '1px solid var(--surface-3)', padding: '14px 0' }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13, marginBottom: 8 }}>
                        <span style={{ color: 'var(--text-dim)' }}>
                          {formatearHora(venta.creado_en)} · {capitalizar(venta.medio_pago)}
                        </span>
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text)', fontWeight: 600 }}>
                          ${totalVenta(venta).toLocaleString('es-CL')}
                        </span>
                      </div>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                        <tbody>
                          {(venta.items || []).map((item) => (
                            <tr key={item.producto_id}>
                              <td style={{ padding: '2px 8px 2px 0', color: 'var(--text-dim)' }}>{item.nombre}</td>
                              <td style={{ padding: '2px 8px', color: 'var(--text-dim)', textAlign: 'right' }}>
                                {item.cantidad} × ${Number(item.precio_unitario).toLocaleString('es-CL')}
                              </td>
                              <td style={{ padding: '2px 0 2px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textAlign: 'right' }}>
                                ${Number(item.subtotal ?? item.cantidad * item.precio_unitario).toLocaleString('es-CL')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))
                )}

                <div
                  style={{
                    borderTop: '1px solid var(--surface-3)', marginTop: 8, paddingTop: 14,
                    display: 'flex', justifyContent: 'flex-end', gap: 18, flexWrap: 'wrap', fontSize: 13,
                  }}
                >
                  <span style={{ color: 'var(--text-dim)' }}>
                    Efectivo <strong style={{ color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>${Number(detalle.total_efectivo || 0).toLocaleString('es-CL')}</strong>
                  </span>
                  <span style={{ color: 'var(--text-dim)' }}>
                    TUU <strong style={{ color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>${Number(detalle.total_tuu || 0).toLocaleString('es-CL')}</strong>
                  </span>
                  <span style={{ color: 'var(--text-dim)' }}>
                    Total <strong style={{ color: 'var(--green)', fontFamily: 'var(--font-mono)' }}>${Number(detalle.total || 0).toLocaleString('es-CL')}</strong>
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}