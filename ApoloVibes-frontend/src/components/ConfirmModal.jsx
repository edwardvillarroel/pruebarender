import { mediaPath } from '../utils/media.js'
import { useState } from 'react'

export default function ConfirmModal({
  onConfirm,
  onCancel,
  mensaje,
  titulo = 'Cerrar sesión',
  textoCancelar = 'No, quedarme',
  textoConfirmar = 'Sí, salir',
  textoCargando = 'Saliendo...',
  confirmarPeligro = true,
  colorConfirmar = null,
  colorTextoConfirmar = '#fff',
  mostrarLogo = true,
}) {

  const [cargando, setCargando] = useState(false)

  async function confirmar() {
    if (cargando) return
    setCargando(true)
    try {
      await onConfirm()
    } finally {
      setCargando(false)
    }
  }

  function cancelar(){
    if (cargando) return
    onCancel()
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)',
      }}
      onClick={cancelar}
    >
      <div
        style={{
          background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
          width: '100%', maxWidth: 360, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'center',
        }}
        onClick={(e) => e.stopPropagation()}
      >
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
            onClick={cancelar}
            disabled={cargando}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: '1px solid var(--line)',
              background: 'transparent', color: 'var(--text)', fontSize: 13, fontWeight: 500,
              cursor: cargando ? 'not-allowed' : 'pointer',
              opacity: cargando ? 0.5 : 1,
            }}
          >
            {textoCancelar}
          </button>
          <button
            onClick={confirmar}
            disabled={cargando}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10,
              border: confirmarPeligro || colorConfirmar ? 'none' : '1px solid var(--line)',
              background: colorConfirmar ?? (confirmarPeligro ? '#b60303' : 'var(--surface-3)'),
              color: colorConfirmar ? colorTextoConfirmar : (confirmarPeligro ? '#fff' : 'var(--text)'),
              fontSize: 13, fontWeight: 600,
              cursor: cargando ? 'not-allowed' : 'pointer',
              opacity: cargando ? 0.7 : 1
            }}
          >
            {cargando ? textoCargando : textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  )
}
