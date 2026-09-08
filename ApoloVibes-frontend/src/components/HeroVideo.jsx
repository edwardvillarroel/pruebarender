import { Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'

export default function HeroEstatico() {
  return (
    <section
      className="hero-section"
      style={{
        position: 'relative',
        minHeight: '620px',
        overflow: 'hidden',
        aspectRatio: '1536 / 1024',
        display: 'flex',
        alignItems: 'flex-start',
      }}
    >
      <img
        src={mediaPath('apolohero.png')}
        alt=""
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: 'center',
        }}
        fetchpriority="high"
      />

      <div
        className="wrap hero-content"
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: 1180,
          margin: '0 auto',
          padding: '90px 40px 0',
        }}
      >

        <div style={{ maxWidth: 460 }}>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              color: '#E8863E',
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              marginBottom: 16,
              display: 'block',
              fontWeight: 600,
            }}
          >
            Apolo Vibes · Impresión 3D
          </span>
          <h1
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 46,
              lineHeight: 1.12,
              letterSpacing: '-.02em',
              fontWeight: 700,
              marginBottom: 20,
              color: '#1E3A5F',
            }}
          >
            Impulsando <span style={{ color: '#E8863E' }}>la creatividad</span>, con cada impresión.
          </h1>
          <p style={{ fontSize: 16, color: '#4A5A6A', marginBottom: 30, lineHeight: 1.55 }}>
            De nuestro stock o hecho a tu medida: tu idea, con la energía de Apolo Vibes.
          </p>
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
              Explorar catálogo →
            </Link>
            <Link
              to="/cotizar"
              className="btn btn-ghost"
              style={{
                border: '1.5px solid #1E3A5F',
                color: '#1E3A5F',
                padding: '14px 28px',
                borderRadius: 8,
                fontWeight: 600,
                textDecoration: 'none',
                background: 'rgba(255,255,255,.6)',
              }}
            >
              Cotizar tu producto
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}