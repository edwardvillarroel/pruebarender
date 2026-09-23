import { useState, useCallback, useEffect } from 'react';
import { Pencil, RefreshCw, AlertTriangle } from 'lucide-react';
import { pedidosApi } from '../../services/orders.js';

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  en_produccion: 'En producción',
  enviado: 'Enviado',
  entregado: 'Entregado',
  cancelado: 'Cancelado',
};

function CodigoModal({ pedido, onConfirm, onCancel }) {
  const [codigo, setCodigo] = useState(pedido?.codigo_seguimiento || '');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  async function guardar() {
    setGuardando(true);
    setError(null);
    try {
      await onConfirm(codigo);
    } catch (err) {
      setError(err.message);
      setGuardando(false);
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)',
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
          width: '100%', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'center',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
          Código de seguimiento Starken
        </h3>
        <p style={{ margin: '0 0 18px', fontSize: 13, color: 'var(--text-dim)' }}>
          Orden de Flete (OF) del pedido <strong>#{pedido.id.slice(0, 8)}</strong>.
        </p>
        <input
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          placeholder="Ej: 222123456"
          maxLength={50}
          autoFocus
          style={{
            width: '100%', padding: '10px 12px', borderRadius: 10,
            border: '1px solid var(--line)', background: 'var(--accent-soft)',
            color: 'var(--text)', fontSize: 14, marginBottom: 14, boxSizing: 'border-box',
          }}
        />
        {error && (
          <p style={{ margin: '0 0 12px', fontSize: 12, color: 'var(--red, #ef4444)' }}>{error}</p>
        )}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: '1px solid var(--line)',
              background: 'transparent', color: 'var(--text)', fontSize: 13, fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Cancelar
          </button>
          <button
            onClick={guardar}
            disabled={guardando || !codigo.trim()}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: 'none',
              background: 'var(--green, #22c55e)', color: '#06210f', fontSize: 13, fontWeight: 600,
              cursor: guardando || !codigo.trim() ? 'not-allowed' : 'pointer',
              opacity: guardando || !codigo.trim() ? 0.5 : 1,
            }}
          >
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Pedidos() {
  const [cargando, setCargando] = useState(true);
  const [pedidos, setPedidos] = useState([]);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState(null);
  const [codigoModal, setCodigoModal] = useState(null);
  const [sincronizandoId, setSincronizandoId] = useState(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await pedidosApi.todos();
      setPedidos(data.pedidos || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar() }, [cargar]);

  async function registrarCodigo(pedido, codigo) {
    await pedidosApi.registrarSeguimiento(pedido.id, codigo);
    setCodigoModal(null);
    setMensaje({ tipo: 'ok', texto: 'Código de seguimiento guardado.' });
    await cargar();
  }

  async function sincronizar(pedido) {
    setSincronizandoId(pedido.id);
    setMensaje(null);
    try {
      const data = await pedidosApi.sincronizarSeguimiento(pedido.id);
      const estado = data.codigo_seguimiento
        ? (data.estado_seguimiento || 'Sin datos de Starken')
        : 'Sin código de seguimiento';
      setMensaje({ tipo: 'ok', texto: `Seguimiento #${data.id.slice(0, 8)}: ${estado}` });
      await cargar();
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setSincronizandoId(null);
    }
  }

  const fecha = (f) => f ? new Date(f).toLocaleDateString('es-CL') : '—';
  const estadoSeguimiento = (p) => {
    if (!p.codigo_seguimiento) return <span style={{ color: 'var(--text-dim)' }}>Sin despacho</span>;
    return p.estado_seguimiento || <span style={{ color: 'var(--text-dim)' }}>Pendiente de consulta</span>;
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, color: 'var(--surface-2)' }}>Pedidos</h1>
        <button className="btn btn-primary" onClick={cargar} disabled={cargando}>
          <RefreshCw size={14} style={{ verticalAlign: '-2px', marginRight: 6 }} />
          Refrescar
        </button>
      </div>

      {cargando ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando pedidos…</p>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--red, #ef4444)', fontSize: 13 }}>
          <AlertTriangle size={16} />
          {error}
        </div>
      ) : pedidos.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>No hay pedidos registrados.</p>
      ) : (
        <>
          {mensaje && (
            <p style={{ color: mensaje.tipo === 'ok' ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
              {mensaje.texto}
            </p>
          )}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ color: 'var(--surface)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
                <th style={{ padding: '0 10px 12px' }}>Pedido</th>
                <th style={{ padding: '0 10px 12px' }}>Fecha</th>
                <th style={{ padding: '0 10px 12px' }}>Estado</th>
                <th style={{ padding: '0 10px 12px' }}>Total</th>
                <th style={{ padding: '0 10px 12px' }}>Código seguimiento</th>
                <th style={{ padding: '0 10px 12px' }}>Estado Starken</th>
                <th style={{ padding: '0 10px 12px' }}></th>
              </tr>
            </thead>
            <tbody>
              {pedidos.map(p => (
                <tr key={p.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
                  <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>
                    {p.id.slice(0, 8)}
                  </td>
                  <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{fecha(p.fecha)}</td>
                  <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>
                    {ETIQUETAS_ESTADO[p.estado] || p.estado}
                  </td>
                  <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>
                    ${p.total.toLocaleString('es-CL')}
                  </td>
                  <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>
                    {p.codigo_seguimiento || '—'}
                  </td>
                  <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>
                    {estadoSeguimiento(p)}
                  </td>
                  <td style={{ padding: '13px 10px', whiteSpace: 'nowrap' }}>
                    <span
                      style={{ cursor: 'pointer', marginRight: 12, display: 'inline-flex', verticalAlign: 'middle' }}
                      onClick={() => setCodigoModal(p)}
                      title="Registrar código de seguimiento"
                    >
                      <Pencil size={16} color='var(--green)' />
                    </span>
                    <span
                      style={{ cursor: sincronizandoId === p.id ? 'wait' : 'pointer', display: 'inline-flex', verticalAlign: 'middle' }}
                      onClick={() => !sincronizandoId && sincronizar(p)}
                      title="Actualizar seguimiento Starken"
                    >
                      <RefreshCw size={16} color={p.codigo_seguimiento ? 'var(--surface)' : 'var(--text-dim)'} />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {codigoModal && (
        <CodigoModal
          pedido={codigoModal}
          onConfirm={(codigo) => registrarCodigo(codigoModal, codigo)}
          onCancel={() => setCodigoModal(null)}
        />
      )}
    </>
  );
}