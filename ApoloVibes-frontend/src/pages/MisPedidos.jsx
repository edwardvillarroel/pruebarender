import { useState, useEffect, useMemo } from 'react';
import { Navigate, Link, useNavigate } from 'react-router-dom';
import { RefreshCw, AlertTriangle, Eye, Star, Package, CircleCheck, X, ChevronLeft, ChevronRight, Check, Clock, Truck, Store, User, Phone, Mail, FileText, Building2, Briefcase, Trash2, CreditCard } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import { pedidosApi } from '../services/orders.js';
import { mediaPath } from '../utils/media.js';
import ResenaModal from '../components/ResenaModal.jsx';
import ConfirmModal from '../components/ConfirmModal.jsx';
import { useBloqueoScroll } from '../hooks/useBloqueoScroll.js';

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  en_produccion: 'En preparación',
  enviado: 'Enviado',
  entregado: 'Recibido',
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

const PAGOS_CONFIRMADOS = new Set(['completado', 'autorizado']);
const PAGOS_FALLIDOS = new Set(['pendiente', 'fallido']);

// Pedido que puede volver a pasar por la pasarela: nunca se confirmó el pago.
const puedePagar = (p) => PAGOS_FALLIDOS.has(p.estado_pago)
  && (p.estado === 'pendiente' || p.estado === 'cancelado');

// Pedido eliminable: no tiene pago confirmado y no entró a preparación.
const puedeEliminar = (p) => !PAGOS_CONFIRMADOS.has(p.estado_pago)
  && (p.estado === 'pendiente' || p.estado === 'cancelado');

const DIRECCION_RETIRO = 'Álvarez 1106, Viña del Mar';

const PASOS = ['pendiente', 'en_produccion', 'enviado', 'entregado'];
const COLOR_TEXTO = '#FFFFFF';
const COLOR_APAGADO = '#B9C6DA';
const FONDO_TARJETA = 'rgba(255,255,255,.06)';
const LINEA = 'rgba(255,255,255,.18)';
const ACENTO = '#FA7F19';

const formatoPesos = (valor) => '$' + Number(valor).toLocaleString('es-CL');
const fechaTexto = (f) => f ? new Date(f).toLocaleDateString('es-CL') : '—';
const fechaLarga = (f) => f ? new Date(f).toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' }) : '—';

function etiquetaPaso(paso, entrega) {
  if (paso === 'enviado' && entrega === 'retiro') return 'Listo para retirar';
  return ETIQUETAS_ESTADO[paso];
}

function formatoTelefono(t) {
  const limpio = String(t || '').replace(/\s+/g, '');
  const m = limpio.match(/^\+569(\d{4})(\d{4})$/);
  return m ? `+56 9 ${m[1]} ${m[2]}` : (t || '');
}

function LineaEstado({ estado, entrega, tieneSeguimiento }) {
  if (estado === 'cancelado') return null;

  let estadoEfectivo = estado;
  if (tieneSeguimiento && (estadoEfectivo === 'pendiente' || estadoEfectivo === 'en_produccion')) {
    estadoEfectivo = 'enviado';
  }

  const actual = Math.max(0, PASOS.indexOf(estadoEfectivo));
  const DIAMETRO = 30;

  return (
    <div style={{ display: 'flex', marginBottom: 24 }}>
      {PASOS.map((paso, i) => {
        const hecho = i < actual;
        const activo = i === actual;
        const encendido = hecho || activo;
        return (
          <div key={paso} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, position: 'relative' }}>
            {i > 0 && (
              <div style={{
                position: 'absolute', top: DIAMETRO / 2 - 1.5, right: '50%', width: '100%', height: 3,
                borderRadius: 2, background: i <= actual ? ACENTO : LINEA,
              }} />
            )}
            <div style={{
              position: 'relative', width: DIAMETRO, height: DIAMETRO, borderRadius: '50%', boxSizing: 'border-box',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: encendido ? ACENTO : 'var(--surface)',
              border: encendido ? 'none' : '2px solid rgba(255,255,255,.3)',
              boxShadow: activo ? '0 0 0 6px rgba(250,127,25,.25)' : 'none',
              zIndex: 1,
            }}>
              {hecho && <Check size={18} color="#FFFFFF" strokeWidth={3.5} />}
            </div>
            <span style={{ fontSize: 12, textAlign: 'center', lineHeight: 1.3, color: encendido ? COLOR_TEXTO : COLOR_APAGADO, fontWeight: activo ? 700 : 400 }}>
              {etiquetaPaso(paso, entrega)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function FilaDato({ icono: Icono, etiqueta, valor }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <Icono size={16} color={COLOR_APAGADO} style={{ marginTop: 2, flexShrink: 0 }} />
      <span style={{ fontSize: 13, color: COLOR_TEXTO, wordBreak: 'break-word' }}>
        {etiqueta && <span style={{ color: COLOR_APAGADO }}>{etiqueta}: </span>}
        {valor}
      </span>
    </div>
  );
}

let cachePedidos = { usuarioId: null, pedidos: null };

function DetalleModal({ pedido, onClose, onPagar, procesando }) {
  const navigate = useNavigate();
  const { repetirPedido } = useCart();
  useBloqueoScroll();
  const [repitiendo, setRepitiendo] = useState(false);
  const cliente = pedido.cliente || {};
  const esFactura = cliente.tipoDocumento === 'factura';
  const esRetiro = pedido.entrega === 'retiro';
  const itemsPedido = pedido.items || [];
  const sinItems = itemsPedido.length === 0;
  const estilo = ESTILO_ESTADO[pedido.estado] || { bg: '#E5E7EB', color: '#374151' };
  const IconoEstado = pedido.estado === 'entregado' ? CircleCheck : pedido.estado === 'cancelado' ? X : Clock;
  // Sin pago confirmado el pedido no entró al flujo de preparación: mostrar
  // "Pendiente / En preparación / ..." sería mentirle al cliente.
  const pagoPendiente = puedePagar(pedido);

  const neto = Math.round(Number(pedido.total) / 1.19);
  const iva = Number(pedido.total) - neto;
  const descuentoProductos = pedido.descuento_productos != null
    ? Number(pedido.descuento_productos)
    : itemsPedido.reduce((acc, item) => {
        const original = Number(item.precio_original || 0);
        const precio = Number(item.precio_unitario || 0);
        return original > precio && precio > 0
          ? acc + (original - precio) * Number(item.cantidad || 1)
          : acc;
      }, 0);
  const descuentoCupon = pedido.descuento_cupon != null
    ? Number(pedido.descuento_cupon)
    : Number(pedido.descuento || pedido.monto_cupon || 0);
  const cuponCodigo = pedido.cupon_codigo || pedido.codigo_cupon || pedido.cupon?.codigo || '';

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

  const nombreCompleto = [cliente.nombre, cliente.apellido].filter(Boolean).join(' ').trim();
  const lineaCalle = [cliente.direccion, cliente.numero, cliente.dpto].filter(Boolean).join(' ').trim();
  const lineaZona = [cliente.comuna, cliente.region].filter(Boolean).join(', ');
  const lineaPostal = cliente.codigoPostal ? ` · ${cliente.codigoPostal}` : '';

  const datos = [
    nombreCompleto && { icono: User, valor: nombreCompleto },
    cliente.telefono && { icono: Phone, valor: formatoTelefono(cliente.telefono) },
    cliente.email && { icono: Mail, valor: cliente.email },
    ...(esFactura
      ? [
        cliente.rut && { icono: FileText, etiqueta: 'RUT', valor: cliente.rut },
        cliente.razonSocial && { icono: Building2, etiqueta: 'Razón social', valor: cliente.razonSocial },
        cliente.giro && { icono: Briefcase, etiqueta: 'Giro', valor: cliente.giro },
      ]
      : []),
  ].filter(Boolean);

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
          position: 'relative', background: 'var(--surface)', borderRadius: 16,
          width: '100%', maxWidth: 480, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'left', maxHeight: '90vh', boxSizing: 'border-box',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <style>{`
          .modal-scroll::-webkit-scrollbar { width: 6px; }
          .modal-scroll::-webkit-scrollbar-track { background: transparent; margin: 8px 0; }
          .modal-scroll::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }
          .modal-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
          .modal-scroll { scrollbar-gutter: stable; }
        `}</style>

        {/* Header */}
        <div style={{
          flexShrink: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 8,
          padding: '18px 52px 14px', background: 'var(--surface)',
          borderBottom: `1px solid ${LINEA}`,
        }}>
          <img
            src={mediaPath('apolo-vibes-logo.webp')}
            alt="Apolo Vibes"
            style={{ display: 'block', height: 64, width: 'auto', objectFit: 'contain', marginBottom: -6 }}
          />

          <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: COLOR_TEXTO }}>
            Pedido #{pedido.id.slice(0, 8).toUpperCase()}
          </h3>
          <p style={{ margin: 0, fontSize: 13, color: COLOR_APAGADO }}>
            {fechaLarga(pedido.fecha)}
          </p>

          {!pagoPendiente && (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: estilo.bg, color: estilo.color,
              fontSize: 12, fontWeight: 600, padding: '5px 12px', borderRadius: 999,
            }}>
              <IconoEstado size={14} />
              {ETIQUETAS_ESTADO[pedido.estado] || pedido.estado}
            </span>
          )}
        </div>

     
        <div className="modal-scroll" style={{ overflowY: 'auto', flex: 1, minHeight: 0 }}>
        <div style={{ padding: '20px 24px 0' }}>

        {!pagoPendiente && (
          <LineaEstado estado={pedido.estado} entrega={pedido.entrega} tieneSeguimiento={!!pedido.codigo_seguimiento} />
        )}

        {(puedePagar(pedido) || puedeEliminar(pedido)) && (
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: 10,
            background: 'rgba(250,127,25,.14)', border: '1px solid rgba(250,127,25,.4)',
            borderRadius: 12, padding: 12, marginBottom: 18,
          }}>
            <AlertTriangle size={16} color={ACENTO} style={{ marginTop: 2, flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: COLOR_TEXTO }}>
              {pedido.estado_pago === 'fallido'
                ? 'El pago de este pedido no se completó. Puedes pagarlo ahora o eliminarlo desde la lista de pedidos.'
                : pedido.estado === 'cancelado'
                  ? 'Este pedido se canceló sin completar el pago. Puedes pagarlo ahora o eliminarlo desde la lista de pedidos.'
                  : 'Este pedido todavía no tiene el pago completado. Puedes pagarlo ahora o eliminarlo desde la lista de pedidos.'}
            </span>
          </div>
        )}

        <div style={{
          display: 'flex', gap: 12, background: FONDO_TARJETA,
          borderRadius: 12, padding: 14, marginBottom: 20,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, flexShrink: 0,
            background: 'rgba(250,127,25,.18)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {esRetiro ? <Store size={20} color={ACENTO} /> : <Truck size={20} color={ACENTO} />}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: COLOR_TEXTO }}>
              {esRetiro ? 'Retiro en tienda' : (ETIQUETA_ENTREGA[pedido.entrega] || pedido.entrega)}
            </div>
            {esRetiro ? (
              <div style={{ marginTop: 2, fontSize: 13, color: COLOR_APAGADO }}>{DIRECCION_RETIRO}</div>
            ) : (
              <div style={{ marginTop: 2, fontSize: 13, color: COLOR_APAGADO, lineHeight: 1.5 }}>
                {lineaCalle && <div>{lineaCalle}</div>}
                {(lineaZona || lineaPostal) && <div>{lineaZona}{lineaPostal}</div>}
                {pedido.codigo_seguimiento && (
                  <div style={{ marginTop: 4, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                    {pedido.transportista === 'bluexpress' ? 'Bluexpress' : 'Starken'} · {pedido.codigo_seguimiento}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Productos */}
        <div style={{ borderTop: `1px solid ${LINEA}` }}>
          {itemsPedido.map((item, i) => (
            <div
              key={`${item.producto_id}-${item.color || ''}-${i}`}
              style={{
                display: 'flex', alignItems: 'center', gap: 14, padding: '14px 0',
                borderBottom: `1px solid ${LINEA}`,
              }}
            >
              <div style={{
                width: 56, height: 56, borderRadius: 10, background: '#FFFFFF', flexShrink: 0,
                overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {item.imagen ? (
                  <img
                    src={item.imagen}
                    alt={item.nombre || 'Producto'}
                    loading="lazy" decoding="async" width="56" height="56"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <Package size={24} color="#8A94A3" />
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: COLOR_TEXTO }}>
                  {item.nombre || 'Producto'}
                </div>
                <div style={{ fontSize: 13, color: COLOR_APAGADO }}>
                  {[item.color, `${item.cantidad} ${item.cantidad === 1 ? 'unidad' : 'unidades'}`].filter(Boolean).join(' · ')}
                </div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: COLOR_TEXTO, whiteSpace: 'nowrap' }}>
                  {formatoPesos(item.precio_unitario * item.cantidad)}
                </div>
                <div style={{ fontSize: 12, color: COLOR_APAGADO, whiteSpace: 'nowrap' }}>
                  {formatoPesos(item.precio_unitario)} c/u
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Totales */}
            <div style={{ padding: '14px 0 18px' }}>
              {descuentoCupon > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#22c55e', marginBottom: 6 }}>
                  <span>Cupón de descuento{cuponCodigo ? ` (${cuponCodigo})` : ''}</span>
                  <span>- {formatoPesos(descuentoCupon)}</span>
                </div>
              )}
              {descuentoProductos > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#22c55e', marginBottom: 6 }}>
                  <span>Descuento</span>
                  <span>- {formatoPesos(descuentoProductos)}</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: COLOR_APAGADO, marginBottom: 6 }}>
                <span>Monto neto</span>
                <span>{formatoPesos(neto)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: COLOR_APAGADO, marginBottom: 12 }}>
                <span>IVA (19%)</span>
                <span>{formatoPesos(iva)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: 14, color: COLOR_TEXTO }}>Total</span>
                <span style={{ fontSize: 24, fontWeight: 700, color: COLOR_TEXTO }}>{formatoPesos(pedido.total)}</span>
              </div>
            </div>

        {/* Datos del cliente */}
        {datos.length > 0 && (
          <div style={{ background: FONDO_TARJETA, borderRadius: 12, padding: 14, marginBottom: 18 }}>
            <p style={{ margin: '0 0 10px', fontSize: 13, fontWeight: 600, color: COLOR_APAGADO }}>
              {esFactura ? 'Datos de facturación' : 'Datos del cliente'}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {datos.map((d, i) => (
                <FilaDato key={i} icono={d.icono} etiqueta={d.etiqueta} valor={d.valor} />
              ))}
            </div>
          </div>
        )}

        </div>
        </div>

        {/* Footer fijo con acciones */}
        <div style={{
          flexShrink: 0,
          display: 'flex', gap: 10,
          padding: '14px 36px', background: 'var(--surface)',
          borderTop: `1px solid ${LINEA}`,
        }}>
          {puedePagar(pedido) ? (
            <button
              onClick={() => onPagar(pedido)}
              disabled={procesando}
              style={{
                flex: 1, padding: '12px 0', borderRadius: 10, border: 'none',
                background: 'var(--accent)', color: '#fff', fontSize: 14, fontWeight: 600,
                cursor: procesando ? 'wait' : 'pointer',
                opacity: procesando ? 0.6 : 1,
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              <CreditCard size={16} />
              {procesando ? 'Redirigiendo…' : 'Pagar ahora'}
            </button>
          ) : (
            <button
              onClick={repetir}
              disabled={repitiendo || sinItems}
              style={{
                flex: 1, padding: '12px 0', borderRadius: 10, border: 'none',
                background: 'var(--accent)', color: '#fff', fontSize: 14, fontWeight: 600,
                cursor: repitiendo || sinItems ? 'not-allowed' : 'pointer',
                opacity: repitiendo || sinItems ? 0.6 : 1,
              }}
            >
              {repitiendo ? 'Agregando…' : 'Repetir pedido'}
            </button>
          )}
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: '12px 0', borderRadius: 10, border: 'none',
              background: 'var(--accent)', color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Cerrar
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
  const [pagandoId, setPagandoId] = useState(null);
  const [eliminando, setEliminando] = useState(null);
  const [pagina, setPagina] = useState(1);
  const filasPorPagina = 10;

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

  async function pagar(pedido) {
    setPagandoId(pedido.id);
    setMensaje(null);
    try {
      const data = await pedidosApi.pagarDeNuevo(pedido.id);
      if (!data.url) throw new Error('No se pudo iniciar el pago');
      window.location.href = data.url;
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
      setPagandoId(null);
    }
  }

  async function confirmarEliminar() {
    if (!eliminando) return;
    try {
      await pedidosApi.eliminar(eliminando.id);
      const restantes = pedidos.filter((p) => p.id !== eliminando.id);
      setPedidos(restantes);
      cachePedidos = { usuarioId: user?.id ?? null, pedidos: restantes };
      setMensaje({ tipo: 'ok', texto: 'Pedido eliminado.' });
      setDetalle((d) => (d?.id === eliminando.id ? null : d));
      setEliminando(null);
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    }
  }

  const fecha = (f) => f ? new Date(f).toLocaleDateString('es-CL') : '—';
  const estadoSeguimiento = (p) => {
    if (p.estado === 'entregado') return 'Recibido';
    if (p.estado === 'cancelado') return 'Cancelado';
    if (!p.codigo_seguimiento) return 'Sin despacho';
    return p.estado_seguimiento || 'Consultando…';
  };

  const totalPaginas = Math.max(1, Math.ceil(pedidos.length / filasPorPagina));
  useEffect(() => {
    if (pagina > totalPaginas) setPagina(totalPaginas);
  }, [totalPaginas, pagina]);

  const pedidosPagina = useMemo(() => {
    const inicio = (pagina - 1) * filasPorPagina;
    return pedidos.slice(inicio, inicio + filasPorPagina);
  }, [pedidos, pagina]);

  // El redirect va después de todos los hooks: un return anticipado antes de
  // useEffect/useMemo cambia la cantidad de hooks entre renders y React falla.
  if (!isLoggedIn) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="wrap" style={{ padding: '48px 32px', minHeight: '100vh', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
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
            src={mediaPath('sinPedidos.webp')}
            alt="Sin pedidos"
            loading="lazy"
            decoding="async"
            width="512"
            height="512"
            style={{ display: 'block', height: 100, width: 'auto', margin: '0 auto 0' }}
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
              <tr style={{ color: 'var(--surface-2)', textAlign: 'center', fontSize: 11, textTransform: 'uppercase', borderBottom: '1px solid var(--line)' }}>
                <th style={{ padding: '0 10px 12px', textAlign: 'left' }}>Pedido</th>
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
              {pedidosPagina.map((p) => {
                const bloqueadoSinc = p.entrega === 'retiro' || p.estado === 'entregado';
                return (
                  <tr key={p.id} style={{ borderBottom: '1px solid var(--surface-3)' }}>
                    <td style={{ padding: '14px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>
                      {p.id.slice(0, 8)}
                    </td>
                    <td style={{ padding: '14px 10px', color: 'var(--text-dim)', textAlign: 'center' }}>{fecha(p.fecha)}</td>
                    <td style={{ padding: '14px 10px', color: 'var(--text-dim)', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
                        <span
                          onClick={() => setDetalle(p)}
                          title="Ver detalle del pedido"
                          style={{
                            cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
                            justifyContent: 'center', color: 'var(--surface-2)'
                          }}
                        >
                          <Eye size={15} style={{ color: 'var(--text-dim)' }} />
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textAlign: 'center'}}>
                      ${p.total.toLocaleString('es-CL')}
                    </td>
                    <td style={{ padding: '14px 10px', color: 'var(--text-dim)', textAlign: 'center' }}>
                      {(() => {
                        const esPagoPendiente = puedePagar(p);
                        const estiloBadge = esPagoPendiente ? ESTILO_ESTADO.pendiente : (ESTILO_ESTADO[p.estado] || ESTILO_ESTADO.pendiente);
                        const IconoBadge = esPagoPendiente
                          ? Clock
                          : p.estado === 'entregado' ? CircleCheck : p.estado === 'cancelado' ? X : Clock;
                        return (
                          <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: 6,
                            background: estiloBadge.bg, color: estiloBadge.color,
                            fontSize: 12, fontWeight: 600, padding: '5px 12px', borderRadius: 999,
                          }}>
                            <IconoBadge size={14} />
                            {esPagoPendiente ? 'Pago pendiente' : (ETIQUETAS_ESTADO[p.estado] || p.estado)}
                          </span>
                        );
                      })()}
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
                        padding: '14px 10px', color: 'var(--text-dim)', textAlign: 'center',
                        opacity: p.entrega === 'retiro' ? 0.35 : 1,
                        cursor: p.entrega === 'retiro' ? 'not-allowed' : 'default',
                      }}
                      title={p.entrega === 'retiro' ? 'No aplica para retiros' : undefined}
                    >
                      {p.entrega === 'retiro' ? 'No aplica para retiros' : estadoSeguimiento(p)}
                    </td>
                    <td style={{ padding: '14px 10px', textAlign: 'center' }}>
                      {puedePagar(p) || puedeEliminar(p) ? (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                          {puedePagar(p) && (
                            <button
                              onClick={() => pagar(p)}
                              disabled={pagandoId === p.id}
                              style={{
                                display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px',
                                borderRadius: 8, border: 'none', background: 'var(--accent)',
                                color: '#fff', fontSize: 12, fontWeight: 600,
                                cursor: pagandoId === p.id ? 'wait' : 'pointer',
                                opacity: pagandoId === p.id ? 0.6 : 1,
                              }}
                            >
                              <CreditCard size={13} />
                              {pagandoId === p.id ? 'Redirigiendo…' : 'Pagar'}
                            </button>
                          )}
                          {puedeEliminar(p) && (
                            <button
                              onClick={() => setEliminando(p)}
                              title="Eliminar pedido"
                              aria-label="Eliminar pedido"
                              style={{
                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                width: 30, height: 30, borderRadius: 8,
                                border: '1px solid var(--surface-3)', background: 'transparent',
                                color: 'var(--red, #ef4444)', cursor: 'pointer',
                              }}
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </div>
                      ) : (
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
                      )}
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
          {pedidos.length > 0 && (
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
                –{Math.min(pagina * filasPorPagina, pedidos.length)} de {pedidos.length}
              </span>
            </div>
          )}
        </>
      )}

      {detalle && (
        <DetalleModal
          pedido={detalle}
          onClose={() => setDetalle(null)}
          onPagar={pagar}
          procesando={pagandoId === detalle.id}
        />
      )}

      {eliminando && (
        <ConfirmModal
          titulo="Eliminar pedido"
          mensaje="Este pedido no tiene el pago completado. Se eliminará de tu historial y, si usaste un cupón, volverá a quedar disponible."
          textoConfirmar="Eliminar pedido"
          textoCargando="Eliminando…"
          textoCancelar="Cancelar"
          confirmarPeligro
          onConfirm={confirmarEliminar}
          onCancel={() => setEliminando(null)}
        />
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