import { Link, useNavigate } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { useState, useEffect, useRef } from 'react'
import { useCart } from '../context/CartContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import { ShoppingCart, Menu, X, User, LayoutDashboard, LogOut, Home, Moon, Sun } from 'lucide-react'
import LoginModal from './LoginModal.jsx'

export default function Navbar() {
  const { cantidadTotal } = useCart()
  const { isLoggedIn, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [scrolled, setScrolled] = useState(false)
  const [showLogin, setShowLogin] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    const alScrollear = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', alScrollear)
    return () => window.removeEventListener('scroll', alScrollear)
  }, [])

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [mobileOpen])

  // Close user menu on click outside
  useEffect(() => {
    if (!userMenuOpen) return
    function handleClick(e) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [userMenuOpen])

  function handleMobileNav(path) {
    setMobileOpen(false)
    navigate(path)
  }

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: scrolled ? 'rgba(250,127,25,.55)' : 'rgba(250,127,25,1)',
        backdropFilter: scrolled ? 'blur(10px)' : 'none',
        borderBottom: '1px solid rgba(30,58,95,.15)',
        transition: 'background .3s ease, backdrop-filter .3s ease'
      }}
    >
<div
          className="wrap"
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto 1fr',
            alignItems: 'center',
            padding: '18px 32px',
            maxWidth: '100%',
            color: '#FBF7EE'
          }}
        >
          {/* LOGO */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 18, color: '#FBF7EE' }}>
            <Home size={20} />
            Apolo Vibes 3D
          </Link>

        {/* Desktop nav */}
        <nav className="nav-links hide-mobile">
          <Link to="/categorias">Categorías</Link>
          <Link to="/cotizar">Cotiza tu producto</Link>
          <Link to="/">Nosotros</Link>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, justifyContent: 'flex-end' }}>
          <button
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
            title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
            style={{
              width: 34, height: 34, borderRadius: '50%',
              border: '1.5px solid rgba(251,247,238,.3)',
              background: 'rgba(251,247,238,.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: '#FBF7EE',
              transition: 'border-color .2s, background .2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(251,247,238,.6)'; e.currentTarget.style.background = 'rgba(251,247,238,.15)' }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(251,247,238,.3)'; e.currentTarget.style.background = 'rgba(251,247,238,.1)' }}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <Link to="/carrito" className="cart-icon" aria-label="Carrito" style={{ color: '#FBF7EE' }}>
            <ShoppingCart size={24} />
            {cantidadTotal > 0 && (
              <span className="cart-badge">{cantidadTotal}</span>
            )}
          </Link>

          {/* Desktop auth */}
          <div className="hide-mobile" style={{ position: 'relative' }} ref={userMenuRef}>
            <button
              onClick={() => isLoggedIn ? setUserMenuOpen(v => !v) : setShowLogin(true)}
              aria-label="Mi cuenta"
              style={{
                width: 34, height: 34, borderRadius: '50%',
                border: '1.5px solid rgba(251,247,238,.3)',
                background: 'rgba(251,247,238,.1)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: '#FBF7EE',
                transition: 'border-color .2s, background .2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(251,247,238,.6)'; e.currentTarget.style.background = 'rgba(251,247,238,.15)' }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(251,247,238,.3)'; e.currentTarget.style.background = 'rgba(251,247,238,.1)' }}
            >
              <User size={18} />
            </button>

            {/* Dropdown */}
            {userMenuOpen && isLoggedIn && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 8px)', right: 0,
                background: 'var(--surface)',
                border: '1px solid var(--line)',
                borderRadius: 12,
                minWidth: 200,
                boxShadow: '0 12px 40px rgba(0,0,0,.35)',
                overflow: 'hidden',
                zIndex: 200,
              }}>
                <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--line)' }}>
                  <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>Sesión activa</p>
                </div>
                <button
                  onClick={() => { setUserMenuOpen(false); navigate('/admin') }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                    padding: '12px 16px', border: 'none', background: 'none',
                    color: 'var(--text)', fontSize: 13, cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background .15s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--accent-soft)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                >
                  <LayoutDashboard size={16} color="var(--accent)" />
                  Panel admin
                </button>
                <button
                  onClick={() => { setUserMenuOpen(false); logout(); navigate('/') }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                    padding: '12px 16px', border: 'none', background: 'none',
                    color: '#ef4444', fontSize: 13, cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background .15s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(239,68,68,.08)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                >
                  <LogOut size={16} />
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>

          {/* Hamburger */}
          <button
            className="hamburger"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
          >
            <Menu size={24} />
          </button>
        </div>
      </div>

      {/* Mobile menu overlay */}
      <div
        className={`nav-mobile-overlay ${mobileOpen ? 'open' : ''}`}
        onClick={() => setMobileOpen(false)}
      >
        <div className="nav-mobile-menu" onClick={e => e.stopPropagation()}>
          <div className="close-btn">
            <button onClick={() => setMobileOpen(false)} aria-label="Cerrar menú">
              <X size={24} />
            </button>
          </div>
          <button onClick={() => handleMobileNav('/')}>Inicio</button>
          <button onClick={() => handleMobileNav('/categorias')}>Categorías</button>
          <button onClick={() => handleMobileNav('/cotizar')}>Cotiza tu producto</button>
          <button onClick={() => handleMobileNav('/carrito')}>Carrito ({cantidadTotal})</button>
          {isLoggedIn ? (
            <>
              <button onClick={() => handleMobileNav('/admin')}>Panel admin</button>
              <button onClick={() => { logout(); setMobileOpen(false); navigate('/') }} style={{ color: '#ef4444' }}>
                Cerrar sesión
              </button>
            </>
          ) : (
            <button onClick={() => { setMobileOpen(false); setShowLogin(true) }}>
              Iniciar sesión
            </button>
          )}
          <button onClick={toggleTheme} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {theme === 'dark' ? <><Sun size={16} /> Modo claro</> : <><Moon size={16} /> Modo oscuro</>}
          </button>
        </div>
      </div>

      {showLogin && (
        <LoginModal onClose={() => setShowLogin(false)} />
      )}
    </header>
  )
}
