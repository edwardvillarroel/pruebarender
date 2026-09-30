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
        src={mediaPath('apolohero.png')}
        alt=""
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          // 'center' dejaba que el recorte horizontal metiera el logo de la imagen
          // debajo del texto en pantallas angostas. Anclando a la izquierda se
          // conserva la mitad vacia de la imagen, que es donde vive el texto.
          // A >=900px el recorte horizontal es 0, asi que este valor es un no-op
          // en escritorio: no cambia la imagen que se ve en pantalla completa.
          objectPosition: 'left center',
        }}
        fetchpriority="high"
      />

      {oscuro && (
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(21,24,29,.6)' }} />
      )}

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

        <div className="hero-texto" style={{ maxWidth: 460 }}>
          <span
            className="hero-eyebrow"
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
              color: oscuro ? '#EDEDE5' : '#1E3A5F',
            }}
          >
            Impulsando <span style={{ color: '#E8863E' }}>la creatividad</span>, con cada impresión.
          </h1>
          <p style={{ fontSize: 16, color: oscuro ? 'rgba(237,237,229,.85)' : '#4A5A6A', marginBottom: 30, lineHeight: 1.55 }}>
            De nuestro stock o hecho a tu medida: tu idea, con la energía de Apolo Vibes.
          </p>
          {/* El marginTop que baja los botones vive en el media query de ≤1024px:
              en pantalla completa los botones van pegados al párrafo como antes. */}
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
      </div>
    </section>
  )
}