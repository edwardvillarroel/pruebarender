import { mediaPath } from '../utils/media.js'

export default function ConfirmModal({
  onConfirm,
  onCancel,
  mensaje,
  titulo = 'Cerrar sesión',
  textoCancelar = 'No, quedarme',
  textoConfirmar = 'Sí, salir',
  confirmarPeligro = true,
  mostrarLogo = true,
}) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)',
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
          width: '100%', maxWidth: 360, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'center',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontSize: 36, marginBottom: 12 }}></div>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 10 }}>
          {mostrarLogo && (
            <img src={mediaPath('apolo-vibes-logo.png')} alt="Logo" style={{ width: 60, height: 60 }} />
          )}
        </div>
        <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
          {titulo}
        </h3>
        <p style={{ margin: '0 0 22px', fontSize: 13, color: 'var(--text-dim)' }}>
          {mensaje}
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: '1px solid var(--line)',
              background: 'transparent', color: 'var(--text)', fontSize: 13, fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {textoCancelar}
          </button>
          <button
            onClick={onConfirm}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10,
              border: confirmarPeligro ? 'none' : '1px solid var(--line)',
              background: confirmarPeligro ? '#b60303' : 'var(--surface-3)',
              color: confirmarPeligro ? '#fff' : 'var(--text)',
              fontSize: 13, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  )
}
