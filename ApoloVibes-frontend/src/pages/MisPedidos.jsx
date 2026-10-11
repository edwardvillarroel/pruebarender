import { useState, useEffect } from 'react';
import { Navigate, Link, useNavigate } from 'react-router-dom';
import { RefreshCw, AlertTriangle, Eye, Star, Package, CircleCheck, MapPin, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import { pedidosApi } from '../services/orders.js';
import { mediaPath } from '../utils/media.js';
import ResenaModal from '../components/ResenaModal.jsx';
import { useBloqueoScroll } from '../hooks/useBloqueoScroll.js';

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  en_produccion: 'En producción',
  enviado: 'Enviado',
  entregado: 'Entregado',
  cancelado: 'Cancelado',
};

const ESTILO_ESTADO = {
  pendiente: { bg: '#FFF1D6', color: '#7A4B00' },
  en_produccion: { bg: '#DCE9FF', color: '#123F8C' },
  enviado: { bg: '#E3DCFF', color: '#3C2A8C' },
  entregado: { bg: '#D7F5D3', color: '#0F5A0B' },
  cancelado: { bg: '#FFD9D9', color: '#8C1212' },
};

const ETIQUETA_ENTREGA = {
  envio: 'Envío a domicilio',
  retiro: 'Retiro',
};

const DIRECCION_RETIRO = 'Álvarez 1106, Viña del Mar';

const formatoPesos = (valor) => '$' + Number(valor).toLocaleString('es-CL');

const fechaTexto = (f) => f ? new Date(f).toLocaleDateString('es-CL') : '—';

let cachePedidos = { usuarioId: null, pedidos: null };

function LogoModal({ archivo = 'PedidosApolo.png', alt = 'Logo' }) {
  return (
    <img
      src={mediaPath(archivo)}
      alt={alt}
      style={{ display: 'block', margin: '0 auto 5px', width: 100, height: 100, objectFit: 'contain' }}
    />
  )
}

function DetalleModal({ pedido, onClose }) {
  const navigate = useNavigate();
  const { repetirPedido } = useCart();
  useBloqueoScroll();
  const [repitiendo, setRepitiendo] = useState(false);
  const itemsPedido = pedido.items || [];
  const sinItems = itemsPedido.length === 0;
  const estilo = ESTILO_ESTADO[pedido.estado] || { bg: '#E5E7EB', color: '#374151' };

  async function repetir() {
    setRepitiendo(true);
    const ok = await repetirPedido(itemsPedido);
    if (ok) {
      onClose();
      navigate('/carrito');
    } else {
      setRepitiendo(false);
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)', padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: 'relative', background: 'var(--surface)', borderRadius: 16, padding: '28px 24px 24px',
          width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'left', maxHeight: '90vh', overflowY: 'auto', boxSizing: 'border-box',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          aria-label="Cerrar"
          style={{
            position: 'absolute', top: 14, right: 14, background: 'none', border: 'none',
            color: '#B9C6DA', cursor: 'pointer', padding: 4, display: 'flex',
          }}
        >
          <X size={20} />
        </button>

        <LogoModal />
        <h3 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#FFFFFF', textAlign: 'center' }}>
          Detalle del pedido
        </h3>
        <p style={{ margin: '0 0 12px', fontSize: 13, color: '#B9C6DA', textAlign: 'center' }}>
          Pedido #{pedido.id.slice(0, 8).toUpperCase()} · {fechaTexto(pedido.fecha)}
        </p>

        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: estilo.bg, color: estilo.color,
            fontSize: 13, fontWeight: 600, padding: '4px 12px', borderRadius: 999,
          }}>
            <CircleCheck size={15} />
            {ETIQUETAS_ESTADO[pedido.estado] || pedido.estado}
          </span>
        </div>

        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 10,
          background: 'rgba(255,255,255,.07)', borderRadius: 10, padding: '12px 14px', marginBottom: 18,
        }}>
          <MapPin size={25} color="#FA7F19" style={{ marginTop: 5, flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#FFFFFF' }}>
              {pedido.entrega === 'retiro' ? 'Retiro ' : (ETIQUETA_ENTREGA[pedido.entrega] || pedido.entrega)}
            </div>
            {pedido.entrega === 'retiro' && (
              <div style={{ fontSize: 13, color: '#B9C6DA' }}>{DIRECCION_RETIRO}</div>
            )}
          </div>
        </div>

        <div style={{ borderTop: '1px solid rgba(255,255,255,.18)' }}>
          {itemsPedido.map((item, i) => (
            <div
              key={`${item.producto_id}-${item.color || ''}-${i}`}
              style={{
                display: 'flex', alignItems: 'center', gap: 14, padding: '12px 0',
                borderBottom: '1px solid rgba(255,255,255,.18)',
              }}
            >
              <div style={{
                width: 56, height: 56, borderRadius: 10, background: '#FFFFFF', flexShrink: 0,
                overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {item.imagen ? (
                  <img src={item.imagen} alt={item.nombre || 'Producto'} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <Package size={24} color="#8A94A3" />
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: '#FFFFFF' }}>{item.nombre || 'Producto'} ( {item.cantidad} )</div>
                <div style={{ fontSize: 13, color: '#B9C6DA' }}>
                  {item.color ? `Color: ${item.color} ` : ''}
                </div>
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: '#FFFFFF', whiteSpace: 'nowrap' }}>
                {formatoPesos(item.precio_unitario * item.cantidad)}
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '16px 0 20px' }}>
          <span style={{ fontSize: 14, color: '#B9C6DA' }}>Total (IVA incluido)</span>
          <span style={{ fontSize: 22, fontWeight: 700, color: '#FFFFFF' }}>{formatoPesos(pedido.total)}</span>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: '12px 0', borderRadius: 10,
              borderColor: 'var(--accent)', background: 'var(--accent)',
              color: '#ffff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Cerrar
          </button>
          <button
            onClick={repetir}
            disabled={repitiendo || sinItems}
            style={{
              flex: 1, padding: '12px 0', borderRadius: 10, border: 'none',
              backgroundColor: 'var(--green, #16bd10)', color: '#06210f', fontSize: 14, fontWeight: 600,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              cursor: repitiendo || sinItems ? 'not-allowed' : 'pointer',
              opacity: repitiendo || sinItems ? 0.6 : 1,
            }}
          >
            <RefreshCw size={16} />
            {repitiendo ? 'Agregando…' : 'Repetir pedido'}
          </button>
        </div>
      </div>
    </div>
  );
}
export default function MisPedidos() {
  const { isLoggedIn, user } = useAuth();
  const hayCache = cachePedidos.usuarioId === (user?.id ?? null) && Array.isArray(cachePedidos.pedidos);
  const [cargando, setCargando] = useState(() => !hayCache);
  const [pedidos, setPedidos] = useState(() => (hayCache ? cachePedidos.pedidos : []));
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState(null);
  const [sincronizandoId, setSincronizandoId] = useState(null);
  const [detalle, setDetalle] = useState(null);
  const [resenando, setResenando] = useState(null);

  async function cargar(silencioso = false) {
    if (!silencioso) {
      setCargando(true);
      setError(null);
    }
    try {
      const data = await pedidosApi.mios();
      const lista = data.pedidos || [];
      setPedidos(lista);
      cachePedidos = { usuarioId: user?.id ?? null, pedidos: lista };
    } catch (err) {
      if (!silencioso) setError(err.message);
    } finally {
      if (!silencioso) setCargando(false);
    }
  }

  useEffect(() => {
    if (isLoggedIn) cargar(hayCache);
  }, [isLoggedIn, user?.id]);

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
      await cargar(true);
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
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 8, color: 'var(--surface)' }}>
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
           <img
          src={mediaPath('sinPedidos.png')}
          alt="Logo"
          style={{ display: 'block', height:200, width: 'auto', margin: '0 auto 10px' }}
        />
          <p style={{ margin: '0 0 12px', color: 'var(--text-dim)' }}>Para realizar pedidos haz click en el enlace de aca abajo</p>
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
              <tr style={{ color: 'var(--surface-2)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase', borderBottom: '1px solid var(--line)' }}>
                <th style={{ padding: '0 10px 12px' }}>Pedido</th>
                <th style={{ padding: '0 10px 12px' }}>Fecha</th>
                <th style={{ padding: '0 10px 12px' }}>Detalles</th>
                <th style={{ padding: '0 10px 12px' }}>Total</th>
                <th style={{ padding: '0 10px 12px' }}>Estado</th>
                <th style={{ padding: '0 10px 12px' }}>Código seguimiento</th>
                <th style={{ padding: '0 10px 12px' }}>Estado de envío</th>
                <th style={{ padding: '0 10px 12px' }}></th>
                <th style={{ padding: '0 10px 12px' }}></th>
              </tr>
            </thead>
            <tbody>
              {pedidos.map((p) => {
                const bloqueadoSinc = p.entrega === 'retiro' || p.estado === 'entregado';
                return (
                  <tr key={p.id} style={{ borderBottom: '1px solid var(--surface-3)' }}>
                    <td style={{ padding: '14px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>
                      {p.id.slice(0, 8)}
                    </td>
                    <td style={{ padding: '14px 10px', color: 'var(--text-dim)' }}>{fecha(p.fecha)}</td>
                    <td style={{ padding: '14px 10px', color: 'var(--text-dim)', textAlign: 'center' }}>
                      <span
                        onClick={() => setDetalle(p)}
                        title="Ver detalle del pedido"
                        style={{ cursor: 'pointer', display: 'inline-flex', color: 'var(--surface-2)' }}
                      >
                        <Eye size={15} style={{ color: 'var(--text-dim)' }} />
                      </span>
                    </td>
                    <td style={{ padding: '14px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                      ${p.total.toLocaleString('es-CL')}
                    </td>
                    <td style={{ padding: '14px 10px', color: 'var(--text-dim)' }}>
                      {ETIQUETAS_ESTADO[p.estado] || p.estado}
                    </td>
                    <td
                      style={{
                        padding: '14px 10px', color: 'var(--text-dim)', textAlign: 'center',
                        opacity: p.entrega === 'retiro' ? 0.35 : 1,
                        cursor: p.entrega === 'retiro' ? 'not-allowed' : 'default',
                      }}
                      title={p.entrega === 'retiro' ? 'No aplica para retiros' : undefined}
                    >
                      {p.entrega === 'retiro' ? '—' : (p.codigo_seguimiento || '—')}
                    </td>
                    <td
                      style={{
                        padding: '14px 10px', color: 'var(--text-dim)',
                        opacity: p.entrega === 'retiro' ? 0.35 : 1,
                        cursor: p.entrega === 'retiro' ? 'not-allowed' : 'default',
                      }}
                      title={p.entrega === 'retiro' ? 'No aplica para retiros' : undefined}
                    >
                      {p.entrega === 'retiro' ? 'No aplica para retiros' : estadoSeguimiento(p)}
                    </td>
                    <td style={{ padding: '14px 10px', textAlign: 'right' }}>
                      <button
                        onClick={() => sincronizar(p)}
                        disabled={bloqueadoSinc || sincronizandoId === p.id}
                        title={bloqueadoSinc
                          ? (p.entrega === 'retiro' ? 'No aplica para retiros' : 'El pedido ya fue entregado')
                          : undefined}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px',
                          borderRadius: 8, border: '1px solid var(--surface-3)', background: 'transparent',
                          color: 'var(--surface-2)', fontSize: 12,
                          cursor: bloqueadoSinc ? 'not-allowed' : sincronizandoId === p.id ? 'wait' : 'pointer',
                          opacity: bloqueadoSinc ? 0.35 : sincronizandoId === p.id ? 0.5 : 1,
                        }}
                      >
                        <RefreshCw size={13} />
                        {sincronizandoId === p.id ? 'Actualizando…' : 'Actualizar'}
                      </button>
                    </td>
                    <td style={{ padding: '14px 10px', textAlign: 'center', position: 'relative' }}>
                      <span
                        onClick={p.estado === 'entregado' ? () => setResenando(p) : undefined}
                        title={p.estado === 'entregado'
                          ? 'Valorar productos de este pedido'
                          : 'Solo puedes valorar pedidos entregados'}
                        style={{
                          display: 'inline-flex', position: 'relative', alignItems: 'center',
                          cursor: p.estado === 'entregado' ? 'pointer' : 'not-allowed',
                          opacity: p.estado === 'entregado' ? 1 : 0.35,
                          color: 'var(--text-dim)',
                        }}
                      >
                        <Star size={15} />
                        {p.resenas_pendientes > 0 && (
                          <span className="cart-badge">{p.resenas_pendientes}</span>
                        )}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {detalle && (
        <DetalleModal pedido={detalle} onClose={() => setDetalle(null)} />
      )}

      {resenando && (
        <ResenaModal
          pedido={resenando}
          onClose={() => {
            setResenando(null);
            cargar(true);
          }}
        />
      )}
    </div>
  );
}