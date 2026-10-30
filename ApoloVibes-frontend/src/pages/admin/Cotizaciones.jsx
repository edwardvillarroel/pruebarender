import { useEffect, useState, useMemo } from 'react'
import {
  ImageOff, Sparkles, Eye, X, User, Mail, Phone, Clock, ChevronLeft,
  ChevronRight, Ruler, Hash, Layers, Tag, Palette,
  Gauge,
  Weight,
  Timer
} from 'lucide-react'
import { useBloqueoScroll } from '../../hooks/useBloqueoScroll.js'
import { mediaPath } from '../../utils/media.js'
import { api } from '../../services/api.js'

const estilosEstado = {
  pendiente: { background: 'rgba(250,204,21,.16)', color: '#b45309' },
  aprobada: { background: 'rgba(34,197,94,.16)', color: '#22c55e' },
  rechazada: { background: 'rgba(239,68,68,.16)', color: '#ef4444' },
}

const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
}

const COLOR_TEXTO = '#FFFFFF'
const COLOR_APAGADO = '#B9C6DA'
const FONDO_TARJETA = 'rgba(255,255,255,.06)'
const LINEA = 'rgba(255,255,255,.18)'
const ACENTO = '#FA7F19'

function formatearPrecio(valor) {
  if (valor === null || valor === undefined || valor === '') return ''
  const num = Number(valor)
  if (Number.isNaN(num)) return valor
  return num.toLocaleString('es-CL')
}

function formatearFecha(valor) {
  if (!valor) return ''
  const d = new Date(valor)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('es-CL', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function formatearFechaLarga(valor) {
  if (!valor) return ''
  const d = new Date(valor)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' })
}

function capitalizar(texto) {
  if (!texto) return ''
  const t = String(texto).trim()
  return t.charAt(0).toUpperCase() + t.slice(1)
}

function leerDescripcion(descripcion) {
  const texto = descripcion || ''
  const tomar = clave => {
    const m = texto.match(new RegExp(`^${clave}:\\s*(.+)$`, 'mi'))
    return m ? m[1].trim() : ''
  }
  const tieneEstructura = /^(Tamaño|Cantidad|Uso|Color):/mi.test(texto)
  return {
    tamano: tomar('Tamaño'),
    uso: tomar('Uso'),
    color: tomar('Color'),
    detalles: tieneEstructura ? tomar('Detalles') : texto.trim(),
  }
}

function MiniaturaModal({ src, nombre }) {
  const [fallo, setFallo] = useState(false)
  const url = src ? (src.startsWith('http') ? src : `/api/uploads/${src.replace(/\\/g, '/')}`) : ''

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
  )
}


function Dato({ etiqueta, valor, icono: Icono }) {
  if (!valor) return null

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        minWidth: 0,
      }}
    >
      <Icono
        size={16}
        color={COLOR_APAGADO}
        style={{ marginTop: 2, flexShrink: 0 }}
      />

      <div style={{ minWidth: 0 }}>
        <span
          style={{
            display: 'block',
            fontSize: 12,
            color: COLOR_APAGADO,
            marginBottom: 3,
          }}
        >
          {etiqueta}
        </span>

        <span
          style={{
            display: 'block',
            fontSize: 14,
            fontWeight: 600,
            color: COLOR_TEXTO,
            overflowWrap: 'anywhere',
          }}
        >
          {valor}
        </span>
      </div>
    </div>
  )
}


function Barra({ etiqueta, valor }) {
  if (valor === null || valor === undefined || valor === '') return null
  const pct = Math.max(0, Math.min(100, Math.round(Number(valor) * 100)))
  return (
    <span style={{ fontSize: 12, color: COLOR_APAGADO, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      {etiqueta}
      <span style={{ width: 48, height: 4, borderRadius: 2, background: LINEA, overflow: 'hidden', display: 'inline-block' }}>
        <i style={{ display: 'block', height: '100%', background: 'var(--accent)', borderRadius: 2, width: `${pct}%` }} />
      </span>
      {pct}%
    </span>
  )
}

function FilaDatoModal({ icono: Icono, etiqueta, valor }) {
  if (!valor) return null
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <Icono size={16} color={COLOR_APAGADO} style={{ marginTop: 2, flexShrink: 0 }} />
      <span style={{ fontSize: 13, color: COLOR_TEXTO, wordBreak: 'break-word' }}>
        {etiqueta && <span style={{ color: COLOR_APAGADO }}>{etiqueta}: </span>}
        {valor}
      </span>
    </div>
  )
}

function DetalleCotizacionModal({ cotizacion, onClose, precios, setPrecios, usarSugerido, aprobar, rechazar }) {
  useBloqueoScroll()
  const c = cotizacion
  const desc = leerDescripcion(c.descripcion)
  const medidas = [c.alto, c.ancho, c.largo].filter(Boolean).length
    ? `${[c.alto, c.ancho, c.largo].filter(Boolean).join(' × ')} ${c.unidad || 'cm'}`
    : desc.tamano
  const uso = c.uso || desc.uso
  const color = c.color || desc.color
  const pendiente = c.estado === 'pendiente'
  const fecha = formatearFechaLarga(c.creado_en)
  const fechaIa = formatearFecha(c.ia_calculado_en)
  const estilo = estilosEstado[c.estado] || estilosEstado.pendiente

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
          .cotm-scroll::-webkit-scrollbar-thumb { background: var(--line); borderRadius: 3px; }
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
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
              {ETIQUETAS_ESTADO[c.estado]}
            </span>
          </div>
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
            {c.precio_estimado_ia != null && (
              <div
                style={{
                  padding: '16px 18px',
                  borderRadius: 12,
                  border: '1px solid rgba(22,189,16,.30)',
                  background: 'rgba(22,189,16,.10)',
                  marginBottom: 18,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 10,
                    flexWrap: 'wrap',
                    marginBottom: 12,
                  }}
                >
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: 13,
                      fontWeight: 600,
                      color: COLOR_TEXTO,
                    }}
                  >
                    <Sparkles size={14} />
                    Estimación ApoloAI
                  </span>
                </div>

                {fechaIa && (
                  <p
                    style={{
                      textAlign: 'left',
                      fontSize: 11,
                      marginLeft: 20,
                      marginTop: -15,
                      marginBottom: 15,
                      color: COLOR_APAGADO,
                    }}
                  >
                    {fechaIa}
                  </p>
                )}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'auto 1fr',
                    gap: 26,
                    alignItems: 'center',
                  }}
                >
                  <div
                    style={{
                      paddingRight: 20,
                      borderRight: '1px solid rgba(64,206,224,.28)',
                      minWidth: 0,
                    }}
                  >
                    <span
                      style={{
                        display: 'block',
                        fontSize: 12,
                        color: COLOR_APAGADO,
                        marginBottom: 3,
                      }}
                    >
                      Precio sugerido
                    </span>

                    <span
                      style={{
                        fontSize: 30,
                        fontWeight: 700,
                        letterSpacing: '-.5px',
                        color: COLOR_TEXTO,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      ${formatearPrecio(c.precio_estimado_ia)}
                    </span>

                    <span style={{ fontSize: 13, color: COLOR_APAGADO }}>
                      {' '}CLP
                    </span>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 10,
                      minWidth: 0,
                    }}
                  >
                    <Dato
                      etiqueta="Material sugerido"
                      icono={Layers}
                      valor={capitalizar(c.material_sugerido_ia) || '-'}
                    />

                    <Dato
                      etiqueta="Complejidad"
                      icono={Gauge}
                      valor={capitalizar(c.complejidad_ia) || '-'}
                    />

                    <Dato
                      etiqueta="Peso estimado"
                      icono={Weight}
                      valor={c.gramos_estimados_ia != null
                        ? `${c.gramos_estimados_ia} g`
                        : '-'}
                    />
                    <Dato
                      etiqueta="Tiempo estimado"
                      icono={Timer}
                      valor={
                        c.tiempo_estimado_horas_ia != null &&
                          c.tiempo_estimado_horas_ia !== ''
                          ? `${c.tiempo_estimado_horas_ia} h`
                          : '-'
                      }
                    />

                  </div>
                </div>
                <div
                  style={{
                    borderTop: '1px solid rgba(64,206,224,.28)',
                    marginTop: 20,
                    paddingTop: 14,
                    display: 'flex',
                    gap: 14,
                    flexWrap: 'wrap',
                    justifyContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <Barra
                    etiqueta="Material"
                    valor={c.confianza_material_ia}
                  />

                  <Barra
                    etiqueta="Complejidad"
                    valor={c.confianza_complejidad_ia}
                  />
                </div>
              </div>
            )}


            {pendiente && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                  marginBottom: 15,
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <label
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: COLOR_APAGADO,
                    }}
                  >
                    Precio asignado
                  </label>

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      height: 46,
                      padding: '0 14px',
                      boxSizing: 'border-box',
                      background: 'var(--input-bg)',
                      border: `1px solid ${LINEA}`,
                      borderRadius: 10,
                    }}
                  >
                    <span style={{ color: COLOR_APAGADO, fontSize: 15 }}>$</span>

                    <input
                      type="number"
                      min="0"
                      placeholder="Ingresa el precio"
                      value={precios[c.id] ?? ''}
                      onChange={(e) =>
                        setPrecios((prev) => ({
                          ...prev,
                          [c.id]: e.target.value,
                        }))
                      }
                      style={{
                        flex: 1,
                        width: '100%',
                        minWidth: 0,
                        border: 'none',
                        outline: 'none',
                        background: 'transparent',
                        fontSize: 16,
                        fontWeight: 600,
                        color: 'var(--surface-2)',
                      }}
                    />

                    <span style={{ color: COLOR_APAGADO, fontSize: 12 }}>
                      CLP
                    </span>
                  </div>
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 10,
                    marginTop: 2,
                  }}
                >
                  <button
                    type="button"
                    onClick={() => rechazar(c.id)}
                    style={{
                      height: 44,
                      borderRadius: 10,
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: 'pointer',
                      background: 'transparent',
                      border: '1px solid rgba(239,68,68,.9)',
                      color: '#f87171',
                    }}
                  >
                    Rechazar
                  </button>

                  <button
                    type="button"
                    onClick={() => aprobar(c.id)}
                    style={{
                      height: 44,
                      borderRadius: 10,
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: 'pointer',
                      background: '#1D9E75',
                      border: '1px solid #1D9E75',
                      color: '#fff',
                    }}
                  >
                    Aprobar cotización
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>
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
  )
}

export default function Cotizaciones() {
  const [items, setItems] = useState([])
  const [precios, setPrecios] = useState({})
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [detalle, setDetalle] = useState(null)
  const [pagina, setPagina] = useState(1)
  const filasPorPagina = 10

  useEffect(() => {
    cargarCotizaciones()
  }, [])

  async function cargarCotizaciones() {
    setCargando(true)
    setError(null)
    try {
      const res = await fetch('/api/cotizaciones')
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || data.mensaje || 'No se pudieron cargar las cotizaciones')
      }
      const data = await res.json()
      const lista = Array.isArray(data) ? data : []
      setItems(lista)
      const iniciales = {}
      lista.forEach((c) => {
        if (c.precio_estimado_ia && !(c.id in precios)) {
          iniciales[c.id] = Math.round(c.precio_estimado_ia)
        }
      })
      if (Object.keys(iniciales).length > 0) {
        setPrecios((prev) => ({ ...prev, ...iniciales }))
      }
      setPagina(1)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }

  function usarSugerido(id) {
    const item = items.find((c) => c.id === id)
    if (item?.precio_estimado_ia) {
      setPrecios((prev) => ({ ...prev, [id]: Math.round(item.precio_estimado_ia) }))
    }
  }

  async function aprobar(id) {
    const precio = precios[id]
    if (!precio) {
      alert('Ingresa un precio asignado antes de aprobar.')
      return
    }
    try {
      await api.patch(`/cotizaciones/${id}`, { estado: 'aprobada', precio: Number(precio) })
      setItems((prev) => prev.map((c) => (c.id === id ? { ...c, estado: 'aprobada', precio: Number(precio) } : c)))
      setDetalle((prev) => (prev && prev.id === id ? { ...prev, estado: 'aprobada', precio: Number(precio) } : prev))
    } catch (e) {
      alert(e.message || 'No se pudo aprobar la cotización')
    }
  }

  async function rechazar(id) {
    try {
      await api.patch(`/cotizaciones/${id}`, { estado: 'rechazada' })
      setItems((prev) => prev.map((c) => (c.id === id ? { ...c, estado: 'rechazada' } : c)))
      setDetalle((prev) => (prev && prev.id === id ? { ...prev, estado: 'rechazada' } : prev))
    } catch (e) {
      alert(e.message || 'No se pudo rechazar la cotización')
    }
  }

  const totalPaginas = Math.max(1, Math.ceil(items.length / filasPorPagina))
  const pedidosPagina = useMemo(() => {
    const inicio = (pagina - 1) * filasPorPagina
    return items.slice(inicio, inicio + filasPorPagina)
  }, [items, pagina])

  useEffect(() => {
    if (pagina > totalPaginas) setPagina(totalPaginas)
  }, [totalPaginas, pagina])

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, margin: 0, color: 'var(--surface)' }}>Cotizaciones</h1>
      </div>



      {cargando && items.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando cotizaciones...</p>
      ) : error ? (
        <p style={{ color: 'var(--red, #ef4444)', fontSize: 13 }}>{error}</p>
      ) : items.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>No hay cotizaciones todavía.</p>
      ) : (
        <>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'center' }}>
            <thead>
              <tr style={{ color: 'var(--surface)', textAlign: 'center', fontSize: 11, textTransform: 'uppercase' }}>
                <th style={{ padding: '0 10px 12px' }}>Cotización</th>
                <th style={{ padding: '0 10px 12px' }}>Cliente</th>
                <th style={{ padding: '0 10px 12px' }}>Correo</th>
                <th style={{ padding: '0 10px 12px' }}>Fecha/Hora</th>
                <th style={{ padding: '0 10px 12px' }}>Material</th>
                <th style={{ padding: '0 10px 12px' }}>Precio sugerido</th>
                <th style={{ padding: '0 10px 12px' }}>Detalle</th>
                <th style={{ padding: '0 10px 12px' }}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {pedidosPagina.map((c) => {
                const fecha = formatearFecha(c.creado_en)
                const estilo = estilosEstado[c.estado] || estilosEstado.pendiente
                return (
                  <tr key={c.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
                    <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>
                      {c.id.slice(0, 8)}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      <div style={{ color: 'var(--text-dim)' }}>{c.nombre}</div>
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{c.email}</div>
                    </td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{fecha}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{c.material}</td>
                    <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                      {c.precio_estimado_ia ? `$${formatearPrecio(c.precio_estimado_ia)}` : <span style={{ color: 'var(--text-dim)' }}>—</span>}
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      <span style={{ cursor: 'pointer', display: 'inline-flex', color: 'var(--text-dim)' }} onClick={() => setDetalle(c)} title="Ver detalle">
                        <Eye size={14} />
                      </span>
                    </td>
                    <td style={{ padding: '13px 10px', textAlign: 'center' }}>
                      <span style={{ display: 'inline-block', padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, ...estilo }}>
                        {ETIQUETAS_ESTADO[c.estado]}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

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
              borderTop: '1px solid var(--surface-3)',
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

              <span style={{ padding: '0 8px', fontFamily: 'var(--font-mono)' }}>{pagina} / {totalPaginas}</span>

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
              Mostrando {(pagina - 1) * filasPorPagina + 1} - {Math.min(pagina * filasPorPagina, items.length)} de {items.length}
            </span>
          </div>
        </>
      )}

      {detalle && (
        <DetalleCotizacionModal
          cotizacion={detalle}
          onClose={() => setDetalle(null)}
          precios={precios}
          setPrecios={setPrecios}
          usarSugerido={usarSugerido}
          aprobar={aprobar}
          rechazar={rechazar}
        />
      )}
    </>
  )
}
