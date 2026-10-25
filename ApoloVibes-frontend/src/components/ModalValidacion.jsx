import { createPortal } from 'react-dom'
import { Check } from 'lucide-react'
import { useTheme } from '../context/ThemeContext.jsx'
import { mediaPath } from '../utils/media.js'

const PASOS = [
  'Tipo de archivo verificado',
  'Estructura de imagen válida',
  'Buscando contenido incrustado',
  'Limpiando metadatos',
]


function estadoPaso(i, percent, completado) {
  if (completado) return 'ok'
  const inicio = (i / PASOS.length) * 100
  const fin = ((i + 1) / PASOS.length) * 100
  if (percent >= fin) return 'ok'
  if (percent >= inicio) return 'run'
  return 'wait'
}

function PuntoPaso({ estado }) {
  const base = {
    width: 20, height: 20, borderRadius: '50%', flexShrink: 0, boxSizing: 'border-box',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  }
  if (estado === 'ok') {
    return (
      <span style={{ ...base, background: '#22c55e', color: '#fff' }}>
        <Check size={12} strokeWidth={3.5} aria-hidden="true" />
      </span>
    )
  }
  if (estado === 'run') {
    return (
      <span
        className="vs-run"
        style={{ ...base, border: '2px solid var(--line)', borderTopColor: 'var(--accent)' }}
      />
    )
  }
  return <span style={{ ...base, border: '2px solid var(--line)' }} />
}


export default function ModalValidacion({ percent = 0, completado = false }) {
  const { theme } = useTheme()
  const esOscuro = theme === 'dark'
  const tinta = esOscuro ? 'var(--text)' : 'var(--text)'
  const valor = completado ? 100 : Math.max(0, Math.min(100, Math.round(percent)))

  return createPortal(
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 10000, padding: 20,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="vs-titulo"
        style={{
          width: '100%', maxWidth: 380, boxSizing: 'border-box',
          background: 'var(--surface)',
          borderRadius: 16, padding: '32px 28px 28px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, .5)', textAlign: 'center',
          border: '1px solid var(--line)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 12 }}>
          <img 
            src={completado ? mediaPath('logoExitoCompra.webp') : mediaPath('Seguridad.webp')} 
            alt={completado ? 'Imagen segura' : 'Validación de seguridad'} 
            style={{ width: 100, height: 100, objectFit: 'contain' }} 
          />
        </div>

      <h3 id="vs-titulo" style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: tinta }}>
        {completado ? 'Imagen segura' : 'Validación de seguridad'}
      </h3>
        <p style={{ margin: '0 0 24px', fontSize: 13, lineHeight: 1.5, color: 'var(--text-dim)' }}>
          Analizando imagen para detectar contenido malicioso
        </p>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: tinta }}>
            {completado ? 'Completado' : 'Analizando'}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600, color: tinta }}>
            {valor}%
          </span>
        </div>

        <div
          role="progressbar"
          aria-label="Progreso del análisis"
          aria-valuenow={valor}
          aria-valuemin={0}
          aria-valuemax={100}
          style={{ height: 8, borderRadius: 4, background: 'rgba(255,255,255,.08)', overflow: 'hidden', marginBottom: 24 }}
        >
          <div
            style={{
              width: `${valor}%`, height: '100%', borderRadius: 4,
              background: completado ? '#22c55e' : 'var(--accent)',
              transition: 'width .3s ease',
            }}
          />
        </div>

        <ul
          style={{
            listStyle: 'none', margin: 0, padding: '18px 20px', textAlign: 'left',
            display: 'flex', flexDirection: 'column', gap: 12,
            background: 'transparent', border: '1px solid var(--line)', borderRadius: 12,
          }}
        >
          {PASOS.map((texto, i) => {
            const estado = estadoPaso(i, valor, completado)
            return (
              <li
                key={texto}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12, fontSize: 14,
                  color: estado === 'wait' ? 'var(--text-dim)' : tinta,
                  fontWeight: estado === 'run' ? 600 : 400,
                }}
              >
                <PuntoPaso estado={estado} />
                <span>{texto}</span>
              </li>
            )
          })}
        </ul>

        <p style={{ margin: '20px 0 0', fontSize: 12, color: 'var(--text-dim)' }}>
          {completado ? 'Todo listo. Continuamos con tu modelo 3D.' : 'Esto toma unos segundos. No cierres esta ventana.'}
        </p>
      </div>
    </div>,
    document.body
  )
}