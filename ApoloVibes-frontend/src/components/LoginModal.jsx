import { useState, useLayoutEffect, useEffect, useRef } from 'react'
import { mediaPath } from '../utils/media.js'
import { createPortal } from 'react-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../services/api.js'
import { CheckCircle2, Eye, EyeOff, Lock, Mail, User, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import CaptchaWidget from './CaptchaWidget.jsx'

const overlayStyle = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 9999, backdropFilter: 'blur(4px)', padding: 20,
}

const modalStyle = {
    background: 'var(--surface)', borderRadius: 20,
    width: '100%', maxWidth: 780, maxHeight: '90vh', boxShadow: '0 20px 60px rgba(0,0,0,.3)',
    position: 'relative', display: 'flex', overflow: 'hidden',
}

const inputStyle = {
    width: '100%', padding: '11px 14px', borderRadius: 10,
    border: '1px solid var(--line)', background: 'var(--bg)',
    color: 'var(--input-text)', fontSize: 14, outline: 'none',
    boxSizing: 'border-box',
}

const errorSlotStyle = { color: '#ef4444', fontSize: 12, margin: '5px 0 14px', height: 14 }

const botonAccionRegistro = {
    padding: '13px 0', borderRadius: 10, border: 'none',
    background: 'var(--accent)', color: '#ffff', fontSize: 14, fontWeight: 600,
    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 8, transition: 'opacity .2s',
}

const botonFlechaRegistro = {
    flex: 1, border: '1px solid var(--line)', borderRadius: 10,
    padding: '11px 0', background: 'transparent', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 6, color: 'var(--text-dim)', fontSize: 13, fontWeight: 600,
    transition: 'border-color .2s',
}

const analizarPassword = (pw) => {
    const reqs = [
        { id: 'largo', label: 'Mínimo 8 caracteres', ok: pw.length >= 8 },
        { id: 'variedad', label: 'Mayúsculas y minúsculas', ok: /[a-z]/.test(pw) && /[A-Z]/.test(pw) },
        { id: 'numero', label: 'Al menos un número', ok: /\d/.test(pw) },
        { id: 'simbolo', label: 'Al menos un símbolo', ok: /[^A-Za-z0-9]/.test(pw) },
    ]
    const puntos = reqs.filter(r => r.ok).length
    if (!pw) return { reqs, puntos, nivel: null, color: null }
    const nivel = puntos <= 1 ? 'Insegura' : puntos === 2 ? 'Débil' : puntos === 3 ? 'Media' : 'Segura'
    const color = puntos <= 1 ? '#ef4444' : puntos === 2 ? '#f59e0b' : puntos === 3 ? '#eab308' : '#22c55e'
    return { reqs, puntos, nivel, color }
}

const ocultarCorreo = (email) => {
    if (!email) return '';
    const [usuario, dominio] = email.trim().split('@');
    if (!usuario || !dominio) return email;
    const visibles = usuario.slice(-4);
    const ocultos = Math.max(usuario.length - 4, 4);
    return `${'x'.repeat(ocultos)}${visibles}@${dominio}`;
}

export default function LoginModal({ onClose }) {
    const { login } = useAuth()
    const [modo, setModo] = useState('login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [mostrarPassword, setMostrarPassword] = useState(false)
    const [registro, setRegistro] = useState({
        nombre: '', apellido: '', email: '', telefono: '', password: '', confirmar: '',
    })
    const [mostrarPasswordRegistro, setMostrarPasswordRegistro] = useState(false)
    const [mostrarConfirmarRegistro, setMostrarConfirmarRegistro] = useState(false)
    const [error, setError] = useState('')
    const [exito, setExito] = useState('')
    const [cargando, setCargando] = useState(false)
    // que el botón "Entrar" (correo/contraseña) no mienta mostrando "Entrando...".
    const [conectandoGoogle, setConectandoGoogle] = useState(false)
    const tiempoCierre = useRef(null)
    const [errores, setErrores] = useState({ email: '', password: '' })
    const [paso, setPaso] = useState(1)
    const [erroresPaso, setErroresPaso] = useState({})
    const [enviandoCodigo, setEnviandoCodigo] = useState(false)
    const [codigoEnviado, setCodigoEnviado] = useState(false)
    const [codigo, setCodigo] = useState('')
    const [olvidar, setOlvidar] = useState({ email: '', codigo: '', password: '', confirmar: '' })
    const [erroresOlvidar, setErroresOlvidar] = useState({})
    const [mostrarNuevaPassword, setMostrarNuevaPassword] = useState(false)
    const [mostrarConfirmarNueva, setMostrarConfirmarNueva] = useState(false)
    const [enviandoCodigoRecup, setEnviandoCodigoRecup] = useState(false)
    const [codigoRecupEnviado, setCodigoRecupEnviado] = useState(false)
    const [errorRecup, setErrorRecup] = useState('')
    const [exitoRecup, setExitoRecup] = useState('')
    const [pasoRecup, setPasoRecup] = useState(1)
    const [cargandoRecup, setCargandoRecup] = useState(false)
    const [expiraRecupEn, setExpiraRecupEn] = useState('')
    const [tiempoRestante, setTiempoRestante] = useState(0)
    const [codigoExpiradoRecup, setCodigoExpiradoRecup] = useState(false)
    const navigate = useNavigate()

    // --- MFA (segundo factor) ---
    const [mfaTicket, setMfaTicket] = useState('')
    const [modoMfa, setModoMfa] = useState(null)
    const [codigoMfa, setCodigoMfa] = useState('')
    const [esperaBlanqueoMfa, setEsperaBlanqueoMfa] = useState(0)

    // En el paso de MFA el modal muestra SOLO el código de verificación: sin
    // divisor "o continua con", sin botón de Google y sin enlace de registro.
    const enPasoMfa = modo === 'login' && Boolean(modoMfa)

    // --- reCAPTCHA ---
    const [captchaRequerido, setCaptchaRequerido] = useState(false)
    const [captchaToken, setCaptchaToken] = useState('')
    

    useEffect(() => {
        const abrir = () => {
            setModoMfa('codigo')
            setMfaTicket('')
        }
        window.addEventListener('apolovibes:google-mfa', abrir)
        if (sessionStorage.getItem('apolovibes_mfa_pendiente') === '1') {
            sessionStorage.removeItem('apolovibes_mfa_pendiente')
            abrir()
        }
        return () => window.removeEventListener('apolovibes:google-mfa', abrir)
    }, [])

    const iniciarGoogle = async () => {
        setConectandoGoogle(true)
        setError('')
        try {
            const data = await api.get('/auth/google/url')
            if (!data.url) throw new Error('No se pudo iniciar sesión con Google')
            window.location.href = data.url
        } catch (err) {
            setError(err.message || 'No se pudo iniciar sesión con Google')
            setConectandoGoogle(false)
        }
    }

    const verificarMfa = async () => {
        if (!codigoMfa.trim()) return
        setCargando(true)
        setError('')
        try {
            const data = await api.post('/auth/mfa/verificar', {
                mfa_ticket: mfaTicket,
                codigo: codigoMfa.trim(),
            })
            login({ token: data.access_token, user: data.user })
            onClose()
        } catch (err) {
            const d = err.datos || {}
            if (d.espera_seg) setEsperaBlanqueoMfa(d.espera_seg)
            setError(err.message || 'Código incorrecto')
        } finally {
            setCargando(false)
        }
    }

    useLayoutEffect(() => {
        const scrollY = window.scrollY
        document.body.style.position = 'fixed'
        document.body.style.top = `-${scrollY}px`
        document.body.style.width = '100%'
        document.body.style.overflow = 'hidden'
        return () => {
            document.body.style.position = ''
            document.body.style.top = ''
            document.body.style.width = ''
            document.body.style.overflow = ''
            window.scrollTo(0, scrollY)
        }
    }, [])

    const formatearTiempo = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

    useEffect(() => {
        if (!expiraRecupEn) return
        const fin = new Date(expiraRecupEn).getTime()
        let id
        const tick = () => {
            const resta = Math.max(0, Math.floor((fin - Date.now()) / 1000))
            setTiempoRestante(resta)
            if (resta <= 0) {
                setCodigoExpiradoRecup(true)
                clearInterval(id)
            }
        }
        tick()
        id = setInterval(tick, 1000)
        return () => clearInterval(id)
    }, [expiraRecupEn])

    const handleSubmit = async (e) => {
        e.preventDefault()
        const nuevosErrores = {
            email: !email.trim() ? 'Completa tu correo' : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) ? 'Ingresa un correo válido' : '',
            password: !password ? 'Completa tu contraseña' : '',
        }
        setErrores(nuevosErrores)
        if (nuevosErrores.email || nuevosErrores.password) return
        if (captchaRequerido && !captchaToken) return
        setError('')
        setExito('')
        setCargando(true)
        try {
            const data = await api.post('/auth/login', { email: email.trim(), password, ...(captchaRequerido && captchaToken ? { captcha_token: captchaToken } : {}) })
            if (data.mfa_requerido) {
                setMfaTicket(data.mfa_ticket || '')
                setModoMfa('codigo')
                setCodigoMfa('')
                setCaptchaRequerido(false)
                setCaptchaToken('')
                return
            }
            login({ token: data.access_token, user: data.user })
            onClose()
        } catch (err) {
            if (captchaRequerido) setCaptchaToken('')
            const msg = err.message || ''
            const d = err.datos || {}

            if (d.espera_seg) {
                setError('Demasiados intentos. Vuelve a intentarlo en unos minutos.')
            } else if (d.captcha_requerido) {
                setCaptchaRequerido(true)
                if (/credenciales/i.test(msg)) {
                    setErrores({ email: 'Credenciales incorrectas', password: 'Credenciales incorrectas'})
                } else {
                    setError(msg)
                }
            } else if (msg.startsWith('Correo')) {
                setErrores(prev => ({ ...prev, email: msg }))
            } else if (msg.startsWith('Contraseña')) {
                setErrores(prev => ({ ...prev, password: msg }))
            } else if (/captcha/i.test(msg) && !/credenciales/i.test(msg)) {
                setError(msg)
            } else if (/credenciales/i.test(msg)) {
                setErrores({ email: 'Credenciales incorrectas', password: 'Credenciales incorrectas' })
            } else {
                setError(msg || 'Error al iniciar sesión')
            }
        } finally {
            setCargando(false)
        }
    }

    const cambiarRegistro = (campo, valor) => {
        setRegistro(prev => ({ ...prev, [campo]: valor }))
        setErroresPaso(prev => (prev[campo] ? { ...prev, [campo]: '' } : prev))
    }

    const limpiarErrorCampo = (campo) => {
        setErroresPaso(prev => (prev[campo] ? { ...prev, [campo]: '' } : prev))
    }

    const validarPaso1 = () => {
        const e = {}
        if (!registro.nombre.trim()) e.nombre = 'Completa tu nombre'
        if (!registro.apellido.trim()) e.apellido = 'Completa tu apellido'
        const mail = registro.email.trim()
        if (!mail) e.email = 'Completa tu correo'
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) e.email = 'Ingresa un correo válido'
        setErroresPaso(e)
        return Object.keys(e).length === 0
    }

    const validarPaso2 = () => {
        const e = {}
        if (!registro.password) e.password = 'Completa tu contraseña'
        else if (registro.password.length < 8 || registro.password.length > 72) e.password = 'La contraseña debe tener entre 8 y 72 caracteres'
        if (!registro.confirmar) e.confirmar = 'Repite tu contraseña'
        else if (registro.confirmar !== registro.password) e.confirmar = 'Las contraseñas no coinciden'
        setErroresPaso(e)
        return Object.keys(e).length === 0
    }

    const enviarCodigoPaso3 = async () => {
        if (enviandoCodigo) return
        setEnviandoCodigo(true)
        setError('')
        setCodigoEnviado(false)
        try {
            await api.post('/auth/registro/crear-codigo', { email: registro.email.trim() })
            setCodigoEnviado(true)
            setPaso(4)
        } catch (err) {
            if ((err.message || '').includes('cuenta con ese correo')) {
                setErroresPaso({ email: err.message })
            } else {
                setError(err.message || 'No se pudo enviar el código')
            }
        } finally {
            setEnviandoCodigo(false)
        }
    }

    const confirmarRegistro = async (e) => {
        e.preventDefault()
        const c = codigo.trim()
        const eCodigo = {}
        if (!c) eCodigo.codigo = 'Ingresa el código'
        else if (!/^\d{6}$/.test(c)) eCodigo.codigo = 'El código tiene 6 dígitos'
        if (Object.keys(eCodigo).length > 0) {
            setErroresPaso(eCodigo)
            return
        }
        setErroresPaso({})
        setError('')
        setExito('')
        setCargando(true)
        try {
            const data = await api.post('/auth/registro/confirmar', {
                email: registro.email.trim(),
                codigo: c,
                password: registro.password,
                nombre: registro.nombre.trim(),
                apellido: registro.apellido.trim(),
                telefono: registro.telefono.trim() ? '+569' + registro.telefono.trim() : null,
            })
            login({ token: data.access_token, user: data.user })
            setExito('¡Cuenta creada! Sesión iniciada correctamente.')
            if (tiempoCierre.current) clearTimeout(tiempoCierre.current)
            tiempoCierre.current = setTimeout(() => {
                onClose()
                navigate('/')
            }, 1800)
        } catch (err) {
            const msg = err.message || 'Error al crear la cuenta'
            if (/c[dó]digo/.test(msg.toLowerCase())) {
                setErroresPaso({ codigo: msg })
            } else {
                setError(msg)
            }
        } finally {
            setCargando(false)
        }
    }

    const cambiarModo = (nuevoModo) => {
        setModo(nuevoModo)
        setError('')
        setExito('')
        setPaso(1)
        setErroresPaso({})
        setCodigoEnviado(false)
        setCodigo('')
        setErroresOlvidar({})
        setErrorRecup('')
        setExitoRecup('')
        setCodigoRecupEnviado(false)
        setPasoRecup(1)
        setExpiraRecupEn('')
        setTiempoRestante(0)
        setCodigoExpiradoRecup(false)
        setModoMfa(null)
        setMfaTicket('')
        setCodigoMfa('')
        setEsperaBlanqueoMfa(0)
        setCaptchaRequerido(false)
        setCaptchaToken('')
        setCargando(false)
        setConectandoGoogle(false)
    }

    // ---- Recuperación de contraseña ----
    const abrirRecuperacion = () => {
        setOlvidar(prev => ({ email: email.trim() || prev.email, codigo: '', password: '', confirmar: '' }))
        cambiarModo('olvidar')
    }

    const cambiarOlvidar = (campo, valor) => {
        setOlvidar(prev => ({ ...prev, [campo]: valor }))
        setErroresOlvidar(prev => (prev[campo] ? { ...prev, [campo]: '' } : prev))
    }

    const validarPasoRecup1 = () => {
        const e = {}
        const mail = olvidar.email.trim()
        if (!mail) e.email = 'Completa tu correo'
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) e.email = 'Ingresa un correo válido'
        setErroresOlvidar(e)
        return Object.keys(e).length === 0
    }

    const enviarCodigoRecuperacion = async () => {
        if (!validarPasoRecup1() || enviandoCodigoRecup) return
        setEnviandoCodigoRecup(true)
        setErrorRecup('')
        setCodigoRecupEnviado(false)
        try {
            const data = await api.post('/auth/recuperar/crear-codigo', { email: olvidar.email.trim() })
            setCodigoRecupEnviado(true)
            setExpiraRecupEn(data.expira_en || new Date(Date.now() + 5 * 60 * 1000).toISOString())
            setCodigoExpiradoRecup(false)
            setPasoRecup(2)
        } catch (err) {

            setErroresOlvidar(prev => ({ ...prev, email: err.message || 'No se pudo enviar el código' }))
        } finally {
            setEnviandoCodigoRecup(false)
        }
    }

    const validarPasoRecup3 = () => {
        const e = {}
        if (!olvidar.password) e.password = 'Completa la nueva contraseña'
        else if (olvidar.password.length < 8 || olvidar.password.length > 72) e.password = 'La contraseña debe tener entre 8 y 72 caracteres'
        if (!olvidar.confirmar) e.confirmar = 'Repite la nueva contraseña'
        else if (olvidar.confirmar !== olvidar.password) e.confirmar = 'Las contraseñas no coinciden'
        setErroresOlvidar(e)
        return Object.keys(e).length === 0
    }

    const verificarCodigoRecuperacion = async (e) => {
        e.preventDefault()
        const c = olvidar.codigo.trim()
        const eCodigo = {}
        if (!c) eCodigo.codigo = 'Ingresa el código'
        else if (!/^\d{6}$/.test(c)) eCodigo.codigo = 'El código tiene 6 dígitos'
        setErroresOlvidar(eCodigo)
        if (Object.keys(eCodigo).length > 0 || cargandoRecup) return
        setErroresOlvidar({})
        setErrorRecup('')
        setCargandoRecup(true)
        try {
            await api.post('/auth/recuperar/verificar-codigo', { email: olvidar.email.trim(), codigo: c })
            setPasoRecup(3)
        } catch (err) {
            const msg = err.message || 'Error al verificar el código'
            if (/c[dó]digo/.test(msg.toLowerCase())) setErroresOlvidar({ codigo: msg })
            else setErrorRecup(msg)
        } finally {
            setCargandoRecup(false)
        }
    }

    const confirmarRecuperacion = async (e) => {
        e.preventDefault()
        if (!validarPasoRecup3() || cargandoRecup) return
        setErroresOlvidar({})
        setErrorRecup('')
        setExitoRecup('')
        setCargandoRecup(true)
        try {
            await api.post('/auth/recuperar/confirmar', {
                email: olvidar.email.trim(),
                codigo: olvidar.codigo.trim(),
                password: olvidar.password,
            })
            setExitoRecup('ok')
            if (tiempoCierre.current) clearTimeout(tiempoCierre.current)
            tiempoCierre.current = setTimeout(() => cambiarModo('login'), 2200)
        } catch (err) {
            const msg = err.message || 'Error al restablecer la contraseña'
            if (/c[dó]digo/.test(msg.toLowerCase())) setErroresOlvidar({ codigo: msg })
            else setErrorRecup(msg)
        } finally {
            setCargandoRecup(false)
        }
    }

    const fortaleza = analizarPassword(registro.password)
    const fortalezaRecup = analizarPassword(olvidar.password)
    const bloqueadoPorCaptcha = captchaRequerido && !captchaToken

    return createPortal(
        <div style={overlayStyle} onClick={onClose}>
            <div
                className="login-modal-inner"
                style={modalStyle}
                onClick={(e) => e.stopPropagation()}
                onMouseDown={(e) => e.stopPropagation()}
            >
                <button
                    onClick={onClose}
                    aria-label="Cerrar"
                    style={{
                        position: 'absolute', top: 16, right: 18, background: 'none',
                        border: 'none', color: 'var(--text-dim)', fontSize: 20, cursor: 'pointer',
                        zIndex: 2, lineHeight: 1,
                    }}
                >
                    &times;
                </button>

                {/* Columna izquierda: formulario */}
                <div className="login-modal-form" style={{ flex: 1, minWidth: 0, minHeight: 0, overflowY: 'auto', padding: '28px 40px' }}>
                    <p
                        style={{
                            fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, textAlign: 'center',
                            color: 'var(--accent)', margin: '0 0 0px',
                        }}
                    >
                        Apolo Vibes 3D
                    </p>
                    <h2 style={{ margin: '0 0 10px', fontSize: 24, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-display)', textAlign: 'center', }}>
                        {modo === 'registro' ? 'Crear cuenta' : modo === 'olvidar' ? 'Recuperar contraseña' : 'Iniciar sesion'}
                    </h2>

                    {modo === 'olvidar' ? (
                        exitoRecup ? (
                            <div style={{ textAlign: 'center', padding: '60px 0 70px' }}>
                                <div
                                    style={{
                                        width: 64, height: 64, borderRadius: '50%', background: '#22c55e',
                                        color: '#fff', fontSize: 34, display: 'flex', alignItems: 'center',
                                        justifyContent: 'center', margin: '0 auto 20px',
                                    }}
                                >
                                    ✓
                                </div>
                                <h3 style={{ margin: '0 0 8px', fontSize: 20, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>
                                    ¡Contraseña actualizada!
                                </h3>
                                <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0 }}>
                                    Ya puedes iniciar sesión. Te vamos a redirigir…
                                </p>
                            </div>
                        ) : pasoRecup === 1 ? (
                            <form onSubmit={(ev) => { ev.preventDefault(); enviarCodigoRecuperacion() }}>
                                <div
                                    style={{
                                        width: 54, height: 54, borderRadius: '50%',
                                        background: 'var(--surface-2)', color: 'var(--accent)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        margin: '0 auto 14px',
                                    }}
                                >
                                    <Mail size={50} />
                                </div>
                                <p style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', margin: '0 0 20px', lineHeight: 1.5 }}>
                                    Te enviaremos un código a tu correo para restablecer tu contraseña.
                                </p>
                                <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                    Correo electronico
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <Mail
                                        size={16}
                                        style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
                                    />
                                    <input
                                        autoFocus
                                        type="email"
                                        placeholder="tucorreo@correo.cl"
                                        value={olvidar.email}
                                        onChange={(e) => cambiarOlvidar('email', e.target.value)}
                                        style={{ ...inputStyle, paddingLeft: 34, color: 'var(--input-text)' }}
                                    />
                                </div>
                                <p style={{ color: '#ef4444', fontSize: 12, margin: '5px 0 14px', minHeight: 16 }}>
                                    {erroresOlvidar.email || ''}
                                </p>

                                <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                                    <button type="button" style={botonFlechaRegistro} onClick={() => cambiarModo('login')}>
                                        Volver
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={enviandoCodigoRecup}
                                        style={{ ...botonAccionRegistro, flex: 1, ...(enviandoCodigoRecup ? { opacity: .7, cursor: 'default' } : {}) }}
                                        onMouseEnter={(e) => { if (!enviandoCodigoRecup) e.currentTarget.style.opacity = '.9' }}
                                        onMouseLeave={(e) => { if (!enviandoCodigoRecup) e.currentTarget.style.opacity = '1' }}
                                    >
                                        {enviandoCodigoRecup ? 'Enviando...' : 'Enviar código'} <span></span>
                                    </button>
                                </div>
                            </form>
                        ) : pasoRecup === 2 ? (
                            <form onSubmit={verificarCodigoRecuperacion}>
                                {codigoRecupEnviado && (
                                    <div style={{ margin: '30px 0 5px', textAlign: 'center' }}>
                                        <CheckCircle2
                                            size={50}
                                            color="#22c55e"
                                            style={{ display: 'block', margin: '0 auto 8px' }}
                                        />
                                        <p style={{ color: 'var(--text-dim)', fontSize: 12, margin: 0, textAlign: 'center', marginBottom: 20 }}>
                                            Código enviado a <strong style={{ color: 'var(--accent)' }}>{ocultarCorreo(olvidar.email.trim())}</strong>
                                        </p>
                                    </div>
                                )}
                                <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', margin: '14px 0 6px' }}>
                                    Codigo de confirmacion
                                </label>
                                <input
                                    autoFocus
                                    type="text"
                                    inputMode="numeric"
                                    maxLength={6}
                                    placeholder="••••••"
                                    value={olvidar.codigo}
                                    onChange={(e) => cambiarOlvidar('codigo', e.target.value.replace(/\D/g, '').slice(0, 6))}
                                    style={{ ...inputStyle, color: 'var(--input-text)', letterSpacing: 6, textAlign: 'center', fontSize: 18 }}
                                />
                                <p style={errorSlotStyle}>{erroresOlvidar.codigo || ''}</p>
                                {errorRecup && (
                                    <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 14px', textAlign: 'center' }}>{errorRecup}</p>
                                )}
                                <p style={{ fontSize: 11, color: codigoExpiradoRecup ? '#ef4444' : tiempoRestante <= 60 ? '#f59e0b' : 'var(--text-dim)', textAlign: 'center', marginTop: 0, marginBottom: 0 }}>
                                    {codigoExpiradoRecup
                                        ? 'El código expiró. Solicita uno nuevo.'
                                        : `El código expira en ${formatearTiempo(tiempoRestante)}`}
                                </p>
                                <div style={{ display: 'flex', gap: 10, marginTop: 20, marginBottom: 20 }}>
                                    <button type="button" style={botonFlechaRegistro} onClick={() => setPasoRecup(1)}>
                                        Volver
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={cargandoRecup || codigoExpiradoRecup}
                                        style={{ ...botonAccionRegistro, flex: 1, ...((cargandoRecup || codigoExpiradoRecup) ? { opacity: .7, cursor: 'default' } : {}) }}
                                        onMouseEnter={(e) => { if (!cargandoRecup && !codigoExpiradoRecup) e.currentTarget.style.opacity = '.9' }}
                                        onMouseLeave={(e) => { if (!cargandoRecup && !codigoExpiradoRecup) e.currentTarget.style.opacity = '1' }}
                                    >
                                        {cargandoRecup ? 'Verificando...' : 'Verificar código'} <span></span>
                                    </button>
                                </div>
                            </form>
                        ) : (
                            <form onSubmit={confirmarRecuperacion}>
                                <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                    Nueva contraseña
                                </label>
                                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                    <Lock
                                        size={16}
                                        style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
                                    />
                                    <input
                                        type={mostrarNuevaPassword ? 'text' : 'password'}
                                        placeholder="Ingresa tu nueva contraseña"
                                        value={olvidar.password}
                                        onChange={(e) => cambiarOlvidar('password', e.target.value)}
                                        style={{ ...inputStyle, paddingLeft: 34, paddingRight: 34, color: 'var(--input-text)' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setMostrarNuevaPassword((v) => !v)}
                                        aria-label={mostrarNuevaPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                        style={{
                                            position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', zIndex: 1,
                                            background: 'none', border: 'none',
                                            color: 'var(--text-dim)', cursor: 'pointer',
                                            padding: 4, display: 'flex',
                                        }}
                                    >
                                        {mostrarNuevaPassword ? <Eye size={16} /> : <EyeOff size={16} />}
                                    </button>
                                </div>
                                <p style={{ ...errorSlotStyle, margin: '8px 0 -15px' }}>{erroresOlvidar.password || ''}</p>
                                <div style={{ marginTop: 8, background: 'var(--surface-2)', borderRadius: 10, padding: '10px 12px' }}>
                                    <div style={{ display: 'grid', gap: 3 }}>
                                        {fortalezaRecup.reqs.map(r => (
                                            <div
                                                key={r.id}
                                                style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: r.ok ? '#22c55e' : 'var(--text-dim)', transition: 'color .15s' }}
                                            >
                                                <span style={{ fontSize: 12 }}>{r.ok ? '✓' : '○'}</span>
                                                {r.label}
                                            </div>
                                        ))}
                                    </div>
                                    <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                                        {[1, 2, 3, 4].map(i => (
                                            <span
                                                key={i}
                                                style={{
                                                    flex: 1, height: 4, borderRadius: 2, transition: 'background .15s',
                                                    background: fortalezaRecup.nivel && i <= fortalezaRecup.puntos ? fortalezaRecup.color : 'var(--line)',
                                                }}
                                            />
                                        ))}
                                    </div>
                                </div>

                                <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', margin: '16px 0 6px' }}>
                                    Confirmar nueva contraseña
                                </label>
                                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                    <Lock
                                        size={16}
                                        style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
                                    />
                                    <input
                                        type={mostrarConfirmarNueva ? 'text' : 'password'}
                                        placeholder="Repite tu nueva contraseña"
                                        value={olvidar.confirmar}
                                        onChange={(e) => cambiarOlvidar('confirmar', e.target.value)}
                                        style={{ ...inputStyle, paddingLeft: 34, paddingRight: 34, color: 'var(--input-text)' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setMostrarConfirmarNueva((v) => !v)}
                                        aria-label={mostrarConfirmarNueva ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                        style={{
                                            position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', zIndex: 1,
                                            background: 'none', border: 'none',
                                            color: 'var(--text-dim)', cursor: 'pointer',
                                            padding: 4, display: 'flex',
                                        }}
                                    >
                                        {mostrarConfirmarNueva ? <Eye size={16} /> : <EyeOff size={16} />}
                                    </button>
                                </div>
                                <p style={{ ...errorSlotStyle, margin: '4px 0 -8px' }}>{erroresOlvidar.confirmar || ''}</p>

                                {errorRecup && (
                                    <p style={{ color: '#ef4444', fontSize: 12, margin: '10px 0 0', textAlign: 'center' }}>{errorRecup}</p>
                                )}

                                <div style={{ display: 'flex', gap: 10, marginTop: 20, marginBottom: 20 }}>
                                    <button type="button" style={botonFlechaRegistro} onClick={() => setPasoRecup(2)}>
                                        Volver
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={cargandoRecup}
                                        style={{ ...botonAccionRegistro, flex: 1, ...(cargandoRecup ? { opacity: .7, cursor: 'default' } : {}) }}
                                        onMouseEnter={(e) => { if (!cargandoRecup) e.currentTarget.style.opacity = '.9' }}
                                        onMouseLeave={(e) => { if (!cargandoRecup) e.currentTarget.style.opacity = '1' }}
                                    >
                                        {cargandoRecup ? 'Guardando...' : 'Restablecer'} <span></span>
                                    </button>
                                </div>
                            </form>
                        )
                    ) : modo === 'login' && modoMfa ? (
                        <form onSubmit={(ev) => { ev.preventDefault(); verificarMfa() }}>
                            <div
                                style={{
                                    width: 54, height: 54, borderRadius: '50%',
                                    background: 'var(--surface-2)', color: 'var(--accent)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    margin: '0 auto 14px',
                                }}
                            >
                                <ShieldCheck size={50} />
                            </div>
                            <p style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', margin: '0 0 20px', lineHeight: 1.5 }}>
                                {modoMfa === 'respaldo'
                                    ? 'Ingresa uno de tus códigos de respaldo (10 caracteres).'
                                    : 'Ingresa el código de 6 dígitos de tu app de autenticación.'}
                            </p>
                            <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                {modoMfa === 'respaldo' ? 'Código de respaldo' : 'Codigo de verificacion'}
                            </label>
                            <input
                                autoFocus
                                type="text"
                                inputMode={modoMfa === 'respaldo' ? 'text' : 'numeric'}
                                maxLength={modoMfa === 'respaldo' ? 12 : 6}
                                placeholder="••••••"
                                value={codigoMfa}
                                onChange={(e) => {
                                    const valor = modoMfa === 'respaldo'
                                        ? e.target.value.toUpperCase()
                                        : e.target.value.replace(/\D/g, '').slice(0, 6)
                                    setCodigoMfa(valor)
                                    setError('')
                                }}
                                style={{ ...inputStyle, color: 'var(--surface)', letterSpacing: modoMfa === 'respaldo' ? 2 : 6, textAlign: 'center', fontSize: 18 }}
                            />
                            <p style={errorSlotStyle}>{error}</p>
                            {esperaBlanqueoMfa > 0 && (
                                <p style={{ fontSize: 11, color: '#ef4444', margin: '0 0 12px', textAlign: 'center' }}>
                                    Demasiados intentos. Vuelve a iniciar sesión dentro de {Math.ceil(esperaBlanqueoMfa / 60)} min.
                                </p>
                            )}
                            <button
                                type="submit"
                                disabled={cargando || !codigoMfa.trim()}
                                style={{
                                    width: '100%', padding: '13px 0', borderRadius: 10, border: 'none',
                                    background: 'var(--accent)', color: '#ffffff', fontSize: 14, fontWeight: 600,
                                    cursor: cargando || !codigoMfa.trim() ? 'default' : 'pointer', marginBottom: 10, display: 'flex', alignItems: 'center',
                                    justifyContent: 'center', gap: 8, transition: 'opacity .2s', opacity: cargando || !codigoMfa.trim() ? .7 : 1,
                                }}
                                onMouseEnter={(e) => { if (!cargando && codigoMfa.trim()) e.currentTarget.style.opacity = '.9' }}
                                onMouseLeave={(e) => { if (!cargando && codigoMfa.trim()) e.currentTarget.style.opacity = '1' }}
                            >
                                {cargando ? 'Verificando...' : 'Verificar'} <span></span>
                            </button>
                            {modoMfa === 'codigo' && (
                                <button
                                    type="button"
                                    style={{ ...botonFlechaRegistro, width: '100%', marginBottom: 10 }}
                                    onClick={() => { setModoMfa('respaldo'); setCodigoMfa(''); setError('') }}
                                >
                                    Usar código de respaldo
                                </button>
                            )}
                            <button
                                type="button"
                                style={{ ...botonFlechaRegistro, width: '100%' }}
                                onClick={() => { setModoMfa(null); setCodigoMfa(''); setMfaTicket(''); setError('') }}
                            >
                                Volver
                            </button>
                        </form>
                    ) : modo === 'login' ? (
                        <form onSubmit={handleSubmit}>
                            <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                Correo electronico
                            </label>
                            <div>
                                <div style={{ position: 'relative' }}>
                                    <Mail
                                        size={16}
                                        style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
                                    />
                                    <input
                                        autoFocus
                                        type="email"
                                        placeholder="tucorreo@correo.cl"
                                        value={email}
                                        onChange={(e) => { setEmail(e.target.value); setErrores(prev => ({ ...prev, email: '' })) }}
                                        style={{ ...inputStyle, paddingLeft: 34, color: 'var(--input-text)' }}
                                    />
                                </div>
                                <p style={{ color: '#ef4444', fontSize: 12, margin: '5px 0 0', height: 16 }}>
                                    {errores.email || ''}
                                </p>
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <label style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 5 }}>Contraseña</label>
                            </div>
                            <div style={{ position: 'relative', marginBottom: 18 }}>
                                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                    <Lock
                                        size={16}
                                        style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
                                    />
                                    <input
                                        type={mostrarPassword ? 'text' : 'password'}
                                        placeholder="••••••••"
                                        value={password}
                                        onChange={(e) => { setPassword(e.target.value); setErrores(prev => ({ ...prev, password: '' })) }}
                                        style={{ ...inputStyle, paddingLeft: 34, paddingRight: 34, color: 'var(--input-text)' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setMostrarPassword((v) => !v)}
                                        aria-label={mostrarPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                        style={{
                                            position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', zIndex: 1,
                                            background: 'none', border: 'none',
                                            color: 'var(--text-dim)', cursor: 'pointer',
                                            padding: 4, display: 'flex',
                                        }}
                                    >
                                        {mostrarPassword ? <Eye size={16} /> : <EyeOff size={16} />}
                                    </button>
                                </div>
                                <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0', height: 16 }}>
                                    {errores.password || ''}
                                </p>
                                <span
                                    role="button"
                                    tabIndex={0}
                                    onClick={abrirRecuperacion}
                                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') abrirRecuperacion() }}
                                    onMouseEnter={(e) => (e.currentTarget.style.opacity = '.75')}
                                    onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                                    style={{
                                        fontSize: 11,
                                        color: 'var(--accent)',
                                        cursor: 'pointer',
                                        display: 'block',
                                        textAlign: 'center',
                                        marginTop: 5,
                                        transition: 'opacity .2s',
                                    }}
                                >
                                    ¿Olvidaste tu contraseña?
                                </span>
                            </div>

                            {error && (
                                <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 14px' }}>{error}</p>
                            )}
                            {exito && (
                                <p style={{ color: '#22c55e', fontSize: 12, margin: '0 0 14px' }}>{exito}</p>
                            )}

                            {captchaRequerido && (
                                <CaptchaWidget token={captchaToken} onToken={setCaptchaToken} />
                            )}

                            <button
                                type="submit"
                                disabled={cargando || bloqueadoPorCaptcha}
                                style={{
                                    width: '100%', padding: '13px 0', borderRadius: 10, border: 'none',
                                    background: bloqueadoPorCaptcha ? '#6b7280' : 'var(--accent)', color: bloqueadoPorCaptcha ? '#d1d5db' : '#ffffff', fontSize: 14, fontWeight: 600,
                                    cursor: cargando || bloqueadoPorCaptcha ? 'not-allowed' : 'pointer', marginBottom: 20, display: 'flex', alignItems: 'center',
                                    justifyContent: 'center', gap: 8, transition: 'opacity .2s', opacity: cargando ? .7 : 1,
                                }}
                                onMouseEnter={(e) => { if (!cargando && !bloqueadoPorCaptcha) e.currentTarget.style.opacity = '.9' }}
                                onMouseLeave={(e) => { if (!cargando && !bloqueadoPorCaptcha) e.currentTarget.style.opacity = '1' }}
                            >
                                {cargando ? 'Entrando...' : 'Entrar'} <span></span>
                            </button>
                        </form>
                    ) : exito ? (
                        <div style={{ textAlign: 'center', padding: '60px 0 70px' }}>
                            <div
                                style={{
                                    width: 64, height: 64, borderRadius: '50%', background: '#22c55e',
                                    color: '#fff', fontSize: 34, display: 'flex', alignItems: 'center',
                                    justifyContent: 'center', margin: '0 auto 20px',
                                }}
                            >
                                ✓
                            </div>
                            <h3 style={{ margin: '0 0 8px', fontSize: 20, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>
                                ¡Cuenta creada!
                            </h3>
                            <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0 }}>
                                Bienvenido/a a Apolo Vibes 3D. Te vamos a redirigir a la tienda…
                            </p>
                        </div>
                    ) : (
                        <div>
                            {/* Paso 1: datos personales */}
                            {paso === 1 && (
                                <form onSubmit={(ev) => { ev.preventDefault(); if (validarPaso1()) setPaso(2) }}>
                                    <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                        Nombre
                                    </label>
                                    <div style={{ position: 'relative' }}>
                                        <span
                                            style={{
                                                position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)',
                                                zIndex: 1, color: 'var(--text-dim)', display: 'flex', pointerEvents: 'none',
                                            }}
                                        >
                                            <User size={16} />
                                        </span>
                                        <input
                                            autoFocus
                                            type="text"
                                            placeholder="Tu nombre"
                                            value={registro.nombre}
                                            onChange={(e) => cambiarRegistro('nombre', e.target.value)}
                                            style={{ ...inputStyle, paddingLeft: 34, color: 'var(--input-text)' }}
                                        />
                                    </div>
                                    <p style={errorSlotStyle}>{erroresPaso.nombre || ''}</p>

                                    <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                        Apellido
                                    </label>
                                    <div style={{ position: 'relative' }}>
                                        <span
                                            style={{
                                                position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)',
                                                zIndex: 1, color: 'var(--text-dim)', display: 'flex', pointerEvents: 'none',
                                            }}
                                        >
                                            <User size={16} />
                                        </span>
                                        <input
                                            type="text"
                                            placeholder="Tu apellido"
                                            value={registro.apellido}
                                            onChange={(e) => cambiarRegistro('apellido', e.target.value)}
                                            style={{ ...inputStyle, paddingLeft: 34, color: 'var(--input-text)' }}
                                        />
                                    </div>
                                    <p style={errorSlotStyle}>{erroresPaso.apellido || ''}</p>

                                    <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                        Correo electronico
                                    </label>
                                    <div style={{ position: 'relative' }}>
                                        <span
                                            style={{
                                                position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)',
                                                zIndex: 1, color: 'var(--text-dim)', display: 'flex', pointerEvents: 'none',
                                            }}
                                        >
                                            <Mail size={16} />
                                        </span>
                                        <input
                                            type="email"
                                            placeholder="tucorreo@correo.cl"
                                            value={registro.email}
                                            onChange={(e) => cambiarRegistro('email', e.target.value)}
                                            style={{ ...inputStyle, paddingLeft: 34, color: 'var(--input-text)' }}
                                        />
                                    </div>
                                    <p style={errorSlotStyle}>{erroresPaso.email || ''}</p>

                                    <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                        Telefono <span style={{ opacity: .6 }}></span>
                                    </label>
                                    <div className="input-prefijo" style={{ marginBottom: 14 }}>
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
                                            placeholder="1234 5678"
                                            value={registro.telefono}
                                            onChange={(e) => cambiarRegistro('telefono', e.target.value.replace(/\D/g, '').slice(0, 8))}
                                        />
                                    </div>

                                    <button
                                        type="submit"
                                        style={{ ...botonAccionRegistro, width: '100%', marginBottom: 14, color: '#ffffff' }}
                                        onMouseEnter={(e) => (e.currentTarget.style.opacity = '.9')}
                                        onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                                    >
                                        Continuar <span></span>
                                    </button>
                                </form>
                            )}

                            {/* Paso 2: contraseña */}
                            {paso === 2 && (
                                <form onSubmit={(ev) => { ev.preventDefault(); if (validarPaso2()) setPaso(3) }}>
                                    <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                        Contraseña
                                    </label>
                                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                        <Lock
                                            size={16}
                                            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
                                        />
                                        <input
                                            autoFocus
                                            type={mostrarPasswordRegistro ? 'text' : 'password'}
                                            placeholder="Ingresa tu contraseña"
                                            value={registro.password}
                                            onChange={(e) => cambiarRegistro('password', e.target.value)}
                                            style={{ ...inputStyle, paddingLeft: 34, paddingRight: 34, color: 'var(--input-text)' }}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setMostrarPasswordRegistro((v) => !v)}
                                            aria-label={mostrarPasswordRegistro ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                            style={{
                                                position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', zIndex: 1,
                                                background: 'none', border: 'none',
                                                color: 'var(--text-dim)', cursor: 'pointer',
                                                padding: 4, display: 'flex',
                                            }}
                                        >
                                            {mostrarPasswordRegistro ? <Eye size={16} /> : <EyeOff size={16} />}
                                        </button>
                                    </div>
                                    <p style={{ ...errorSlotStyle, margin: '8px 0 -15px' }}>{erroresPaso.password || ''}</p>
                                    {/* Requisitos de contraseña segura + medidor en vivo */}
                                    <div style={{ marginTop: 8, background: 'var(--surface-2)', borderRadius: 10, padding: '10px 12px' }}>
                                        <div style={{ display: 'grid', gap: 3 }}>
                                            {fortaleza.reqs.map(r => (
                                                <div
                                                    key={r.id}
                                                    style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: r.ok ? '#22c55e' : 'var(--text-dim)', transition: 'color .15s' }}
                                                >
                                                    <span style={{ fontSize: 12 }}>{r.ok ? '✓' : '○'}</span>
                                                    {r.label}
                                                </div>
                                            ))}
                                        </div>
                                        <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                                            {[1, 2, 3, 4].map(i => (
                                                <span
                                                    key={i}
                                                    style={{
                                                        flex: 1, height: 4, borderRadius: 2, transition: 'background .15s',
                                                        background: fortaleza.nivel && i <= fortaleza.puntos ? fortaleza.color : 'var(--line)',
                                                    }}
                                                />
                                            ))}
                                        </div>
                                        <p style={{ fontSize: 11, fontWeight: 600, color: fortaleza.color || 'var(--text-dim)', margin: '4px 0 0', minHeight: 14 }}>
                                            {fortaleza.nivel || 'La fortaleza se actualiza mientras escribes'}
                                        </p>
                                    </div>


                                    <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                        Confirmar contraseña
                                    </label>
                                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', marginBottom: 20 }}>
                                        <Lock
                                            size={16}
                                            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }}
                                        />
                                        <input
                                            type={mostrarConfirmarRegistro ? 'text' : 'password'}
                                            placeholder="Repite tu contraseña"
                                            value={registro.confirmar}
                                            onChange={(e) => cambiarRegistro('confirmar', e.target.value)}
                                            style={{ ...inputStyle, paddingLeft: 34, paddingRight: 34, color: 'var(--input-text)' }}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setMostrarConfirmarRegistro((v) => !v)}
                                            aria-label={mostrarConfirmarRegistro ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                            style={{
                                                position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', zIndex: 1,
                                                background: 'none', border: 'none',
                                                color: 'var(--text-dim)', cursor: 'pointer',
                                                padding: 4, display: 'flex',
                                            }}
                                        >
                                            {mostrarConfirmarRegistro ? <Eye size={16} /> : <EyeOff size={16} />}
                                        </button>
                                    </div>
                                    <p style={{ ...errorSlotStyle, margin: '-13px 0 15px' }}>{erroresPaso.confirmar || ''}</p>

                                    <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                                        <button type="button" style={botonFlechaRegistro} onClick={() => setPaso(1)}>
                                            Volver
                                        </button>
                                        <button
                                            type="submit"
                                            style={{ ...botonAccionRegistro, flex: 1, color: '#ffff' }}
                                            onMouseEnter={(e) => (e.currentTarget.style.opacity = '.9')}
                                            onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                                        >
                                            Continuar <span></span>
                                        </button>
                                    </div>
                                </form>
                            )}

                            {/* Paso 3: enviar código */}
                            {paso === 3 && (
                                <div style={{ textAlign: 'center', padding: '16px 0 6px' }}>
                                    <div
                                        style={{
                                            width: 54, height: 54, borderRadius: '50%',
                                            background: 'var(--surface-2)', color: 'var(--accent)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            margin: '0 auto 14px',
                                        }}
                                    >
                                        <Mail size={50} />
                                    </div>
                                    <p style={{ fontSize: 13, color: 'var(--text)', margin: '15px 0 5px', fontWeight: 600 }}>
                                        Te enviaremos un código de confirmación
                                    </p>
                                    <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 50px' }}>
                                        a <strong style={{ color: 'var(--accent)' }}>{ocultarCorreo(registro.email)}</strong>
                                    </p>

                                    {codigoEnviado && (
                                        <p style={{ color: '#22c55e', fontSize: 12, margin: '0 0 14px' }}>
                                            Código enviado. Revisa tu correo.
                                        </p>
                                    )}
                                    {error && (
                                        <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 14px' }}>{error}</p>
                                    )}

                                    <button
                                        type="button"
                                        onClick={enviarCodigoPaso3}
                                        disabled={enviandoCodigo}
                                        style={{ ...botonAccionRegistro, width: '100%', marginBottom: 12, ...(enviandoCodigo ? { opacity: .7, cursor: 'default' } : {}) }}
                                        onMouseEnter={(e) => { if (!enviandoCodigo) e.currentTarget.style.opacity = '.9' }}
                                        onMouseLeave={(e) => { if (!enviandoCodigo) e.currentTarget.style.opacity = '1' }}
                                    >
                                        {enviandoCodigo ? 'Enviando...' : codigoEnviado ? 'Reenviar código' : 'Enviar código'} <span></span>
                                    </button>
                                    <button
                                        type="button"
                                        style={{ ...botonFlechaRegistro, width: '100%', marginBottom: 20 }}
                                        onClick={() => setPaso(2)}
                                    >
                                        Volver
                                    </button>
                                </div>
                            )}

                            {/* Paso 4: validar código */}
                            {paso === 4 && (
                                <form onSubmit={confirmarRegistro}>
                                    {codigoEnviado && (
                                        <div style={{ margin: '30px 0 5px', textAlign: 'center' }}>
                                            <CheckCircle2
                                                size={40}
                                                color="#22c55e"
                                                style={{ display: 'block', margin: '0 auto 10px' }}
                                            />
                                            <p style={{ color: 'var(--text-dim)', fontSize: 12, margin: 0, textAlign: 'center' }}>
                                                Código enviado a <strong style={{ color: 'var(--accent)' }}>{registro.email.trim()}</strong>
                                            </p>
                                        </div>
                                    )}
                                    <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 30, textAlign: 'center' }}>
                                        Codigo de confirmacion
                                    </label>
                                    <input
                                        autoFocus
                                        type="text"
                                        inputMode="numeric"
                                        maxLength={6}
                                        placeholder="••••••"
                                        value={codigo}
                                        onChange={(e) => {
                                            setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))
                                            limpiarErrorCampo('codigo')
                                        }}
                                        style={{ ...inputStyle, color: 'var(--input-text)', letterSpacing: 6, textAlign: 'center', fontSize: 18 }}
                                    />
                                    <p style={errorSlotStyle}>{erroresPaso.codigo || ''}</p>

                                    {error && (
                                        <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 14px', textAlign: 'center' }}>{error}</p>
                                    )}

                                    <div style={{ display: 'flex', gap: 10, marginBottom: 20, marginTop: 30 }}>
                                        <button type="button" style={botonFlechaRegistro} onClick={() => setPaso(3)}>
                                            Volver
                                        </button>
                                        <button
                                            type="submit"
                                            disabled={cargando}
                                            style={{ ...botonAccionRegistro, flex: 1, ...(cargando ? { opacity: .7, cursor: 'default' } : {}) }}
                                            onMouseEnter={(e) => { if (!cargando) e.currentTarget.style.opacity = '.9' }}
                                            onMouseLeave={(e) => { if (!cargando) e.currentTarget.style.opacity = '1' }}
                                        >
                                            {cargando ? 'Verificando...' : 'Crear cuenta'} <span></span>
                                        </button>
                                    </div>
                                </form>
                            )}
                        </div>
                    )}

                    {modo === 'login' && !enPasoMfa && (
                        <>
                            <p style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', margin: '0 0 14px' }}>
                                o continua con
                            </p>

                            <div style={{ display: 'flex', gap: 10, marginBottom: 22 }}>
                                <button
                                    type="button"
                                    aria-label="Continuar con Google"
                                    aria-busy={conectandoGoogle}
                                    disabled={conectandoGoogle}
                                    onClick={iniciarGoogle}
                                    style={{
                                        flex: 1, border: '1px solid var(--line)', borderRadius: 10,
                                        padding: '11px 0', background: 'transparent', cursor: conectandoGoogle ? 'default' : 'pointer',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        gap: 8, color: 'var(--text-dim)', fontSize: 12, opacity: conectandoGoogle ? .6 : 1,
                                        transition: 'border-color .2s',
                                    }}
                                    onMouseEnter={(e) => { if (!conectandoGoogle) e.currentTarget.style.borderColor = 'var(--accent)' }}
                                    onMouseLeave={(e) => { if (!conectandoGoogle) e.currentTarget.style.borderColor = 'var(--line)' }}
                                >
                                    {conectandoGoogle ? 'Conectando...' : (
                                        <>
                                            <svg width="16" height="16" viewBox="0 0 24 24">
                                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                            </svg>
                                            Google
                                        </>
                                    )}
                                </button>
                            </div>
                        </>
                    )}

                    {!enPasoMfa && (
                        <p style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', margin: 0 }}>
                            {modo === 'registro' ? (
                                <>
                                    Ya tienes cuenta?{' '}
                                    <span
                                        style={{ color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }}
                                        onClick={() => cambiarModo('login')}
                                    >
                                        Inicia sesion
                                    </span>
                                </>
                            ) : (
                                <>
                                    No tienes cuenta?{' '}
                                    <span
                                        style={{ color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }}
                                        onClick={() => cambiarModo('registro')}
                                    >
                                        Registrate gratis
                                    </span>
                                </>
                            )}
                        </p>
                    )}
                </div>

                <div
                    className="login-visual"
                    style={{
                        flex: 1, background: 'linear-gradient(180deg, #ffffff 73%, var(--accent) 100%)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        padding: 40, minWidth: 260,
                    }}
                >
                    <div style={{ textAlign: 'center' }}>
                        <div
                            style={{
                                width: 250, height: 250, margin: '0 auto 20px', borderRadius: 24,
                                background: 'rgba(255, 255, 255, 0)', display: 'flex',
                                alignItems: 'center', justifyContent: 'center', position: 'relative'
                            }}
                        >
                            <img
                                src={mediaPath('apolo-vibes-logo.png')}
                                alt=""
                                aria-hidden="true"
                                style={{
                                    position: 'absolute',
                                    inset: 0,
                                    width: '100%',
                                    height: '100%',
                                    objectFit: 'contain',
                                    objectPosition: 'center',
                                }}
                                fetchpriority="high"
                            />

                        </div>
                        <p style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: '#E8863E', margin: '0 0 8px' }}>
                            Ideas hechas realidad
                        </p>
                        <p style={{ fontSize: 13, color: '#1E3A5F', fontWeight: 700, maxWidth: 200, margin: '0 auto', lineHeight: 1.5 }}>
                            Impresión 3D a tu medida, con la energía de Apolo Vibes
                        </p>
                    </div>
                </div>
            </div>
        </div>,
        document.body
    )
}