import { useState, useRef } from 'react'
import { api } from '../services/api.js'
import { generarModelo3DMock } from '../services/ai-model.js'
import ModelViewer from '../components/ModelViewer.jsx'
import GenerationProgress from '../components/GenerationProgress.jsx'
import SelectOpciones from '../components/SelectOpciones.jsx'
import { Upload, X, FileImage } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import { createPortal } from 'react-dom'
import { mediaPath } from '../utils/media.js'
import ModalValidacion from '../components/ModalValidacion.jsx'

const ESTADO_INICIAL = {
  nombre: '', email: '', telefono: '',
  material: 'PLA', descripcion: '',
}

const MATERIALES = ['PLA', 'PLA+', 'ABS+', 'No estoy seguro']
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const estiloError = { color: '#ef4444', fontSize: 12, margin: '6px 0 0' }

function Paso({ titulo, completo, bloqueado, textoBloqueo, children }) {
  return (
    <div style={{
      background: 'var(--surface-3)', border: '1px solid var(--line)',
      borderRadius: 12,
      padding: 24, marginBottom: 24, opacity: bloqueado ? 0.4 : 1,
      transition: 'opacity .2s'
    }}>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16, color: 'var(--surface)' }}>{titulo}</h2>

      {bloqueado && (
        <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 12px' }}>{textoBloqueo}</p>
      )}

      <fieldset
        disabled={bloqueado}
        style={{
          border: 'none', padding: 0, margin: 0, minWidth: 0
        }}
      >
        {children}
      </fieldset>
    </div>
  )
}

export default function Cotizacion() {
  const { user } = useAuth()
  const [form, setForm] = useState({
    ...ESTADO_INICIAL,
    nombre: user?.nombre || '',
    email: user?.email || '',
  })
  const [archivo, setArchivo] = useState(null)
  const [previsualizacion, setPrevisualizacion] = useState(null)
  const [generando, setGenerando] = useState(false)
  const [progreso, setProgreso] = useState({ status: 'idle', percent: 0, message: '' })
  const [modeloUrl, setModeloUrl] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [enviado, setEnviado] = useState(false)
  const [error, setError] = useState(null)
  const [tocado, setTocado] = useState({})
  const fileInputRef = useRef(null)
  const [visorFallo, setVisorFallo] = useState(false)
  const [mostrarModalImagenInvalida, setMostrarModalImagenInvalida] = useState(false)
  const [mensajeImagenInvalida, setMensajeImagenInvalida] = useState('La imagen seleccionada no es válida o contiene contenido no permitido. Por favor sube una imagen JPG, PNG o WebP.')
  const [validandoImagen, setValidandoImagen] = useState(false)
  const [progresoValidacion, setProgresoValidacion] = useState({ status: 'idle', percent: 0, message: '' })

  const email = form.email.trim()
  const telefono = form.telefono.trim()
  const erroresCampo = {
    nombre: form.nombre.trim() ? '' : 'Por favor complete su nombre.',
    email: !email ? 'Por favor ingrese su email.' : EMAIL_RE.test(email) ? '' : 'Ingrese un email válido',
    telefono: !telefono ? 'Por favor ingrese su teléfono.' : /^\d{9}$/.test(telefono) ? '' : 'Ingrese un teléfono móvil válido.',
    descripcion: form.descripcion.trim() ? '' : 'Por favor describa la pieza.',
  }

  const errorDe = campo => (tocado[campo] ? erroresCampo[campo] : '')
  const borde = campo => (errorDe(campo) ? { borderColor: '#ef4444' } : undefined)
  const marcar = campo => setTocado(prev => (prev[campo] ? prev : { ...prev, [campo]: true }))

  const procesando = validandoImagen || generando
  const paso1Completo = !!archivo && !procesando
  const paso2Completo = paso1Completo && !erroresCampo.nombre && !erroresCampo.email && !erroresCampo.telefono
  const paso3Completo = paso2Completo && !erroresCampo.descripcion

  const modeloValido = !!modeloUrl && !visorFallo

  function manejarErrorVisor() {
    setVisorFallo(true)
    setProgreso({ status: 'failed', percent: 0, message: 'No se pudo cargar el modelo 3D' })
  }

  function actualizar(campo, valor) {
    setForm(prev => ({ ...prev, [campo]: valor }))
  }

  async function manejarArchivo(e) {
    const file = e.target.files[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setError('El archivo debe ser una imagen (JPG, PNG o WEBP).')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    if (file.size > 8 * 1024 * 1024) {
      setError('La imagen no puede pesar más de 8MB.')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    setError(null)
    setArchivo(file)
    setPrevisualizacion(URL.createObjectURL(file))
    setModeloUrl(null)
    setVisorFallo(false)
    setProgreso({ status: 'idle', percent: 0, message: '' })

    setValidandoImagen(true)
    setProgresoValidacion({ status: 'uploading', percent: 0, message: 'Iniciando validación de seguridad...' })

    const interval = setInterval(() => {
      setProgresoValidacion(prev => {
        if (prev.percent >= 95) return { ...prev, status: 'processing', message: 'Finalizando análisis...' }
        const next = prev.percent + 7
        const messages = [
          'Comprobando firma mágica...',
          'Verificando tipo de archivo...',
          'Escaneando contenido embebido...',
          'Validando estructura de imagen...',
          'Revisando patrones sospechosos...',
          'Aplicando filtros de seguridad...',
          'Verificando integridad...',
        ]
        const idx = Math.min(Math.floor((next) / 13), messages.length - 1)
        return { status: next > 25 ? (next > 65 ? 'processing' : 'uploading') : 'uploading', percent: Math.min(next, 95), message: messages[idx] || messages[messages.length - 1] }
      })
    }, 180)

    try {
      const fd = new FormData()
      fd.append('imagen', file)
      await Promise.all([
        api.post('/cotizaciones/validar-imagen', fd),
        new Promise(r => setTimeout(r, 2000))
      ])
      clearInterval(interval)
      setProgresoValidacion({ status: 'processing', percent: 98, message: 'Finalizando análisis...' })
      await new Promise(r => setTimeout(r, 400))
      setProgresoValidacion({ status: 'completed', percent: 100, message: 'Imagen segura - Validación completada' })
      await new Promise(r => setTimeout(r, 700))
    } catch (err) {
      clearInterval(interval)
      setValidandoImagen(false)
      setProgresoValidacion({ status: 'idle', percent: 0, message: '' })
      setArchivo(null)
      setPrevisualizacion(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      const msg = err?.response?.data?.error || 'La imagen seleccionada no es válida o contiene contenido no permitido. Por favor sube una imagen JPG, PNG o WebP.'
      setMensajeImagenInvalida(msg)
      setMostrarModalImagenInvalida(true)
      return
    }
    setValidandoImagen(false)
    setProgresoValidacion({ status: 'idle', percent: 0, message: '' })

    // Iniciar generación
    setGenerando(true)
    setProgreso({ status: 'uploading', percent: 5, message: 'Subiendo imagen...' })

    try {
      const resultado = await generarModelo3DMock(file, setProgreso)
      setModeloUrl(resultado.modelUrl)
    } catch (err) {
      setError('No pudimos generar el modelo 3D. Puedes continuar con la cotización de todas formas.')
      setProgreso({ status: 'failed', percent: 0, message: 'Error en la generación' })
    } finally {
      setGenerando(false)
    }
  }

  function quitarImagen() {
    if (procesando) return
    setArchivo(null)
    setPrevisualizacion(null)
    setModeloUrl(null)
    setVisorFallo(false)
    setProgreso({ status: 'idle', percent: 0, message: '' })
    setProgresoValidacion({ status: 'idle', percent: 0, message: '' })
    setValidandoImagen(false)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function enviarSolicitud(e) {
    e.preventDefault()
    if (!paso3Completo || enviando) return

    setEnviando(true)
    setError(null)

    const data = new FormData()
    Object.entries(form).forEach(([k, v]) => data.append(k, v))
    data.set('telefono', '+56' + form.telefono.trim())
    data.append('imagen', archivo)
    if (modeloValido) data.append('modeloUrl', modeloUrl)

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
          Recibimos tu pieza de referencia{modeloValido ? ' y el modelo 3D generado' : ''}.
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
        Sube una imagen de lo que necesitas imprimir. Nuestra IA generará un modelo 3D de referencia para ti
        y nuestro equipo revisará la cotización. Una vez enviada tu cotización nuestro equipo te confirmará el precio final.
      </p>

      <form noValidate onSubmit={enviarSolicitud}>
        {/* ─── Paso 1: Imagen + generación 3D ─── */}
        <Paso titulo="Imagen de referencia" completo={paso1Completo} bloqueado={false}>
          {!archivo ? (
            <label
              htmlFor="imagen-input"
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                border: '2px dashed var(--line)', borderRadius: 10, padding: '48px 20px',
                cursor: 'pointer', background: 'var(--input-bg)',
                transition: 'border-color .2s',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
            >
              <Upload size={32} color="var(--text-dim)" strokeWidth={1.5} style={{ marginBottom: 12 }} />
              <span style={{ fontSize: 14, color: 'var(--text-dim)', fontWeight: 500, marginBottom: 4 }}>
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
                  border: '1px solid var(--line)', background: 'var(--input-bg)',
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
                    title={procesando ? 'Espera que termine el proceso' : 'Quitar imagen'}
                    disabled={procesando}
                    style={{
                      position: 'absolute', top: 8, right: 8,
                      width: 28, height: 28, borderRadius: 8,
                      background: 'rgba(0,0,0,.6)', border: 'none',
                      color: '#fff',
                      cursor: procesando ? 'not-allowed' : 'pointer',
                      opacity: procesando ? 0.4 : 1,
                      transition: 'opacity .2s',
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
                  <ModelViewer modelUrl={modeloUrl} height={280} onError={manejarErrorVisor} />
                ) : (
                  <div style={{
                    height: 280, borderRadius: 10, border: '1px solid var(--line)',
                    background: 'var(--input-bg)'
                    , display: 'flex', alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    {generando ? (
                      <div style={{ textAlign: 'center' }}>
                        <div style={{
                          width: 40, height: 40, margin: '0 auto 10px',
                          border: '3px solid rgba(255,255,255,.08)',
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
        </Paso>

        {/* ─── Paso 2: Datos de contacto ─── */}
        <Paso
          titulo="Tus datos"
          completo={paso2Completo}
          bloqueado={!paso1Completo}
          textoBloqueo="Sube tu imagen de referencia para continuar."
        >
          <div className="cotizacion-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
            <div>
              <label htmlFor="cot-nombre">Nombre</label>
              <input
                id="cot-nombre"
                required
                value={form.nombre}
                autoComplete="given-name"
                onChange={e => actualizar('nombre', e.target.value)}
                onBlur={() => marcar('nombre')}
                aria-invalid={errorDe('nombre') ? true : undefined}
                style={{ background: 'var(--input-bg)', ...borde('nombre') }}
              />
              {errorDe('nombre') && <p role="alert" style={estiloError}>{errorDe('nombre')}</p>}
            </div>
            <div>
              <label htmlFor="cot-email">Email</label>
              <input
                id="cot-email"
                required
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={e => actualizar('email', e.target.value)}
                onBlur={() => marcar('email')}
                aria-invalid={errorDe('email') ? true : undefined}
                style={{ background: 'var(--input-bg)', ...borde('email') }} />
              {errorDe('email') && <p role="alert" style={estiloError}>{errorDe('email')}</p>}
            </div>
          </div>

          <div className="cotizacion-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div>
              <label htmlFor="cot-telefono">Teléfono</label>
              <div className="input-prefijo" style={borde('telefono')}>
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
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, opacity: .85 }}>+56</span>
                <span style={{ opacity: .4 }}>|</span>
                <input
                  id="cot-telefono"
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel-national"
                  pattern="[0-9]*"
                  maxLength={9}
                  required
                  placeholder="912345678"
                  aria-label="Teléfono móvil chileno"
                  value={form.telefono}
                  onChange={e => actualizar('telefono', e.target.value.replace(/\D/g, '').slice(0, 9))}
                  onBlur={() => marcar('telefono')}
                />
              </div>
              {errorDe('telefono') && <p role="alert" style={estiloError}>{errorDe('telefono')}</p>}
            </div>
            <div>
              <label>Material preferido</label>
              <SelectOpciones options={MATERIALES} value={form.material} onChange={v => actualizar('material', v)} />
            </div>
          </div>
        </Paso>

        {/* ─── Paso 3: Descripción ─── */}
        <Paso
          titulo="Descripción de la pieza"
          completo={paso3Completo}
          bloqueado={!paso2Completo}
          textoBloqueo="Completa tus datos de contacto para continuar."
        >
          <label htmlFor="cot-descripcion" >Describe lo que necesitas</label>
          <textarea
            id="cot-descripcion"
            rows={4}
            required
            placeholder="Dimensiones aproximadas, cantidad, uso de la pieza, color, acabado deseado, etc."
            value={form.descripcion}
            onChange={e => actualizar('descripcion', e.target.value)}
            onBlur={() => marcar('descripcion')}
            aria-invalid={errorDe('descripcion') ? true : undefined}
            style={{ resize: 'vertical', minHeight: 100, background: 'var(--input-bg)', ...borde('descripcion') }}
          />
          {errorDe('descripcion') && <p role="alert" style={estiloError}>{errorDe('descripcion')}</p>}
        </Paso>

        {error && (
          <p role="alert" style={{ color: 'var(--accent)', fontSize: 13, marginBottom: 16, padding: '10px 14px', background: 'var(--accent-soft)', borderRadius: 8 }}>
            {error}
          </p>
        )}

        <button
          className="btn btn-primary"
          type="submit"
          disabled={!paso3Completo || enviando}
          style={{
            width: '100%', padding: '14px 0', fontSize: 15,
            justifyContent: 'center', opacity: paso3Completo ? 1 : 0.5,
          }}
        >
          {enviando ? 'Enviando...' : 'Enviar solicitud de cotización'}
        </button>
      </form>

      {validandoImagen && (
        <ModalValidacion
          percent={progresoValidacion.percent}
          completado={progresoValidacion.status === 'completed'}
        />
      )}

      {mostrarModalImagenInvalida && createPortal(
        <ConfirmModal
          titulo="Imagen no válida"
          mensaje={mensajeImagenInvalida}
          textoCancelar="Entendido"
          textoConfirmar="Cerrar"
          confirmarPeligro={false}
          onCancel={() => setMostrarModalImagenInvalida(false)}
          onConfirm={() => setMostrarModalImagenInvalida(false)}
        />,
        document.body
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </section>
  )
}
