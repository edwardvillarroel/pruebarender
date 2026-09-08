import { useState } from 'react'
import { Link } from 'react-router-dom'
import LegalModal from './LegalModal.jsx'

const ICONOS_SOCIALES = [
  {
    nombre: 'Instagram',
    href: 'https://instagram.com/3d.apolovibes',
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="2" y="2" width="20" height="20" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    nombre: 'TikTok',
    href: '',
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M16.6 5.82s.51.5 0 0A4.278 4.278 0 0 1 15.54 3h-3.09v12.4a2.592 2.592 0 0 1-2.59 2.5c-1.42 0-2.6-1.16-2.6-2.6 0-1.72 1.66-3.01 3.37-2.48V9.66c-3.45-.46-6.47 2.22-6.47 5.64 0 3.33 2.76 5.7 5.69 5.7 3.14 0 5.69-2.55 5.69-5.7V9.01a7.35 7.35 0 0 0 4.32 1.39V7.31s-1.88.09-3.26-1.49z" />
      </svg>
    ),
  },
  {
    nombre: 'Facebook',
    href: '',
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95c5.05-.5 9-4.76 9-9.95z" />
      </svg>
    ),
  },
]

const ENLACES_TIENDA = [
  { nombre: 'Figuras de Colección', href: '/categorias?cat=figuras' },
  { nombre: 'Impresoras de resina', href: '/categorias?cat=impresoras-resina' },
  { nombre: 'Filamentos', href: '/categorias?cat=filamentos' },
  { nombre: 'Resinas', href: '/categorias?cat=resinas' },
  { nombre: 'Piezas y repuestos', href: '/categorias?cat=repuestos' },
]

const ENLACES_EMPRESA = [
  { nombre: 'Nosotros', href: '/' },
  { nombre: 'Cotiza tu producto', href: '/cotizar' },
]

const LINK_BUTTON_STYLE = {
  fontSize: 13, color: 'var(--text-dim)', background: 'none',
  border: 'none', padding: 0, cursor: 'pointer', textAlign: 'left',
  fontFamily: 'inherit',
}

export default function Footer() {
  const [modalAbierto, setModalAbierto] = useState(null)

  return (
    <>
      <footer style={{ background: 'var(--surface)', marginTop: 60 }}>
        <div className="wrap" style={{ padding: '56px 0 24px' }}>
          <div
            className="footer-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: '1.4fr 1fr 1fr 1fr',
              gap: 32,
              paddingBottom: 32,
              borderBottom: '1px solid var(--line)',
            }}
          >
            <div>
              <p
                style={{
                  fontFamily: 'var(--font-display)',
                  fontWeight: 700,
                  fontSize: 16,
                  color: 'var(--accent)',
                  marginBottom: 10,
                }}
              >
                Apolo Vibes 3D
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 16, maxWidth: 220 }}>
                De nuestro stock o hecho a tu medida: tu idea, con la energía de Apolo Vibes.
              </p>

              <p
                style={{
                  fontSize: 11,
                  fontWeight: 500,
                  color: 'var(--text-dim)',
                  letterSpacing: '.04em',
                  textTransform: 'uppercase',
                  marginBottom: 8,
                }}
              >
                Síguenos
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                {ICONOS_SOCIALES.map((red) => (
                  <a
                    key={red.nombre}
                    href={red.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={red.nombre}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      background: 'var(--surface-2)',
                      border: '1px solid var(--line)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--accent)',
                      transition: 'border-color .2s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--line)')}
                  >
                    {red.svg}
                  </a>
                ))}
              </div>
            </div>


            <div>
              <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)', marginBottom: 12 }}>Tienda</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                {ENLACES_TIENDA.map((e) => (
                  <Link key={e.nombre} to={e.href} style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                    {e.nombre}
                  </Link>
                ))}
              </div>
            </div>

            <div>
              <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)', marginBottom: 12 }}>Empresa</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                {ENLACES_EMPRESA.map((e) => (
                  <Link key={e.nombre} to={e.href} style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                    {e.nombre}
                  </Link>
                ))}
                <button onClick={() => setModalAbierto('terminos')} style={LINK_BUTTON_STYLE}>
                  Términos y condiciones
                </button>
                <button onClick={() => setModalAbierto('privacidad')} style={LINK_BUTTON_STYLE}>
                  Política de privacidad
                </button>
              </div>
            </div>

            <div>
              <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)', marginBottom: 12 }}>Contacto</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9, fontSize: 13, color: 'var(--text-dim)' }}>
                <span>correo@gmail.com</span>
                <span>+569xxxxxxxx</span>
                <span>Viña del Mar, Chile</span>
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingTop: 20,
              fontSize: 12,
              color: 'var(--text-dim)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span>©2025 ApoloVibes3D</span>
            <span>Impulsando la creatividad con cada impresión</span>
          </div>
        </div>
      </footer>

      <LegalModal tipo={modalAbierto} onClose={() => setModalAbierto(null)} />
    </>
  )
}
