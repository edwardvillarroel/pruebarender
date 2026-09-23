import { useState, useEffect } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { RefreshCw, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { pedidosApi } from '../services/orders.js';

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  en_produccion: 'En producción',
  enviado: 'Enviado',
  entregado: 'Entregado',
  cancelado: 'Cancelado',
};

export default function MisPedidos() {
  const { isLoggedIn } = useAuth();
  const [cargando, setCargando] = useState(true);
  const [pedidos, setPedidos] = useState([]);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState(null);
  const [sincronizandoId, setSincronizandoId] = useState(null);

  async function cargar() {
    setCargando(true);
    setError(null);
    try {
      const data = await pedidosApi.mios();
      setPedidos(data.pedidos || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    if (isLoggedIn) cargar();
  }, [isLoggedIn]);

  if (!isLoggedIn) {
    return <Navigate to="/" replace />;
  }

  async function sincronizar(pedido) {
    setSincronizandoId(pedido.id);
    setMensaje(null);
    try {
      const data = await pedidosApi.sincronizarSeguimiento(pedido.id);
      setMensaje({
        tipo: 'ok',
        texto: data.estado_seguimiento
          ? `Estado de tu pedido: ${data.estado_seguimiento}`
          : 'Sin datos de seguimiento por el momento.',
      });
      await cargar();
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setSincronizandoId(null);
    }
  }

  const fecha = (f) => f ? new Date(f).toLocaleDateString('es-CL') : '—';
  const estadoSeguimiento = (p) => {
    if (!p.codigo_seguimiento) return 'Sin despacho';
    return p.estado_seguimiento || 'Consultando…';
  };

  return (
    <div className="wrap" style={{ padding: '48px 32px', minHeight: '50vh' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 8, color: 'var(--text)' }}>
        Mis pedidos
      </h1>
      <p style={{ margin: '0 0 28px', fontSize: 14, color: 'var(--text-dim)' }}>
        Aquí puedes revisar el estado de cada pedido y su seguimiento de envío.
      </p>

      {cargando ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando tus pedidos…</p>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#b60303', fontSize: 13 }}>
          <AlertTriangle size={16} />
          {error}
        </div>
      ) : pedidos.length === 0 ? (
        <div style={{ border: '1px dashed var(--surface-3)', borderRadius: 16, padding: '40px 24px', textAlign: 'center' }}>
          <p style={{ margin: '0 0 12px', color: 'var(--text-dim)' }}>Todavía no tienes pedidos.</p>
          <Link to="/categorias" style={{ color: '#009D4E' }}>Ir a la tienda</Link>
        </div>
      ) : (
        <>
          {mensaje && (
            <p style={{ color: mensaje.tipo === 'ok' ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
              {mensaje.texto}
            </p>
          )}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ color: 'var(--text-dim)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase', borderBottom: '1px solid var(--line)' }}>
                <th style={{ padding: '0 10px 12px' }}>Pedido</th>
                <th style={{ padding: '0 10px 12px' }}>Fecha</th>
                <th style={{ padding: '0 10px 12px' }}>Estado</th>
                <th style={{ padding: '0 10px 12px' }}>Total</th>
                <th style={{ padding: '0 10px 12px' }}>Código seguimiento</th>
                <th style={{ padding: '0 10px 12px' }}>Estado de envío</th>
                <th style={{ padding: '0 10px 12px' }}></th>
              </tr>
            </thead>
            <tbody>
              {pedidos.map((p) => (
                <tr key={p.id} style={{ borderBottom: '1px solid var(--surface-3)' }}>
                  <td style={{ padding: '14px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>
                    {p.id.slice(0, 8)}
                  </td>
                  <td style={{ padding: '14px 10px', color: 'var(--text-dim)' }}>{fecha(p.fecha)}</td>
                  <td style={{ padding: '14px 10px', color: 'var(--text-dim)' }}>
                    {ETIQUETAS_ESTADO[p.estado] || p.estado}
                  </td>
                  <td style={{ padding: '14px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text)' }}>
                    ${p.total.toLocaleString('es-CL')}
                  </td>
                  <td style={{ padding: '14px 10px', color: 'var(--text-dim)' }}>
                    {p.codigo_seguimiento || '—'}
                  </td>
                  <td style={{ padding: '14px 10px', color: 'var(--text-dim)' }}>
                    {estadoSeguimiento(p)}
                  </td>
                  <td style={{ padding: '14px 10px', textAlign: 'right' }}>
                    <button
                      onClick={() => sincronizar(p)}
                      disabled={sincronizandoId === p.id}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px',
                        borderRadius: 8, border: '1px solid var(--surface-3)', background: 'transparent',
                        color: 'var(--text)', fontSize: 12, cursor: sincronizandoId === p.id ? 'wait' : 'pointer',
                        opacity: sincronizandoId === p.id ? 0.5 : 1,
                      }}
                    >
                      <RefreshCw size={13} />
                      {sincronizandoId === p.id ? 'Actualizando…' : 'Actualizar estado'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}