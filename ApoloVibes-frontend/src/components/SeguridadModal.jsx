import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../services/api.js'
import { Eye, EyeOff, KeyRound, RefreshCw, ShieldCheck } from 'lucide-react'
import Apolovibeslogo from '../../public/media/apolo-vibes-logo.png'

const overlayStyle = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 9999, backdropFilter: 'blur(4px)', padding: 20,
}

const modalStyle = {
    background: 'var(--surface)', borderRadius: 20,
    width: '100%', maxWidth: 520, maxHeight: '90vh', boxShadow: '0 20px 60px rgba(0,0,0,.3)',
    position: 'relative', padding: '28px 32px', overflowY: 'auto', boxSizing: 'border-box',
}

const inputStyle = {
    width: '100%', padding: '11px 14px', borderRadius: 10,
    border: '1px solid var(--line)', background: 'var(--bg)',
    color: 'var(--text)', fontSize: 14, outline: 'none',
    boxSizing: 'border-box',
}

const botonAccion = {
    width: '100%', padding: '13px 0', borderRadius: 10, border: 'none',
    background: 'var(--accent)', color: '#ffffff', fontSize: 14, fontWeight: 600,
    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 8, transition: 'opacity .2s', marginBottom: 10,
}

const botonFlecha = {
    flex: 1, border: '1px solid var(--line)', borderRadius: 10,
    padding: '11px 0', background: 'transparent', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 6, color: 'var(--text-dim)', fontSize: 13, fontWeight: 600,
    transition: 'border-color .2s',
}

const seccionStyle = {
    border: '1px solid var(--line)', borderRadius: 12, padding: '16px 18px', marginBottom: 16, background: 'var(--surface-2)',
}

export default function SeguridadModal({ onClose }) {
    const { user, actualizarUsuario } = useAuth()

    // ---- Cambio de contraseña ----
    const [passForm, setPassForm] = useState({ actual: '', nueva: '', confirmar: '' })
    const [mostrarPass, setMostrarPass] = useState({ actual: false, nueva: false, confirmar: false })
    const [mensajePass, setMensajePass] = useState({ ok: '', error: '' })
    const [cargandoPass, setCargandoPass] = useState(false)

    // ---- MFA ----
    const [pasoMfa, setPasoMfa] = useState('idle') // idle | qr | listo
    const [qrData, setQrData] = useState('')
    const [secreto, setSecreto] = useState('')
    const [codigoMfa, setCodigoMfa] = useState('')
    const [codigosRespaldo, setCodigosRespaldo] = useState([])
    const [mensajeMfa, setMensajeMfa] = useState({ ok: '', error: '' })
    const [cargandoMfa, setCargandoMfa] = useState(false)
    const [passwordDesactivar, setPasswordDesactivar] = useState('')
    const [mostrarPasswordDesactivar, setMostrarPasswordDesactivar] = useState(false)

    const mfaActivo = !!user?.mfa_activo

    const cambiarPassword = async (e) => {
        e.preventDefault()
        setMensajePass({ ok: '', error: '' })
        if (!passForm.actual) return setMensajePass({ ok: '', error: 'Ingresa tu contraseña actual' })
        if (passForm.nueva.length < 8 || passForm.nueva.length > 72)
            return setMensajePass({ ok: '', error: 'La nueva contraseña debe tener entre 8 y 72 caracteres' })
        if (passForm.nueva !== passForm.confirmar)
            return setMensajePass({ ok: '', error: 'Las contraseñas no coinciden' })
        setCargandoPass(true)
        try {
            await api.post('/auth/cambiar-contrasena', {
                password_actual: passForm.actual,
                nueva_password: passForm.nueva,
            })
            setMensajePass({ ok: 'Contraseña actualizada. Se cerraron tus otras sesiones.', error: '' })
            setPassForm({ actual: '', nueva: '', confirmar: '' })
        } catch (err) {
            setMensajePass({ ok: '', error: err.message || 'No se pudo cambiar la contraseña' })
        } finally {
            setCargandoPass(false)
        }
    }

    const iniciarConfiguracionMfa = async () => {
        setCargandoMfa(true)
        setMensajeMfa({ ok: '', error: '' })
        try {
            const data = await api.get('/auth/mfa/configurar')
            setQrData(data.qr_base64 || '')
            setSecreto(data.secreto || '')
            setPasoMfa('qr')
        } catch (err) {
            setMensajeMfa({ ok: '', error: err.message || 'No se pudo iniciar la configuración' })
        } finally {
            setCargandoMfa(false)
        }
    }

    const activarMfa = async () => {
        if (!codigoMfa.trim()) return
        setCargandoMfa(true)
        setMensajeMfa({ ok: '', error: '' })
        try {
            const data = await api.post('/auth/mfa/activar', { codigo: codigoMfa.trim() })
            setCodigosRespaldo(data.codigos_respaldo || [])
            setPasoMfa('listo')
            actualizarUsuario({ ...user, mfa_activo: true })
        } catch (err) {
            setMensajeMfa({ ok: '', error: err.message || 'Código incorrecto' })
        } finally {
            setCargandoMfa(false)
        }
    }

    const regenerarCodigos = async () => {
        setCargandoMfa(true)
        setMensajeMfa({ ok: '', error: '' })
        try {
            const data = await api.post('/auth/mfa/codigos-respaldo')
            setCodigosRespaldo(data.codigos_respaldo || [])
            setPasoMfa('listo')
        } catch (err) {
            setMensajeMfa({ ok: '', error: err.message || 'No se pudieron regenerar los códigos' })
        } finally {
            setCargandoMfa(false)
        }
    }

    const desactivarMfa = async () => {
        if (!passwordDesactivar) return setMensajeMfa({ ok: '', error: 'Ingresa tu contraseña' })
        if (!codigoMfa.trim()) return setMensajeMfa({ ok: '', error: 'Ingresa tu código de autenticación' })
        setCargandoMfa(true)
        setMensajeMfa({ ok: '', error: '' })
        try {
            await api.post('/auth/mfa/desactivar', { password: passwordDesactivar, codigo: codigoMfa.trim() })
            setPasoMfa('idle')
            setCodigoMfa('')
            setPasswordDesactivar('')
            setCodigosRespaldo([])
            actualizarUsuario({ ...user, mfa_activo: false })
        } catch (err) {
            setMensajeMfa({ ok: '', error: err.message || 'No se pudo desactivar MFA' })
        } finally {
            setCargandoMfa(false)
        }
    }

    const togglePass = (campo) => setMostrarPass(prev => ({ ...prev, [campo]: !prev[campo] }))

    const inputPass = (campo, placeholder, icono) => (
        <div style={{ position: 'relative', marginBottom: 6 }}>
            <span style={{
                position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                zIndex: 1, color: 'var(--text-dim)', display: 'flex', pointerEvents: 'none',
            }}>
                {icono}
            </span>
            <input
                autoComplete="new-password"
                type={mostrarPass[campo] ? 'text' : 'password'}
                placeholder={placeholder}
                value={passForm[campo]}
                onChange={(e) => setPassForm(prev => ({ ...prev, [campo]: e.target.value }))}
                style={{ ...inputStyle, paddingLeft: 34, paddingRight: 34 }}
            />
            <button
                type="button"
                onClick={() => togglePass(campo)}
                aria-label={`${mostrarPass[campo] ? 'Ocultar' : 'Mostrar'} contraseña`}
                style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', zIndex: 1,
                    background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 4, display: 'flex',
                }}
            >
                {mostrarPass[campo] ? <Eye size={16} /> : <EyeOff size={16} />}
            </button>
        </div>
    )

    return createPortal(
        <div style={overlayStyle} onClick={onClose}>
            <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
                <button
                    onClick={onClose}
                    aria-label="Cerrar"
                    style={{
                        position: 'absolute', top: 16, right: 18, background: 'none',
                        border: 'none', color: 'var(--text-dim)', fontSize: 20, cursor: 'pointer', zIndex: 2, lineHeight: 1,
                    }}
                >
                    &times;
                </button>

                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 10 }}>
                    <img src={Apolovibeslogo} alt="Logo" style={{ width: 60, height: 60, marginBottom: -10 }} />
                </div>

                <h2 style={{ display: 'flex', justifyContent: 'center', gap: 8, fontSize: 20, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-display)', margin: '0 0 6px' }}>
                    Seguridad
                </h2>
                <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 20px', textAlign: 'center' }}>
                    Protege tu cuenta con autenticación de dos factores y gestiona tu contraseña.
                </p>

                {/* --- Cambio de contraseña --- */}
                <div style={seccionStyle}>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 600, color: 'var(--text)', margin: '0 0 12px' }}>
                        <KeyRound size={16} /> Cambiar contraseña
                    </h3>
                    <form onSubmit={cambiarPassword}>
                        {inputPass('actual', 'Contraseña actual', <KeyRound size={16} />)}
                        {inputPass('nueva', 'Nueva contraseña (8-72 caracteres)', <KeyRound size={16} />)}
                        {inputPass('confirmar', 'Confirmar nueva contraseña', <KeyRound size={16} />)}
                        {mensajePass.error && <p style={{ color: '#ef4444', fontSize: 12, margin: '4px 0 10px' }}>{mensajePass.error}</p>}
                        {mensajePass.ok && <p style={{ color: '#22c55e', fontSize: 12, margin: '4px 0 10px' }}>{mensajePass.ok}</p>}
                        <button
                            type="submit"
                            disabled={cargandoPass}
                            style={{ ...botonAccion, marginBottom: 0, opacity: cargandoPass ? .7 : 1, cursor: cargandoPass ? 'default' : 'pointer' }}
                        >
                            {cargandoPass ? 'Guardando...' : 'Actualizar contraseña'}
                        </button>
                    </form>
                </div>

                {/* --- MFA --- */}
                <div style={seccionStyle}>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 600, color: 'var(--text)', margin: '0 0 4px' }}>
                        <ShieldCheck size={16} /> Autenticación de dos factores
                    </h3>
                    <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 12px' }}>
                        {mfaActivo
                            ? 'Verificación en dos pasos activada. Se requiere el código de tu app en cada inicio de sesión.'
                            : 'Añade una capa extra de seguridad con una app de autenticación (Google Authenticator, etc.).'}
                    </p>

                    {!mfaActivo && pasoMfa === 'idle' && (
                        <button
                            type="button"
                            onClick={iniciarConfiguracionMfa}
                            disabled={cargandoMfa}
                            style={{ ...botonAccion, marginBottom: 0, opacity: cargandoMfa ? .7 : 1, cursor: cargandoMfa ? 'default' : 'pointer' }}
                        >
                            {cargandoMfa ? 'Preparando...' : 'Activar dos factores'}
                        </button>
                    )}

                    {pasoMfa === 'qr' && (
                        <>
                            <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 10px', lineHeight: 1.5 }}>
                                Escanea el código QR con tu app de autenticación. Si no puedes escanearlo,
                                ingresa manualmente el secreto: <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)', wordBreak: 'break-all' }}>{secreto}</strong>
                            </p>
                            {qrData && (
                                <img
                                    src={qrData}
                                    alt="Código QR de autenticación"
                                    style={{ width: 180, height: 180, display: 'block', margin: '0 auto 12px', borderRadius: 8, background: '#fff', padding: 8, boxSizing: 'border-box' }}
                                />
                            )}
                            <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6 }}>
                                Código de la app
                            </label>
                            <input
                                type="text"
                                inputMode="numeric"
                                maxLength={6}
                                placeholder="••••••"
                                value={codigoMfa}
                                onChange={(e) => { setCodigoMfa(e.target.value.replace(/\D/g, '').slice(0, 6)); setMensajeMfa({ ok: '', error: '' }) }}
                                style={{ ...inputStyle, letterSpacing: 6, textAlign: 'center', fontSize: 18, marginBottom: 10 }}
                            />
                            {mensajeMfa.error && <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 10px' }}>{mensajeMfa.error}</p>}
                            <button
                                type="button"
                                onClick={activarMfa}
                                disabled={cargandoMfa || !codigoMfa.trim()}
                                style={{ ...botonAccion, opacity: (cargandoMfa || !codigoMfa.trim()) ? .7 : 1, cursor: (cargandoMfa || !codigoMfa.trim()) ? 'default' : 'pointer' }}
                            >
                                {cargandoMfa ? 'Activando...' : 'Confirmar y activar'}
                            </button>
                        </>
                    )}

                    {pasoMfa === 'listo' && (
                        <>
                            <p style={{ fontSize: 12, color: '#22c55e', margin: '0 0 10px', fontWeight: 600 }}>
                                ✓ {mfaActivo ? 'Autenticación activa' : 'Listo'}
                            </p>
                            <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 10px', lineHeight: 1.5 }}>
                                Guarda estos códigos de respaldo en un lugar seguro. Sirven solo una vez
                                para entrar sin tu app de autenticación.
                            </p>
                            <div style={{
                                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, padding: '10px 12px',
                                background: 'var(--bg)', borderRadius: 8, marginBottom: 12,
                            }}>
                                {codigosRespaldo.map(c => (
                                    <span key={c} style={{
                                        fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text)',
                                        background: 'var(--surface-2)', borderRadius: 6, padding: '6px 8px', textAlign: 'center', margin: 0,
                                    }}>
                                        {c}
                                    </span>
                                ))}
                            </div>
                            <div style={{ display: 'flex', gap: 10 }}>
                                {mfaActivo && (
                                    <button type="button" onClick={regenerarCodigos} disabled={cargandoMfa} style={{ ...botonFlecha, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                        <RefreshCw size={14} /> Regenerar
                                    </button>
                                )}
                                <button
                                    type="button"
                                    onClick={() => { setPasoMfa('idle'); setCodigoMfa(''); }}
                                    style={{ ...botonFlecha, flex: 1 }}
                                >
                                    Cerrar
                                </button>
                            </div>
                        </>
                    )}

                    {mfaActivo && pasoMfa === 'idle' && (
                        <>
                            <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
                                <button type="button" onClick={regenerarCodigos} disabled={cargandoMfa} style={{ ...botonFlecha, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                    <RefreshCw size={14} /> Nuevos códigos
                                </button>
                            </div>
                            <input
                                type="password"
                                placeholder="Contraseña (para confirmar)"
                                value={passwordDesactivar}
                                onChange={(e) => { setPasswordDesactivar(e.target.value); setMensajeMfa({ ok: '', error: '' }) }}
                                style={{ ...inputStyle, marginBottom: 6 }}
                            />
                            <input
                                type="text"
                                inputMode="numeric"
                                maxLength={6}
                                placeholder="Código de tu app"
                                value={codigoMfa}
                                onChange={(e) => { setCodigoMfa(e.target.value.replace(/\D/g, '').slice(0, 6)); setMensajeMfa({ ok: '', error: '' }) }}
                                style={{ ...inputStyle, letterSpacing: 6, textAlign: 'center', fontSize: 18, marginBottom: 10 }}
                            />
                            {mensajeMfa.error && <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 10px' }}>{mensajeMfa.error}</p>}
                            <button
                                type="button"
                                onClick={desactivarMfa}
                                disabled={cargandoMfa}
                                style={{
                                    width: '100%', padding: '11px 0', borderRadius: 10, border: '1px solid #b60303',
                                    background: 'transparent', color: '#b60303', fontSize: 13, fontWeight: 600,
                                    cursor: cargandoMfa ? 'default' : 'pointer', opacity: cargandoMfa ? .7 : 1,
                                }}
                            >
                                {cargandoMfa ? 'Desactivando...' : 'Desactivar dos factores'}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>,
        document.body
    )
}