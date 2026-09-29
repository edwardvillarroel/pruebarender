
import { useEffect, useRef, useState } from 'react'


const SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY || ''

const contenedorStyle = {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%',
    maxWidth: 304, height: 80, BoxSizing: 'border-box', margin: '12px auto', padding: '0 12px',
    color: 'var(--text)', background: 'var(--bg-card)', border: '1px solid var(--line)', borderRadius: 4,
    boxShadow: '0 0 4px rgba(0,0,0,0.8)', fontSize: 14, userSelect: 'none',
}

const checkboxStyle = {
    width: 28, height: 28, boxSizing: 'border-box', borderRadius: 3, border: '2px solid #c1c1c1',
    background: 'var(--bg)', display: 'flex', alignItems: 'center',
    justifyContent: 'center', cursor: 'pointer', flexShrink: 0,
    color: '#fff', fontSize: 14, transition: 'background .15s, border-color .15s',
}

export default function CaptchaWidget({ token, onToken }) {
    const contRef = useRef(null)
    const widgetIdRef = useRef(null)
    const callbacksRef = useRef({})
    const [verificado, setVerificado] = useState(false)
    const [oculto, setOculto] = useState(false)
    const [verificandoDev, setVerificandoDev] = useState(false)
    const timerDevRef = useRef(null)

    useEffect(() => () => clearTimeout(timerDevRef.current), [])

    const verificarDev = () => {
        if (verificandoDev || token) return
        setVerificandoDev(true)
        timerDevRef.current = setTimeout(() => {
            setVerificandoDev(false)
            onToken('dev-no-key')
        }, 900)
    }

    useEffect(() => {
        if (!token){
            setOculto(false)
            return
        }
        const t = setTimeout(() => setOculto(true), 800)
        return () => clearTimeout(t)
    }, [token])

    useEffect(() => {
        if (!token && verificado) {
            setVerificado(false)
            if (widgetIdRef.current !== null && window.grecaptcha?.reset) {
                window.grecaptcha.reset(widgetIdRef.current)
            }
        }
    }, [token, verificado])

    useEffect(() => {
        if (!SITE_KEY || !contRef.current) return

        const nombreCallback = `recaptchaOnload_${Date.now()}`
        callbacksRef.current[nombreCallback] = () => {
            widgetIdRef.current = window.grecaptcha.render(contRef.current, {
                sitekey: SITE_KEY,
                theme: document.body.dataset.theme || 'light',
                callback: (t) => {
                    setVerificado(true)
                    onToken(t)
                },
                'expired-callback': () => {
                    setVerificado(false)
                    onToken('')
                },
            })
        }

        if (window.grecaptcha && window.grecaptcha.render) {
            widgetIdRef.current = window.grecaptcha.render(contRef.current, {
                sitekey: SITE_KEY,
                theme: document.body.dataset.theme || 'light',
                callback: (t) => {
                    setVerificado(true)
                    onToken(t)
                },
                'expired-callback': () => {
                    setVerificado(false)
                    onToken('')
                },
            })
        } else {
            window[nombreCallback] = callbacksRef.current[nombreCallback]
            const script = document.createElement('script')
            script.src = `https://www.google.com/recaptcha/api.js?onload=${nombreCallback}&render=explicit`
            script.async = true
            script.defer = true
            document.head.appendChild(script)
        }

        return () => {
            if (window[nombreCallback]) delete window[nombreCallback]
        }
    }, [onToken])

    if (!SITE_KEY) {
        if (oculto) return null
        return (
            <div style={contenedorStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div
                        role="checkbox"
                        aria-checked={!!token}
                        tabIndex={0}
                        onClick={verificarDev}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); alternar(); } }}
                        style={{ ...checkboxStyle, cursor: verificandoDev || token ? 'default' : 'pointer', ...(verificandoDev || token ? { borderColor: 'transparent', background: 'transparent' } : {}) }}
                    >
                        {verificandoDev && (
                            <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true">
                            <circle
                                cx="12" cy="12" r="9" fill="none" stroke="#4a90e2"
                                strokeWidth="3" strokeDasharray="42 60" strokeLinecap="round"
                            >
                                <animateTransform
                                    attributeName="transform" type="rotate"
                                    from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite"
                                />
                            </circle>
                        </svg>
                        )}

                        {token && (
                            <svg with="28" height="28" viewBox="0 0 24 24" aria-hidden="true">
                                <path
                                    d="M4 12.5l5 5L20 6.5"
                                    fill="none" stroke="#22c55e" strokeWidth="3"
                                    strokeLinecap="round" strokeLinejoin="round"
                                />
                            </svg>
                        )}
                    </div>
                    <span style={{ fontWeight: 500 }}>No soy un robot</span>
                </div>

                <div style={{ textAlign: 'center', lineHeight: 1.2, opacity: .75 }}>
                    <svg width="30" height="30" viewBox="0 0 48 48" aria-hidden="true">
                        <path fill="#4a90e2" d="M24 4 6 11v13c0 9 7.6 16.4 18 19 10.4-2.6 18-10 18-19V11L24 4z" />
                        <path fill="#fff" d="M22 32l-7-7 2.2-2.2 4.8 4.8 8.8-8.8 2.2 2.2L22 32z" />
                    </svg>
                    <div style={{ fontSize: 9, marginTop: 2 }}>Verificación</div>
                    <div style={{ fontSize: 8 }}>Privacidad · Términos</div>
                </div>
            </div>
        )
    }

    return (
        <div style={{ margin: '0 0 12px', display: token ? 'none' : 'block' }}>
            <div ref={contRef}></div>
            {!verificado && !oculto && (
                <p style={{ fontSize: 11, color: 'var(--text-dim)', margin: '4px 0 0' }}>
                    Marca la verificación de seguridad para continuar.
                </p>
            )}
        </div>
    )
}