import { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Pencil, RefreshCw, AlertTriangle, Eye, Search, ChevronLeft, ChevronRight,
  X, CircleCheck, Package, Truck, Store, User, Phone, Mail, Clock, Check,
  FileText, Building2, Briefcase, ClipboardList,
} from 'lucide-react';
import { pedidosApi, TRANSPORTISTAS } from '../../services/orders.js';
import ConfirmModal from '../../components/ConfirmModal.jsx';
import { mediaPath } from '../../utils/media.js';
import { useBloqueoScroll } from '../../hooks/useBloqueoScroll.js';

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  en_produccion: 'En preparación',
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


const LOGOS_TRANSPORTISTA = {
  starken: 'starken-logo.webp',
  bluexpress: 'bluexpress-logo.webp',
};


const FONDO_TRANSPORTISTA = {
  starken: 'var(--green, #22c55e)',
  bluexpress: '#b6ebfc',
};


const ESTILO_BADGE = {
  display: 'inline-block', padding: '4px 10px', borderRadius: 999,
  fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap',
};


const ESTADOS_DESPACHO = {
  sin_despacho: { texto: 'Sin despacho', bg: 'var(--surface-3)', color: 'var(--text-dim)' },
  en_despacho: { texto: 'En despacho', bg: 'rgba(250,204,21,.16)', color: '#b45309' },
  ingresado: { texto: 'Ingresado', bg: 'rgba(250,204,21,.16)', color: '#b45309' },
  en_transito: { texto: 'En tránsito', bg: 'rgba(59,130,246,.16)', color: '#1d4ed8' },
  en_bodega_sucursal: { texto: 'En bodega sucursal', bg: 'rgba(139,92,246,.16)', color: '#6d28d9' },
  en_ruta_de_entrega: { texto: 'En ruta de entrega', bg: 'rgba(14,165,233,.16)', color: '#0369a1' },
  entregado: { texto: 'Entregado', bg: 'rgba(34,197,94,.16)', color: 'var(--green, #22c55e)' },
};

const normalizarEstado = (valor) =>
  String(valor ?? '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '_');

function BadgeDespacho({ estado }) {
  const clave = normalizarEstado(estado)
  const estilo = ESTADOS_DESPACHO[clave] || ESTADOS_DESPACHO.en_despacho
  return <span style={{ ...ESTILO_BADGE, background: estilo.bg, color: estilo.color }}>{estilo.texto}</span>
}

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

function LogoModal({ archivo = 'apolo-vibes-logo.webp', alt = 'Logo' }) {
  return (
    <img
      src={mediaPath(archivo)}
      alt={alt}
      style={{ display: 'block', margin: '0 auto 12px', width: 100, height: 100, objectFit: 'contain' }}
    />
  )
}


function LogoTransportista({ valor, label }) {
  const [fallo, setFallo] = useState(false);
  const archivo = LOGOS_TRANSPORTISTA[valor];

  if (!archivo || fallo) {
    return (
      <span style={{ fontSize: 13, fontWeight: 600, color: valor === 'starken' ? '#06210f' : '#123F8C' }}>
        {label}
      </span>
    );
  }

  return (
    <img
      src={mediaPath(archivo)}
      alt={label}
      onError={() => setFallo(true)}
      draggable={false}
      style={{ display: 'block', height: 24, maxWidth: '100%', width: 'auto', objectFit: 'contain' }}
    />
  );
}

// ─── Detalle del pedido (nuevo diseño) ───────────────────────

const PASOS = ['pendiente', 'en_produccion', 'enviado', 'entregado'];

const COLOR_TEXTO = '#FFFFFF';
const COLOR_APAGADO = '#B9C6DA';
const FONDO_TARJETA = 'rgba(255,255,255,.06)';
const LINEA = 'rgba(255,255,255,.18)';
const ACENTO = '#FA7F19';

const fechaLarga = (f) =>
  f ? new Date(f).toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' }) : '—';

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
          <div
            key={paso}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
              gap: 10, position: 'relative',
            }}
          >
            {i > 0 && (
              <div style={{
                position: 'absolute', top: DIAMETRO / 2 - 1.5, right: '50%', width: '100%', height: 3,
                borderRadius: 2,
                background: i <= actual ? ACENTO : LINEA,
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
            <span style={{
              fontSize: 12, textAlign: 'center', lineHeight: 1.3,
              color: encendido ? COLOR_TEXTO : COLOR_APAGADO,
              fontWeight: activo ? 700 : 400,
            }}>
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

function DetalleModal({ pedido, onClose }) {
  useBloqueoScroll();
  const cliente = pedido.cliente || {};
  const esFactura = cliente.tipoDocumento === 'factura';
  const esRetiro = pedido.entrega === 'retiro';
  const itemsPedido = pedido.items || [];
  const estilo = ESTILO_ESTADO[pedido.estado] || { bg: '#E5E7EB', color: '#374151' };
  const IconoEstado = pedido.estado === 'entregado' ? CircleCheck : pedido.estado === 'cancelado' ? X : Clock;

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

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: estilo.bg, color: estilo.color,
              fontSize: 12, fontWeight: 600, padding: '5px 12px', borderRadius: 999,
            }}>
              <IconoEstado size={14} />
              {ETIQUETAS_ESTADO[pedido.estado] || pedido.estado}
            </span>
          </div>
        </div>

     
        <div className="modal-scroll" style={{ overflowY: 'auto', flex: 1, minHeight: 0 }}>
        <div style={{ padding: '20px 24px 0' }}>

        <LineaEstado estado={pedido.estado} entrega={pedido.entrega} tieneSeguimiento={!!pedido.codigo_seguimiento} />

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

        {/* Footer fijo con acción de cierre */}
        <div style={{
          flexShrink: 0,
          padding: '14px 36px', background: 'var(--surface)',
          borderTop: `1px solid ${LINEA}`,
        }}>
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
                aria-label={t.label}
                title={t.label}
                onClick={() => setTransportista(t.valor)}
                disabled={guardando}
                style={{
                  flex: 1, height: 48, padding: '0 12px', borderRadius: 10, boxSizing: 'border-box',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: guardando ? 'not-allowed' : 'pointer',
                  border: activo ? '2px solid var(--green)' : '2px solid var(--line)',
                  background: FONDO_TRANSPORTISTA[t.valor] || '#FFFFFF',
                  opacity: activo ? 1 : 0.55,
                  filter: activo ? 'none' : 'grayscale(1)',
                  transition: 'opacity .15s ease, filter .15s ease, border-color .15s ease',
                }}
              >
                <LogoTransportista valor={t.valor} label={t.label} />
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


  const claveDespacho = (p) => {
    if (!p.codigo_seguimiento) return 'sin_despacho'
    if (p.transportista === 'bluexpress') return 'en_despacho'
    return p.estado_seguimiento || 'en_despacho'
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
        <ClipboardList size={22} style={{ color: 'var(--surface)' }} />
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, margin: 0, color: 'var(--surface)' }}>Pedidos</h1>
      </div>
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
                const bloqueado = p.estado === 'entregado' || p.estado === 'cancelado'
                const sinSync = esRetiro || p.transportista === 'bluexpress' || bloqueado
                const sinCodigo = esRetiro || bloqueado
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
                          onClick={() => !sinCodigo && setCodigoModal(p)}
                          title={esRetiro
                            ? 'Los retiros no tienen código de seguimiento'
                            : bloqueado
                              ? 'El pedido ya está cerrado'
                              : 'Editar código de seguimiento'}
                          style={{
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--surface)',
                            cursor: sinCodigo ? 'not-allowed' : 'pointer',
                            opacity: sinCodigo ? 0.45 : 1,
                          }}
                        >
                          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>{p.codigo_seguimiento}</span>
                          <span style={{ display: 'block', fontSize: 10, color: 'var(--text-dim)' }}>
                            {p.transportista === 'bluexpress' ? 'Bluexpress' : 'Starken'}
                          </span>
                        </span>
                      ) : (
                        <span
                          onClick={() => !sinCodigo && setCodigoModal(p)}
                          title={esRetiro
                            ? 'Los retiros no tienen código de seguimiento'
                            : bloqueado
                              ? 'El pedido ya está cerrado'
                              : 'Registrar código de seguimiento'}
                          aria-disabled={sinCodigo}
                          style={{
                            display: 'inline-flex',
                            cursor: sinCodigo ? 'not-allowed' : 'pointer',
                            opacity: sinCodigo ? 0.35 : 1
                          }}
                        >
                          <Pencil size={16} color={sinCodigo ? 'var(--text-dim)' : "var(--green)"} />
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      {esRetiro ? null : (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, flexWrap: 'wrap' }}>
                          {p.estado === 'entregado' || p.estado === 'cancelado' ? (
                            <ChipEstado pedido={p} />
                          ) : p.codigo_seguimiento && normalizarEstado(claveDespacho(p)) === 'en_ruta_de_entrega' ? (
                            // "En ruta de entrega" es el ultimo paso antes de entregado:
                            // se reemplaza el badge por el chip de accion final.
                            <ChipEstado pedido={p} onClick={() => setEntregarPedido(p)} />
                          ) : p.codigo_seguimiento ? (
                            // Cualquier estado activo: badge del estado al lado del chip de accion.
                            <>
                              <BadgeDespacho estado={claveDespacho(p)} />
                              <ChipEstado pedido={p} onClick={() => setEntregarPedido(p)} />
                            </>
                          ) : (
                            <BadgeDespacho estado={claveDespacho(p)} />
                          )}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      {p.entrega === 'retiro' ? (
                        <ChipEstado pedido={p} onClick={() => setEntregarPedido(p)} />
                      ) : null}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      <span
                        style={{
                          cursor: sinSync ? 'not-allowed' : sincronizandoId === p.id ? 'wait' : 'pointer',
                          display: 'inline-flex',
                          opacity: sinSync ? 0.35 : 1
                        }}
                        onClick={() => !sinSync && !sincronizandoId && sincronizar(p)}
                        title={
                          esRetiro
                            ? 'No aplica para retiros'
                            : bloqueado
                              ? 'El pedido ya está cerrado'
                              : p.transportista === 'bluexpress'
                                ? 'Sin consulta automática para Bluexpress'
                                : 'Actualizar seguimiento'
                        }
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