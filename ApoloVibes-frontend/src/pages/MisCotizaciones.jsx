import { useState, useEffect, useMemo } from 'react';
import { Navigate, Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, Eye, Info, X, User, Mail, Phone, Clock,
    Lock, CheckCircle2, ChevronLeft, ChevronRight, Ruler, Hash, Layers, Tag, Palette, ImageOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { mediaPath } from '../utils/media.js';
import { useBloqueoScroll } from '../hooks/useBloqueoScroll.js';
import { api } from '../services/api.js';

const estilosEstado = {
    pendiente: { background: '#FFF1D6', color: '#7A4B00' },
    aprobada: { background: '#D7F5D3', color: '#0F5A0B' },
    rechazada: { background: '#FFD9D9', color: '#8C1212' },
    pagada: { background: '#DCE9FF', color: '#123F8C'},
};

const ETIQUETAS_ESTADO = {
    pendiente: 'Pendiente',
    aprobada: 'Aprobada',
    rechazada: 'Rechazada',
    pagada: 'Pagada',
};

const COLOR_TEXTO = '#FFFFFF';
const COLOR_APAGADO = '#B9C6DA';
const FONDO_TARJETA = 'rgba(255,255,255,.06)';
const LINEA = 'rgba(255,255,255,.18)';
const ACENTO = '#FA7F19';

function formatearPrecio(valor) {
    if (valor === null || valor === undefined || valor === '') return '';
    const num = Number(valor);
    if (Number.isNaN(num)) return valor;
    return num.toLocaleString('es-CL');
}

function formatearFecha(valor) {
    if (!valor) return '';
    const d = new Date(valor);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('es-CL', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    });
}

function formatearFechaLarga(valor) {
    if (!valor) return '';
    const d = new Date(valor);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' });
}

function capitalizar(texto) {
    if (!texto) return '';
    const t = String(texto).trim();
    return t.charAt(0).toUpperCase() + t.slice(1);
}

function leerDescripcion(descripcion) {
    const texto = descripcion || '';
    const tomar = (clave) => {
        const m = texto.match(new RegExp(`^${clave}:\\s*(.+)$`, 'mi'));
        return m ? m[1].trim() : '';
    };
    const tieneEstructura = /^(Tamaño|Cantidad|Uso|Color):/mi.test(texto);
    return {
        tamano: tomar('Tamaño'),
        uso: tomar('Uso'),
        color: tomar('Color'),
        detalles: tieneEstructura ? tomar('Detalles') : texto.trim(),
    };
}

function MiniaturaModal({ src, nombre }) {
    const [fallo, setFallo] = useState(false);
    const url = src ? (src.startsWith('http') ? src : `/api/uploads/${src.replace(/\\/g, '/')}`) : '';

    return (
        <div style={{ width: 96, height: 96, borderRadius: 12, overflow: 'hidden', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--input-bg)', border: `1px solid ${LINEA}`, color: COLOR_APAGADO }}>
            {url && !fallo ? (
                <img
                    src={url}
                    alt={`Referencia enviada por ${nombre}`}
                    loading="lazy"
                    decoding="async"
                    width="96"
                    height="96"
                    onError={() => setFallo(true)}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
            ) : (
                <ImageOff size={28} strokeWidth={1.5} aria-label="Sin imagen" />
            )}
        </div>
    );
}

function FilaDatoModal({ icono: Icono, etiqueta, valor }) {
    if (!valor) return null;
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



function avisoActivoCotizacion(c) {
    return c.estado !== 'pendiente' && !!c.aviso_estado_en && !c.aviso_estado_visto;
}

function AvisoCotizacionModal({ cotizacion, onClose }) {
    useBloqueoScroll();
    const numero = `#${String(cotizacion.id).slice(0, 8).toUpperCase()}`;
    const aprobada = cotizacion.estado === 'aprobada';

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
                    background: 'var(--surface)', borderRadius: 16, width: '100%',
                    maxWidth: 460, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
                    padding: '28px 26px', boxSizing: 'border-box',
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 14 }}>
                    <img
                        src={mediaPath(aprobada ? 'logoExitoCompra.webp' : 'logoFailCompra.webp')}
                        alt={aprobada ? 'Cotización aprobada' : 'Cotización rechazada'}
                        style={{ width: 104, height: 'auto', display: 'block' }}
                    />
                </div>

                <h3 style={{ margin: '0 0 8px', fontSize: 18, fontWeight: 700, color: 'var(--text)', textAlign: 'center' }}>
                    {aprobada ? 'Tu cotización fue aprobada' : 'Tu cotización fue rechazada'}
                </h3>

                <p style={{ margin: '0 0 6px', fontSize: 13, color: 'var(--text-dim)', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
                    Cotización {numero}
                </p>

                <p style={{ margin: '0 0 18px', fontSize: 14, color: 'var(--text)', lineHeight: 1.6, textAlign: 'center' }}>
                    {aprobada
                        ? 'El administrador asignó un precio a tu cotización. Ya puedes revisarla y pagarla desde Mis cotizaciones -> detalles.'
                        : 'Lamentablemente tu cotización no fue aprobada en esta ocasión.'}
                </p>

                <button
                    onClick={onClose}
                    style={{
                        width: '100%', padding: '11px 0', borderRadius: 10, border: 'none',
                        backgroundColor: 'var(--accent)', color: '#fff', fontSize: 14,
                        fontWeight: 600, cursor: 'pointer',
                    }}
                >
                    Entendido
                </button>
            </div>
        </div>
    );
}

function DetalleCotizacionModal({ cotizacion, onClose }) {
    useBloqueoScroll();
    const navigate = useNavigate();
    const c = cotizacion || {};
    const desc = leerDescripcion(c.descripcion);
    const medidas = [c.alto, c.ancho, c.largo].filter(Boolean).length
        ? `${[c.alto, c.ancho, c.largo].filter(Boolean).join(' × ')} ${c.unidad || 'cm'}`
        : desc.tamano;
    const uso = c.uso || desc.uso;
    const color = c.color || desc.color;
    const fecha = formatearFechaLarga(c.creado_en);
    const pagada = Boolean(c.pagada);
    const estadoMostrado = pagada ? 'pagada' : c.estado;
    const estilo = estilosEstado[estadoMostrado] || estilosEstado.pendiente;

    function pagarCotizacion() {
        onClose();
        navigate(`/checkout?cotizacion=${c.id}`, { state: { cotizacion: c } });
    }

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0, 0, 0, 0.49)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                backdropFilter: 'blur(4px)',
                padding: 16,
            }}
            onClick={onClose}
        >
            <div
                style={{
                    position: 'relative',
                    background: 'var(--surface)',
                    borderRadius: 16,
                    width: '100%',
                    maxWidth: 480,
                    boxShadow: '0 20px 60px rgba(0,0,0,.3)',
                    maxHeight: '90vh',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <style>{`
                  .cotm-scroll::-webkit-scrollbar { width: 6px; }
                  .cotm-scroll::-webkit-scrollbar-track { background: transparent; margin: 8px 0; }
                  .cotm-scroll::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }
                  .cotm-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
                  .cotm-scroll { scrollbar-gutter: stable; }
                `}</style>

                <div style={{
                    flexShrink: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    padding: '18px 52px 14px',
                    background: 'var(--surface)',
                    borderBottom: `1px solid ${LINEA}`,
                }}>
                    <img
                        src={mediaPath('apolo-vibes-logo.webp')}
                        alt="Apolo Vibes"
                        style={{ display: 'block', height: 64, width: 'auto', objectFit: 'contain', marginBottom: -6 }}
                    />
                    <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: COLOR_TEXTO }}>
                        Cotización #{String(c.id).slice(0, 8).toUpperCase()}
                    </h3>
                    <p style={{ margin: 0, fontSize: 13, color: COLOR_APAGADO }}>{fecha}</p>
                    <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        background: estilo.background,
                        color: estilo.color,
                        fontSize: 12,
                        fontWeight: 600,
                        padding: '5px 12px',
                        borderRadius: 999,
                    }}>
                        {ETIQUETAS_ESTADO[estadoMostrado] || estadoMostrado}
                    </span>
                </div>

                <div className="cotm-scroll" style={{ overflowY: 'auto', flex: 1, minHeight: 0 }}>
                    <div style={{ padding: '20px 24px 0' }}>
                        <div style={{ background: FONDO_TARJETA, borderRadius: 12, padding: 14, marginBottom: 20 }}>
                            <p style={{ margin: '0 0 10px', fontSize: 13, fontWeight: 600, color: COLOR_APAGADO }}>Datos del cliente</p>
                            <div style={{ display: 'flex', gap: 12 }}>
                                <MiniaturaModal src={c.imagen} nombre={c.nombre} />
                                <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
                                    <FilaDatoModal icono={User} valor={c.nombre} />
                                    <FilaDatoModal icono={Mail} valor={c.email} />
                                    <FilaDatoModal icono={Phone} valor={c.telefono} />
                                    <FilaDatoModal icono={Clock} valor={fecha ? `Creada el ${fecha}` : null} />
                                </div>
                            </div>
                        </div>

                        <div style={{ background: FONDO_TARJETA, borderRadius: 12, padding: 14, marginBottom: 18 }}>
                            <p style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: COLOR_APAGADO }}>Detalles del producto</p>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                                {medidas && <FilaDatoModal icono={Ruler} valor={`Medidas: ${medidas}`} />}
                                {c.cantidad && <FilaDatoModal icono={Hash} valor={`Cantidad: ${c.cantidad}`} />}
                                {c.material && <FilaDatoModal icono={Layers} valor={`Material: ${c.material}`} />}
                                {uso && <FilaDatoModal icono={Tag} valor={`Uso: ${uso}`} />}
                                {color && <FilaDatoModal icono={Palette} valor={`Color: ${capitalizar(color)}`} />}
                            </div>
                        </div>

                        {desc.detalles && (
                            <div style={{ background: FONDO_TARJETA, borderRadius: 12, padding: 14, marginBottom: 18 }}>
                                <span style={{ display: 'block', fontSize: 12, color: COLOR_APAGADO, marginBottom: 6 }}>Detalles de la solicitud</span>
                                <p style={{ margin: 0, fontSize: 13, color: COLOR_TEXTO, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{desc.detalles}</p>
                            </div>
                        )}

                        {c.estado === 'aprobada' && c.precio != null && (
                            <div
                                style={{
                                    padding: '16px 18px',
                                    borderRadius: 12,
                                    border: '1px solid rgba(22,189,16,.30)',
                                    background: 'rgba(22,189,16,.10)',
                                    marginBottom: 18,
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600, color: COLOR_TEXTO }}>
                                        {pagada ? 'Precio pagado' : 'Precio asignado'}
                                    </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 14 }}>
                                    <span style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-.5px', color: COLOR_TEXTO }}>
                                        ${formatearPrecio(c.precio)}
                                    </span>
                                    <span style={{ fontSize: 14, color: COLOR_APAGADO }}>CLP</span>
                                </div>
                                {pagada ? (
                                    <>
                                        <div style={{
                                            width: '100%',
                                            height: 44,
                                            borderRadius: 10,
                                            background: 'rgba(22, 189, 16, 0.35)',
                                            border: '1px solid rgba(22, 189, 16, 0.45)',
                                            color: 'rgba(255, 255, 255, 0.55)',
                                            fontSize: 14,
                                            fontWeight: 600,
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            gap: 8,
                                        }}>
                                            <CheckCircle2 size={16} />
                                            Pagado
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 10 }}>
                                            <Link to="/mis-pedidos" style={{ fontSize: 13, color: '#2563eb' }}>
                                                Ver mi pedido
                                            </Link>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <button
                                            type="button"
                                            onClick={pagarCotizacion}
                                            style={{
                                                width: '100%',
                                                height: 44,
                                                borderRadius: 10,
                                                border: 'none',
                                                background: 'rgba(22, 189, 16, 0.8)',
                                                color: '#fff',
                                                fontSize: 14,
                                                fontWeight: 600,
                                                cursor: 'pointer',
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                gap: 8,
                                            }}
                                        >
                                            <Lock size={16} />
                                            Pagar ahora
                                        </button>
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 10, fontSize: 12, color: COLOR_APAGADO }}>
                                            <span>Pago seguro con</span>
                                            <img
                                                src={mediaPath('tuu.webp')}
                                                alt="Tuu"
                                                loading="lazy"
                                                decoding="async"
                                                style={{ height: 20, width: 'auto', display: 'block' }}
                                            />
                                        </div>
                                    </>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                <div style={{ flexShrink: 0, padding: '14px 36px', background: 'var(--surface)', borderTop: `1px solid ${LINEA}` }}>
                    <button
                        onClick={onClose}
                        style={{
                            width: '100%',
                            padding: '12px 0',
                            borderRadius: 10,
                            border: 'none',
                            background: ACENTO,
                            color: '#fff',
                            fontSize: 14,
                            fontWeight: 600,
                            cursor: 'pointer',
                        }}
                    >
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function MisCotizaciones() {
    const { isLoggedIn, user } = useAuth();
    const [cargando, setCargando] = useState(true);
    const [cotizaciones, setCotizaciones] = useState([]);
    const [error, setError] = useState(null);
    const [detalle, setDetalle] = useState(null);
    const [avisoCotizacion, setAvisoCotizacion] = useState(null);
    const [pagina, setPagina] = useState(1);
    const filasPorPagina = 10;

    async function cargar() {
        setCargando(true);
        setError(null);
        try {
            const data = await api.get('/cotizaciones/mias');
            setCotizaciones(Array.isArray(data) ? data : []);
            setPagina(1);
        } catch (err) {
            setError(err.message);
        } finally {
            setCargando(false);
        }
    }

    useEffect(() => {
        if (isLoggedIn) cargar();
    }, [isLoggedIn, user?.id]);

    const totalPaginas = Math.max(1, Math.ceil(cotizaciones.length / filasPorPagina));
    useEffect(() => {
        if (pagina > totalPaginas) setPagina(totalPaginas);
    }, [totalPaginas, pagina]);

    const cotizacionesPagina = useMemo(() => {
        const inicio = (pagina - 1) * filasPorPagina;
        return cotizaciones.slice(inicio, inicio + filasPorPagina);
    }, [cotizaciones, pagina]);

    if (!isLoggedIn) {
        return <Navigate to="/" replace />;
    }

    async function abrirAviso(c) {
        setAvisoCotizacion(c);
        try {
            await api.post(`/cotizaciones/${c.id}/aviso/visto`);
            setCotizaciones((prev) => prev.map((x) => (x.id === c.id ? { ...x, aviso_estado_visto: true } : x)));
        } catch { }
    }

    return (
        <div className="wrap" style={{ padding: '48px 32px', minHeight: '100vh', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 8, color: 'var(--surface)' }}>
                Mis cotizaciones
            </h1>
            <p style={{ margin: '0 0 28px', fontSize: 14, color: 'var(--text-dim)' }}>
                Aquí puedes revisar el estado y el detalle de tus cotizaciones.
            </p>

            {cargando ? (
                <p style={{ color: 'var(--text-dim)' }}>Cargando tus cotizaciones…</p>
            ) : error ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#b60303', fontSize: 13 }}>
                    <AlertTriangle size={16} />
                    {error}
                </div>
            ) : cotizaciones.length === 0 ? (
                <div style={{ border: '1px dashed var(--surface-3)', borderRadius: 16, padding: '40px 24px', textAlign: 'center' }}>
                    <img
                        src={mediaPath('sinproductos.webp')}
                        alt="Sin cotizaciones"
                        loading="lazy"
                        decoding="async"
                        width="512"
                        height="512"
                        style={{ display: 'block', height: 100, width: 'auto', margin: '0 auto 0' }}
                    />
                    <p style={{ margin: '12px 0', color: 'var(--text-dim)' }}>Aún no has enviado ninguna cotización.</p>
                    <Link to="/cotizar" style={{ color: '#009D4E' }}>Ir a cotizar</Link>
                </div>
            ) : (
                <>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'center' }}>
                        <thead style={{ borderBottom: '1px solid var(--surface-3)' }}>
                            <tr style={{ color: 'var(--surface)', textAlign: 'center', fontSize: 11, textTransform: 'uppercase' }}>
                                <th style={{ padding: '0 10px 12px' }}>Cotización</th>
                                <th style={{ padding: '0 10px 12px' }}>Fecha/Hora</th>
                                <th style={{ padding: '0 10px 12px' }}>Material</th>
                                <th style={{ padding: '0 10px 12px' }}>Precio</th>
                                <th style={{ padding: '0 10px 12px' }}>Detalle</th>
                                <th style={{ padding: '0 10px 12px' }}>Estado</th>
                                <th style={{ padding: '0 10px 12px' }}></th>
                            </tr>
                        </thead>
                        <tbody>
                            {cotizacionesPagina.map((c) => {
                                const fecha = formatearFecha(c.creado_en);
                                const estadoMostrado = c.pagada ? 'pagada' : c.estado;
                                const estilo = estilosEstado[estadoMostrado] || estilosEstado.pendiente;
                                return (
                                    <tr key={c.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
                                        <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>
                                            {String(c.id).slice(0, 8).toUpperCase()}
                                        </td>
                                        <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{fecha || '—'}</td>
                                        <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{c.material || '—'}</td>
                                        <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                                            {c.precio != null ? `$${formatearPrecio(c.precio)}` : <span style={{ color: 'var(--text-dim)' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                                            <button
                                                onClick={() => setDetalle(c)}
                                                title="Ver detalle"
                                                style={{
                                                    background: 'transparent', border: 'none', cursor: 'pointer',
                                                    color: 'var(--text-dim)', display: 'inline-flex',
                                                    alignItems: 'center', justifyContent: 'center', padding: 6,
                                                }}
                                            >
                                                <Eye size={16} />
                                            </button>
                                        </td>
                                        <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                                            <span style={{ display: 'inline-block', padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, ...estilo }}>
                                                {ETIQUETAS_ESTADO[estadoMostrado] || estadoMostrado}
                                            </span>
                                        </td>
                                        <td style={{ padding: '14px 10px', textAlign: 'center', position: 'relative' }}>
                                            <span
                                                onClick={avisoActivoCotizacion(c) ? () => abrirAviso(c) : undefined}
                                                title={avisoActivoCotizacion(c)
                                                    ? 'Ver novedad de tu cotización'
                                                    : c.estado === 'pendiente'
                                                        ? 'Aún no hay novedades'
                                                        : 'Ya viste el aviso'}
                                                style={{
                                                    display: 'inline-flex', position: 'relative', alignItems: 'center',
                                                    cursor: avisoActivoCotizacion(c) ? 'pointer' : 'not-allowed',
                                                    opacity: avisoActivoCotizacion(c) ? 1 : 0.35,
                                                    color: 'var(--text-dim)',
                                                }}
                                            >
                                                <Info size={15} />
                                                {avisoActivoCotizacion(c) && <span className="cart-badge">1</span>}
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>

                    {cotizaciones.length > 0 && (
                        <div
                            style={{
                                position: 'sticky',
                                bottom: 0,
                                zIndex: 10,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                marginTop: 'auto',
                                gap: 8,
                                padding: '20px 16px 12px',
                                background: 'var(--bg)',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-dim)' }}>
                                <button
                                    onClick={() => setPagina(p => Math.max(1, p - 1))}
                                    disabled={pagina === 1}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        width: 30,
                                        height: 30,
                                        borderRadius: 8,
                                        border: '1px solid var(--surface-3)',
                                        background: 'transparent',
                                        color: 'var(--text-dim)',
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
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        width: 30,
                                        height: 30,
                                        borderRadius: 8,
                                        border: '1px solid var(--surface-3)',
                                        background: 'transparent',
                                        color: 'var(--text-dim)',
                                        cursor: pagina === totalPaginas ? 'not-allowed' : 'pointer',
                                        opacity: pagina === totalPaginas ? 0.4 : 1,
                                    }}
                                    aria-label="Página siguiente"
                                >
                                    <ChevronRight size={15} />
                                </button>
                            </div>

                            <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                                Mostrando {(pagina - 1) * filasPorPagina + 1} – {Math.min(pagina * filasPorPagina, cotizaciones.length)} de {cotizaciones.length}
                            </span>
                        </div>
                    )}
                </>
            )}

            {detalle && <DetalleCotizacionModal cotizacion={detalle} onClose={() => setDetalle(null)} />}
            {avisoCotizacion && <AvisoCotizacionModal cotizacion={avisoCotizacion} onClose={() => setAvisoCotizacion(null)} />}
        </div>
    );
}
