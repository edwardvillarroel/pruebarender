import { useEffect, useState } from 'react'
import { api } from '../../services/api.js'
import { Plus, Trash2, Tag } from 'lucide-react'

const TIPOS = [
  { valor: 'porcentaje', etiqueta: 'Porcentaje' },
  { valor: 'monto', etiqueta: 'Monto fijo' },
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

export default function CuponesAdmin() {
  const [cupones, setCupones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [form, setForm] = useState(FORM_INICIAL)

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

  async function eliminar(id) {
    if (!window.confirm('¿Eliminar este cupón?')) return
    try {
      await api.delete(`/admin/cupones/${id}`)
      setCupones(prev => prev.filter(c => c.id !== id))
    } catch (e) {
      alert(e.response?.data?.error || 'Error al eliminar')
    }
  }

  const esPorcentaje = form.tipo === 'porcentaje'

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
        <Tag size={22} style={{ color: 'var(--surface)' }} />
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, margin: 0, color: 'var(--surface)' }}>Códigos de descuento</h1>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 360px) 1fr', gap: 24, alignItems: 'start' }}>
        <form onSubmit={crear} style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, padding: 18 }}>
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

        <div style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--surface-2)', fontSize: 11, textTransform: 'uppercase', borderBottom: '1px solid var(--line)' }}>
                <th style={{ padding: '12px 16px' }}>Código</th>
                <th style={{ padding: '12px 16px' }}>Tipo</th>
                <th style={{ padding: '12px 16px' }}>Valor</th>
                <th style={{ padding: '12px 16px' }}>Uso único</th>
                <th style={{ padding: '12px 16px' }}>Estado</th>
                <th style={{ padding: '12px 16px' }}>Usado</th>
                <th style={{ padding: '12px 16px' }}></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} style={{ padding: 18, textAlign: 'center', color: 'var(--text-dim)' }}>Cargando...</td></tr>
              ) : cupones.length === 0 ? (
                <tr><td colSpan={7} style={{ padding: 18, textAlign: 'center', color: 'var(--text-dim)' }}>Sin cupones</td></tr>
              ) : cupones.map(c => (
                <tr key={c.id} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '12px 16px', color: 'var(--surface)', fontFamily: 'var(--font-mono)' }}>{c.codigo}</td>
                  <td style={{ padding: '12px 16px', color: 'var(--text-dim)' }}>{c.tipo === 'porcentaje' ? 'Porcentaje' : 'Monto fijo'}</td>
                  <td style={{ padding: '12px 16px', color: 'var(--surface)' }}>{c.tipo === 'porcentaje' ? `${c.valor}%` : `$${Number(c.valor).toLocaleString('es-CL')}`}</td>
                  <td style={{ padding: '12px 16px', color: 'var(--text-dim)' }}>{c.uso_unico ? 'Sí' : 'No'}</td>
                  <td style={{ padding: '12px 16px', color: c.activo && !c.usado ? '#22c55e' : 'var(--text-dim)' }}>{c.activo && !c.usado ? 'Activo' : 'Inactivo'}</td>
                  <td style={{ padding: '12px 16px', color: 'var(--text-dim)' }}>{c.usado ? 'Sí' : 'No'}</td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <button onClick={() => eliminar(c.id)} title="Eliminar" style={{ background: 'none', border: 'none', color: 'var(--red)', cursor: 'pointer' }}>
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}