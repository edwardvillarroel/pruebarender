import { useEffect, useMemo, useState } from 'react'
import { api } from '../../services/api.js'
import { Plus, Trash2, Tag, Copy, Check, Search } from 'lucide-react'
import ConfirmModal from '../../components/ConfirmModal.jsx'
import { mediaPath } from '../../utils/media.js'

const TIPOS = [
  { valor: 'porcentaje', etiqueta: 'Porcentaje' },
  { valor: 'monto', etiqueta: 'Monto fijo' },
]

const FILTROS = [
  { valor: 'todos', etiqueta: 'Todos' },
  { valor: 'activo', etiqueta: 'Activos' },
  { valor: 'canjeado', etiqueta: 'Canjeados' },
]

const estiloCampo = {
  width: '100%',
  padding: '9px 10px',
  borderRadius: 8,
  border: '1px solid var(--line)',
  background: 'var(--input-bg)',
  color: 'var(--text-dim)',
}

const FORM_INICIAL = {
  codigo: '',
  tipo: 'porcentaje',
  valor: '',
  uso_unico: false,
  descripcion: ''
}

function estadoDe(c) {
  return c.usado && c.uso_unico ? 'canjeado' : 'activo'
}

const ESTADOS = {
  activo: { texto: 'Activo', color: 'var(--green)' },
  canjeado: { texto: 'Canjeado', color: 'var(--text-dim)' },
}

export default function CuponesAdmin() {
  const [cupones, setCupones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [eliminando, setEliminando] = useState(null)
  const [errorEliminar, setErrorEliminar] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [form, setForm] = useState(FORM_INICIAL)
  const [filtro, setFiltro] = useState('todos')
  const [busqueda, setBusqueda] = useState('')
  const [copiado, setCopiado] = useState(null)

  async function cargar() {
    setLoading(true)
    try {
      const res = await api.get('/admin/cupones')
      setCupones(res.cupones || [])
    } catch (e) {
      setError(e.message || 'Error al cargar cupones')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [])

  async function crear(e) {
    e.preventDefault()
    setError('')
    setGuardando(true)
    try {
      await api.post('/admin/cupones', {
        codigo: form.codigo,
        tipo: form.tipo,
        valor: Number(form.valor),
        uso_unico: form.uso_unico,
        descripcion: form.descripcion || null
      })
      setForm(FORM_INICIAL)
      await cargar()
    } catch (e) {
      setError(e.response?.data?.error || e.message || 'Error al crear cupón')
    } finally {
      setGuardando(false)
    }
  }

  async function confirmarEliminar() {
    if (!eliminando) return
    try {
      await api.del(`/admin/cupones/${eliminando.id}`)
      setCupones(prev => prev.filter(c => c.id !== eliminando.id))
      setErrorEliminar('')
      setEliminando(null)
    } catch (e) {
      setErrorEliminar(e.response?.data?.error || e.message || 'Error al eliminar')
      setEliminando(null)
    }
  }

  async function copiar(c) {
    try {
      await navigator.clipboard.writeText(c.codigo)
      setCopiado(c.id)
      setTimeout(() => setCopiado(actual => (actual === c.id ? null : actual)), 1500)
    } catch {
    }
  }

  const esPorcentaje = form.tipo === 'porcentaje'

  const conteo = useMemo(() => {
    const base = { todos: cupones.length, activo: 0, canjeado: 0 }
    cupones.forEach(c => { base[estadoDe(c)]++ })
    return base
  }, [cupones])

  const visibles = useMemo(() => {
    const q = busqueda.trim().toUpperCase()
    return cupones.filter(c =>
      (filtro === 'todos' || estadoDe(c) === filtro) &&
      (!q || c.codigo.toUpperCase().includes(q))
    )
  }, [cupones, filtro, busqueda])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
        <Tag size={22} style={{ color: 'var(--surface)' }} />
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, margin: 0, color: 'var(--surface)' }}>Códigos de descuento</h1>
      </div>

      <div className="cup-layout">
        <form onSubmit={crear} className="cup-form">
          <h2 style={{ fontSize: 15, margin: '0 0 14px', color: 'var(--surface)' }}>Crear cupón</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

            <input
              value={form.codigo}
              onChange={e => setForm(f => ({ ...f, codigo: e.target.value.toUpperCase() }))}
              placeholder="Nombre del código"
              style={estiloCampo}
            />

            {/* Tipo (selector segmentado) + valor con símbolo */}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <div
                role="radiogroup"
                aria-label="Tipo de descuento"
                style={{
                  flex: 1, display: 'flex', padding: 3, borderRadius: 8,
                  border: '1px solid var(--line)', background: 'var(--input-bg)',
                }}
              >
                {TIPOS.map(t => {
                  const activo = form.tipo === t.valor
                  return (
                    <button
                      key={t.valor}
                      type="button"
                      role="radio"
                      aria-checked={activo}
                      onClick={() => setForm(f => ({ ...f, tipo: t.valor }))}
                      style={{
                        flex: 1, padding: '6px 0', borderRadius: 6, border: 'none', cursor: 'pointer',
                        fontSize: 13, fontWeight: activo ? 600 : 400,
                        background: activo ? 'var(--accent)' : 'transparent',
                        color: activo ? '#fff' : 'var(--text-dim)',
                        transition: 'background .15s, color .15s',
                      }}
                    >
                      {t.etiqueta}
                    </button>
                  )
                })}
              </div>

              <div style={{ position: 'relative', width: 96 }}>
                <input
                  type="number"
                  min="1"
                  max={esPorcentaje ? 100 : undefined}
                  value={form.valor}
                  onChange={e => setForm(f => ({ ...f, valor: e.target.value }))}
                  placeholder={esPorcentaje ? '10' : '5000'}
                  aria-label={esPorcentaje ? 'Porcentaje de descuento' : 'Monto de descuento'}
                  style={{ ...estiloCampo, padding: '9px 28px 9px 10px' }}
                />
                <span style={{
                  position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                  fontSize: 14, color: 'var(--text-dim)', pointerEvents: 'none',
                }}>
                  {esPorcentaje ? '%' : '$'}
                </span>
              </div>
            </div>

            <input
              value={form.descripcion}
              onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}
              placeholder="Descripción (opcional)"
              style={estiloCampo}
            />

            {/* Uso único (interruptor) */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
              padding: '10px 12px', borderRadius: 8,
              border: '1px solid var(--line)', background: 'var(--input-bg)',
            }}>
              <div>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: 'var(--surface)' }}>Uso único</p>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--text-dim)' }}>Se desactiva tras el primer canje</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={form.uso_unico}
                aria-label="Uso único"
                onClick={() => setForm(f => ({ ...f, uso_unico: !f.uso_unico }))}
                style={{
                  width: 36, height: 20, borderRadius: 10, border: 'none', padding: 0, flexShrink: 0,
                  position: 'relative', cursor: 'pointer',
                  background: form.uso_unico ? 'var(--green)' : 'var(--line)',
                  transition: 'background .2s',
                }}
              >
                <span style={{
                  position: 'absolute', top: 2, left: form.uso_unico ? 18 : 2,
                  width: 16, height: 16, borderRadius: '50%', background: '#fff',
                  transition: 'left .2s',
                }} />
              </button>
            </div>

            <button type="submit" disabled={guardando} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <Plus size={16} /> {guardando ? 'Guardando...' : 'Crear cupón'}
            </button>
          </div>
          {error && <p style={{ color: '#ef4444', fontSize: 13, marginTop: 10 }}>{error}</p>}
        </form>

        <div className="cup-card">
          {/* Barra: filtros + búsqueda */}
          <div className="cup-barra">
            <div className="cup-tabs">
              {FILTROS.map(f => (
                <button
                  key={f.valor}
                  type="button"
                  className="cup-tab"
                  aria-pressed={filtro === f.valor}
                  onClick={() => setFiltro(f.valor)}
                >
                  {f.etiqueta} · {conteo[f.valor]}
                </button>
              ))}
            </div>

            <div className="cup-buscar">
              <Search size={15} aria-hidden="true" />
              <input
                type="search"
                value={busqueda}
                onChange={e => setBusqueda(e.target.value)}
                placeholder="Buscar código"
                aria-label="Buscar código"
              />
            </div>
          </div>

          {errorEliminar && (
            <p style={{ margin: 0, padding: '0 20px 12px', color: 'var(--red)', fontSize: 13 }}>{errorEliminar}</p>
          )}

          <div className="cup-tabla-wrap">
            <table className="cup-tabla">
              <thead>
                <tr>
                  <th className="cup-col-codigo">Código</th>
                  <th></th>
                  <th>Tipo</th>
                  <th>Valor</th>
                  <th>Uso</th>
                  <th>Estado</th>
                  <th style={{ width: 80 }}></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '40px 20px' }}>
                      <img
                        src={mediaPath('cargando.webp')}
                        alt=""
                        decoding="async"
                        width="512"
                        height="512"
                        style={{ display: 'block', height: 70, width: 'auto', margin: '0 auto 12px' }}
                      />
                      Cargando...
                    </td>
                  </tr>
                ) : visibles.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '40px 20px' }}>
                      <img
                        src={mediaPath('sinproductos.webp')}
                        alt=""
                        loading="lazy"
                        decoding="async"
                        width="512"
                        height="512"
                        style={{ display: 'block', height: 70, width: 'auto', margin: '0 auto 12px' }}
                      />
                      {cupones.length === 0 ? 'Aún no hay cupones. Crea el primero desde el formulario.' : 'Ningún cupón coincide con el filtro.'}
                    </td>
                  </tr>
                ) : visibles.map(c => {
                  const est = ESTADOS[estadoDe(c)]
                  const pct = c.tipo === 'porcentaje'
                  return (
                    <tr key={c.id}>
                      <td className="cup-col-codigo">
                        <span className="cup-codigo">{c.codigo}</span>
                      </td>
                      <td style={{ color: 'var(--text-dim)' }}>
                        <button
                          type="button"
                          className="cup-icono"
                          onClick={() => copiar(c)}
                          aria-label={`Copiar código ${c.codigo}`}
                          title={copiado === c.id ? 'Copiado' : 'Copiar'}
                        >
                          {copiado === c.id ? <Check size={14} style={{ color: 'var(--green)' }} /> : <Copy size={14} />}
                        </button>
                      </td>
                      <td style={{ color: 'var(--text-dim)' }}>
                        {pct ? 'Porcentaje' : 'Monto fijo'}
                      </td>
                      <td style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-dim)' }}>
                        {pct ? `${c.valor}%` : `$${Number(c.valor).toLocaleString('es-CL')}`}
                      </td>
                      <td>
                        <span className="cup-pill">{c.uso_unico ? 'Uso único' : 'Ilimitado'}</span>
                      </td>
                      <td>
                        <span className="cup-estado" style={{ color: est.color }}>{est.texto}</span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="cup-icono peligro"
                          onClick={() => { setErrorEliminar(''); setEliminando(c) }}
                          aria-label={`Eliminar cupón ${c.codigo}`}
                          title="Eliminar"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {!loading && cupones.length > 0 && (
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--line)', fontSize: 12, color: 'var(--text-dim)' }}>
              Mostrando {visibles.length} de {cupones.length} cupones
            </div>
          )}
        </div>
      </div>

      {eliminando && (
        <ConfirmModal
          titulo="Eliminar cupón"
          mensaje={`¿Seguro que querés eliminar el cupón ${eliminando.codigo}? Esta acción no se puede deshacer.`}
          textoCancelar="Cancelar"
          textoConfirmar="Eliminar cupón"
          textoCargando="Eliminando…"
          onConfirm={confirmarEliminar}
          onCancel={() => setEliminando(null)}
        />
      )}
    </div>
  )
}
