import { Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { useTheme } from '../context/ThemeContext.jsx'

export default function HeroEstatico() {
  const { theme } = useTheme()
  const oscuro = theme === 'dark'

  return (
    <section
      className="hero-section"
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '480px',
        overflow: 'hidden',
        aspectRatio: '1536 / 900',
        display: 'flex',
        alignItems: 'flex-start',
        marginBottom: -40
      }}
    >
      <img
        src={mediaPath('apolohero2.png')}
        alt=""
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: 'left center',
        }}
        fetchpriority="high"
      />

      {oscuro && (
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(21,24,29,.6)' }} />
      )}

      <div
        className="wrap hero-content">
          <div className="hero-buttons" style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <Link
              to="/categorias"
              className="btn btn-primary"
              style={{
                background: '#ff6d05',
                color: '#fff',
                padding: '14px 28px',
                borderRadius: 8,
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              Explorar catálogo
            </Link>
            <Link
              to="/cotizar"
              className="btn btn-ghost"
              style={{
                border: oscuro ? '1.5px solid rgba(237,237,229,.5)' : '1.5px solid #1E3A5F',
                color: oscuro ? '#EDEDE5' : '#1E3A5F',
                padding: '14px 28px',
                borderRadius: 8,
                fontWeight: 600,
                textDecoration: 'none',
                background: oscuro ? 'transparent' : 'rgba(255,255,255,.6)',
              }}
            >
              Cotizar tu producto
            </Link>
          </div>
        </div>
    </section>
  )
}