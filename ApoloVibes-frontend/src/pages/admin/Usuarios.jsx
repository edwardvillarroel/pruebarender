import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, FileText, Plus, RefreshCw, Search, ShoppingBag, Trash2, Users, XCircle } from 'lucide-react'
import { usuariosApi } from '../../services/usuarios.js'
import ConfirmModal from '../../components/ConfirmModal.jsx'
import { useAuth } from '../../context/AuthContext.jsx'

function numero(valor) {
  return Number(valor || 0).toLocaleString('es-CL')
}

// ---------- tarjeta de resumen ----------

function TarjetaResumen({ icon: Icon, label, valor, detalle, color }) {
  return (
    <div style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--surface)', marginBottom: 6 }}>
        <Icon size={15} style={{ color: color || 'var(--accent)' }} />
        {label}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, color: 'var(--surface)' }}>{valor}</div>
      {detalle && (
        <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginTop: 6 }}>{detalle}</div>
      )}
    </div>
  )
}

// ---------- celda numerica ----------

function CeldaNumero({ valor, color, icon: Icon, titulo }) {
  return (
    <td
      title={titulo}
      style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: color || 'var(--text-dim)', whiteSpace: 'nowrap', textAlign: 'right' }}
    >
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {Icon && <Icon size={14} style={{ color: color || 'var(--text-dim)' }} />}
        {numero(valor)}
      </span>
    </td>
  )
}

// ---------- badge de estado ----------

function BadgeEstado({ activo }) {
  const estiloActiva = {
    color: 'var(--green, #22c55e)',
    background: 'rgba(34, 197, 94, .16)',
  }
  const estiloBloqueada = {
    color: 'var(--red, #ef4444)',
    background: 'rgba(239, 68, 68, .16)',
  }
  const estilo = activo ? estiloActiva : estiloBloqueada
  const texto = activo ? 'Activa' : 'Bloqueada'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.4px',
      padding: '2px 8px', borderRadius: 20,
      color: estilo.color, background: estilo.background,
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: estilo.color,
        display: 'inline-block',
      }} />
      {texto}
    </span>
  )
}

// ---------- modal alta usuario ----------

function ModalAltaUsuario({ abierto, onCerrar, onGuardar, guardando, error }) {
  const [form, setForm] = useState({
    nombre: '',
    apellido: '',
    email: '',
    password: '',
    rol: 'cliente',
  })

  useEffect(() => {
    if (abierto) {
      setForm({ nombre: '', apellido: '', email: '', password: '', rol: 'cliente' })
    }
  }, [abierto])

  if (!abierto) return null

  const cambiar = (campo, valor) => setForm(f => ({ ...f, [campo]: valor }))

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.49)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 9999, backdropFilter: 'blur(4px)',
    }} onClick={onCerrar}>
      <div style={{
        background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
        width: '100%', maxWidth: 440, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
        textAlign: 'center', maxHeight: '90vh', overflowY: 'auto',
      }} onClick={e => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
          Crear usuario
        </h3>
        <p style={{ margin: '0 0 20px', fontSize: 13, color: 'var(--text-dim)' }}>
          El usuario podrá iniciar sesión con los datos que definas.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, textAlign: 'left' }}>
          <input
            value={form.nombre}
            onChange={e => cambiar('nombre', e.target.value)}
            placeholder="Nombre"
            aria-label="Nombre"
            style={{
              width: '100%', padding: '9px 10px', borderRadius: 8, border: '1px solid var(--line)',
              background: 'var(--bg)', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box',
            }}
          />
          <input
            value={form.apellido}
            onChange={e => cambiar('apellido', e.target.value)}
            placeholder="Apellido (obligatorio para clientes)"
            aria-label="Apellido"
            style={{
              width: '100%', padding: '9px 10px', borderRadius: 8, border: '1px solid var(--line)',
              background: 'var(--bg)', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box',
            }}
          />
          <input
            value={form.email}
            onChange={e => cambiar('email', e.target.value)}
            placeholder="Correo electrónico"
            type="email"
            aria-label="Correo electrónico"
            style={{
              width: '100%', padding: '9px 10px', borderRadius: 8, border: '1px solid var(--line)',
              background: 'var(--bg)', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box',
            }}
          />
          <input
            value={form.password}
            onChange={e => cambiar('password', e.target.value)}
            placeholder="Contraseña (mínimo 8 caracteres)"
            type="password"
            aria-label="Contraseña"
            style={{
              width: '100%', padding: '9px 10px', borderRadius: 8, border: '1px solid var(--line)',
              background: 'var(--bg)', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box',
            }}
          />
          <div>
            <p style={{ margin: '0 0 6px', fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Rol inicial</p>
            <select
              value={form.rol}
              onChange={e => cambiar('rol', e.target.value)}
              aria-label="Rol inicial"
              style={{
                width: '100%', padding: '9px 10px', borderRadius: 8, border: '1px solid var(--line)',
                background: 'var(--bg)', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box',
              }}
            >
              <option value="cliente">Cliente</option>
              <option value="admin">Administrador</option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => onGuardar(form)}
            disabled={guardando}
            style={{
              marginTop: 8, padding: '10px 0', borderRadius: 10, border: 'none',
              background: 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 600,
              cursor: guardando ? 'not-allowed' : 'pointer', opacity: guardando ? 0.7 : 1,
            }}
          >
            {guardando ? 'Creando...' : 'Crear usuario'}
          </button>

          {error && (
            <p style={{ margin: 0, padding: '0 20px 12px', color: 'var(--red)', fontSize: 13 }}>{error}</p>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------- componente principal ----------

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [busqueda, setBusqueda] = useState('')
  const [recarga, setRecarga] = useState(0)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [errorAlta, setErrorAlta] = useState(null)
  const [usuarioEliminar, setUsuarioEliminar] = useState(null)
  const [eliminando, setEliminando] = useState(false)

  const { user: usuarioActual } = useAuth()
  const esAdminActual = usuarioActual?.rol === 'admin'

  useEffect(() => {
    let vigente = true
    setCargando(true)
    setError(null)
    usuariosApi.listar()
      .then(res => {
        if (!vigente) return
        setUsuarios(res.usuarios ?? [])
      })
      .catch(err => {
        if (!vigente) return
        setError(err.message)
      })
      .finally(() => {
        if (vigente) setCargando(false)
      })
    return () => { vigente = false }
  }, [recarga])

  const filtrados = useMemo(() => {
    const termino = busqueda.trim().toLowerCase()
    if (!termino) return usuarios
    return usuarios.filter(u => {
      const nombre = `${u.nombre_completo || ''} ${u.nombre || ''} ${u.apellido || ''}`
      return nombre.toLowerCase().includes(termino) || (u.email || '').toLowerCase().includes(termino)
    })
  }, [usuarios, busqueda])

  const resumen = useMemo(() => usuarios.reduce((acc, u) => ({
    productos: acc.productos + Number(u.productos_comprados || 0),
    pedidas: acc.pedidas + Number(u.cotizaciones_pedidas || 0),
    aprobadas: acc.aprobadas + Number(u.cotizaciones_aprobadas || 0),
    rechazadas: acc.rechazadas + Number(u.cotizaciones_rechazadas || 0),
  }), { productos: 0, pedidas: 0, aprobadas: 0, rechazadas: 0 }), [usuarios])

  function refrescar() {
    setRecarga(n => n + 1)
  }

  async function guardarUsuario(form) {
    setGuardando(true)
    setErrorAlta(null)
    try {
      await usuariosApi.crear(form)
      setModalAbierto(false)
      refrescar()
    } catch (err) {
      setErrorAlta(err.message)
    } finally {
      setGuardando(false)
    }
  }

  async function confirmarEliminar() {
    if (!usuarioEliminar) return
    setEliminando(true)
    try {
      await usuariosApi.eliminar(usuarioEliminar.id)
      setUsuarioEliminar(null)
      refrescar()
    } catch (err) {
      setErrorAlta(err.message)
    } finally {
      setEliminando(false)
    }
  }

  async function toggleEstado(u) {
    try {
      await usuariosApi.cambiarEstado(u.id, !u.activo)
      refrescar()
    } catch (err) {
      setErrorAlta(err.message)
    }
  }

  async function cambiarRol(u, rol) {
    try {
      await usuariosApi.cambiarRol(u.id, rol)
      refrescar()
    } catch (err) {
      setErrorAlta(err.message)
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Users size={22} style={{ color: 'var(--surface)' }} />
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, margin: 0, color: 'var(--surface)' }}>Usuarios</h1>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: 280, maxWidth: '100%' }}>
            <Search
              size={15}
              style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
            />
            <input
              type="search"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar por nombre o correo..."
              aria-label="Buscar usuarios"
              style={{
                width: '100%', padding: '9px 12px 9px 34px', borderRadius: 10,
                border: '1px solid var(--line)', background: 'var(--input-bg)',
                color: 'var(--surface)', fontSize: 13, boxSizing: 'border-box',
              }}
            />
          </div>
          <button
            type="button"
            onClick={() => { setErrorAlta(null); setModalAbierto(true) }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6, padding: '9px 14px',
              borderRadius: 10, border: '1px solid var(--line)', background: 'var(--surface)',
              color: 'var(--text)', fontSize: 12.5, fontWeight: 600, cursor: 'pointer',
            }}
          >
            <Plus size={14} />
            Agregar usuario
          </button>
        </div>
      </div>

      {cargando && usuarios.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando usuarios…</p>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--red, #ef4444)', fontSize: 13, flexWrap: 'wrap' }}>
          <AlertTriangle size={16} />
          No se pudo cargar el listado de usuarios: {error}
          <button
            type="button"
            onClick={() => setRecarga(n => n + 1)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px',
              borderRadius: 8, border: '1px solid var(--line)', background: 'var(--surface-3)',
              color: 'var(--surface)', fontSize: 12.5, cursor: 'pointer',
            }}
          >
            <RefreshCw size={13} />
            Reintentar
          </button>
        </div>
      ) : usuarios.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>Todavía no hay usuarios registrados.</p>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 18, marginBottom: 24 }}>
            <TarjetaResumen icon={Users} label="Usuarios registrados" valor={numero(usuarios.length)} />
            <TarjetaResumen
              icon={ShoppingBag}
              label="Productos comprados"
              valor={numero(resumen.productos)}
              detalle="Unidades en pedidos pagados"
            />
            <TarjetaResumen
              icon={FileText}
              label="Cotizaciones pedidas"
              valor={numero(resumen.pedidas)}
              detalle={`${numero(resumen.aprobadas)} aprobadas · ${numero(resumen.rechazadas)} rechazadas`}
            />
          </div>

          {filtrados.length === 0 ? (
            <p style={{ color: 'var(--text-dim)' }}>No hay usuarios que coincidan con «{busqueda}»</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 860 }}>
                <thead>
                  <tr style={{ color: 'var(--surface)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
                    <th style={{ padding: '0 10px 12px' }}>Nombre</th>
                    <th style={{ padding: '0 10px 12px' }}>Correo</th>
                    <th style={{ padding: '0 10px 12px', textAlign: 'right' }}>Productos comprados</th>
                    <th style={{ padding: '0 10px 12px', textAlign: 'right' }}>Cotizaciones pedidas</th>
                    <th style={{ padding: '0 10px 12px', textAlign: 'right' }}>Aprobadas</th>
                    <th style={{ padding: '0 10px 12px', textAlign: 'right' }}>Rechazadas</th>
                    <th style={{ padding: '0 10px 12px' }}>Estado</th>
                    <th style={{ padding: '0 10px 12px', textAlign: 'right' }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.map(u => {
                    const esPropia = esAdminActual && String(u.id) === String(usuarioActual?.id)
                    return (
                      <>
                      <tr key={u.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
                        <td style={{ padding: '13px 10px', color: 'var(--surface)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span>{u.nombre_completo || '—'}</span>
                            {u.rol === 'admin' && (
                              <span style={{
                                fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.4px',
                                padding: '2px 8px', borderRadius: 20,
                                color: 'var(--accent)', background: 'rgba(250,127,25,.14)',
                              }}>
                                Admin
                            </span>
                            )}
                          </div>
                        </td>
                        <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{u.email}</td>
                        <CeldaNumero
                          valor={u.productos_comprados}
                          icon={ShoppingBag}
                          titulo={`${numero(u.pedidos_pagados)} ${Number(u.pedidos_pagados) === 1 ? 'pedido pagado' : 'pedidos pagados'}`}
                        />
                        <CeldaNumero valor={u.cotizaciones_pedidas} />
                        <CeldaNumero valor={u.cotizaciones_aprobadas} icon={CheckCircle2} color="var(--green, #22c55e)" />
                        <CeldaNumero valor={u.cotizaciones_rechazadas} icon={XCircle} color="var(--red, #ef4444)" />
                        <td style={{ padding: '13px 10px' }}>
                          <BadgeEstado activo={u.activo} />
                        </td>
                        <td style={{ padding: '13px 10px', textAlign: 'right' }}>
                          {esPropia ? (
                            <span style={{ fontSize: 11.5, color: 'var(--text-dim)' }}>Tu cuenta</span>
                          ) : (
                            <div style={{ display: 'inline-flex', gap: 6, justifyContent: 'flex-end' }}>
                              <button
                                type="button"
                                onClick={() => toggleEstado(u)}
                                title={u.activo ? 'Bloquear cuenta' : 'Desbloquear cuenta'}
                                style={{
                                  padding: '6px 10px', borderRadius: 8, border: '1px solid var(--line)',
                                  background: 'var(--input-bg)', color: 'var(--text)', fontSize: 11.5, cursor: 'pointer',
                                }}
                              >
                                {u.activo ? 'Bloquear' : 'Desbloquear'}
                              </button>
                              {u.rol === 'admin' ? (
                                <button
                                  type="button"
                                  onClick={() => cambiarRol(u, 'cliente')}
                                  title="Quitar permisos de administrador"
                                  style={{
                                    padding: '6px 10px', borderRadius: 8, border: '1px solid var(--line)',
                                    background: 'var(--input-bg)', color: 'var(--text)', fontSize: 11.5, cursor: 'pointer',
                                  }}
                                >
                                  Quitar admin
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => cambiarRol(u, 'admin')}
                                  title="Otorgar permisos de administrador"
                                  style={{
                                    padding: '6px 10px', borderRadius: 8, border: '1px solid var(--line)',
                                    background: 'var(--input-bg)', color: 'var(--text)', fontSize: 11.5, cursor: 'pointer',
                                  }}
                                >
                                  Dar admin
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => { setErrorAlta(null); setUsuarioEliminar(u) }}
                                title="Eliminar usuario"
                                style={{
                                  padding: '6px 10px', borderRadius: 8, border: '1px solid var(--line)',
                                  background: 'var(--input-bg)', color: 'var(--red, #ef4444)', fontSize: 11.5, cursor: 'pointer',
                                }}
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                      </>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {errorAlta && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.49)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 9999, backdropFilter: 'blur(4px)',
        }} onClick={() => setErrorAlta(null)}>
          <div style={{
            background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
            width: '100%', maxWidth: 420, boxShadow: '0 20px 60px rgba(0,0,0,.3)', textAlign: 'center',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 10 }}>
              <AlertTriangle size={32} style={{ color: 'var(--red, #ef4444)' }} />
            </div>
            <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
              Error
            </h3>
            <p style={{ margin: '0 0 22px', fontSize: 13, color: 'var(--text-dim)' }}>
              {errorAlta}
            </p>
            <button
              type="button"
              onClick={() => setErrorAlta(null)}
              style={{
                width: '100%', padding: '10px 0', borderRadius: 10, border: '1px solid var(--line)',
                background: 'transparent', color: 'var(--text)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
              }}
            >
              Cerrar
            </button>
          </div>
        </div>
      )}

      {usuarioEliminar && (
        <ConfirmModal
          titulo="Eliminar usuario"
          mensaje={`¿Seguro que querés eliminar a «${usuarioEliminar.nombre_completo || usuarioEliminar.email}»? Esta acción no se puede deshacer.`}
          textoCancelar="Cancelar"
          textoConfirmar="Eliminar usuario"
          textoCargando="Eliminando…"
          onConfirm={confirmarEliminar}
          onCancel={() => setUsuarioEliminar(null)}
        />
      )}

      <ModalAltaUsuario
        abierto={modalAbierto}
        onCerrar={() => { setModalAbierto(false); setErrorAlta(null) }}
        onGuardar={guardarUsuario}
        guardando={guardando}
        error={errorAlta}
      />
    </>
  )
}
