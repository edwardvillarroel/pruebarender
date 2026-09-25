import { useEffect, useRef, useState } from 'react'

// Site key pública de reCAPTCHA v2 (google.com/recaptcha/admin). Si no está
// configurada (entorno sin credenciales), se muestra un checkbox local porque el
// gateway en modo dev solo exige que el token no venga vacío.
const SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY || ''

const contenedorStyle = {
    display: 'flex', alignItems: 'center', gap: 10, fontSize: 12,
    color: 'var(--text-dim)', margin: '0 0 12px', userSelect: 'none',
}

const checkboxStyle = {
    width: 24, height: 24, borderRadius: 6, border: '1px solid var(--line)',
    background: 'var(--bg)', display: 'flex', alignItems: 'center',
    justifyContent: 'center', cursor: 'pointer', flexShrink: 0,
    color: '#fff', fontSize: 14, transition: 'background .15s, border-color .15s',
}

export default function CaptchaWidget({ token, onToken }) {
    const contRef = useRef(null)
    const widgetIdRef = useRef(null)
    const callbacksRef = useRef({})
    const [verificado, setVerificado] = useState(false)

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

    // Sin site key (dev): checkbox local, envía token "dev" que el gateway acepta
    // cuando RECAPTCHA_SECRET_KEY está vacío.
    if (!SITE_KEY) {
        return (
            <div style={contenedorStyle}>
                <div
                    role="checkbox"
                    aria-checked={!!token}
                    tabIndex={0}
                    onClick={() => onToken(token ? '' : 'dev-no-key')}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onToken(token ? '' : 'dev-no-key') }}
                    style={{ ...checkboxStyle, background: token ? '#22c55e' : 'var(--bg)', borderColor: token ? '#22c55e' : 'var(--line)' }}
                >
                    {token ? '✓' : ''}
                </div>
                <span>No soy un robot</span>
                <svg width="22" height="22" viewBox="0 0 48 48" aria-hidden="true" style={{ marginLeft: 'auto', opacity: .7 }}>
                    <path fill="#FFD500" d="M24 4 4 12v12c0 9.9 8.6 18 20 20s20-10.1 20-20V12L24 4z" />
                    <path fill="#FF8F00" d="M24 6.6 6 13.6v10.4c0 8.5 7.4 15.5 18 17.4 10.6-1.9 18-8.9 18-17.4V13.6L24 6.6z" />
                    <path fill="#fff" d="M22 34.5l-8-8 2.2-2.2 5.8 5.7 9.8-9.8 2.2 2.3-12 12z" />
                    <path fill="#1e3a5f" d="M24 4L4 12v12c0 9.9 8.6 18 20 20v-4C13.9 38.9 8 31.6 8 24V14l16-6.4 16 6.4v10c0 2.1-.4 4.1-1.1 6l3.1.8v-10.8L24 4z" opacity=".05" />
                </svg>
            </div>
        )
    }

    return (
        <div style={{ margin: '0 0 12px' }}>
            <div ref={contRef}></div>
            {!verificado && !token && (
                <p style={{ fontSize: 11, color: 'var(--text-dim)', margin: '4px 0 0' }}>
                    Marca la verificación de seguridad para continuar.
                </p>
            )}
        </div>
    )
}