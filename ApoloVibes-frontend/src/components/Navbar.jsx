import { createPortal } from 'react-dom'
import { Link, useNavigate } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { useCart } from '../context/CartContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import { mediaPath } from '../utils/media.js'
import { ShoppingCart, Menu, X, User, LayoutDashboard, LogOut, Moon, Sun, CircleCheck, ClipboardList, Minus, Plus, Trash2, ShieldCheck, Calculator, ChevronRight } from 'lucide-react'
import { useProductos } from '../context/ProductContext.jsx'
import LoginModal from './LoginModal.jsx'
import SeguridadModal from './SeguridadModal.jsx'
import ConfirmModal from './ConfirmModal.jsx'

export default function Navbar() {
  const { items, cantidadTotal, solicitarLogin, abrirLogin, cerrarLogin, quitarItem, actualizarCantidadItem, total, requiereLogin } = useCart()
  const { isLoggedIn, isAdmin, logout, user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [cartOpen, setCartOpen] = useState(false)
  const [seguridadOpen, setSeguridadOpen] = useState(false)
  const [confirmarLogout, setConfirmarLogout] = useState(false)
  const userMenuRef = useRef(null)
  const cartMenuRef = useRef(null)
  const navigate = useNavigate()
  const { categorias } = useProductos()

  useEffect(() => {
    const alScrollear = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', alScrollear)
    return () => window.removeEventListener('scroll', alScrollear)
  }, [])

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [mobileOpen])

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

  useEffect(() => {
    if (!cartOpen) return
    function handleClick(e) {
      if (cartMenuRef.current && !cartMenuRef.current.contains(e.target)) {
        setCartOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [cartOpen])

  useEffect(() => {
    const abrirGoogleMfa = () => abrirLogin()
    window.addEventListener('apolovibes:google-mfa', abrirGoogleMfa)
    return () => window.removeEventListener('apolovibes:google-mfa', abrirGoogleMfa)
  }, [abrirLogin])

  function handleMobileNav(path) {
    setMobileOpen(false)
    navigate(path)
  }

  function handlePedirLogout(cerrarMenu) {
    cerrarMenu()
    setConfirmarLogout(true)
  }

  async function handleLogout() {
    try {
      await logout()
    } finally {
      setConfirmarLogout(false)
      navigate('/')
    }
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            className="hamburger"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
          >
            <Menu size={24} />
          </button>

          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 18, color: '#FBF7EE' }}>
            <img src={mediaPath('nombrelogo2.png')} alt="Logo" style={{ height: 50, width: 'auto' }} />
          </Link>
        </div>
        {/* Desktop nav */}
        <nav className="nav-links hide-mobile">
          <Link to="/categorias">Catálogo</Link>
          <Link to="/cotizar">Cotiza tu producto</Link>
          <Link to="/">Nosotros</Link>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, justifyContent: 'flex-end' }}>
          <button
            className="theme-toggle"
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

          {/* Desktop auth */}
          <div style={{ position: 'relative' }} ref={userMenuRef}>
            <button
              onClick={() => isLoggedIn ? setUserMenuOpen(v => !v) : abrirLogin()}
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
                background: 'rgba(250,127,25,1)',
                border: '1px solid var(--line)',
                borderRadius: 12,
                minWidth: 200,
                boxShadow: '0 12px 40px rgba(0, 0, 0, 0.55)',
                overflow: 'hidden',
                zIndex: 200,
              }}>
                <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--bg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
                      {user?.nombre || user?.email}
                    </span>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      color: '#02ff5f', fontSize: 11, fontWeight: 700, letterSpacing: .3,
                    }}>
                      Activo<CircleCheck size={13} />
                    </span>
                  </div>
                </div>
                {isAdmin && (
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
                    <LayoutDashboard size={16} color="var(--text)" />
                    Panel Administrador
                  </button>
                )}
                {!isAdmin && (
                  <button
                    onClick={() => { setUserMenuOpen(false); navigate('/mis-pedidos') }}
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
                    <ClipboardList size={16} color="var(--text)" />
                    Mis pedidos
                  </button>
                )}
                <button
                  onClick={() => { setUserMenuOpen(false); setSeguridadOpen(true) }}
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
                  <ShieldCheck size={16} color="var(--text)" />
                  Seguridad
                </button>
                <button
                  onClick={() => handlePedirLogout(() => setUserMenuOpen(false))}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                    padding: '12px 16px', border: 'none', background: 'none',
                    color: '#b60303', fontSize: 13, cursor: 'pointer',
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

          <div className="cart-icon" ref={cartMenuRef} style={{ position: 'relative', color: '#FBF7EE' }}>
            <button
              onClick={() => setCartOpen(v => !v)}
              aria-label="Carrito"
              aria-expanded={cartOpen}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                position: 'relative',
                display: 'inline-flex',
                alignItems: 'center',
                cursor: 'pointer',
                color: '#FBF7EE',
              }}
            >
              <ShoppingCart size={24} />
              {cantidadTotal > 0 && (
                <span className="cart-badge">{cantidadTotal}</span>
              )}
            </button>

            {cartOpen && (
              <div style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                background: 'var(--bg)',
                border: '1px solid var(--line)',
                borderRadius: 12,
                width: 380,
                maxWidth: '92vw',
                boxShadow: '0 12px 40px rgba(0, 0, 0, 0.25)',
                overflow: 'hidden',
                zIndex: 200,
                animation: 'toast-entrada 0.3s ease',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', borderBottom: '1px solid var(--bg)' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                    <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 18, color: 'var(--surface)' }}> Tu carrito</h1>
                    <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                      ({cantidadTotal} {cantidadTotal === 1 ? 'producto' : 'productos'})
                    </span>
                  </div>
                  <button
                    onClick={() => setCartOpen(false)}
                    aria-label="Cerrar carrito"
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: 2 }}
                  >
                    <X size={18} />
                  </button>
                </div>

                {!requiereLogin && items.length > 0 && (
                  <p style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 5, marginTop: -15, marginLeft: 15 }}>
                    (Los Productos en tu carrito no están reservados).
                  </p>
                )}

                <div className="separador-suave" style={{ display: 'flex', flexDirection: 'column', fontSize: 16, color: 'var(--text)' }}></div>

                <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                  {requiereLogin ? (
                    <div style={{ padding: '32px 16px', textAlign: 'center' }}>
                      <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: '0 0 14px' }}>
                        Inicia sesión para usar el carrito.
                      </p>
                      <button
                        className="btn btn-primary"
                        onClick={() => { setCartOpen(false); abrirLogin() }}
                        style={{ color: 'var(--text)' }}
                      >
                        Iniciar sesión
                      </button>
                    </div>
                  ) : items.length === 0 ? (
                    <div style={{ padding: '32px 16px', textAlign: 'center' }}>
                        <img
                        src={mediaPath('carritoVacio.png')}
                        alt="Logo"
                        style={{ display: 'block', height: 80, width: 'auto', margin: '0 auto 10px' }}
                    />
                      <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: '0 0 14px' }}>
                        Tu carrito está vacío.
                      </p>
                      <button
                        className="btn btn-primary"
                        onClick={() => { setCartOpen(false); navigate('/categorias') }}
                        style={{ color: 'var(--text)' }}
                      >
                        Ver catálogo
                      </button>
                    </div>
                  ) : (
                    items.map((item, index) => (
                      <div
                        key={item.itemId}
                        style={{
                          display: 'flex',
                          gap: 12,
                          padding: '12px 16px',
                          borderBottom: index < items.length - 1 ? '1px solid var(--surface-3)' : 'none',
                        }}
                      >
                        <div
                          style={{
                            width: 56,
                            height: 56,
                            borderRadius: 8,
                            overflow: 'hidden',
                            background: item.imagen ? '#FFFFFF' : 'var(--surface-2)',
                            flexShrink: 0,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          {item.imagen && (
                            <img
                              src={item.imagen}
                              alt={item.nombre}
                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                          )}
                        </div>

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                            <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--surface)', margin: '0 0 4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {item.nombre}
                            </p>
                            <button
                              type="button"
                              onClick={() => quitarItem(item.itemId)}
                              aria-label={`Quitar ${item.nombre} del carrito`}
                              title="Quitar producto"
                              style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 2, flexShrink: 0 }}
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                          <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 8px' }}>
                            ${item.precio.toLocaleString('es-CL')} c/u
                          </p>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                            <div style={{ display: 'flex', background: 'var(--bg)', alignItems: 'center', border: '1px solid var(--line)', borderRadius: 6, overflow: 'hidden' }}>
                              <button
                                type="button"
                                onClick={() => actualizarCantidadItem(item.itemId, Math.max(1, item.cantidad - 1))}
                                aria-label={`Reducir cantidad de ${item.nombre}`}
                                style={{
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  width: 26, height: 26, border: 'none', background: 'var(--surface-3)',
                                  color: 'inherit', cursor: 'pointer',
                                }}
                              >
                                <Minus size={13} style={{ color: 'var(--surface)' }} />
                              </button>
                              <span style={{ minWidth: 26, textAlign: 'center', fontSize: 13, color: 'var(--surface)' }}>
                                {item.cantidad}
                              </span>
                              <button
                                type="button"
                                onClick={() => actualizarCantidadItem(item.itemId, item.cantidad + 1)}
                                aria-label={`Aumentar cantidad de ${item.nombre}`}
                                style={{
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  width: 26, height: 26, border: 'none', background: 'var(--surface-3)',
                                  color: 'inherit', cursor: 'pointer',
                                }}
                              >
                                <Plus size={13} style={{ color: 'var(--surface)' }} />
                              </button>
                            </div>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 800, color: 'var(--surface-2)' }}>
                              ${(item.precio * item.cantidad).toLocaleString('es-CL')}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <div className="separador-suave" style={{ display: 'flex', flexDirection: 'column', fontSize: 16, color: 'var(--text)' }}></div>
                {!requiereLogin && items.length > 0 && (
                  <div style={{ padding: '14px 16px', borderTop: '1px solid var(--bg)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, fontWeight: 600, color: 'var(--surface)', marginBottom: 12 }}>
                      <span>Total</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>${total.toLocaleString('es-CL')} CLP</span>
                    </div>
                    <button
                      className="btn btn-primary"
                      onClick={() => { setCartOpen(false); navigate('/carrito') }}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, color: 'var(--text)', background: 'var(--surface)' }}
                    >
                      Continuar con la compra
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile menu overlay */}
      {createPortal(
        <div
          className={`nav-mobile-overlay ${mobileOpen ? 'open' : ''}`}
          onClick={() => setMobileOpen(false)}
        >
          <div className="nav-mobile-menu" onClick={e => e.stopPropagation()}>
            {/* Bloque superior: usuario o login + X a la derecha */}
            <div className="nm-header">
              <div className="nm-header-top">
                {isLoggedIn ? (
                  <div className="nm-user">
                    <User size={22} />
                    <span>{user?.nombre || user?.email}</span>
                  </div>
                ) : (
                  <div className="nm-user">
                    <User size={22} />
                    <span>¡Te damos la bienvenida!</span>
                  </div>
                )}
                <button className="nm-close" onClick={() => setMobileOpen(false)} aria-label="Cerrar menú">
                  <X size={24} />
                </button>
              </div>
              {!isLoggedIn && (
                <button className="nm-login" onClick={() => { setMobileOpen(false); abrirLogin() }}>
                  Inicia sesión
                </button>
              )}
            </div>

            {/* Mis pedidos (o panel admin) */}
            {isLoggedIn && (
              <div className="nm-section">
                {isAdmin ? (
                  <button className="nm-item" onClick={() => handleMobileNav('/admin')}>
                    <LayoutDashboard size={18} /> Panel admin
                  </button>
                ) : (
                  <button className="nm-item" onClick={() => handleMobileNav('/mis-pedidos')}>
                    <ClipboardList size={18} /> Mis pedidos
                  </button>
                )}
              </div>
            )}
            <div className="nm-section">
              <button className="nm-item" onClick={() => handleMobileNav('/cotizar')}>
                <Calculator size={18} /> Cotiza tu producto
              </button>
            </div>


            {/* Categorías */}
            <div className="nm-section">
              <div className="nm-title">Categorías</div>
              <button className="nm-item" onClick={() => handleMobileNav('/categorias')}>
                Ver todo el catálogo <ChevronRight size={18} className="nm-chevron" />
              </button>
              {categorias.map(c => (
                <button
                  key={c.id}
                  className="nm-item"
                  onClick={() => handleMobileNav(`/categorias?cat=${c.id}`)}
                >
                  {c.nombre} <ChevronRight size={18} className="nm-chevron" />
                </button>
              ))}
            </div>

            {/* Resto */}

            <div className="nm-section">
              {isLoggedIn && (
                <button className="nm-item" onClick={() => { setMobileOpen(false); setSeguridadOpen(true) }}>
                  <ShieldCheck size={18} /> Seguridad
                </button>
              )}
            </div>
             <div className="nm-section">
              <button className="nm-item" onClick={toggleTheme}>
                {theme === 'dark' ? <><Sun size={18} /> Modo claro</> : <><Moon size={18} /> Modo oscuro</>}
              </button>
            </div>
          </div> 
        </div>,
        document.body
      )}

      {solicitarLogin && (
        <LoginModal onClose={cerrarLogin} />
      )}

      {seguridadOpen && (
        <SeguridadModal onClose={() => setSeguridadOpen(false)} />
      )}


      {confirmarLogout && createPortal(
        <ConfirmModal
          onConfirm={handleLogout}
          onCancel={() => setConfirmarLogout(false)}
          mensaje="Vas a cerrar tu sesión en Apolo Vibes. ¿Seguro?"
        />,
        document.body
      )}
    </header>
  )
}
