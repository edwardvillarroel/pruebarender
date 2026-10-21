import { Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { useTheme } from '../context/ThemeContext.jsx'

export default function HeroEstatico() {
  const { theme } = useTheme()
  const oscuro = theme === 'dark'

  return (
    <section className="hero-section">
      <div className="hero-media">
        <img
          src={mediaPath('apolohero2.png')}
          alt=""
          aria-hidden="true"
          fetchpriority="high"
        />
        {oscuro && <div className="hero-overlay" />}
      </div>


      <div className="wrap hero-content">
        <div className="hero-buttons">
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