import { useState, useRef } from 'react'
import { api } from '../services/api.js'
import { generarModelo3DMock } from '../services/ai-model.js'
import ModelViewer from '../components/ModelViewer.jsx'
import GenerationProgress from '../components/GenerationProgress.jsx'
import SelectOpciones from '../components/SelectOpciones.jsx'
import { Upload, X, RotateCcw, FileImage } from 'lucide-react'

const ESTADO_INICIAL = {
  nombre: '', email: '', telefono: '',
  material: 'PLA', descripcion: '',
}

const MATERIALES = ['PLA', 'PETG', 'Resina', 'ABS', 'No estoy seguro']

export default function Cotizacion() {
  const [form, setForm] = useState(ESTADO_INICIAL)
  const [archivo, setArchivo] = useState(null)
  const [previsualizacion, setPrevisualizacion] = useState(null)
  const [generando, setGenerando] = useState(false)
  const [progreso, setProgreso] = useState({ status: 'idle', percent: 0, message: '' })
  const [modeloUrl, setModeloUrl] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [enviado, setEnviado] = useState(false)
  const [error, setError] = useState(null)
  const [errores, setErrores] = useState({})
  const fileInputRef = useRef(null)
  const abortRef = useRef(null)

  function actualizar(campo, valor) {
    setForm(prev => ({ ...prev, [campo]: valor }))
    // Si el campo tenía error, se limpia apenas el usuario escribe
    setErrores(prev => {
      if (!(campo in prev)) return prev
      const next = { ...prev }
      delete next[campo]
      return next
    })
  }

  async function manejarArchivo(e) {
    const file = e.target.files[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setError('El archivo debe ser una imagen (JPG, PNG o WEBP).')
      return
    }
    if (file.size > 8 * 1024 * 1024) {
      setError('La imagen no puede pesar más de 8MB.')
      return
    }

    setError(null)
    setArchivo(file)
    setPrevisualizacion(URL.createObjectURL(file))
    setModeloUrl(null)

    // Iniciar generación
    setGenerando(true)
    setProgreso({ status: 'uploading', percent: 5, message: 'Subiendo imagen...' })

    try {
      const resultado = await generarModelo3DMock(file, setProgreso)
      setModeloUrl(resultado.modelUrl)
    } catch (err) {
      setError('No pudimos generar el modelo 3D. Podés continuar con la cotización de todas formas.')
      setProgreso({ status: 'failed', percent: 0, message: 'Error en la generación' })
    } finally {
      setGenerando(false)
    }
  }

  function quitarImagen() {
    setArchivo(null)
    setPrevisualizacion(null)
    setModeloUrl(null)
    setProgreso({ status: 'idle', percent: 0, message: '' })
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function enviarSolicitud(e) {
    e.preventDefault()

    const nuevosErrores = {}
    if (!form.nombre.trim()) nuevosErrores.nombre = 'Por favor complete su nombre.'
    if (!form.email.trim()) nuevosErrores.email = 'Por favor ingrese su email.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) nuevosErrores.email = 'Ingrese un email válido, por ejemplo nombre@mail.com.'
    if (!form.descripcion.trim()) nuevosErrores.descripcion = 'Por favor describa la pieza.'
    const tel = form.telefono.trim()
    if (!tel) nuevosErrores.telefono = 'Por favor ingrese su teléfono.'
    else if (!/^\d{8}$/.test(tel)) nuevosErrores.telefono = 'Ingrese un teléfono móvil válido, por ejemplo 1234 5678.'
    if (Object.keys(nuevosErrores).length) { setErrores(nuevosErrores); return }
    if (!archivo) { setError('Suba una imagen de referencia de la pieza.'); return }

    setEnviando(true)
    setError(null)

    const data = new FormData()
    Object.entries(form).forEach(([k, v]) => data.append(k, v))
    // El teléfono se guarda completo en formato internacional (+569 + 8 dígitos)
    if (form.telefono.trim()) data.set('telefono', '+569' + form.telefono.trim())
    data.append('imagen', archivo)
    if (modeloUrl) data.append('modeloUrl', modeloUrl)

    try {
      await api.post('/cotizaciones', data)
      setEnviado(true)
    } catch (err) {
      setError('No pudimos enviar tu solicitud. Intenta nuevamente.')
    } finally {
      setEnviando(false)
    }
  }

  if (enviado) {
    return (
      <section className="wrap" style={{ paddingTop: '100px', paddingBottom: '100px', textAlign: 'center', maxWidth: 480, margin: '0 auto' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, marginBottom: 12 }}>Solicitud enviada</h1>
        <p style={{ color: 'var(--text-dim)' }}>
          Recibimos tu pieza de referencia{modeloUrl ? ' y el modelo 3D generado' : ''}.
          Nuestro equipo la revisa y te responde con un precio estimado dentro de 24 a 48 horas hábiles a {form.email}.
        </p>
      </section>
    )
  }

  return (
    <section className="wrap" style={{ paddingTop: '48px', paddingBottom: '80px', maxWidth: 740 }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent)', textTransform: 'uppercase' }}>
        Cotización personalizada
      </span>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, margin: '10px 0 8px', color: 'var(--surface)' }}>Cotiza tu producto</h1>
      <p style={{ color: 'var(--text-dim)', marginBottom: 32, lineHeight: 1.6 }}>
        Sube una imagen de lo que necesitas imprimir. Nuestra IA generará un modelo 3D de referencia
        y nuestro equipo revisara la cotización y te confirmará el precio final.
      </p>

      <form noValidate onSubmit={enviarSolicitud}>
        {/* ─── Paso 1: Imagen + generación 3D ─── */}
        <div style={{
          background: 'var(--surface-3)',
          border: '1px solid var(--line)',
          borderRadius: 12,
          padding: 24,
          marginBottom: 24,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 15,
              background: archivo ? '#22c55e' : 'var(--accent-soft)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 700,
              color: archivo ? 'var(--text)' : 'var(--accent)',
            }}>
              {archivo ? '✓' : '1'}
            </div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: 'var(--surface)' }}>Imagen de referencia</h2>
          </div>

          {!archivo ? (
            <label
              htmlFor="imagen-input"
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                border: '2px dashed var(--line)', borderRadius: 10, padding: '48px 20px',
                cursor: 'pointer', background: 'var(--bg)',
                transition: 'border-color .2s',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
            >
              <Upload size={32} color="var(--text-dim)" strokeWidth={1.5} style={{ marginBottom: 12 }} />
              <span style={{ fontSize: 14, color: 'var(--text--dim)', fontWeight: 500, marginBottom: 4 }}>
                Haz clic para subir una imagen
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                JPG, PNG o WEBP · máx. 8MB
              </span>
            </label>
          ) : (
            <div className="grid-2" style={{ marginBottom: 16 }}>
              {/* Imagen original */}
              <div>
                <p style={{ fontSize: 11, textAlign: 'center', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 8 }}>
                  Imagen original
                </p>
                <div style={{
                  position: 'relative', borderRadius: 10, overflow: 'hidden',
                  border: '1px solid var(--line)', background: '#fff',
                }}>
                  <img
                    src={previsualizacion}
                    alt="Referencia subida"
                    style={{ width: '100%', maxHeight: 280, objectFit: 'cover', display: 'block' }}
                  />
                  <button
                    type="button"
                    onClick={quitarImagen}
                    aria-label="Quitar imagen"
                    style={{
                      position: 'absolute', top: 8, right: 8,
                      width: 28, height: 28, borderRadius: 8,
                      background: 'rgba(0,0,0,.6)', border: 'none',
                      color: '#fff', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>

              {/* Modelo 3D generado */}
              <div>
                <p style={{ fontSize: 11, textAlign: 'center', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 8 }}>
                  Modelo 3D generado
                </p>
                {modeloUrl ? (
                  <ModelViewer modelUrl={modeloUrl} height={280} />
                ) : (
                  <div style={{
                    height: 280, borderRadius: 10, border: '1px solid var(--line)',
                    background: 'var(--bg)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    {generando ? (
                      <div style={{ textAlign: 'center' }}>
                        <div style={{
                          width: 40, height: 40, margin: '0 auto 10px',
                          border: '3px solid var(--line)',
                          borderTopColor: 'var(--accent)',
                          borderRadius: '50%',
                          animation: 'spin 1s linear infinite',
                        }} />
                        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Generando...</span>
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: 20 }}>
                        <FileImage size={28} color="var(--text-dim)" strokeWidth={1.5} style={{ marginBottom: 8 }} />
                        <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>
                          El modelo 3D aparecerá aquí
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          <input
            ref={fileInputRef}
            id="imagen-input"
            type="file"
            accept="image/*"
            onChange={manejarArchivo}
            style={{ display: 'none' }}
          />

          {/* Barra de progreso */}
          {(generando || progreso.status === 'completed' || progreso.status === 'failed') && (
            <GenerationProgress
              status={progreso.status}
              percent={progreso.percent}
              message={progreso.message}
            />
          )}
        </div>

        {/* ─── Paso 2: Datos de contacto ─── */}
        <div style={{
          background: 'var(--surface-3)',
          border: '1px solid var(--line)',
          borderRadius: 12,
          padding: 24,
          marginBottom: 24,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 15,
              background: form.nombre && form.email ? '#22c55e' : 'var(--accent-soft)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 700,
              color: form.nombre && form.email ? 'var(--text)' : 'var(--accent)',
            }}>
              {form.nombre && form.email ? '✓' : '2'}
            </div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: 'var(--surface)' }}>Tus datos</h2>
          </div>

          <div className="cotizacion-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
            <div>
              <label>Nombre</label>
              <input required value={form.nombre} onChange={e => actualizar('nombre', e.target.value)} />
              {errores.nombre && <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0' }}>{errores.nombre}</p>}
            </div>
            <div>
              <label>Email</label>
              <input required type="email" value={form.email} onChange={e => actualizar('email', e.target.value)} />
              {errores.email && <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0' }}>{errores.email}</p>}
            </div>
          </div>

          <div className="cotizacion-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div>
              <label>Teléfono</label>
              <div className="input-prefijo" style={errores.telefono ? { borderColor: '#ef4444' } : undefined}>
                <svg
                  aria-hidden="true"
                  width={20}
                  height={14}
                  viewBox="0 0 60 40"
                  style={{ borderRadius: 3, flexShrink: 0 }}
                >
                  <rect width="60" height="20" fill="#FFFFFF" />
                  <rect y="20" width="60" height="20" fill="#D52B1E" />
                  <rect width="20" height="20" fill="#0039A6" />
                  <polygon
                    points="10,3 11.65,7.73 16.66,7.84 12.66,10.87 14.12,15.66 10,12.8 5.89,15.66 7.34,10.87 3.34,7.84 8.35,7.73"
                    fill="#FFFFFF"
                  />
                </svg>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, opacity: .85 }}>+569</span>
                <span style={{ opacity: .4 }}>|</span>
                <input
                  type="tel"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={8}
                  required
                  placeholder="1234 5678"
                  aria-label="Teléfono móvil chileno"
                  value={form.telefono}
                  onChange={e => actualizar('telefono', e.target.value.replace(/\D/g, '').slice(0, 8))}
                />
              </div>
              {errores.telefono && <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0' }}>{errores.telefono}</p>}
            </div>
            <div>
              <label>Material preferido</label>
              <SelectOpciones options={MATERIALES} value={form.material} onChange={v => actualizar('material', v)} />
            </div>
          </div>
        </div>

        {/* ─── Paso 3: Descripción ─── */}
        <div style={{
          background: 'var(--surface-3)',
          border: '1px solid var(--line)',
          borderRadius: 12,
          padding: 24,
          marginBottom: 24,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 15,
              background: form.descripcion ? '#22c55e' : 'var(--accent-soft)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 700,
              color: form.descripcion ? 'var(--text)' : 'var(--accent)',
            }}>
              {form.descripcion ? '✓' : '3'}
            </div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: 'var(--surface)' }}>Descripción de la pieza</h2>
          </div>

          <label>Describe lo que necesitas</label>
          <textarea
            rows={4}
            required
            placeholder="Dimensiones aproximadas, cantidad, uso de la pieza, color, acabado deseado, etc."
            value={form.descripcion}
            onChange={e => actualizar('descripcion', e.target.value)}
            style={{ resize: 'vertical', minHeight: 100 }}
          />
          {errores.descripcion && <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0' }}>{errores.descripcion}</p>}
        </div>

        {error && (
          <p style={{ color: 'var(--accent)', fontSize: 13, marginBottom: 16, padding: '10px 14px', background: 'var(--accent-soft)', borderRadius: 8 }}>
            {error}
          </p>
        )}

        <button
          className="btn btn-primary"
          type="submit"
          disabled={enviando || !archivo}
          style={{
            width: '100%', padding: '14px 0', fontSize: 15,
            justifyContent: 'center',
          }}
        >
          {enviando ? 'Enviando...' : 'Enviar solicitud de cotización'}
        </button>
      </form>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </section>
  )
}
