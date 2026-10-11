import { useState, useCallback, useEffect, useMemo } from 'react';
import { Pencil, RefreshCw, AlertTriangle, Eye, Search, ChevronLeft, ChevronRight, X, CircleCheck, MapPin, Package } from 'lucide-react';
import { pedidosApi, TRANSPORTISTAS } from '../../services/orders.js';
import ConfirmModal from '../../components/ConfirmModal.jsx';
import { mediaPath } from '../../utils/media.js';
import { useBloqueoScroll } from '../../hooks/useBloqueoScroll.js';

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  en_produccion: 'En producción',
  enviado: 'Enviado',
  entregado: 'Entregado',
  cancelado: 'Cancelado',
};

// Mismos colores de chip que el detalle de MisPedidos, para que el modal de
// admin se vea igual (mismo lenguaje visual en toda la app).
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

function ChipEstado({ pedido, onClick }) {
  const estiloBase = {
    display: 'inline-block', padding: '4px 10px', borderRadius: 999,
    fontSize: 11, fontWeight: 600, cursor: onClick ? 'pointer' : 'default',
  }
  if (pedido.estado === 'entregado') {
    return (
      <span style={{ ...estiloBase, background: 'rgba(34,197,94,.16)', color: 'var(--green, #22c55e)' }}>
        Entregado
      </span>
    )
  }
  if (pedido.estado === 'cancelado') {
    return (
      <span style={{ ...estiloBase, background: 'var(--surface-3)', color: 'var(--text-dim)' }}>
        Cancelado
      </span>
    )
  }
  return (
    <span
      onClick={onClick}
      title="Marcar como entregado"
      style={{ ...estiloBase, background: 'rgba(250,204,21,.16)', color: '#b45309' }}
    >
      {pedido.entrega === 'retiro' ? 'Listo para retirar' : 'Marcar entregado'}
    </span>
  )
}

function LogoModal({ archivo = 'apolo-vibes-logo.png', alt = 'Logo' }) {
  return (
    <img
      src={mediaPath(archivo)}
      alt={alt}
      style={{ display: 'block', margin: '0 auto 12px', width: 100, height: 100, objectFit: 'contain' }}
    />
  )
}

function DetalleModal({ pedido, onClose }) {
  useBloqueoScroll();
  const cliente = pedido.cliente || {};
  const esFactura = cliente.tipoDocumento === 'factura';
  const itemsPedido = pedido.items || [];
  const estilo = ESTILO_ESTADO[pedido.estado] || { bg: '#E5E7EB', color: '#374151' };
  const campos = [
    ['Cliente', [cliente.nombre, cliente.apellido].filter(Boolean).join(' ')],
    ['Teléfono', cliente.telefono],
    ['Email', cliente.email],
    ...(pedido.entrega === 'envio'
      ? [
        ['Dirección', [cliente.direccion, cliente.numero, cliente.dpto].filter(Boolean).join(' ')],
        ['Comuna', cliente.comuna],
        ['Ciudad', cliente.ciudad],
        ['Región', cliente.region],
        ['Código postal', cliente.codigoPostal],
      ]
      : []),
    ...(esFactura
      ? [
        ['RUT', cliente.rut],
        ['Razón social', cliente.razonSocial],
        ['Giro', cliente.giro],
      ]
      : []),
  ]
    .map(([etiqueta, valor]) => [etiqueta, typeof valor === 'string' ? valor.trim() : ''])
    .filter(([, valor]) => valor);

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
                  {item.color ? `Color: ${item.color}` : ''}
                </div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: '#FFFFFF', whiteSpace: 'nowrap' }}>
                  {formatoPesos(item.precio_unitario * item.cantidad)}
                </div>
                <div style={{ fontSize: 12, color: '#B9C6DA', whiteSpace: 'nowrap' }}>
                  {formatoPesos(item.precio_unitario)} c/u
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '16px 0 20px' }}>
          <span style={{ fontSize: 14, color: '#B9C6DA' }}>Total (IVA incluido)</span>
          <span style={{ fontSize: 22, fontWeight: 700, color: '#FFFFFF' }}>{formatoPesos(pedido.total)}</span>
        </div>

        {campos.length > 0 && (
          <div style={{ background: 'rgba(255,255,255,.07)', borderRadius: 10, padding: '14px 16px', marginBottom: 18 }}>
            <div style={{
              fontSize: 12, fontWeight: 700, letterSpacing: '.04em', textTransform: 'uppercase',
              color: '#B9C6DA', marginBottom: 10,
            }}>
              {esFactura ? 'Datos de facturación' : 'Datos del cliente'}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <tbody>
                {campos.map(([etiqueta, valor]) => (
                  <tr key={etiqueta}>
                    <td style={{ padding: '3px 8px 3px 0', color: '#B9C6DA', width: '36%', verticalAlign: 'top' }}>
                      {etiqueta}
                    </td>
                    <td style={{ padding: '3px 0', color: '#FFFFFF' }}>{valor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <button
          onClick={onClose}
          style={{
            width: '100%', padding: '12px 0', borderRadius: 10, border: 'none',
            background: 'var(--accent)', color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          }}
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}

function CodigoModal({ pedido, onConfirm, onCancel }) {
  const [transportista, setTransportista] = useState(pedido?.transportista || 'starken');
  const [codigo, setCodigo] = useState(pedido?.codigo_seguimiento || '');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const actual = TRANSPORTISTAS.find(t => t.valor === transportista) || TRANSPORTISTAS[0];

  async function guardar() {
    setGuardando(true);
    setError(null);
    try {
      await onConfirm(codigo.trim(), transportista);
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
      onClick={guardando ? undefined : onCancel}
    >
      <div
        style={{
          background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
          width: '100%', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'center',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <LogoModal />
        <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
          Código de seguimiento
        </h3>
        <p style={{ margin: '0 0 18px', fontSize: 13, color: 'var(--text-dim)' }}>
          Pedido <strong>#{pedido.id.slice(0, 8)}</strong>
        </p>

        <div className="separador-suave" style={{ marginBottom: 18 }} />

        <p style={{ margin: '0 0 8px', fontSize: 12, color: 'var(--text-dim)' }}>
          Empresa de transporte
        </p>
        <div role="radiogroup" aria-label="Empresa de transporte" style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
          {TRANSPORTISTAS.map(t => {
            const activo = transportista === t.valor;
            return (
              <button
                key={t.valor}
                type="button"
                role="radio"
                aria-checked={activo}
                onClick={() => setTransportista(t.valor)}
                disabled={guardando}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 10, fontSize: 13, fontWeight: 600,
                  cursor: guardando ? 'not-allowed' : 'pointer',
                  border: activo ? '1px solid var(--green)' : '1px solid var(--line)',
                  background: activo ? 'var(--bg)' : 'transparent',
                  color: activo ? 'var(--surface)' : 'var(--text-dim)',
                }}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        <p style={{ margin: '0 0 18px', fontSize: 13, color: 'var(--text-dim)' }}>
          {actual.ayuda}
        </p>
        <input
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          placeholder={actual.placeholder}
          maxLength={50}
          autoFocus
          style={{
            width: '100%', padding: '10px 12px', borderRadius: 10,
            border: '1px solid var(--line)', background: 'var(--bg)',
            color: 'var(--surface)', fontSize: 14, marginBottom: 14, boxSizing: 'border-box',
          }}
        />
        {error && (
          <p style={{ margin: '0 0 12px', fontSize: 12, color: 'var(--red, #ef4444)' }}>{error}</p>
        )}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onCancel}
            disabled={guardando}
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
              background: 'var(--green)', color: 'var(--text)', fontSize: 13, fontWeight: 600,
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

let pedidosCache = null;

export default function Pedidos() {
  const [cargando, setCargando] = useState(true);
  const [pedidos, setPedidos] = useState(pedidosCache ?? []);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState(null);
  const [codigoModal, setCodigoModal] = useState(null);
  const [sincronizandoId, setSincronizandoId] = useState(null);
  const [detalle, setDetalle] = useState(null);
  const [entregarPedido, setEntregarPedido] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [pagina, setPagina] = useState(1);
  const [filasPorPagina, setFilasPorPagina] = useState(6);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await pedidosApi.todos();
      pedidosCache = data.pedidos || [];
      setPedidos(pedidosCache);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar() }, [cargar]);

  const normalizar = (v) =>
    String(v ?? '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  const pedidosFiltrados = useMemo(() => {
    const q = normalizar(busqueda.trim());
    if (!q) return pedidos;
    return pedidos.filter(p => {
      const c = p.cliente || {};
      const texto = [
        p.id,
        p.codigo_seguimiento,
        p.transportista,
        p.estado,
        ETIQUETAS_ESTADO[p.estado],
        p.entrega,
        ETIQUETA_ENTREGA[p.entrega],
        p.estado_seguimiento,
        fechaTexto(p.fecha),
        c.nombre,
        c.apellido,
        c.email,
        c.rut,
      ].map(normalizar).join(' ');
      return texto.includes(q);
    });
  }, [pedidos, busqueda]);

  useEffect(() => {
    const calcularFilas = () => {
      const disponible = window.innerHeight - 340;
      const base = Math.floor(disponible / 60);
      const maximo = window.innerWidth < 768 ? 5 : 8;
      setFilasPorPagina(Math.max(3, Math.min(base, maximo)));
    };
    calcularFilas();
    window.addEventListener('resize', calcularFilas);
    return () => window.removeEventListener('resize', calcularFilas);
  }, []);

  useEffect(() => { setPagina(1) }, [busqueda]);

  const totalPaginas = Math.max(1, Math.ceil(pedidosFiltrados.length / filasPorPagina));

  useEffect(() => {
    if (pagina > totalPaginas) setPagina(totalPaginas);
  }, [totalPaginas, pagina]);

  const pedidosPagina = useMemo(() => {
    const inicio = (pagina - 1) * filasPorPagina;
    return pedidosFiltrados.slice(inicio, inicio + filasPorPagina);
  }, [pedidosFiltrados, pagina, filasPorPagina]);


  async function registrarCodigo(pedido, codigo, transportista) {
    await pedidosApi.registrarSeguimiento(pedido.id, codigo, transportista);
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

  async function marcarEntregado(pedido) {
    setMensaje(null);
    try {
      await pedidosApi.cambiarEstado(pedido.id, 'entregado');
      setEntregarPedido(null);
      setMensaje({ tipo: 'ok', texto: `Pedido #${pedido.id.slice(0, 8)} marcado como entregado.` });
      await cargar();
    } catch (err) {
      setEntregarPedido(null);
      setMensaje({ tipo: 'error', texto: err.message });
    }
  }

  const estadoSeguimiento = (p) => {
    if (!p.codigo_seguimiento) return <span style={{ color: 'var(--text-dim)' }}>Sin despacho</span>;
    if (p.transportista === 'bluexpress') return <span style={{ color: 'var(--text-dim)' }}>Sin consulta automática</span>;
    return p.estado_seguimiento || <span style={{ color: 'var(--text-dim)' }}>Pendiente de consulta</span>;
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, color: 'var(--surface-2)' }}>Pedidos</h1>
        <div style={{ position: 'relative', width: 280, maxWidth: '100%' }}>
          <Search
            size={15}
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
          />
          <input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar pedido, cliente, código..."
            aria-label="Buscar pedidos"
            style={{
              width: '100%', padding: '9px 12px 9px 34px', borderRadius: 10,
              border: '1px solid var(--line)', background: '#ffff',
              color: 'var(--surface)', fontSize: 13, boxSizing: 'border-box',
            }}
          />
        </div>
      </div>

      {cargando && pedidos.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando pedidos…</p>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--red, #ef4444)', fontSize: 13 }}>
          <AlertTriangle size={16} />
          {error}
        </div>
      ) : pedidos.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>No hay pedidos registrados.</p>
      ) : pedidosFiltrados.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>No hay pedidos que coincidan con «{busqueda}»</p>
      ) : (
        <>
          {mensaje && (
            <p style={{ color: mensaje.tipo === 'ok' ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
              {mensaje.texto}
            </p>
          )}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'center' }}>
            <thead>
              <tr style={{ color: 'var(--surface)', textAlign: 'center', fontSize: 11, textTransform: 'uppercase' }}>
                <th style={{ padding: '0 10px 12px' }}>Pedido</th>
                <th style={{ padding: '0 10px 12px' }}>Fecha</th>
                <th style={{ padding: '0 10px 12px' }}>Total</th>
                <th style={{ padding: '0 10px 12px' }}>Detalle</th>
                <th style={{ padding: '0 10px 12px' }}>Código seguimiento</th>
                <th style={{ padding: '0 10px 12px' }}>Despacho</th>
                <th style={{ padding: '0 10px 12px' }}>Retiro</th>
                <th style={{ padding: '0 10px 12px' }}></th>
              </tr>
            </thead>
            <tbody>
              {pedidosPagina.map(p => {
                const esRetiro = p.entrega === 'retiro'
                const sinSync = esRetiro || p.transportista === 'bluexpress'
                return (
                  <tr key={p.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
                    <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>
                      {p.id.slice(0, 8)}
                    </td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{fechaTexto(p.fecha)}</td>
                    <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>
                      ${p.total.toLocaleString('es-CL')}
                    </td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>
                      <span
                        style={{ cursor: 'pointer', display: 'inline-flex' }}
                        onClick={() => setDetalle(p)}
                        title="Ver detalle del pedido"
                      >
                        <Eye size={14} />
                      </span>
                    </td>
                    <td style={{ padding: '13px 10px' }}>
                      {p.codigo_seguimiento ? (
                        <span
                          onClick={() => !esRetiro && setCodigoModal(p)}
                          title={esRetiro ? 'Los retiros no tienen código de seguimiento' : 'Editar código de seguimiento'}
                          style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)', cursor: 'pointer' }}
                        >
                          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>{p.codigo_seguimiento}</span>
                          <span style={{ display: 'block', fontSize: 10, color: 'var(--text-dim)' }}>
                            {p.transportista === 'bluexpress' ? 'Bluexpress' : 'Starken'}
                          </span>
                        </span>
                      ) : (
                        <span
                          onClick={() => !esRetiro && setCodigoModal(p)}
                          title={esRetiro ? 'Los retiros no tienen código de seguimiento' : 'Registrar código de seguimiento'}
                          aria-disabled={esRetiro}
                          style={{
                            display: 'inline-flex',
                            cursor: esRetiro ? 'not-allowed' : 'pointer',
                            opacity: esRetiro ? 0.35 : 1
                          }}
                        >
                          <Pencil size={16} color={esRetiro ? 'var(--text-dim)' : "var(--green)"} />
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      {esRetiro ? (
                        <span style={{ color: 'var(--text-dim)' }}>-</span>
                      ) : (
                        <>
                          {estadoSeguimiento(p)}
                          <div style={{ marginTop: 6 }}>
                            <ChipEstado pedido={p} onClick={() => setEntregarPedido(p)} />
                          </div>
                        </>
                      )}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      {p.entrega === 'retiro' ? (
                        <ChipEstado pedido={p} onClick={() => setEntregarPedido(p)} />
                      ) : p.entrega === 'envio' ? (
                        <span style={{ color: 'var(--text-dim)' }}>Envío a domicilio</span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      <span
                        style={{
                          cursor: sinSync ? 'not-allowed' : sincronizandoId === p.id ? 'wait' : 'pointer',
                          display: 'inline-flex',
                          opacity: sinSync ? 0.35 : 1
                        }}
                        onClick={() => !sinSync && !sincronizandoId && sincronizar(p)}
                        title={esRetiro ? 'No aplica para retiros' : sinSync ? 'Sin consulta automática para Bluexpress' : 'Actualizar seguimiento'}
                      >
                        <RefreshCw size={16} color={p.codigo_seguimiento && !sinSync ? 'var(--surface)' : 'var(--text-dim)'} />
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </>
      )}

      {pedidosFiltrados.length > 0 && (
        <div
          style={{
            position: 'sticky', bottom: 0, zIndex: 10,
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            marginTop: 'auto', gap: 8, padding: '20px 16px 12px',
            background: 'var(--bg)', borderTop: '1px solid var(--surface-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-dim)' }}>
            <button
              onClick={() => setPagina(p => Math.max(1, p - 1))}
              disabled={pagina === 1}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: 30, height: 30, borderRadius: 8, border: '1px solid var(--surface-3)',
                background: 'transparent', color: 'var(--text-dim)',
                cursor: pagina === 1 ? 'not-allowed' : 'pointer',
                opacity: pagina === 1 ? 0.4 : 1,
              }}
              aria-label="Página anterior"
            >
              <ChevronLeft size={15} />
            </button>

            <span style={{ padding: '0 8px', fontFamily: 'var(--font-mono)' }}>
              {pagina} / {totalPaginas}
            </span>

            <button
              onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
              disabled={pagina === totalPaginas}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: 30, height: 30, borderRadius: 8, border: '1px solid var(--surface-3)',
                background: 'transparent', color: 'var(--text-dim)',
                cursor: pagina === totalPaginas ? 'not-allowed' : 'pointer',
                opacity: pagina === totalPaginas ? 0.4 : 1,
              }}
              aria-label="Página siguiente"
            >
              <ChevronRight size={15} />
            </button>
          </div>

          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            Mostrando {(pagina - 1) * filasPorPagina + 1}
            –{Math.min(pagina * filasPorPagina, pedidosFiltrados.length)} de {pedidosFiltrados.length}
          </span>
        </div>
      )}

      {codigoModal && (
        <CodigoModal
          pedido={codigoModal}
          onConfirm={(codigo, transportista) => registrarCodigo(codigoModal, codigo, transportista)}
          onCancel={() => setCodigoModal(null)}
        />
      )}

      {entregarPedido && (
        <ConfirmModal
          titulo="Marcar como entregado"
          mensaje={entregarPedido.entrega === 'retiro'
            ? `¿Confirmas que el pedido #${entregarPedido.id.slice(0, 8)} (retiro en tienda) fue entregado al cliente?`
            : `¿Confirmas que el pedido #${entregarPedido.id.slice(0, 8)} (envío a domicilio) fue entregado al cliente?`}
          textoCancelar="Cancelar"
          textoConfirmar="Sí, entregado"
          textoCargando="Guardando…"
          confirmarPeligro={false}
          colorConfirmar="var(--green, #22c55e)"
          colorTextoConfirmar="#06210f"
          mostrarLogo={true}
          onConfirm={() => marcarEntregado(entregarPedido)}
          onCancel={() => setEntregarPedido(null)}
        />
      )}

      {detalle && (
        <DetalleModal pedido={detalle} onClose={() => setDetalle(null)} />
      )}
    </>
  );
}