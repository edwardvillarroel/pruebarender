import { useState, useLayoutEffect } from 'react'
import { mediaPath } from '../utils/media.js'
import { createPortal } from 'react-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../services/api.js'
import { Eye, EyeOff } from 'lucide-react'

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
    color: 'var(--text)', fontSize: 14, outline: 'none',
    boxSizing: 'border-box',
}

export default function LoginModal({ onClose }) {
    const { login } = useAuth()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [mostrarPassword, setMostrarPassword] = useState(false)
    const [error, setError] = useState('')
    const [cargando, setCargando] = useState(false)

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

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!email || !password) {
            setError('Completa todos los campos')
            return
        }
        setError('')
        setCargando(true)
        try {
            const data = await api.post('/auth/login', { email, password })
            login({ token: data.access_token, user: data.user })
            onClose()
        } catch (err) {
            setError(err.message || 'Error al iniciar sesión')
        } finally {
            setCargando(false)
        }
    }

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
                <div style={{ flex: 1, padding: '44px 40px', minWidth: 0 }}>
                    <p
                        style={{
                            fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16,
                            color: 'var(--accent)', margin: '0 0 6px',
                        }}
                    >
                        Apolo Vibes 3D
                    </p>
                    <h2 style={{ margin: '0 0 24px', fontSize: 24, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>
                        Iniciar sesion
                    </h2>

                    <form onSubmit={handleSubmit}>
                        <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                            Correo electronico
                        </label>
                        <input
                            autoFocus
                            type="email"
                            placeholder="tucorreo@correo.cl"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            style={{ ...inputStyle, marginBottom: 14 }}
                        />

                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                            <label style={{ fontSize: 12, color: 'var(--text-dim)' }}>Contraseña</label>
                        </div>
                        <div style={{ position: 'relative', marginBottom: 18 }}>
                            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                <button
                                    type="button"
                                    onClick={() => setMostrarPassword((v) => !v)}
                                    aria-label={mostrarPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                    style={{
                                        position: 'absolute', left: 10, zIndex: 1,
                                        background: 'none', border: 'none',
                                        color: 'var(--text-dim)', cursor: 'pointer',
                                        padding: 4, display: 'flex',
                                    }}
                                >
                                    {mostrarPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                                <input
                                    type={mostrarPassword ? 'text' : 'password'}
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    style={{ ...inputStyle, paddingLeft: 34 }}
                                />
                            </div>
                            <span
                                style={{
                                    fontSize: 11,
                                    color: 'var(--accent)',
                                    cursor: 'pointer',
                                    display: 'block',
                                    textAlign: 'center',
                                    marginTop: 12,
                                }}
                            >
                                ¿Olvidaste tu contraseña?
                            </span>
                        </div>

                        {error && (
                            <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 14px' }}>{error}</p>
                        )}

                        <button
                            type="submit"
                            disabled={cargando}
                            style={{
                                width: '100%', padding: '13px 0', borderRadius: 10, border: 'none',
                                background: 'var(--accent)', color: '#0B0D10', fontSize: 14, fontWeight: 600,
                                cursor: cargando ? 'default' : 'pointer', marginBottom: 20, display: 'flex', alignItems: 'center',
                                justifyContent: 'center', gap: 8, transition: 'opacity .2s', opacity: cargando ? .7 : 1,
                            }}
                            onMouseEnter={(e) => { if (!cargando) e.currentTarget.style.opacity = '.9' }}
                            onMouseLeave={(e) => { if (!cargando) e.currentTarget.style.opacity = '1' }}
                        >
                            {cargando ? 'Entrando...' : 'Entrar'} <span>→</span>
                        </button>
                    </form>

                    <p style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', margin: '0 0 14px' }}>
                        o continua con
                    </p>

                    <div style={{ display: 'flex', gap: 10, marginBottom: 22 }}>
                        <button
                            type="button"
                            aria-label="Continuar con Google"
                            style={{
                                flex: 1, border: '1px solid var(--line)', borderRadius: 10,
                                padding: '11px 0', background: 'transparent', cursor: 'pointer',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                gap: 8, color: 'var(--text-dim)', fontSize: 12,
                                transition: 'border-color .2s',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                            onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--line)')}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24">
                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                            </svg>
                            Google
                        </button>
                        <button
                            type="button"
                            aria-label="Continuar con Facebook"
                            style={{
                                flex: 1, border: '1px solid var(--line)', borderRadius: 10,
                                padding: '11px 0', background: 'transparent', cursor: 'pointer',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                gap: 8, color: 'var(--text-dim)', fontSize: 12,
                                transition: 'border-color .2s',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                            onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--line)')}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="#1877F2">
                                <path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95c5.05-.5 9-4.76 9-9.95z" />
                            </svg>
                            Facebook
                        </button>
                    </div>

                    <p style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', margin: 0 }}>
                        No tienes cuenta?{' '}
                        <span style={{ color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }}>
                            Registrate gratis
                        </span>
                    </p>
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