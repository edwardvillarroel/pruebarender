import { createPortal } from 'react-dom'
import { mediaPath } from '../utils/media.js'
import { useBloqueoScroll } from '../hooks/useBloqueoScroll.js'

const overlayStyle = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
    backdropFilter: 'blur(4px)', zIndex: 10000,
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
}

const cardStyle = {
    background: 'var(--surface)', border: '1px solid var(--line)',
    borderRadius: 20, maxWidth: 430, width: '100%', padding: '28px 26px',
    textAlign: 'center', color: 'var(--text)',
    boxShadow: '0 24px 60px rgba(0,0,0,.45)',
}

export default function AvisoMfaModal({ onActivar, onCerrar }) {
    useBloqueoScroll()

    return createPortal(
        <div style={overlayStyle} onClick={onCerrar}>
            <div style={cardStyle} onClick={(e) => e.stopPropagation()}>
                <img
                    src={mediaPath('ApoloSeguridad.webp')}
                    alt="Seguridad ApoloVibes"
                    style={{ width: 108, height: 'auto', display: 'block', margin: '0 auto 6px' }}
                />

                <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '14px 0 10px' }}>
                    Protege tu cuenta de administrador
                </h2>

                <p style={{
                    color: 'var(--text-dim)', fontSize: '.9rem',
                    lineHeight: 1.55, margin: '0 0 22px',
                }}>
                    Tu cuenta todavía no tiene la verificación en dos pasos. Si alguien consigue tu
                    contraseña podría entrar al panel y ver pedidos, ventas y datos de tus clientes.
                    Activarla te toma menos de un minuto con Google Authenticator o Authy.
                </p>

                <button
                    type="button"
                    onClick={onActivar}
                    style={{
                        width: '100%', background: '#FA7F19', color: '#ffffff',
                        fontWeight: 700, borderRadius: 10, padding: '12px 16px',
                        border: 'none', cursor: 'pointer', fontSize: 14, marginBottom: 15
                    }}
                >
                    Activar verificación en dos pasos
                </button>

                <button
                    type="button"
                    onClick={onCerrar}
                    style={{
                        width: '100%', background: 'transparent', color: 'var(--text-dim)',
                        border: 'none', padding: 10, cursor: 'pointer', fontSize: 13,
                    }}
                >
                    Más tarde
                </button>
            </div>
        </div>,
        document.body
    )
}
