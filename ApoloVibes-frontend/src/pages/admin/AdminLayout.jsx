import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { Menu, LogOut } from 'lucide-react'

const itemStyle = ({ isActive }) => ({
  display: 'block', padding: '10px 12px', borderRadius: 8, fontSize: 13, marginBottom: 2,
  color: isActive ? 'var(--text)' : 'var(--surface)',
  background: isActive ? 'var(--surface-3)' : 'transparent',
  fontWeight: isActive ? 600 : 400,
  textDecoration: 'none',
})

const sidebarBtnStyle = {
  display: 'block', width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 13,
  marginBottom: 2, color: '#b60303', background: 'transparent', border: 'none',
  textAlign: 'left', cursor: 'pointer', fontWeight: 500,
}

function ConfirmModal({ onConfirm, onCancel }) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.88)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)',
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: '#002a5e4b', borderRadius: 16, padding: '32px 28px',
          width: '100%', maxWidth: 360, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'center',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontSize: 36, marginBottom: 12 }}></div>
        <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
          Cerrar sesión
        </h3>
        <p style={{ margin: '0 0 22px', fontSize: 13, color: 'var(--text-dim)' }}>
          Vas a salir del panel de administración. ¿Seguro?
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
            No, quedarme
          </button>
          <button
            onClick={onConfirm}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: 'none',
              background: '#b60303', color: '#fff', fontSize: 13, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Sí, salir
          </button>
        </div>
      </div>
    </div>
  )
}

function SidebarContent({ onLogout }) {
  return (
    <>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, padding: '6px 10px 28px' }}>
        Apolo Vibes 3D
      </div>
      <nav style={{ flex: 1 }}>
        <NavLink to="/admin" end style={itemStyle}>Dashboard</NavLink>
        <NavLink to="/admin/pedidos" style={itemStyle}>Pedidos</NavLink>
        <NavLink to="/admin/inventario" style={itemStyle}>Inventario</NavLink>
        <NavLink to="/admin/cotizaciones" style={itemStyle}>Cotizaciones</NavLink>
        <NavLink to="/admin/venta" style={itemStyle}>Registrar Venta</NavLink>
      </nav>
      <button style={sidebarBtnStyle} onClick={onLogout}> <LogOut size={16} />
        Cerrar sesión
      </button>
    </>
  )
}

export default function AdminLayout() {
  const [showConfirm, setShowConfirm] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    setShowConfirm(false)
    setSidebarOpen(false)
    logout()
    navigate('/')
  }

  return (
    <div className="admin-layout" style={{ display: 'grid', gridTemplateColumns: '238px 1fr', minHeight: '100vh' }}>
      {/* Desktop sidebar */}
      <aside className="hide-mobile" style={{
        background: 'var(--accent)', borderRight: '1px solid var(--line)',
        padding: '24px 18px', display: 'flex', flexDirection: 'column',
      }}>
        <SidebarContent onLogout={() => setShowConfirm(true)} />
      </aside>

      {/* Mobile sidebar overlay */}
      <div
        className={`admin-sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />
      <aside className={`admin-sidebar ${sidebarOpen ? 'open' : ''}`} style={{
        background: 'var(--accent)', borderRight: '1px solid var(--line)',
        padding: '24px 18px', flexDirection: 'column',
      }}>
        <SidebarContent onLogout={() => setShowConfirm(true)} />
      </aside>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <header className="admin-topbar" style={{
          display: 'none', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px', borderBottom: '1px solid var(--line)',
          background: 'var(--accent)',
        }}>
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Abrir menú"
            style={{ background: 'none', border: 'none', color: 'var(--text)', cursor: 'pointer', padding: 4 }}
          >
            <Menu size={22} />
          </button>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>
            Apolo Vibes 3D
          </span>
          <div style={{ width: 30 }} />
        </header>

        <header className="hide-mobile" style={{
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
          padding: '16px 34px', borderBottom: '1px solid var(--accent)',
          background: 'var(--accent)',
        }}>
          <button
            title="Mi cuenta"
            style={{
              width: 36, height: 36, borderRadius: '50%', border: '1px solid var(--surface-3)',
              background: 'var(--accent-2)', display: 'flex', alignItems: 'center',
              justifyContent: 'center', cursor: 'pointer', color: 'var(--text-dim)',
              transition: 'border-color .2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--line)'}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </button>
        </header>

        <main style={{ padding: '28px 34px', flex: 1 }}>
          <Outlet />
        </main>
      </div>

      {showConfirm && <ConfirmModal onConfirm={handleLogout} onCancel={() => setShowConfirm(false)} />}
    </div>
  )
}
